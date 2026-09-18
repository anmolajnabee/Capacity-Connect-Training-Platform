"""Admin control centre: organization totals, users, approvals and roles."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    Announcement,
    ApprovalRequest,
    ApprovalStatus,
    Assessment,
    AssessmentAttempt,
    AssessmentResult,
    Certificate,
    Course,
    CourseStatus,
    CourseTrainerAssignment,
    Enrollment,
    EnrollmentStatus,
    LearningResource,
    Skill,
    User,
    UserRole,
)
from app.states.auth_state import AuthState
from app.security import read_session
from app.services.email_notifications import enqueue

logger = logging.getLogger(__name__)

ROLE_OPTIONS: list[str] = [
    UserRole.TRAINEE.value,
    UserRole.TRAINER.value,
    UserRole.ADMIN.value,
]
ROLE_FILTERS: list[str] = ["All"] + ROLE_OPTIONS
STATUS_FILTERS: list[str] = [
    "All",
    ApprovalStatus.PENDING.value,
    ApprovalStatus.APPROVED.value,
    ApprovalStatus.REJECTED.value,
    ApprovalStatus.SUSPENDED.value,
]

TOTAL_KEYS: list[str] = [
    "users",
    "trainees",
    "trainers",
    "admins",
    "pending",
    "suspended",
    "inactive",
    "courses",
    "published_courses",
    "draft_courses",
    "skills",
    "resources",
    "enrollments",
    "completions",
    "assessments",
    "attempts",
    "results",
    "passes",
    "certificates",
    "announcements",
    "assignments",
]


async def admin_guard(state: rx.State) -> int:
    """Return the authenticated, approved administrator id, or 0."""
    auth = await state.get_state(AuthState)
    uid = read_session(auth.session_cookie)
    if uid <= 0:
        return 0
    async with rx.asession() as session:
        return int(
            await session.scalar(
                select(User.id).where(
                    User.id == uid,
                    User.role == "admin",
                    User.is_active.is_(True),
                    User.approval_status == "approved",
                )
            )
            or 0
        )


def stamp(value: dt.datetime | None) -> str:
    if value is None:
        return "—"
    moment = value if value.tzinfo else value.replace(tzinfo=dt.UTC)
    return moment.strftime("%d %b %Y, %H:%M UTC")


def day_stamp(value: dt.date | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d %b %Y")


class UserRow(TypedDict):
    id: int
    name: str
    email: str
    phone: str
    role: str
    requested_role: str
    approval_status: str
    is_active: bool
    last_login: str
    joined: str
    audit: str
    note: str
    is_self: bool


class AdminState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    totals: dict[str, int] = {key: 0 for key in TOTAL_KEYS}
    users: list[UserRow] = []
    search_query: str = ""
    role_filter: str = "All"
    status_filter: str = "All"

    @rx.var
    def role_choices(self) -> list[str]:
        return ROLE_OPTIONS

    @rx.var
    def role_filter_options(self) -> list[str]:
        return ROLE_FILTERS

    @rx.var
    def status_filter_options(self) -> list[str]:
        return STATUS_FILTERS

    @rx.var
    def filtered_users(self) -> list[UserRow]:
        query = self.search_query.strip().lower()
        rows: list[UserRow] = []
        for row in self.users:
            if self.role_filter != "All" and row["role"] != self.role_filter:
                continue
            if (
                self.status_filter != "All"
                and row["approval_status"] != self.status_filter
            ):
                continue
            if query and query not in (
                f"{row['name']} {row['email']} {row['phone']}".lower()
            ):
                continue
            rows.append(row)
        return rows

    @rx.var
    def pending_users(self) -> list[UserRow]:
        return [
            row
            for row in self.users
            if row["approval_status"] == ApprovalStatus.PENDING.value
        ]

    @rx.var
    def pending_count(self) -> int:
        return len(self.pending_users)

    @rx.var
    def completion_rate(self) -> float:
        enrolled = self.totals.get("enrollments", 0)
        if not enrolled:
            return 0.0
        return self.totals.get("completions", 0) * 100 / enrolled

    @rx.var
    def pass_rate(self) -> float:
        results = self.totals.get("results", 0)
        if not results:
            return 0.0
        return self.totals.get("passes", 0) * 100 / results

    # ------------------------------------------------------------- filters
    @rx.event
    def set_search_query(self, value: str):
        self.search_query = value

    @rx.event
    def set_role_filter(self, value: str):
        self.role_filter = value

    @rx.event
    def set_status_filter(self, value: str):
        self.status_filter = value

    @rx.event
    def clear_filters(self):
        self.search_query = ""
        self.role_filter = "All"
        self.status_filter = "All"

    # --------------------------------------------------------------- loads
    @rx.event
    async def load_control_centre(self):
        self.error_message = ""
        self.success_message = ""
        admin_id = await admin_guard(self)
        if admin_id == 0:
            self.error_message = "Administrator access is required."
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load_totals(session)
                await self._load_users(session, admin_id)
        except Exception as exception:
            logging.exception(f"Error loading control centre: {exception}")
            self.error_message = "Could not load the control centre data."
        self.is_loading = False

    async def _count(self, session, model, *conditions) -> int:
        statement = select(func.count()).select_from(model)
        if conditions:
            statement = statement.where(*conditions)
        return int(await session.scalar(statement) or 0)

    async def _load_totals(self, session) -> None:
        totals = {key: 0 for key in TOTAL_KEYS}
        totals["users"] = await self._count(session, User)
        totals["trainees"] = await self._count(
            session, User, User.role == UserRole.TRAINEE.value
        )
        totals["trainers"] = await self._count(
            session, User, User.role == UserRole.TRAINER.value
        )
        totals["admins"] = await self._count(
            session, User, User.role == UserRole.ADMIN.value
        )
        totals["pending"] = await self._count(
            session,
            User,
            User.approval_status == ApprovalStatus.PENDING.value,
        )
        totals["suspended"] = await self._count(
            session,
            User,
            User.approval_status == ApprovalStatus.SUSPENDED.value,
        )
        totals["inactive"] = await self._count(
            session, User, User.is_active.is_(False)
        )
        totals["courses"] = await self._count(session, Course)
        totals["published_courses"] = await self._count(
            session, Course, Course.status == CourseStatus.PUBLISHED.value
        )
        totals["draft_courses"] = await self._count(
            session, Course, Course.status == CourseStatus.DRAFT.value
        )
        totals["skills"] = await self._count(session, Skill)
        totals["resources"] = await self._count(session, LearningResource)
        totals["enrollments"] = await self._count(session, Enrollment)
        totals["completions"] = await self._count(
            session,
            Enrollment,
            Enrollment.status == EnrollmentStatus.COMPLETED.value,
        )
        totals["assessments"] = await self._count(session, Assessment)
        totals["attempts"] = await self._count(session, AssessmentAttempt)
        totals["results"] = await self._count(session, AssessmentResult)
        totals["passes"] = await self._count(
            session, AssessmentResult, AssessmentResult.is_passed.is_(True)
        )
        totals["certificates"] = await self._count(
            session, Certificate, Certificate.is_revoked.is_(False)
        )
        totals["announcements"] = await self._count(session, Announcement)
        totals["assignments"] = await self._count(
            session, CourseTrainerAssignment
        )
        self.totals = totals

    async def _load_users(self, session, admin_id: int) -> None:
        audits = (
            await session.execute(
                select(ApprovalRequest).order_by(ApprovalRequest.created_at)
            )
        ).scalars()
        latest: dict[int, ApprovalRequest] = {}
        for record in audits:
            latest[record.user_id] = record
        people = (
            await session.execute(select(User).order_by(User.full_name))
        ).scalars()
        rows: list[UserRow] = []
        for user in people:
            record = latest.get(user.id)
            audit = "No approval record"
            note = ""
            requested = user.role
            if record is not None:
                requested = record.requested_role
                note = record.note
                if record.decided_at is not None:
                    audit = f"{record.status} · {stamp(record.decided_at)}"
                else:
                    audit = (
                        f"awaiting decision · raised {stamp(record.created_at)}"
                    )
            rows.append(
                {
                    "id": user.id,
                    "name": user.full_name,
                    "email": user.email,
                    "phone": user.phone or "—",
                    "role": user.role,
                    "requested_role": requested,
                    "approval_status": user.approval_status,
                    "is_active": user.is_active,
                    "last_login": stamp(user.last_login_at),
                    "joined": stamp(user.created_at),
                    "audit": audit,
                    "note": note,
                    "is_self": user.id == admin_id,
                }
            )
        self.users = rows

    # ----------------------------------------------------------- mutations
    async def _decide(
        self, user_id: int, approve: bool, note: str
    ) -> str | None:
        """Apply an approval decision. Returns an error message or None."""
        admin_id = await admin_guard(self)
        if admin_id == 0:
            return "Only an approved administrator may record decisions."
        now = dt.datetime.now(dt.UTC)
        async with rx.asession() as session:
            user = await session.get(User, user_id)
            if user is None:
                return "That account no longer exists."
            if user.id == admin_id and not approve:
                return "You cannot reject your own administrator account."
            target_status = "approved" if approve else "rejected"
            if user.approval_status == target_status:
                return None
            if approve:
                user.is_active = True
            await enqueue(
                session,
                "account_approval",
                user,
                f"{target_status}/{now.isoformat()}",
            )
            user.approval_status = (
                ApprovalStatus.APPROVED.value
                if approve
                else ApprovalStatus.REJECTED.value
            )
            user.is_active = approve
            record = await session.scalar(
                select(ApprovalRequest)
                .where(ApprovalRequest.user_id == user_id)
                .order_by(ApprovalRequest.created_at.desc())
            )
            if record is None:
                record = ApprovalRequest(
                    user_id=user_id,
                    requested_role=user.role,
                    status=user.approval_status,
                    note=note,
                )
                session.add(record)
            record.status = user.approval_status
            record.note = note or record.note
            record.decided_by_id = admin_id
            record.decided_at = now
            await session.commit()
        return None

    @rx.event
    async def record_decision(self, user_id: int, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        decision = str(form_data.get("decision", "approve")).strip()
        note = str(form_data.get("note", "")).strip()
        if decision not in ("approve", "reject"):
            self.error_message = "Choose approve or reject."
            return
        if decision == "reject" and len(note) < 5:
            self.error_message = (
                "A rejection needs a decision note of at least 5 characters."
            )
            return
        try:
            problem = await self._decide(user_id, decision == "approve", note)
        except Exception as exception:
            logging.exception(f"Error recording decision: {exception}")
            self.error_message = "Could not record that decision. Try again."
            return
        if problem:
            self.error_message = problem
            return
        self.success_message = (
            "Access approved and the account activated."
            if decision == "approve"
            else "Access request declined and recorded in the audit trail."
        )
        return AdminState.load_control_centre

    @rx.event
    async def set_account_state(self, user_id: int, suspend: bool):
        self.error_message = ""
        self.success_message = ""
        admin_id = await admin_guard(self)
        if admin_id == 0:
            self.error_message = (
                "Only an approved administrator may change account status."
            )
            return
        if suspend and user_id == admin_id:
            self.error_message = "You cannot suspend your own account."
            return
        try:
            async with rx.asession() as session:
                user = await session.get(User, user_id)
                if user is None:
                    self.error_message = "That account no longer exists."
                    return
                target_status = "suspended" if suspend else "approved"
                if user.approval_status == target_status:
                    return
                if not suspend:
                    user.is_active = True
                await enqueue(
                    session,
                    "account_status",
                    user,
                    f"{target_status}/{dt.datetime.now(dt.UTC).isoformat()}",
                )
                if suspend:
                    user.approval_status = ApprovalStatus.SUSPENDED.value
                    user.is_active = False
                else:
                    user.approval_status = ApprovalStatus.APPROVED.value
                    user.is_active = True
                await session.commit()
        except Exception as exception:
            logging.exception(f"Error changing account state: {exception}")
            self.error_message = "Could not change that account. Try again."
            return
        self.success_message = (
            "Account suspended." if suspend else "Account reinstated."
        )
        return AdminState.load_control_centre

    @rx.event
    async def change_role(self, user_id: int, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        new_role = str(form_data.get("role", "")).strip()
        note = str(form_data.get("role_note", "")).strip()
        if new_role not in ROLE_OPTIONS:
            self.error_message = "Choose a valid role."
            return
        admin_id = await admin_guard(self)
        if admin_id == 0:
            self.error_message = (
                "Only an approved administrator may change roles."
            )
            return
        if user_id == admin_id and new_role != UserRole.ADMIN.value:
            self.error_message = (
                "You cannot remove your own administrator role."
            )
            return
        try:
            async with rx.asession() as session:
                user = await session.get(User, user_id)
                if user is None:
                    self.error_message = "That account no longer exists."
                    return
                if user.role == new_role:
                    self.error_message = (
                        f"{user.full_name} already holds the {new_role} role."
                    )
                    return
                if user.role == UserRole.ADMIN.value:
                    remaining = int(
                        await session.scalar(
                            select(func.count())
                            .select_from(User)
                            .where(
                                User.role == UserRole.ADMIN.value,
                                User.id != user.id,
                                User.approval_status
                                == ApprovalStatus.APPROVED.value,
                            )
                        )
                        or 0
                    )
                    if remaining == 0:
                        self.error_message = (
                            "At least one approved administrator must remain."
                        )
                        return
                previous = user.role
                user.role = new_role
                session.add(
                    ApprovalRequest(
                        user_id=user.id,
                        requested_role=new_role,
                        status=user.approval_status,
                        decided_by_id=admin_id,
                        decided_at=dt.datetime.now(dt.UTC),
                        note=note
                        or f"Role changed from {previous} to {new_role}.",
                    )
                )
                await session.commit()
                changed_name = user.full_name
        except Exception as exception:
            logging.exception(f"Error changing role: {exception}")
            self.error_message = "Could not change that role. Try again."
            return
        self.success_message = f"{changed_name} is now a {new_role}."
        return AdminState.load_control_centre

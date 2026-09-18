"""Role management operations: permission scopes, workload context, audit."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    ApprovalRequest,
    ApprovalStatus,
    Assessment,
    Certificate,
    CourseTrainerAssignment,
    Enrollment,
    EnrollmentStatus,
    User,
    UserRole,
)
from app.states.admin_state import ROLE_OPTIONS, admin_guard, stamp

logger = logging.getLogger(__name__)

ROLE_RANK: dict[str, int] = {
    UserRole.TRAINEE.value: 1,
    UserRole.TRAINER.value: 2,
    UserRole.ADMIN.value: 3,
}


class RoleContextRow(TypedDict):
    id: int
    name: str
    email: str
    role: str
    approval_status: str
    is_active: bool
    is_self: bool
    enrollments: int
    completions: int
    certificates: int
    courses: int
    cohort: int
    last_activity: str
    context: str
    impact: str
    guardrail: str


class AuditEntry(TypedDict):
    id: int
    name: str
    email: str
    requested_role: str
    status: str
    note: str
    decided: str
    decided_by: str
    pending: bool


class AdminRoleOpsState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    context_rows: list[RoleContextRow] = []
    audit_entries: list[AuditEntry] = []
    role_query: str = ""
    role_scope_filter: str = "All"

    counts: dict[str, int] = {
        "trainees": 0,
        "trainers": 0,
        "admins": 0,
        "pending": 0,
        "suspended": 0,
        "inactive": 0,
        "trainers_without_course": 0,
        "trainees_without_enrollment": 0,
        "role_decisions": 0,
    }

    @rx.var
    def role_scope_options(self) -> list[str]:
        return ["All"] + ROLE_OPTIONS

    @rx.var
    def role_choices(self) -> list[str]:
        return ROLE_OPTIONS

    @rx.var
    def filtered_context(self) -> list[RoleContextRow]:
        query = self.role_query.strip().lower()
        rows: list[RoleContextRow] = []
        for row in self.context_rows:
            if (
                self.role_scope_filter != "All"
                and row["role"] != self.role_scope_filter
            ):
                continue
            if query and query not in f"{row['name']} {row['email']}".lower():
                continue
            rows.append(row)
        return rows

    @rx.event
    def set_role_query(self, value: str):
        self.role_query = value

    @rx.event
    def set_role_scope_filter(self, value: str):
        self.role_scope_filter = value

    # ---------------------------------------------------------------- load
    @rx.event
    async def load_role_operations(self):
        self.error_message = ""
        admin_id = await admin_guard(self)
        if admin_id == 0:
            self.error_message = "Administrator access is required."
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load_counts(session)
                await self._load_context(session, admin_id)
                await self._load_audit(session)
        except Exception as exception:
            logging.exception(f"Error loading role operations: {exception}")
            self.error_message = "Could not load role management data."
        self.is_loading = False

    async def _count(self, session, model, *conditions) -> int:
        statement = select(func.count()).select_from(model)
        if conditions:
            statement = statement.where(*conditions)
        return int(await session.scalar(statement) or 0)

    async def _load_counts(self, session) -> None:
        counts = {
            "trainees": await self._count(
                session, User, User.role == UserRole.TRAINEE.value
            ),
            "trainers": await self._count(
                session, User, User.role == UserRole.TRAINER.value
            ),
            "admins": await self._count(
                session, User, User.role == UserRole.ADMIN.value
            ),
            "pending": await self._count(
                session,
                User,
                User.approval_status == ApprovalStatus.PENDING.value,
            ),
            "suspended": await self._count(
                session,
                User,
                User.approval_status == ApprovalStatus.SUSPENDED.value,
            ),
            "inactive": await self._count(
                session, User, User.is_active.is_(False)
            ),
            "trainers_without_course": 0,
            "trainees_without_enrollment": 0,
            "role_decisions": await self._count(session, ApprovalRequest),
        }
        staffed = select(CourseTrainerAssignment.trainer_id).distinct()
        counts["trainers_without_course"] = await self._count(
            session,
            User,
            User.role == UserRole.TRAINER.value,
            User.id.not_in(staffed),
        )
        enrolled = (
            select(Enrollment.trainee_id)
            .where(Enrollment.status == EnrollmentStatus.ACTIVE.value)
            .distinct()
        )
        counts["trainees_without_enrollment"] = await self._count(
            session,
            User,
            User.role == UserRole.TRAINEE.value,
            User.id.not_in(enrolled),
        )
        self.counts = counts

    async def _load_context(self, session, admin_id: int) -> None:
        people = (
            (
                await session.execute(
                    select(User).order_by(User.role, User.full_name).limit(200)
                )
            )
            .scalars()
            .all()
        )
        rows: list[RoleContextRow] = []
        for user in people:
            enrollments = await self._count(
                session, Enrollment, Enrollment.trainee_id == user.id
            )
            completions = await self._count(
                session,
                Enrollment,
                Enrollment.trainee_id == user.id,
                Enrollment.status == EnrollmentStatus.COMPLETED.value,
            )
            certificates = await self._count(
                session, Certificate, Certificate.trainee_id == user.id
            )
            courses = await self._count(
                session,
                CourseTrainerAssignment,
                CourseTrainerAssignment.trainer_id == user.id,
            )
            cohort = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Enrollment)
                    .join(
                        CourseTrainerAssignment,
                        CourseTrainerAssignment.course_id
                        == Enrollment.course_id,
                    )
                    .where(CourseTrainerAssignment.trainer_id == user.id)
                )
                or 0
            )
            authored = await self._count(
                session, Assessment, Assessment.created_by_id == user.id
            )
            if user.role == UserRole.TRAINEE.value:
                context = (
                    f"{enrollments} enrolments · {completions} completed · "
                    f"{certificates} certificates"
                )
                impact = (
                    "Promotion to trainer keeps the learning history but grants "
                    "content upload, assessment authoring and cohort visibility."
                )
            elif user.role == UserRole.TRAINER.value:
                context = (
                    f"{courses} assigned courses · {cohort} trainees in cohort · "
                    f"{authored} assessments authored"
                )
                impact = (
                    f"Demotion to trainee removes access to {courses} course "
                    f"workspaces and {cohort} trainee records. Staffing "
                    "assignments must be reallocated."
                    if courses
                    else "No live staffing — a role change has no delivery impact."
                )
            else:
                context = f"Last session {stamp(user.last_login_at)}"
                impact = (
                    "Demotion withdraws approval powers, role changes, "
                    "announcement publishing and full registry oversight."
                )
            rows.append(
                {
                    "id": user.id,
                    "name": user.full_name,
                    "email": user.email,
                    "role": user.role,
                    "approval_status": user.approval_status,
                    "is_active": user.is_active,
                    "is_self": user.id == admin_id,
                    "enrollments": enrollments,
                    "completions": completions,
                    "certificates": certificates,
                    "courses": courses,
                    "cohort": cohort,
                    "last_activity": stamp(user.last_login_at),
                    "context": context,
                    "impact": impact,
                    "guardrail": (
                        "Your own administrator role is locked."
                        if user.id == admin_id
                        else "A written reason of at least 10 characters is required."
                    ),
                }
            )
        self.context_rows = rows

    async def _load_audit(self, session) -> None:
        triples = (
            await session.execute(
                select(ApprovalRequest, User)
                .join(User, User.id == ApprovalRequest.user_id)
                .order_by(ApprovalRequest.created_at.desc())
                .limit(25)
            )
        ).all()
        entries: list[AuditEntry] = []
        for record, user in triples:
            decider = (
                await session.scalar(
                    select(User.full_name).where(
                        User.id == record.decided_by_id
                    )
                )
                if record.decided_by_id
                else None
            ) or "Awaiting an administrator"
            entries.append(
                {
                    "id": record.id,
                    "name": user.full_name,
                    "email": user.email,
                    "requested_role": record.requested_role,
                    "status": record.status,
                    "note": record.note or "No reason recorded.",
                    "decided": stamp(record.decided_at or record.created_at),
                    "decided_by": decider,
                    "pending": record.decided_at is None,
                }
            )
        self.audit_entries = entries

    # ----------------------------------------------------------- mutations
    @rx.event
    async def apply_role(self, user_id: int, form_data: dict[str, Any]):
        """Change a role with a mandatory reason, preserving all guardrails."""
        self.error_message = ""
        self.success_message = ""
        new_role = str(form_data.get("role", "")).strip()
        reason = str(form_data.get("reason", "")).strip()
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
                "Self-demotion is blocked. Ask another administrator."
            )
            return
        if len(reason) < 10:
            self.error_message = (
                "Privilege escalation and demotion both need a written reason "
                "of at least 10 characters."
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
                    remaining = await self._count(
                        session,
                        User,
                        User.role == UserRole.ADMIN.value,
                        User.id != user.id,
                        User.approval_status == ApprovalStatus.APPROVED.value,
                    )
                    if remaining == 0:
                        self.error_message = (
                            "At least one approved administrator must remain."
                        )
                        return
                previous = user.role
                direction = (
                    "escalation"
                    if ROLE_RANK.get(new_role, 0) > ROLE_RANK.get(previous, 0)
                    else "demotion"
                )
                user.role = new_role
                session.add(
                    ApprovalRequest(
                        user_id=user.id,
                        requested_role=new_role,
                        status=user.approval_status,
                        decided_by_id=admin_id,
                        decided_at=dt.datetime.now(dt.UTC),
                        note=(
                            f"Role {direction}: {previous} → {new_role}. "
                            f"Reason: {reason}"
                        ),
                    )
                )
                await session.commit()
                name = user.full_name
        except Exception as exception:
            logging.exception(f"Error applying role change: {exception}")
            self.error_message = "Could not change that role. Try again."
            return
        self.success_message = (
            f"{name} is now a {new_role}. The {direction} and its reason are "
            "recorded in the approval audit trail."
        )
        return AdminRoleOpsState.load_role_operations

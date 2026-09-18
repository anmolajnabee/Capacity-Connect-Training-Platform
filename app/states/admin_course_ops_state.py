"""Course lifecycle control and trainer staffing operations for admins."""

from __future__ import annotations

import logging
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    ApprovalStatus,
    Assessment,
    Certificate,
    Course,
    CourseAssignment,
    CourseRequiredSkill,
    CourseStatus,
    CourseTrainerAssignment,
    Enrollment,
    EnrollmentStatus,
    LearningResource,
    TrainerAssignmentRole,
    TrainerProfile,
    User,
    UserRole,
    UserSkill,
)
from app.states.admin_competency_state import LEVEL_TARGET
from app.states.admin_oversight_state import AdminOversightState
from app.states.admin_state import admin_guard, day_stamp

logger = logging.getLogger(__name__)

TRANSITIONS: dict[str, tuple[str, str, str]] = {
    CourseStatus.DRAFT.value: (
        CourseStatus.PUBLISHED.value,
        "Publish course",
        "Publishing opens the course for nomination and makes it visible on the public catalogue.",
    ),
    CourseStatus.PUBLISHED.value: (
        CourseStatus.ARCHIVED.value,
        "Archive course",
        "Archiving closes new nominations. Existing enrolments, results and certificates are retained.",
    ),
    CourseStatus.ARCHIVED.value: (
        CourseStatus.DRAFT.value,
        "Return to draft",
        "Returning to draft lets the secretariat revise content, dates and staffing before republishing.",
    ),
}

ASSIGNMENT_ROLES: list[str] = [
    TrainerAssignmentRole.LEAD.value,
    TrainerAssignmentRole.CO_TRAINER.value,
    TrainerAssignmentRole.GUEST.value,
]


class CheckRow(TypedDict):
    label: str
    detail: str
    passed: bool


class CourseOpsRow(TypedDict):
    id: int
    code: str
    title: str
    status: str
    category: str
    window: str
    deadline: str
    capacity: int
    duration: float
    enrolled: int
    active: int
    completed: int
    at_risk: int
    fill: int
    completion: int
    published_resources: int
    total_resources: int
    assessments: int
    assignments: int
    certificates: int
    trainer_count: int
    lead_count: int
    trainers: str
    readiness: int
    checks: list[CheckRow]
    blockers: list[str]
    target: str
    next_label: str
    next_hint: str
    blocked: bool


class StaffingRow(TypedDict):
    id: int
    course_id: int
    course: str
    code: str
    course_status: str
    trainer_id: int
    trainer: str
    email: str
    designation: str
    assignment_role: str
    status: str
    match_score: float
    cohort: int
    trainer_courses: int
    note: str
    assigned_by: str


class CourseChoiceRow(TypedDict):
    id: int
    label: str
    status: str
    trainer_count: int


class TrainerChoiceRow(TypedDict):
    id: int
    label: str
    courses: int
    cohort: int
    available: bool


class AdminCourseOpsState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    course_rows: list[CourseOpsRow] = []
    staffing_rows: list[StaffingRow] = []
    course_choices: list[CourseChoiceRow] = []
    trainer_choices: list[TrainerChoiceRow] = []

    confirm_course_id: int = 0
    confirm_target: str = ""

    lifecycle_filter: str = "All"

    metrics: dict[str, int] = {
        "publish_ready": 0,
        "blocked": 0,
        "unstaffed": 0,
        "understaffed": 0,
        "archived": 0,
    }

    @rx.var
    def lifecycle_options(self) -> list[str]:
        return ["All", "draft", "published", "archived"]

    @rx.var
    def assignment_role_options(self) -> list[str]:
        return ASSIGNMENT_ROLES

    @rx.var
    def filtered_course_rows(self) -> list[CourseOpsRow]:
        if self.lifecycle_filter == "All":
            return self.course_rows
        return [
            row
            for row in self.course_rows
            if row["status"] == self.lifecycle_filter
        ]

    @rx.var
    def unstaffed_choices(self) -> list[CourseChoiceRow]:
        return [row for row in self.course_choices if row["trainer_count"] < 2]

    @rx.event
    def set_lifecycle_filter(self, value: str):
        self.lifecycle_filter = value

    @rx.event
    def request_transition(self, course_id: int, target: str):
        self.error_message = ""
        self.success_message = ""
        self.confirm_course_id = course_id
        self.confirm_target = target

    @rx.event
    def cancel_transition(self):
        self.confirm_course_id = 0
        self.confirm_target = ""

    # ---------------------------------------------------------------- load
    @rx.event
    async def load_course_ops(self):
        self.error_message = ""
        if await admin_guard(self) == 0:
            self.error_message = "Administrator access is required."
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load_courses(session)
                await self._load_staffing(session)
        except Exception as exception:
            logging.exception(f"Error loading course operations: {exception}")
            self.error_message = "Could not load course lifecycle data."
        self.is_loading = False

    async def _count(self, session, model, *conditions) -> int:
        statement = select(func.count()).select_from(model)
        if conditions:
            statement = statement.where(*conditions)
        return int(await session.scalar(statement) or 0)

    async def _evaluate(
        self, session, course: Course
    ) -> tuple[list[CheckRow], list[str], dict[str, int]]:
        trainer_count = await self._count(
            session,
            CourseTrainerAssignment,
            CourseTrainerAssignment.course_id == course.id,
        )
        lead_count = await self._count(
            session,
            CourseTrainerAssignment,
            CourseTrainerAssignment.course_id == course.id,
            CourseTrainerAssignment.assignment_role
            == TrainerAssignmentRole.LEAD.value,
        )
        published_resources = await self._count(
            session,
            LearningResource,
            LearningResource.course_id == course.id,
            LearningResource.is_published.is_(True),
        )
        total_resources = await self._count(
            session,
            LearningResource,
            LearningResource.course_id == course.id,
        )
        dates_ok = (
            course.start_date is not None
            and course.end_date is not None
            and course.end_date >= course.start_date
        )
        deadline_ok = (
            course.enrollment_deadline is not None
            and course.start_date is not None
            and course.enrollment_deadline <= course.start_date
        )
        checks: list[CheckRow] = [
            {
                "label": "Trainer assigned",
                "detail": (
                    f"{trainer_count} trainer(s) on the delivery team, "
                    f"{lead_count} lead."
                    if trainer_count
                    else "No trainer is accountable for delivery yet."
                ),
                "passed": trainer_count > 0,
            },
            {
                "label": "Published learning resource",
                "detail": (
                    f"{published_resources} of {total_resources} resources are published."
                    if total_resources
                    else "The trainer library holds no material for this course."
                ),
                "passed": published_resources > 0,
            },
            {
                "label": "Valid delivery window",
                "detail": (
                    f"{day_stamp(course.start_date)} → {day_stamp(course.end_date)}"
                    if dates_ok
                    else "Start and end dates are missing or out of order."
                ),
                "passed": dates_ok,
            },
            {
                "label": "Nomination deadline on or before start",
                "detail": (
                    f"Closes {day_stamp(course.enrollment_deadline)}"
                    if deadline_ok
                    else "Set a nomination deadline that falls on or before the start date."
                ),
                "passed": deadline_ok,
            },
            {
                "label": "Positive capacity",
                "detail": f"{course.capacity} seats"
                if course.capacity > 0
                else "Capacity must be greater than zero.",
                "passed": course.capacity > 0,
            },
            {
                "label": "Positive duration",
                "detail": f"{float(course.duration_hours):.1f} contact hours"
                if course.duration_hours > 0
                else "Record the contact hours for this programme.",
                "passed": float(course.duration_hours) > 0,
            },
        ]
        blockers = [
            f"{row['label']} — {row['detail']}"
            for row in checks
            if not row["passed"]
        ]
        counts = {
            "trainer_count": trainer_count,
            "lead_count": lead_count,
            "published_resources": published_resources,
            "total_resources": total_resources,
        }
        return checks, blockers, counts

    async def _load_courses(self, session) -> None:
        rows: list[CourseOpsRow] = []
        metrics = {
            "publish_ready": 0,
            "blocked": 0,
            "unstaffed": 0,
            "understaffed": 0,
            "archived": 0,
        }
        courses = (
            (await session.execute(select(Course).order_by(Course.code)))
            .scalars()
            .all()
        )
        choices: list[CourseChoiceRow] = []
        for course in courses:
            checks, blockers, counts = await self._evaluate(session, course)
            enrolled = await self._count(
                session, Enrollment, Enrollment.course_id == course.id
            )
            active = await self._count(
                session,
                Enrollment,
                Enrollment.course_id == course.id,
                Enrollment.status == EnrollmentStatus.ACTIVE.value,
            )
            completed = await self._count(
                session,
                Enrollment,
                Enrollment.course_id == course.id,
                Enrollment.status == EnrollmentStatus.COMPLETED.value,
            )
            at_risk = await self._count(
                session,
                Enrollment,
                Enrollment.course_id == course.id,
                Enrollment.status == EnrollmentStatus.AT_RISK.value,
            )
            assessments = await self._count(
                session, Assessment, Assessment.course_id == course.id
            )
            assignments = await self._count(
                session,
                CourseAssignment,
                CourseAssignment.course_id == course.id,
            )
            certificates = await self._count(
                session, Certificate, Certificate.course_id == course.id
            )
            trainer_names = list(
                (
                    await session.execute(
                        select(User.full_name)
                        .join(
                            CourseTrainerAssignment,
                            CourseTrainerAssignment.trainer_id == User.id,
                        )
                        .where(CourseTrainerAssignment.course_id == course.id)
                        .order_by(User.full_name)
                    )
                )
                .scalars()
                .all()
            )
            target, label, hint = TRANSITIONS.get(
                course.status,
                (CourseStatus.DRAFT.value, "Return to draft", ""),
            )
            blocked = (
                target == CourseStatus.PUBLISHED.value and len(blockers) > 0
            )
            passed = len([row for row in checks if row["passed"]])
            readiness = int(round(passed * 100 / len(checks))) if checks else 0
            if course.status == CourseStatus.DRAFT.value and not blockers:
                metrics["publish_ready"] += 1
            if course.status == CourseStatus.DRAFT.value and blockers:
                metrics["blocked"] += 1
            if counts["trainer_count"] == 0:
                metrics["unstaffed"] += 1
            elif counts["trainer_count"] == 1:
                metrics["understaffed"] += 1
            if course.status == CourseStatus.ARCHIVED.value:
                metrics["archived"] += 1
            rows.append(
                {
                    "id": course.id,
                    "code": course.code,
                    "title": course.title,
                    "status": course.status,
                    "category": course.category or "General",
                    "window": (
                        f"{day_stamp(course.start_date)} → {day_stamp(course.end_date)}"
                        if course.start_date
                        else "Schedule pending"
                    ),
                    "deadline": day_stamp(course.enrollment_deadline),
                    "capacity": course.capacity,
                    "duration": float(course.duration_hours),
                    "enrolled": enrolled,
                    "active": active,
                    "completed": completed,
                    "at_risk": at_risk,
                    "fill": int(round(enrolled * 100 / course.capacity))
                    if course.capacity
                    else 0,
                    "completion": int(round(completed * 100 / enrolled))
                    if enrolled
                    else 0,
                    "published_resources": counts["published_resources"],
                    "total_resources": counts["total_resources"],
                    "assessments": assessments,
                    "assignments": assignments,
                    "certificates": certificates,
                    "trainer_count": counts["trainer_count"],
                    "lead_count": counts["lead_count"],
                    "trainers": ", ".join(trainer_names)
                    if trainer_names
                    else "Unassigned",
                    "readiness": readiness,
                    "checks": checks,
                    "blockers": blockers,
                    "target": target,
                    "next_label": label,
                    "next_hint": hint,
                    "blocked": blocked,
                }
            )
            choices.append(
                {
                    "id": course.id,
                    "label": f"{course.code} · {course.title}",
                    "status": course.status,
                    "trainer_count": counts["trainer_count"],
                }
            )
        self.course_rows = rows
        self.course_choices = choices
        self.metrics = metrics

    async def _load_staffing(self, session) -> None:
        triples = (
            await session.execute(
                select(CourseTrainerAssignment, Course, User)
                .join(Course, Course.id == CourseTrainerAssignment.course_id)
                .join(User, User.id == CourseTrainerAssignment.trainer_id)
                .order_by(CourseTrainerAssignment.match_score.desc())
            )
        ).all()
        rows: list[StaffingRow] = []
        for record, course, trainer in triples:
            profile = await session.scalar(
                select(TrainerProfile).where(
                    TrainerProfile.user_id == trainer.id
                )
            )
            cohort = await self._count(
                session, Enrollment, Enrollment.course_id == course.id
            )
            trainer_courses = await self._count(
                session,
                CourseTrainerAssignment,
                CourseTrainerAssignment.trainer_id == trainer.id,
            )
            assigned_by = (
                await session.scalar(
                    select(User.full_name).where(
                        User.id == record.assigned_by_id
                    )
                )
                if record.assigned_by_id
                else None
            ) or "System seed"
            rows.append(
                {
                    "id": record.id,
                    "course_id": course.id,
                    "course": course.title,
                    "code": course.code,
                    "course_status": course.status,
                    "trainer_id": trainer.id,
                    "trainer": trainer.full_name,
                    "email": trainer.email,
                    "designation": profile.designation
                    if profile
                    else "Profile pending",
                    "assignment_role": record.assignment_role.replace("_", " "),
                    "status": record.status,
                    "match_score": float(record.match_score or 0.0),
                    "cohort": cohort,
                    "trainer_courses": trainer_courses,
                    "note": record.notes or "No staffing note recorded.",
                    "assigned_by": assigned_by,
                }
            )
        self.staffing_rows = rows

        trainers = (
            await session.execute(
                select(User, TrainerProfile)
                .outerjoin(TrainerProfile, TrainerProfile.user_id == User.id)
                .where(
                    User.role == UserRole.TRAINER.value,
                    User.approval_status == ApprovalStatus.APPROVED.value,
                    User.is_active.is_(True),
                )
                .order_by(User.full_name)
            )
        ).all()
        choices: list[TrainerChoiceRow] = []
        for trainer, profile in trainers:
            courses = await self._count(
                session,
                CourseTrainerAssignment,
                CourseTrainerAssignment.trainer_id == trainer.id,
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
                    .where(CourseTrainerAssignment.trainer_id == trainer.id)
                )
                or 0
            )
            choices.append(
                {
                    "id": trainer.id,
                    "label": f"{trainer.full_name} · {courses} courses · {cohort} trainees",
                    "courses": courses,
                    "cohort": cohort,
                    "available": bool(profile.is_available)
                    if profile
                    else False,
                }
            )
        self.trainer_choices = choices

    # ----------------------------------------------------------- mutations
    async def _match_score(self, session, course_id: int, trainer_id: int):
        pairs = (
            (
                await session.execute(
                    select(CourseRequiredSkill).where(
                        CourseRequiredSkill.course_id == course_id
                    )
                )
            )
            .scalars()
            .all()
        )
        if not pairs:
            return 0.0, 0, 0
        held = {
            row.skill_id: row
            for row in (
                (
                    await session.execute(
                        select(UserSkill).where(UserSkill.user_id == trainer_id)
                    )
                )
                .scalars()
                .all()
            )
        }
        total_weight = sum(float(row.weight) for row in pairs)
        weighted = 0.0
        matched = 0
        for requirement in pairs:
            skill = held.get(requirement.skill_id)
            score = int(skill.proficiency_score) if skill else 0
            weighted += score * float(requirement.weight)
            if score >= LEVEL_TARGET.get(requirement.minimum_level, 50):
                matched += 1
        average = weighted / total_weight if total_weight else 0.0
        return round(average, 1), matched, len(pairs)

    @rx.event
    async def apply_transition(self, course_id: int, target: str):
        self.error_message = ""
        self.success_message = ""
        if await admin_guard(self) == 0:
            self.error_message = (
                "Only an approved administrator may change a course status."
            )
            return
        valid = {status.value for status in CourseStatus}
        if target not in valid:
            self.error_message = "That lifecycle transition is not allowed."
            return
        try:
            async with rx.asession() as session:
                course = await session.get(Course, course_id)
                if course is None:
                    self.error_message = "That course no longer exists."
                    return
                allowed = TRANSITIONS.get(course.status, ("", "", ""))[0]
                if target != allowed:
                    self.error_message = (
                        f"A {course.status} course can only move to {allowed}."
                    )
                    return
                if target == CourseStatus.PUBLISHED.value:
                    _checks, blockers, _counts = await self._evaluate(
                        session, course
                    )
                    if blockers:
                        self.error_message = (
                            "Publication blocked: " + "; ".join(blockers)
                        )
                        return
                course.status = target
                await session.commit()
                title = f"{course.code} · {course.title}"
        except Exception as exception:
            logging.exception(f"Error changing course status: {exception}")
            self.error_message = "Could not change that course. Try again."
            return
        self.confirm_course_id = 0
        self.confirm_target = ""
        self.success_message = f"{title} is now {target}."
        yield AdminCourseOpsState.load_course_ops
        yield AdminOversightState.load_oversight

    @rx.event
    async def assign_trainer(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        admin_id = await admin_guard(self)
        if admin_id == 0:
            self.error_message = (
                "Only an approved administrator may staff a course."
            )
            return
        course_id = int(form_data.get("course_id") or 0)
        trainer_id = int(form_data.get("trainer_id") or 0)
        role = str(form_data.get("assignment_role", "")).strip()
        note = str(form_data.get("note", "")).strip()
        if course_id == 0 or trainer_id == 0:
            self.error_message = "Choose both a course and a trainer."
            return
        if role not in ASSIGNMENT_ROLES:
            self.error_message = "Choose lead, co-trainer or guest."
            return
        if len(note) < 10:
            self.error_message = "Record a staffing note of at least 10 characters for the audit trail."
            return
        try:
            async with rx.asession() as session:
                course = await session.get(Course, course_id)
                trainer = await session.get(User, trainer_id)
                if course is None or trainer is None:
                    self.error_message = (
                        "That course or trainer no longer exists."
                    )
                    return
                if (
                    trainer.role != UserRole.TRAINER.value
                    or trainer.approval_status != ApprovalStatus.APPROVED.value
                    or not trainer.is_active
                ):
                    self.error_message = (
                        "Only approved, active trainer accounts can be staffed "
                        "onto a course."
                    )
                    return
                existing = await session.scalar(
                    select(CourseTrainerAssignment).where(
                        CourseTrainerAssignment.course_id == course_id,
                        CourseTrainerAssignment.trainer_id == trainer_id,
                    )
                )
                if existing is not None:
                    self.error_message = (
                        f"{trainer.full_name} is already assigned to "
                        f"{course.code} as {existing.assignment_role.replace('_', ' ')}."
                    )
                    return
                if role == TrainerAssignmentRole.LEAD.value:
                    leads = await self._count(
                        session,
                        CourseTrainerAssignment,
                        CourseTrainerAssignment.course_id == course_id,
                        CourseTrainerAssignment.assignment_role
                        == TrainerAssignmentRole.LEAD.value,
                    )
                    if leads:
                        self.error_message = (
                            f"{course.code} already has a lead trainer. "
                            "Assign as co-trainer or guest."
                        )
                        return
                score, matched, required = await self._match_score(
                    session, course_id, trainer_id
                )
                session.add(
                    CourseTrainerAssignment(
                        course_id=course_id,
                        trainer_id=trainer_id,
                        assignment_role=role,
                        status=ApprovalStatus.APPROVED.value,
                        match_score=score,
                        assigned_by_id=admin_id,
                        notes=(
                            f"{note} | Competency match {score:.1f}% with "
                            f"{matched} of {required} required skills met."
                        ),
                    )
                )
                await session.commit()
                name = trainer.full_name
                code = course.code
        except Exception as exception:
            logging.exception(f"Error staffing course: {exception}")
            self.error_message = "Could not record that assignment. Try again."
            return
        self.success_message = (
            f"{name} staffed onto {code} as {role.replace('_', ' ')} "
            f"with a {score:.1f}% competency match."
        )
        yield AdminCourseOpsState.load_course_ops
        yield AdminOversightState.load_oversight

    @rx.event
    async def remove_assignment(self, assignment_id: int):
        self.error_message = ""
        self.success_message = ""
        if await admin_guard(self) == 0:
            self.error_message = (
                "Only an approved administrator may change staffing."
            )
            return
        try:
            async with rx.asession() as session:
                record = await session.get(
                    CourseTrainerAssignment, assignment_id
                )
                if record is None:
                    self.error_message = "That assignment no longer exists."
                    return
                course = await session.get(Course, record.course_id)
                if (
                    course is not None
                    and course.status == CourseStatus.PUBLISHED.value
                ):
                    remaining = await self._count(
                        session,
                        CourseTrainerAssignment,
                        CourseTrainerAssignment.course_id == course.id,
                        CourseTrainerAssignment.id != record.id,
                    )
                    if remaining == 0:
                        self.error_message = (
                            "A published course must keep at least one trainer. "
                            "Archive it first or staff a replacement."
                        )
                        return
                await session.delete(record)
                await session.commit()
        except Exception as exception:
            logging.exception(f"Error removing staffing: {exception}")
            self.error_message = "Could not remove that assignment."
            return
        self.success_message = "Staffing assignment withdrawn."
        yield AdminCourseOpsState.load_course_ops
        yield AdminOversightState.load_oversight

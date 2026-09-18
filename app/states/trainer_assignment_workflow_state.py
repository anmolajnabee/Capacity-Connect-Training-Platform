"""Trainer assignment authoring, publishing and submission grading."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    AssignmentStatus,
    AssignmentSubmission,
    AssignmentType,
    Course,
    CourseAssignment,
    Enrollment,
    SubmissionStatus,
    User,
)
from app.seed import ensure_seed_data
from app.services.email_notifications import enqueue
from app.states.trainee_assignment_state import aware, stamp, timeline_percent
from app.states.trainer_state import trainer_guard

logger = logging.getLogger(__name__)

ASSIGNMENT_TYPES: list[str] = [item.value for item in AssignmentType]
MIN_FEEDBACK_CHARS = 20
MIN_INSTRUCTION_CHARS = 30


class CourseOption(TypedDict):
    id: int
    label: str


class TrainerAssignmentRow(TypedDict):
    id: int
    course_id: int
    course_code: str
    course_title: str
    title: str
    assignment_type: str
    instructions: str
    reference_url: str
    total_marks: float
    passing_marks: float
    status: str
    due_display: str
    is_overdue: bool
    late_policy: str
    allow_resubmission: bool
    timeline: int
    cohort: int
    submitted: int
    graded: int
    pending_review: int
    late: int
    awaiting: int
    graded_percent: int
    submitted_percent: int


class SubmissionRow(TypedDict):
    id: int
    assignment_id: int
    assignment_title: str
    trainee: str
    email: str
    status: str
    is_late: bool
    attempt_count: int
    submitted_at: str
    response_text: str
    submission_url: str
    is_graded: bool
    marks_awarded: float
    total_marks: float
    feedback: str
    graded_at: str


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _parse_due(value: str) -> dt.datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        moment = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.UTC)
    return moment


class TrainerAssignmentWorkflowState(rx.State):
    is_loading: bool = False
    is_saving: bool = False
    error_message: str = ""
    success_message: str = ""

    course_options: list[CourseOption] = []
    assignments: list[TrainerAssignmentRow] = []
    submissions: list[SubmissionRow] = []
    selected_assignment_id: int = 0
    grading_submission_id: int = 0
    status_filter: str = "All"

    metrics: dict[str, int] = {
        "assignments": 0,
        "published": 0,
        "drafts": 0,
        "submissions": 0,
        "awaiting": 0,
        "graded": 0,
    }

    # ------------------------------------------------------------- computed
    @rx.var
    def type_options(self) -> list[str]:
        return ASSIGNMENT_TYPES

    @rx.var
    def status_options(self) -> list[str]:
        return ["All", "draft", "published", "closed"]

    @rx.var
    def has_courses(self) -> bool:
        return len(self.course_options) > 0

    @rx.var
    def has_assignments(self) -> bool:
        return len(self.assignments) > 0

    @rx.var
    def filtered_assignments(self) -> list[TrainerAssignmentRow]:
        if self.status_filter == "All":
            return self.assignments
        return [
            row
            for row in self.assignments
            if row["status"] == self.status_filter
        ]

    @rx.var
    def selected_assignment(self) -> TrainerAssignmentRow | None:
        for row in self.assignments:
            if row["id"] == self.selected_assignment_id:
                return row
        return None

    @rx.var
    def selected_title(self) -> str:
        current = self.selected_assignment
        return current["title"] if current else ""

    @rx.var
    def selected_course(self) -> str:
        current = self.selected_assignment
        return (
            f"{current['course_code']} · {current['course_title']}"
            if current
            else ""
        )

    @rx.var
    def selected_total_marks(self) -> float:
        current = self.selected_assignment
        return current["total_marks"] if current else 0.0

    @rx.var
    def has_submissions(self) -> bool:
        return len(self.submissions) > 0

    @rx.var
    def grading_progress(self) -> int:
        submissions = self.metrics.get("submissions", 0)
        if not submissions:
            return 0
        return int(round(self.metrics.get("graded", 0) * 100 / submissions))

    # --------------------------------------------------------------- events
    @rx.event
    def set_status_filter(self, value: str):
        self.status_filter = value

    @rx.event
    def toggle_grading(self, submission_id: int):
        self.error_message = ""
        self.success_message = ""
        self.grading_submission_id = (
            0 if self.grading_submission_id == submission_id else submission_id
        )

    @rx.event
    async def select_assignment(self, assignment_id: int):
        self.error_message = ""
        self.success_message = ""
        self.grading_submission_id = 0
        self.selected_assignment_id = assignment_id
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        try:
            async with rx.asession() as session:
                await self._load_submissions(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error loading submissions: {exception}")
            self.error_message = (
                "Could not load submissions for this assignment."
            )

    @rx.event
    async def load_workspace(self):
        self.error_message = ""
        self.success_message = ""
        ensure_seed_data()
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error loading trainer assignments: {exception}")
            self.error_message = "Could not load your assignment workspace."
        self.is_loading = False

    # -------------------------------------------------------------- loaders
    async def _owned_course_ids(self, session, trainer_id: int) -> list[int]:
        from app.models import CourseTrainerAssignment

        return list(
            (
                await session.scalars(
                    select(CourseTrainerAssignment.course_id).where(
                        CourseTrainerAssignment.trainer_id == trainer_id,
                        CourseTrainerAssignment.status == "approved",
                    )
                )
            ).all()
        )

    async def _load(self, session, trainer_id: int) -> None:
        course_ids = await self._owned_course_ids(session, trainer_id)
        options: list[CourseOption] = []
        if course_ids:
            courses = (
                await session.execute(
                    select(Course)
                    .where(Course.id.in_(course_ids))
                    .order_by(Course.title)
                )
            ).scalars()
            options = [
                {"id": course.id, "label": f"{course.code} · {course.title}"}
                for course in courses
            ]
        self.course_options = options

        rows: list[TrainerAssignmentRow] = []
        metrics = {
            "assignments": 0,
            "published": 0,
            "drafts": 0,
            "submissions": 0,
            "awaiting": 0,
            "graded": 0,
        }
        if not course_ids:
            self.assignments = []
            self.submissions = []
            self.metrics = metrics
            return
        pairs = (
            await session.execute(
                select(CourseAssignment, Course)
                .join(Course, Course.id == CourseAssignment.course_id)
                .where(
                    CourseAssignment.course_id.in_(course_ids),
                    CourseAssignment.created_by_id == trainer_id,
                )
                .order_by(CourseAssignment.created_at.desc())
            )
        ).all()
        now = dt.datetime.now(dt.UTC)
        for assignment, course in pairs:
            cohort = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Enrollment)
                    .where(Enrollment.course_id == course.id)
                )
                or 0
            )
            submissions = (
                await session.scalars(
                    select(AssignmentSubmission).where(
                        AssignmentSubmission.assignment_id == assignment.id
                    )
                )
            ).all()
            real = [
                row
                for row in submissions
                if row.status != SubmissionStatus.DRAFT.value
            ]
            graded = [
                row
                for row in real
                if row.status == SubmissionStatus.GRADED.value
            ]
            late = [row for row in real if row.is_late]
            due = aware(assignment.due_at)
            metrics["assignments"] += 1
            metrics["submissions"] += len(real)
            metrics["graded"] += len(graded)
            metrics["awaiting"] += len(real) - len(graded)
            if assignment.status == AssignmentStatus.PUBLISHED.value:
                metrics["published"] += 1
            elif assignment.status == AssignmentStatus.DRAFT.value:
                metrics["drafts"] += 1
            rows.append(
                {
                    "id": assignment.id,
                    "course_id": course.id,
                    "course_code": course.code,
                    "course_title": course.title,
                    "title": assignment.title,
                    "assignment_type": assignment.assignment_type.replace(
                        "_", " "
                    ),
                    "instructions": assignment.instructions,
                    "reference_url": assignment.reference_url,
                    "total_marks": float(assignment.total_marks or 0.0),
                    "passing_marks": float(assignment.passing_marks or 0.0),
                    "status": assignment.status,
                    "due_display": stamp(assignment.due_at),
                    "is_overdue": bool(due and now > due),
                    "late_policy": (
                        f"Late accepted · {assignment.late_penalty_percent:.0f}% penalty"
                        if assignment.allow_late_submission
                        else "No late submissions"
                    ),
                    "allow_resubmission": bool(assignment.allow_resubmission),
                    "timeline": timeline_percent(
                        assignment.published_at or assignment.created_at,
                        assignment.due_at,
                    ),
                    "cohort": cohort,
                    "submitted": len(real),
                    "graded": len(graded),
                    "pending_review": len(real) - len(graded),
                    "late": len(late),
                    "awaiting": max(0, cohort - len(real)),
                    "graded_percent": int(round(len(graded) * 100 / len(real)))
                    if real
                    else 0,
                    "submitted_percent": int(round(len(real) * 100 / cohort))
                    if cohort
                    else 0,
                }
            )
        self.assignments = rows
        self.metrics = metrics
        if rows and not any(
            row["id"] == self.selected_assignment_id for row in rows
        ):
            self.selected_assignment_id = rows[0]["id"]
        if not rows:
            self.selected_assignment_id = 0
        await self._load_submissions(session, trainer_id)

    async def _load_submissions(self, session, trainer_id: int) -> None:
        if self.selected_assignment_id <= 0:
            self.submissions = []
            return
        assignment = await session.get(
            CourseAssignment, self.selected_assignment_id
        )
        if assignment is None or assignment.created_by_id != trainer_id:
            self.submissions = []
            return
        pairs = (
            await session.execute(
                select(AssignmentSubmission, User)
                .join(User, User.id == AssignmentSubmission.trainee_id)
                .where(
                    AssignmentSubmission.assignment_id == assignment.id,
                    AssignmentSubmission.status != SubmissionStatus.DRAFT.value,
                )
                .order_by(AssignmentSubmission.submitted_at.desc().nulls_last())
            )
        ).all()
        self.submissions = [
            {
                "id": submission.id,
                "assignment_id": assignment.id,
                "assignment_title": assignment.title,
                "trainee": user.full_name,
                "email": user.email,
                "status": submission.status,
                "is_late": bool(submission.is_late),
                "attempt_count": submission.attempt_count,
                "submitted_at": stamp(submission.submitted_at),
                "response_text": submission.response_text,
                "submission_url": submission.submission_url,
                "is_graded": submission.status == SubmissionStatus.GRADED.value,
                "marks_awarded": float(submission.marks_awarded or 0.0),
                "total_marks": float(assignment.total_marks or 0.0),
                "feedback": submission.feedback,
                "graded_at": stamp(submission.graded_at)
                if submission.graded_at
                else "",
            }
            for submission, user in pairs
        ]

    # ------------------------------------------------------------ mutations
    @rx.event
    async def create_assignment(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        try:
            course_id = int(form_data.get("course_id") or 0)
        except (TypeError, ValueError):
            course_id = 0
        title = str(form_data.get("title") or "").strip()
        instructions = str(form_data.get("instructions") or "").strip()
        reference_url = str(form_data.get("reference_url") or "").strip()
        assignment_type = str(
            form_data.get("assignment_type") or AssignmentType.ESSAY.value
        )
        total_marks = _to_float(form_data.get("total_marks"), 0.0)
        passing_marks = _to_float(form_data.get("passing_marks"), 0.0)
        penalty = _to_float(form_data.get("late_penalty_percent"), 0.0)
        due_at = _parse_due(str(form_data.get("due_at") or ""))
        publish = str(form_data.get("publish_state") or "draft") == "published"
        allow_late = bool(form_data.get("allow_late_submission"))
        allow_resubmission = bool(form_data.get("allow_resubmission"))

        if course_id <= 0:
            self.error_message = "Choose one of your assigned courses."
            return
        if len(title) < 6:
            self.error_message = (
                "Give the assignment a descriptive title (6+ characters)."
            )
            return
        if len(instructions) < MIN_INSTRUCTION_CHARS:
            self.error_message = (
                f"Instructions must be at least {MIN_INSTRUCTION_CHARS} "
                "characters so trainees know what to produce."
            )
            return
        if reference_url and not reference_url.lower().startswith("https://"):
            self.error_message = (
                "The reference link must be a secure HTTPS URL."
            )
            return
        if total_marks <= 0 or total_marks > 1000:
            self.error_message = "Total marks must be between 1 and 1000."
            return
        if passing_marks < 0 or passing_marks > total_marks:
            self.error_message = (
                "Pass mark must be between 0 and the total marks."
            )
            return
        if penalty < 0 or penalty > 100:
            self.error_message = (
                "Late penalty must be between 0 and 100 percent."
            )
            return
        if due_at is None:
            self.error_message = "Set a valid due date and time."
            return
        if publish and due_at <= dt.datetime.now(dt.UTC):
            self.error_message = (
                "A published assignment needs a due date in the future."
            )
            return
        if assignment_type not in ASSIGNMENT_TYPES:
            assignment_type = AssignmentType.ESSAY.value

        self.is_saving = True
        yield
        try:
            async with rx.asession() as session:
                owned = await self._owned_course_ids(session, trainer_id)
                if course_id not in owned:
                    self.error_message = (
                        "You can only create assignments for courses assigned "
                        "to you."
                    )
                    self.is_saving = False
                    return
                now = dt.datetime.now(dt.UTC)
                assignment = CourseAssignment(
                    course_id=course_id,
                    created_by_id=trainer_id,
                    title=title,
                    instructions=instructions,
                    reference_url=reference_url,
                    assignment_type=assignment_type,
                    total_marks=total_marks,
                    passing_marks=passing_marks,
                    status=AssignmentStatus.PUBLISHED.value
                    if publish
                    else AssignmentStatus.DRAFT.value,
                    is_published=publish,
                    published_at=now if publish else None,
                    due_at=due_at,
                    allow_late_submission=allow_late,
                    late_penalty_percent=penalty,
                    allow_resubmission=allow_resubmission,
                    submission_note=str(
                        form_data.get("submission_note") or ""
                    ).strip(),
                )
                session.add(assignment)
                await session.flush()
                new_id = assignment.id
                if publish:
                    await enqueue(session, "assignment_published", assignment)
                await session.commit()
                self.selected_assignment_id = new_id
            async with rx.asession() as session:
                await self._load(session, trainer_id)
            self.success_message = (
                f"Assignment published for the cohort: {title}."
                if publish
                else f"Draft assignment saved: {title}."
            )
        except Exception as exception:
            logging.exception(f"Error creating assignment: {exception}")
            self.error_message = "Could not create the assignment. Try again."
        self.is_saving = False

    @rx.event
    async def publish_assignment(self, assignment_id: int):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        try:
            async with rx.asession() as session:
                assignment = await session.get(CourseAssignment, assignment_id)
                if assignment is None or assignment.created_by_id != trainer_id:
                    self.error_message = (
                        "You can only publish assignments you authored."
                    )
                    return
                if assignment.status != AssignmentStatus.DRAFT.value:
                    self.error_message = (
                        "Only draft assignments can be published."
                    )
                    return
                assignment.status = AssignmentStatus.PUBLISHED.value
                assignment.is_published = True
                assignment.published_at = dt.datetime.now(dt.UTC)
                title = assignment.title
                await enqueue(session, "assignment_published", assignment)
                await session.commit()
            async with rx.asession() as session:
                await self._load(session, trainer_id)
            self.success_message = (
                f"{title} is now visible to enrolled trainees."
            )
        except Exception as exception:
            logging.exception(f"Error publishing assignment: {exception}")
            self.error_message = "Could not publish this assignment."

    @rx.event
    async def close_assignment(self, assignment_id: int):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        try:
            async with rx.asession() as session:
                assignment = await session.get(CourseAssignment, assignment_id)
                if assignment is None or assignment.created_by_id != trainer_id:
                    self.error_message = (
                        "You can only close assignments you authored."
                    )
                    return
                if assignment.status != AssignmentStatus.PUBLISHED.value:
                    self.error_message = (
                        "Only published assignments can be closed."
                    )
                    return
                assignment.status = AssignmentStatus.CLOSED.value
                title = assignment.title
                await session.commit()
            async with rx.asession() as session:
                await self._load(session, trainer_id)
            self.success_message = f"{title} is closed for new submissions."
        except Exception as exception:
            logging.exception(f"Error closing assignment: {exception}")
            self.error_message = "Could not close this assignment."

    @rx.event
    async def grade_submission(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        try:
            submission_id = int(form_data.get("submission_id") or 0)
        except (TypeError, ValueError):
            submission_id = 0
        marks = _to_float(form_data.get("marks_awarded"), -1.0)
        feedback = str(form_data.get("feedback") or "").strip()
        if submission_id <= 0:
            self.error_message = "Select a submission to grade."
            return
        if len(feedback) < MIN_FEEDBACK_CHARS:
            self.error_message = (
                f"Constructive feedback of at least {MIN_FEEDBACK_CHARS} "
                "characters is required with every grade."
            )
            return
        self.is_saving = True
        yield
        try:
            async with rx.asession() as session:
                submission = await session.get(
                    AssignmentSubmission, submission_id
                )
                if submission is None:
                    self.error_message = "That submission no longer exists."
                    self.is_saving = False
                    return
                assignment = await session.get(
                    CourseAssignment, submission.assignment_id
                )
                if assignment is None or assignment.created_by_id != trainer_id:
                    self.error_message = (
                        "You can only grade submissions for your own "
                        "assignments."
                    )
                    self.is_saving = False
                    return
                total = float(assignment.total_marks or 0.0)
                if marks < 0 or marks > total:
                    self.error_message = (
                        f"Marks must be between 0 and {total:.0f}."
                    )
                    self.is_saving = False
                    return
                submission.marks_awarded = marks
                submission.feedback = feedback
                submission.status = SubmissionStatus.GRADED.value
                submission.graded_by_id = trainer_id
                submission.graded_at = dt.datetime.now(dt.UTC)
                await enqueue(
                    session,
                    "assignment_graded",
                    submission,
                    str(submission.attempt_count),
                )
                await session.commit()
            async with rx.asession() as session:
                await self._load(session, trainer_id)
            self.grading_submission_id = 0
            self.success_message = (
                f"Grade recorded: {marks:.0f} marks with feedback."
            )
        except Exception as exception:
            logging.exception(f"Error grading submission: {exception}")
            self.error_message = "Could not record this grade. Try again."
        self.is_saving = False

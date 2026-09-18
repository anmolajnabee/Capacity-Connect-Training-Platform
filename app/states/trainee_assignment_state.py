"""Trainee assignment workflow: eligibility, submissions, grades and feedback."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import select

from app.models import (
    AssignmentStatus,
    AssignmentSubmission,
    Course,
    CourseAssignment,
    Enrollment,
    SubmissionStatus,
    User,
    UserRole,
)
from app.seed import ensure_seed_data

logger = logging.getLogger(__name__)

MIN_WORK_CHARS = 40
BUCKETS: list[str] = ["All", "pending", "submitted", "graded", "overdue"]


def aware(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.UTC)
    return value


def stamp(value: dt.datetime | None) -> str:
    moment = aware(value)
    if moment is None:
        return "Not set"
    return moment.strftime("%d %b %Y · %H:%M UTC")


def timeline_percent(
    published: dt.datetime | None, due: dt.datetime | None
) -> int:
    start = aware(published)
    end = aware(due)
    if end is None:
        return 0
    now = dt.datetime.now(dt.UTC)
    if start is None or start >= end:
        return 100 if now >= end else 50
    span = (end - start).total_seconds()
    used = (now - start).total_seconds()
    return max(0, min(100, int(round(used * 100 / span))))


class AssignmentCard(TypedDict):
    id: int
    course_id: int
    course_code: str
    course_title: str
    title: str
    assignment_type: str
    instructions: str
    reference_url: str
    submission_note: str
    total_marks: float
    passing_marks: float
    due_display: str
    days_left: int
    is_overdue: bool
    allow_late: bool
    late_penalty: float
    allow_resubmission: bool
    late_policy: str
    trainer_name: str
    timeline: int
    bucket: str
    status_label: str
    submission_id: int
    submitted_at: str
    response_text: str
    submission_url: str
    is_late: bool
    attempt_count: int
    is_graded: bool
    marks_awarded: float
    score_percent: int
    is_passed: bool
    feedback: str
    graded_at: str
    graded_by: str
    can_submit: bool
    blocked_reason: str


class TraineeAssignmentState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""
    is_saving: bool = False

    assignments: list[AssignmentCard] = []
    bucket_filter: str = "All"
    open_assignment_id: int = 0

    metrics: dict[str, int] = {
        "total": 0,
        "pending": 0,
        "submitted": 0,
        "graded": 0,
        "overdue": 0,
        "average": 0,
    }

    # ------------------------------------------------------------- computed
    @rx.var
    def bucket_options(self) -> list[str]:
        return BUCKETS

    @rx.var
    def filtered_assignments(self) -> list[AssignmentCard]:
        if self.bucket_filter == "All":
            return self.assignments
        return [
            row
            for row in self.assignments
            if row["bucket"] == self.bucket_filter
        ]

    @rx.var
    def has_assignments(self) -> bool:
        return len(self.assignments) > 0

    @rx.var
    def has_matches(self) -> bool:
        return len(self.filtered_assignments) > 0

    @rx.var
    def grading_progress(self) -> int:
        total = self.metrics.get("total", 0)
        if not total:
            return 0
        return int(round(self.metrics.get("graded", 0) * 100 / total))

    @rx.var
    def result_label(self) -> str:
        return (
            f"{len(self.filtered_assignments)} of {len(self.assignments)} "
            "assignments"
        )

    # -------------------------------------------------------------- helpers
    async def _uid(self) -> int:
        from app.states.auth_state import AuthState

        auth = await self.get_state(AuthState)
        if auth.role != UserRole.TRAINEE.value or auth.user_id <= 0:
            return 0
        return auth.user_id

    # --------------------------------------------------------------- events
    @rx.event
    def set_bucket_filter(self, value: str):
        self.bucket_filter = value

    @rx.event
    def toggle_form(self, assignment_id: int):
        self.error_message = ""
        self.success_message = ""
        self.open_assignment_id = (
            0 if self.open_assignment_id == assignment_id else assignment_id
        )

    @rx.event
    def close_form(self):
        self.open_assignment_id = 0

    @rx.event
    async def load_assignments(self):
        self.error_message = ""
        self.success_message = ""
        ensure_seed_data()
        trainee_id = await self._uid()
        if trainee_id == 0:
            self.error_message = (
                "Sign in with a trainee account to view assignments."
            )
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load(session, trainee_id)
        except Exception as exception:
            logging.exception(f"Error loading trainee assignments: {exception}")
            self.error_message = "Could not load your assignments right now."
        self.is_loading = False

    async def _load(self, session, trainee_id: int) -> None:
        course_ids = list(
            (
                await session.scalars(
                    select(Enrollment.course_id).where(
                        Enrollment.trainee_id == trainee_id
                    )
                )
            ).all()
        )
        cards: list[AssignmentCard] = []
        metrics = {
            "total": 0,
            "pending": 0,
            "submitted": 0,
            "graded": 0,
            "overdue": 0,
            "average": 0,
        }
        if not course_ids:
            self.assignments = []
            self.metrics = metrics
            return
        pairs = (
            await session.execute(
                select(CourseAssignment, Course)
                .join(Course, Course.id == CourseAssignment.course_id)
                .where(
                    CourseAssignment.course_id.in_(course_ids),
                    CourseAssignment.status.in_(
                        [
                            AssignmentStatus.PUBLISHED.value,
                            AssignmentStatus.CLOSED.value,
                        ]
                    ),
                )
                .order_by(CourseAssignment.due_at.asc().nulls_last())
            )
        ).all()
        now = dt.datetime.now(dt.UTC)
        score_total = 0.0
        score_count = 0
        for assignment, course in pairs:
            submission = await session.scalar(
                select(AssignmentSubmission).where(
                    AssignmentSubmission.assignment_id == assignment.id,
                    AssignmentSubmission.trainee_id == trainee_id,
                )
            )
            trainer_name = (
                await session.scalar(
                    select(User.full_name).where(
                        User.id == assignment.created_by_id
                    )
                )
                if assignment.created_by_id
                else None
            ) or "Course faculty"
            due = aware(assignment.due_at)
            is_overdue = bool(due and now > due)
            days_left = int((due - now).total_seconds() // 86400) if due else 0
            is_graded = bool(
                submission
                and submission.status == SubmissionStatus.GRADED.value
            )
            has_submitted = bool(
                submission
                and submission.status
                in (
                    SubmissionStatus.SUBMITTED.value,
                    SubmissionStatus.LATE.value,
                    SubmissionStatus.GRADED.value,
                    SubmissionStatus.RETURNED.value,
                )
            )
            marks = (
                float(submission.marks_awarded or 0.0) if submission else 0.0
            )
            total_marks = float(assignment.total_marks or 0.0)
            score_percent = (
                int(round(marks * 100 / total_marks))
                if is_graded and total_marks > 0
                else 0
            )
            if is_graded:
                score_total += score_percent
                score_count += 1

            can_submit = True
            blocked = ""
            if assignment.status == AssignmentStatus.CLOSED.value:
                can_submit = False
                blocked = "This assignment has been closed by the trainer."
            elif is_graded and not assignment.allow_resubmission:
                can_submit = False
                blocked = "Graded — resubmission is not permitted."
            elif has_submitted and not assignment.allow_resubmission:
                can_submit = False
                blocked = "Submitted — resubmission is not permitted."
            elif is_overdue and not assignment.allow_late_submission:
                can_submit = False
                blocked = (
                    "The deadline has passed and late work is not accepted."
                )

            if is_graded:
                bucket = "graded"
                status_label = "Graded"
            elif has_submitted:
                bucket = "submitted"
                status_label = (
                    "Submitted late" if submission.is_late else "Submitted"
                )
            elif is_overdue:
                bucket = "overdue"
                status_label = "Overdue"
            else:
                bucket = "pending"
                status_label = "Pending submission"
            metrics[bucket] = metrics.get(bucket, 0) + 1
            metrics["total"] += 1

            late_policy = (
                (
                    f"Late work accepted · {assignment.late_penalty_percent:.0f}% penalty"
                    if assignment.late_penalty_percent
                    else "Late work accepted without penalty"
                )
                if assignment.allow_late_submission
                else "No late submissions accepted"
            )
            cards.append(
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
                    "submission_note": assignment.submission_note,
                    "total_marks": total_marks,
                    "passing_marks": float(assignment.passing_marks or 0.0),
                    "due_display": stamp(assignment.due_at),
                    "days_left": days_left,
                    "is_overdue": is_overdue,
                    "allow_late": bool(assignment.allow_late_submission),
                    "late_penalty": float(assignment.late_penalty_percent),
                    "allow_resubmission": bool(assignment.allow_resubmission),
                    "late_policy": late_policy,
                    "trainer_name": trainer_name,
                    "timeline": timeline_percent(
                        assignment.published_at or assignment.created_at,
                        assignment.due_at,
                    ),
                    "bucket": bucket,
                    "status_label": status_label,
                    "submission_id": submission.id if submission else 0,
                    "submitted_at": stamp(submission.submitted_at)
                    if submission
                    else "Not submitted",
                    "response_text": submission.response_text
                    if submission
                    else "",
                    "submission_url": submission.submission_url
                    if submission
                    else "",
                    "is_late": bool(submission.is_late)
                    if submission
                    else False,
                    "attempt_count": submission.attempt_count
                    if submission
                    else 0,
                    "is_graded": is_graded,
                    "marks_awarded": marks,
                    "score_percent": score_percent,
                    "is_passed": is_graded
                    and marks >= float(assignment.passing_marks or 0.0),
                    "feedback": submission.feedback if submission else "",
                    "graded_at": stamp(submission.graded_at)
                    if submission and submission.graded_at
                    else "",
                    "graded_by": (
                        await session.scalar(
                            select(User.full_name).where(
                                User.id == submission.graded_by_id
                            )
                        )
                        or ""
                    )
                    if submission and submission.graded_by_id
                    else "",
                    "can_submit": can_submit,
                    "blocked_reason": blocked,
                }
            )
        metrics["average"] = (
            int(round(score_total / score_count)) if score_count else 0
        )
        self.assignments = cards
        self.metrics = metrics

    @rx.event
    async def submit_work(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        trainee_id = await self._uid()
        if trainee_id == 0:
            self.error_message = (
                "Sign in with a trainee account to submit work."
            )
            return
        try:
            assignment_id = int(form_data.get("assignment_id") or 0)
        except (TypeError, ValueError):
            assignment_id = 0
        work = str(form_data.get("response_text") or "").strip()
        url = str(form_data.get("submission_url") or "").strip()
        if assignment_id <= 0:
            self.error_message = "Select a valid assignment before submitting."
            return
        if len(work) < MIN_WORK_CHARS:
            self.error_message = (
                f"Describe your submitted work in at least {MIN_WORK_CHARS} "
                "characters so the trainer can assess it."
            )
            return
        if url and not url.lower().startswith("https://"):
            self.error_message = "The evidence link must be a secure HTTPS URL."
            return
        self.is_saving = True
        yield
        try:
            async with rx.asession() as session:
                assignment = await session.get(CourseAssignment, assignment_id)
                if assignment is None:
                    self.error_message = "That assignment no longer exists."
                    self.is_saving = False
                    return
                enrollment = await session.scalar(
                    select(Enrollment).where(
                        Enrollment.course_id == assignment.course_id,
                        Enrollment.trainee_id == trainee_id,
                    )
                )
                if enrollment is None:
                    self.error_message = (
                        "You must be enrolled in this course to submit work."
                    )
                    self.is_saving = False
                    return
                if assignment.status != AssignmentStatus.PUBLISHED.value:
                    self.error_message = (
                        "This assignment is not open for submissions."
                    )
                    self.is_saving = False
                    return
                now = dt.datetime.now(dt.UTC)
                due = aware(assignment.due_at)
                is_late = bool(due and now > due)
                if is_late and not assignment.allow_late_submission:
                    self.error_message = (
                        "The deadline has passed and late work is not accepted."
                    )
                    self.is_saving = False
                    return
                submission = await session.scalar(
                    select(AssignmentSubmission).where(
                        AssignmentSubmission.assignment_id == assignment.id,
                        AssignmentSubmission.trainee_id == trainee_id,
                    )
                )
                if submission is not None and not assignment.allow_resubmission:
                    self.error_message = (
                        "You have already submitted and resubmission is "
                        "not permitted for this assignment."
                    )
                    self.is_saving = False
                    return
                status = (
                    SubmissionStatus.LATE.value
                    if is_late
                    else SubmissionStatus.SUBMITTED.value
                )
                if submission is None:
                    submission = AssignmentSubmission(
                        assignment_id=assignment.id,
                        trainee_id=trainee_id,
                        response_text=work,
                        submission_url=url,
                        status=status,
                        is_late=is_late,
                        attempt_count=1,
                        submitted_at=now,
                    )
                    session.add(submission)
                else:
                    submission.response_text = work
                    submission.submission_url = url
                    submission.status = status
                    submission.is_late = is_late
                    submission.attempt_count = (
                        submission.attempt_count or 0
                    ) + 1
                    submission.submitted_at = now
                    submission.marks_awarded = None
                    submission.feedback = ""
                    submission.graded_by_id = None
                    submission.graded_at = None
                enrollment.last_activity_at = now
                await session.commit()
            async with rx.asession() as session:
                await self._load(session, trainee_id)
            self.open_assignment_id = 0
            self.success_message = (
                "Late submission recorded — your trainer has been notified."
                if is_late
                else "Submission saved. Your trainer will review and grade it."
            )
        except Exception as exception:
            logging.exception(f"Error submitting assignment work: {exception}")
            self.error_message = "Could not save your submission. Try again."
        self.is_saving = False

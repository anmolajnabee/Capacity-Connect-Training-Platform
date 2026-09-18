"""Assigned courses, trainee roster and performance classification."""

from __future__ import annotations

import logging
from typing import TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    AssessmentResult,
    Course,
    CourseTrainerAssignment,
    Enrollment,
    EnrollmentStatus,
    LearningResource,
    User,
)
from app.states.trainer_state import days_since, trainer_guard

logger = logging.getLogger(__name__)

# Transparent classification thresholds
INACTIVE_DAYS = 21
AT_RISK_DAYS = 14
AT_RISK_PROGRESS = 40
HIGH_PROGRESS = 75
HIGH_SCORE = 70

STATUS_LABELS: list[str] = [
    "All",
    "high-performing",
    "at-risk",
    "inactive",
    "incomplete",
    "completed",
]


class CourseCard(TypedDict):
    id: int
    code: str
    title: str
    category: str
    level: str
    mode: str
    status: str
    role: str
    match_score: float
    cohort: int
    active: int
    completed: int
    at_risk: int
    completion: int
    avg_progress: float
    resources: int
    window: str


class RosterRow(TypedDict):
    enrollment_id: int
    trainee_id: int
    trainee: str
    email: str
    course: str
    course_code: str
    progress: int
    status: str
    classification: str
    last_activity: str
    days_idle: int
    avg_score: float
    attempts: int


class CoursePerformance(TypedDict):
    course_id: int
    code: str
    title: str
    cohort: int
    completion: int
    avg_progress: int
    avg_score: int
    high: int
    at_risk: int
    inactive: int
    incomplete: int


def classify(
    progress: float, status: str, idle_days: int, avg_score: float
) -> str:
    """Transparent classification of a trainee's standing in a course."""
    if status == EnrollmentStatus.COMPLETED.value or progress >= 100:
        return "completed"
    if idle_days >= INACTIVE_DAYS:
        return "inactive"
    if (
        status == EnrollmentStatus.AT_RISK.value
        or progress < AT_RISK_PROGRESS
        or (avg_score > 0 and avg_score < 50)
    ):
        return "at-risk"
    if progress >= HIGH_PROGRESS and (
        avg_score == 0 or avg_score >= HIGH_SCORE
    ):
        return "high-performing"
    return "incomplete"


class TrainerCourseState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    courses: list[CourseCard] = []
    roster: list[RosterRow] = []
    performance: list[CoursePerformance] = []

    search_query: str = ""
    status_filter: str = "All"
    course_filter: str = "All"

    totals: dict[str, int] = {
        "cohort": 0,
        "high": 0,
        "at_risk": 0,
        "inactive": 0,
        "incomplete": 0,
        "completed": 0,
    }

    @rx.var
    def course_names(self) -> list[str]:
        return ["All"] + [course["title"] for course in self.courses]

    @rx.var
    def status_options(self) -> list[str]:
        return STATUS_LABELS

    @rx.var
    def filtered_roster(self) -> list[RosterRow]:
        query = self.search_query.strip().lower()
        rows: list[RosterRow] = []
        for row in self.roster:
            if self.status_filter != "All" and (
                row["classification"] != self.status_filter
            ):
                continue
            if (
                self.course_filter != "All"
                and row["course"] != self.course_filter
            ):
                continue
            if query and query not in (
                f"{row['trainee']} {row['email']} {row['course_code']}".lower()
            ):
                continue
            rows.append(row)
        return rows

    @rx.event
    def set_search_query(self, value: str):
        self.search_query = value

    @rx.event
    def set_status_filter(self, value: str):
        self.status_filter = value

    @rx.event
    def set_course_filter(self, value: str):
        self.course_filter = value

    @rx.event
    def clear_filters(self):
        self.search_query = ""
        self.status_filter = "All"
        self.course_filter = "All"

    @rx.event
    async def load_courses(self):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error loading trainer courses: {exception}")
            self.error_message = "Could not load your assigned courses."
        self.is_loading = False

    async def _load(self, session, trainer_id: int) -> None:
        cards: list[CourseCard] = []
        roster: list[RosterRow] = []
        performance: list[CoursePerformance] = []
        totals = {
            "cohort": 0,
            "high": 0,
            "at_risk": 0,
            "inactive": 0,
            "incomplete": 0,
            "completed": 0,
        }
        pairs = (
            await session.execute(
                select(CourseTrainerAssignment, Course)
                .join(Course, Course.id == CourseTrainerAssignment.course_id)
                .where(
                    CourseTrainerAssignment.trainer_id == trainer_id,
                    CourseTrainerAssignment.status == "approved",
                )
                .order_by(Course.title)
            )
        ).all()
        for assignment, course in pairs:
            rows = (
                await session.execute(
                    select(Enrollment, User)
                    .join(User, User.id == Enrollment.trainee_id)
                    .where(Enrollment.course_id == course.id)
                    .order_by(User.full_name)
                )
            ).all()
            counts = {
                "high-performing": 0,
                "at-risk": 0,
                "inactive": 0,
                "incomplete": 0,
                "completed": 0,
            }
            progress_sum = 0.0
            score_sum = 0.0
            score_rows = 0
            for enrollment, trainee in rows:
                results = (
                    await session.execute(
                        select(
                            func.avg(AssessmentResult.percentage),
                            func.count(AssessmentResult.id),
                        ).where(AssessmentResult.trainee_id == trainee.id)
                    )
                ).first()
                avg_score = float(results[0] or 0.0) if results else 0.0
                attempts = int(results[1] or 0) if results else 0
                idle = days_since(enrollment.last_activity_at)
                classification = classify(
                    float(enrollment.progress_percent),
                    enrollment.status,
                    idle,
                    avg_score,
                )
                counts[classification] += 1
                progress_sum += float(enrollment.progress_percent)
                if attempts:
                    score_sum += avg_score
                    score_rows += 1
                roster.append(
                    {
                        "enrollment_id": enrollment.id,
                        "trainee_id": trainee.id,
                        "trainee": trainee.full_name,
                        "email": trainee.email,
                        "course": course.title,
                        "course_code": course.code,
                        "progress": int(round(enrollment.progress_percent)),
                        "status": enrollment.status.replace("_", " "),
                        "classification": classification,
                        "last_activity": "No activity yet"
                        if idle >= 999
                        else f"{idle} days ago",
                        "days_idle": min(idle, 999),
                        "avg_score": avg_score,
                        "attempts": attempts,
                    }
                )
            cohort = len(rows)
            active = len(
                [
                    row
                    for row, _trainee in rows
                    if row.status == EnrollmentStatus.ACTIVE.value
                ]
            )
            resources = int(
                await session.scalar(
                    select(func.count())
                    .select_from(LearningResource)
                    .where(LearningResource.course_id == course.id)
                )
                or 0
            )
            completion = (
                int(round(counts["completed"] * 100 / cohort)) if cohort else 0
            )
            avg_progress = progress_sum / cohort if cohort else 0.0
            avg_score = score_sum / score_rows if score_rows else 0.0
            cards.append(
                {
                    "id": course.id,
                    "code": course.code,
                    "title": course.title,
                    "category": course.category,
                    "level": course.level,
                    "mode": course.mode,
                    "status": course.status,
                    "role": assignment.assignment_role.replace("_", " "),
                    "match_score": float(assignment.match_score),
                    "cohort": cohort,
                    "active": active,
                    "completed": counts["completed"],
                    "at_risk": counts["at-risk"] + counts["inactive"],
                    "completion": completion,
                    "avg_progress": avg_progress,
                    "resources": resources,
                    "window": (
                        f"{course.start_date.strftime('%d %b %Y')} → "
                        f"{course.end_date.strftime('%d %b %Y')}"
                        if course.start_date and course.end_date
                        else "Schedule pending"
                    ),
                }
            )
            performance.append(
                {
                    "course_id": course.id,
                    "code": course.code,
                    "title": course.title,
                    "cohort": cohort,
                    "completion": completion,
                    "avg_progress": int(round(avg_progress)),
                    "avg_score": int(round(avg_score)),
                    "high": counts["high-performing"],
                    "at_risk": counts["at-risk"],
                    "inactive": counts["inactive"],
                    "incomplete": counts["incomplete"],
                }
            )
            totals["cohort"] += cohort
            totals["high"] += counts["high-performing"]
            totals["at_risk"] += counts["at-risk"]
            totals["inactive"] += counts["inactive"]
            totals["incomplete"] += counts["incomplete"]
            totals["completed"] += counts["completed"]
        self.courses = cards
        self.roster = roster
        self.performance = performance
        self.totals = totals

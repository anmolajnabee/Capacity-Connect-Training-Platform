"""Organization analytics derived directly from the database."""

from __future__ import annotations

import logging
from typing import TypedDict

import reflex as rx
import reflex_xy
from sqlalchemy import func, select

from app.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentResult,
    Certificate,
    Course,
    Enrollment,
    EnrollmentStatus,
    User,
    UserRole,
)
from app.states.admin_state import admin_guard

logger = logging.getLogger(__name__)


class ParticipationRow(TypedDict):
    index: int
    code: str
    title: str
    enrolled: int
    active: int
    completed: int
    certified: int
    completion: int
    certification: int


class AssessmentSeriesRow(TypedDict):
    index: int
    title: str
    code: str
    attempts: int
    results: int
    pass_rate: int
    avg_score: float


class RoleRow(TypedDict):
    role: str
    count: int
    share: int


class AdminAnalyticsState(rx.State):
    is_loading: bool = False
    error_message: str = ""

    participation: list[ParticipationRow] = []
    assessment_series: list[AssessmentSeriesRow] = []
    role_mix: list[RoleRow] = []

    headline: dict[str, float] = {
        "enrolled": 0.0,
        "completion_rate": 0.0,
        "certification_rate": 0.0,
        "pass_rate": 0.0,
        "average_score": 0.0,
    }

    @rx.var
    def has_participation(self) -> bool:
        return len(self.participation) > 0

    @rx.var
    def has_assessment_series(self) -> bool:
        return len(self.assessment_series) > 0

    @reflex_xy.data
    def participation_columns(self) -> dict[str, list[float]]:
        return {
            "course": [float(row["index"]) for row in self.participation],
            "enrolled": [float(row["enrolled"]) for row in self.participation],
            "completed": [
                float(row["completed"]) for row in self.participation
            ],
            "certified": [
                float(row["certified"]) for row in self.participation
            ],
        }

    @reflex_xy.data
    def outcome_columns(self) -> dict[str, list[float]]:
        return {
            "assessment": [
                float(row["index"]) for row in self.assessment_series
            ],
            "pass_rate": [
                float(row["pass_rate"]) for row in self.assessment_series
            ],
            "average_score": [
                float(row["avg_score"]) for row in self.assessment_series
            ],
        }

    @rx.event
    async def load_analytics(self):
        self.error_message = ""
        if await admin_guard(self) == 0:
            self.error_message = "Administrator access is required."
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load_participation(session)
                await self._load_outcomes(session)
                await self._load_role_mix(session)
        except Exception as exception:
            logging.exception(f"Error loading analytics: {exception}")
            self.error_message = "Could not compute organization analytics."
        self.is_loading = False

    async def _load_participation(self, session) -> None:
        courses = (
            await session.execute(select(Course).order_by(Course.code))
        ).scalars()
        rows: list[ParticipationRow] = []
        total_enrolled = 0
        total_completed = 0
        total_certified = 0
        index = 0
        for course in courses:
            enrolled = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Enrollment)
                    .where(Enrollment.course_id == course.id)
                )
                or 0
            )
            if enrolled == 0:
                continue
            index += 1
            completed = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Enrollment)
                    .where(
                        Enrollment.course_id == course.id,
                        Enrollment.status == EnrollmentStatus.COMPLETED.value,
                    )
                )
                or 0
            )
            active = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Enrollment)
                    .where(
                        Enrollment.course_id == course.id,
                        Enrollment.status == EnrollmentStatus.ACTIVE.value,
                    )
                )
                or 0
            )
            certified = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Certificate)
                    .where(
                        Certificate.course_id == course.id,
                        Certificate.is_revoked.is_(False),
                    )
                )
                or 0
            )
            total_enrolled += enrolled
            total_completed += completed
            total_certified += certified
            rows.append(
                {
                    "index": index,
                    "code": course.code,
                    "title": course.title,
                    "enrolled": enrolled,
                    "active": active,
                    "completed": completed,
                    "certified": certified,
                    "completion": int(round(completed * 100 / enrolled)),
                    "certification": int(round(certified * 100 / enrolled)),
                }
            )
        self.participation = rows
        headline = dict(self.headline)
        headline["enrolled"] = float(total_enrolled)
        headline["completion_rate"] = (
            total_completed * 100 / total_enrolled if total_enrolled else 0.0
        )
        headline["certification_rate"] = (
            total_certified * 100 / total_enrolled if total_enrolled else 0.0
        )
        self.headline = headline

    async def _load_outcomes(self, session) -> None:
        pairs = (
            await session.execute(
                select(Assessment, Course)
                .join(Course, Course.id == Assessment.course_id)
                .order_by(Assessment.title)
            )
        ).all()
        rows: list[AssessmentSeriesRow] = []
        total_results = 0
        total_passes = 0
        score_sum = 0.0
        index = 0
        for assessment, course in pairs:
            results = int(
                await session.scalar(
                    select(func.count())
                    .select_from(AssessmentResult)
                    .where(AssessmentResult.assessment_id == assessment.id)
                )
                or 0
            )
            attempts = int(
                await session.scalar(
                    select(func.count())
                    .select_from(AssessmentAttempt)
                    .where(AssessmentAttempt.assessment_id == assessment.id)
                )
                or 0
            )
            if results == 0 and attempts == 0:
                continue
            index += 1
            passes = int(
                await session.scalar(
                    select(func.count())
                    .select_from(AssessmentResult)
                    .where(
                        AssessmentResult.assessment_id == assessment.id,
                        AssessmentResult.is_passed.is_(True),
                    )
                )
                or 0
            )
            avg_score = float(
                await session.scalar(
                    select(func.avg(AssessmentResult.percentage)).where(
                        AssessmentResult.assessment_id == assessment.id
                    )
                )
                or 0.0
            )
            total_results += results
            total_passes += passes
            score_sum += avg_score * results
            rows.append(
                {
                    "index": index,
                    "title": assessment.title,
                    "code": course.code,
                    "attempts": attempts,
                    "results": results,
                    "pass_rate": int(round(passes * 100 / results))
                    if results
                    else 0,
                    "avg_score": avg_score,
                }
            )
        self.assessment_series = rows
        headline = dict(self.headline)
        headline["pass_rate"] = (
            total_passes * 100 / total_results if total_results else 0.0
        )
        headline["average_score"] = (
            score_sum / total_results if total_results else 0.0
        )
        self.headline = headline

    async def _load_role_mix(self, session) -> None:
        rows: list[RoleRow] = []
        total = int(
            await session.scalar(select(func.count()).select_from(User)) or 0
        )
        for role in (
            UserRole.TRAINEE.value,
            UserRole.TRAINER.value,
            UserRole.ADMIN.value,
        ):
            count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(User)
                    .where(User.role == role)
                )
                or 0
            )
            rows.append(
                {
                    "role": role,
                    "count": count,
                    "share": int(round(count * 100 / total)) if total else 0,
                }
            )
        self.role_mix = rows

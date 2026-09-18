"""Course discovery, enrolment, module resources and course feedback."""

from __future__ import annotations

import datetime as dt
import logging
import secrets
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    Assessment,
    AssessmentResult,
    Certificate,
    Course,
    CourseFeedback,
    CourseRequiredSkill,
    CourseStatus,
    CourseTrainerAssignment,
    Enrollment,
    EnrollmentStatus,
    LearningResource,
    ResourceProgress,
    Skill,
    User,
)
from app.seed import ensure_seed_data
from app.services.email_notifications import enqueue
from app.states.trainee_state import grade_for, parse_int

logger = logging.getLogger(__name__)


class DiscoverCourse(TypedDict):
    id: int
    code: str
    title: str
    summary: str
    category: str
    level: str
    mode: str
    duration_hours: float
    start_date: str
    deadline: str
    trainer_name: str
    skills: list[str]
    capacity: int
    enrolled: int
    seats_left: int
    resource_count: int
    is_enrolled: bool
    is_open: bool
    closed_reason: str


class EnrolledCourse(TypedDict):
    enrollment_id: int
    course_id: int
    code: str
    title: str
    category: str
    status: str
    status_key: str
    progress: int
    completed_resources: int
    total_resources: int
    enrolled_at: str
    last_activity: str
    trainer_name: str


class ResourceItem(TypedDict):
    id: int
    title: str
    description: str
    resource_type: str
    duration_minutes: int
    external_url: str
    is_completed: bool


class ModuleGroup(TypedDict):
    name: str
    total: int
    completed: int
    percent: int
    resources: list[ResourceItem]


class FeedbackCourse(TypedDict):
    course_id: int
    code: str
    title: str
    trainer_name: str
    submitted: bool
    overall_rating: int
    content_rating: int
    trainer_rating: int
    relevance_rating: int
    comments: str
    suggestions: str
    updated: str


EMPTY_FEEDBACK: FeedbackCourse = {
    "course_id": 0,
    "code": "",
    "title": "",
    "trainer_name": "",
    "submitted": False,
    "overall_rating": 5,
    "content_rating": 5,
    "trainer_rating": 5,
    "relevance_rating": 5,
    "comments": "",
    "suggestions": "",
    "updated": "",
}


class TraineeLearningState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    discovery: list[DiscoverCourse] = []
    categories: list[str] = ["All"]
    levels: list[str] = [
        "All",
        "Beginner",
        "Intermediate",
        "Advanced",
        "Expert",
    ]
    search_query: str = ""
    category_filter: str = "All"
    level_filter: str = "All"
    only_open: bool = False

    enrollments: list[EnrolledCourse] = []
    selected_enrollment_id: int = 0
    modules: list[ModuleGroup] = []

    feedback_courses: list[FeedbackCourse] = []
    active_feedback: FeedbackCourse = EMPTY_FEEDBACK
    rating_options: list[int] = [1, 2, 3, 4, 5]

    async def _uid(self) -> int:
        from app.security import validate_role

        return await validate_role(self, "trainee")

    # ------------------------------------------------------------ computed
    @rx.var
    def filtered_courses(self) -> list[DiscoverCourse]:
        needle = self.search_query.strip().lower()
        results: list[DiscoverCourse] = []
        for course in self.discovery:
            if (
                self.category_filter != "All"
                and course["category"] != self.category_filter
            ):
                continue
            if (
                self.level_filter != "All"
                and course["level"] != self.level_filter
            ):
                continue
            if self.only_open and not course["is_open"]:
                continue
            haystack = (
                f"{course['title']} {course['code']} {course['summary']} "
                f"{course['trainer_name']} {' '.join(course['skills'])}"
            ).lower()
            if needle and needle not in haystack:
                continue
            results.append(course)
        return results

    @rx.var
    def discovery_count_label(self) -> str:
        return f"{len(self.filtered_courses)} of {len(self.discovery)} published courses"

    @rx.var
    def selected_enrollment(self) -> EnrolledCourse | None:
        for item in self.enrollments:
            if item["enrollment_id"] == self.selected_enrollment_id:
                return item
        return None

    @rx.var
    def selected_title(self) -> str:
        current = self.selected_enrollment
        return current["title"] if current else ""

    @rx.var
    def selected_progress(self) -> int:
        current = self.selected_enrollment
        return current["progress"] if current else 0

    @rx.var
    def selected_code(self) -> str:
        current = self.selected_enrollment
        return current["code"] if current else ""

    @rx.var
    def has_modules(self) -> bool:
        return len(self.modules) > 0

    @rx.var
    def feedback_open(self) -> bool:
        return self.active_feedback["course_id"] > 0

    # ------------------------------------------------------------- setters
    @rx.event
    def set_search_query(self, value: str):
        self.search_query = value

    @rx.event
    def set_category_filter(self, value: str):
        self.category_filter = value

    @rx.event
    def set_level_filter(self, value: str):
        self.level_filter = value

    @rx.event
    def toggle_only_open(self):
        self.only_open = not self.only_open

    @rx.event
    def clear_filters(self):
        self.search_query = ""
        self.category_filter = "All"
        self.level_filter = "All"
        self.only_open = False

    # ------------------------------------------------------------ discovery
    async def _load_discovery(self, session, uid: int) -> None:
        today = dt.date.today()
        enrolled_ids = set(
            (
                await session.scalars(
                    select(Enrollment.course_id).where(
                        Enrollment.trainee_id == uid
                    )
                )
            ).all()
        )
        rows = (
            await session.scalars(
                select(Course)
                .where(Course.status == CourseStatus.PUBLISHED.value)
                .order_by(Course.start_date.desc().nullslast(), Course.id)
            )
        ).all()
        cards: list[DiscoverCourse] = []
        categories: set[str] = set()
        for course in rows:
            skills = list(
                (
                    await session.scalars(
                        select(Skill.name)
                        .join(
                            CourseRequiredSkill,
                            CourseRequiredSkill.skill_id == Skill.id,
                        )
                        .where(CourseRequiredSkill.course_id == course.id)
                        .order_by(CourseRequiredSkill.weight.desc())
                    )
                ).all()
            )
            trainer = await session.scalar(
                select(User.full_name)
                .join(
                    CourseTrainerAssignment,
                    CourseTrainerAssignment.trainer_id == User.id,
                )
                .where(CourseTrainerAssignment.course_id == course.id)
                .order_by(CourseTrainerAssignment.match_score.desc())
                .limit(1)
            )
            enrolled = int(
                await session.scalar(
                    select(func.count(Enrollment.id)).where(
                        Enrollment.course_id == course.id
                    )
                )
                or 0
            )
            seats_left = max(course.capacity - enrolled, 0)
            reason = ""
            if (
                course.enrollment_deadline
                and course.enrollment_deadline < today
            ):
                reason = f"Enrolment closed on {course.enrollment_deadline.strftime('%d %b %Y')}"
            elif course.capacity > 0 and seats_left == 0:
                reason = "All seats have been allotted"
            resource_count = int(
                await session.scalar(
                    select(func.count(LearningResource.id)).where(
                        LearningResource.course_id == course.id,
                        LearningResource.is_published.is_(True),
                    )
                )
                or 0
            )
            cards.append(
                {
                    "id": course.id,
                    "code": course.code,
                    "title": course.title,
                    "summary": course.summary,
                    "category": course.category or "General",
                    "level": course.level.capitalize(),
                    "mode": course.mode.capitalize(),
                    "duration_hours": float(course.duration_hours),
                    "start_date": (
                        course.start_date.strftime("%d %b %Y")
                        if course.start_date
                        else "Rolling intake"
                    ),
                    "deadline": (
                        course.enrollment_deadline.strftime("%d %b %Y")
                        if course.enrollment_deadline
                        else "Open"
                    ),
                    "trainer_name": trainer or "Trainer to be assigned",
                    "skills": skills,
                    "capacity": course.capacity,
                    "enrolled": enrolled,
                    "seats_left": seats_left,
                    "resource_count": resource_count,
                    "is_enrolled": course.id in enrolled_ids,
                    "is_open": reason == "",
                    "closed_reason": reason,
                }
            )
            categories.add(course.category or "General")
        self.discovery = cards
        self.categories = ["All", *sorted(categories)]

    @rx.event
    async def load_discovery(self):
        ensure_seed_data()
        uid = await self._uid()
        if uid <= 0:
            return
        self.is_loading = True
        self.error_message = ""
        yield
        try:
            async with rx.asession() as session:
                await self._load_discovery(session, uid)
        except Exception as exception:
            logging.exception(f"Error loading course discovery: {exception}")
            self.error_message = "Could not load the course catalogue. Retry."
        self.is_loading = False

    @rx.event
    async def enroll(self, course_id: int):
        self.error_message = ""
        self.success_message = ""
        uid = await self._uid()
        if uid <= 0:
            return rx.redirect("/login")
        code = ""
        try:
            async with rx.asession() as session:
                course = await session.get(Course, course_id)
                if course is None:
                    self.error_message = "That course no longer exists."
                    return
                if course.status != CourseStatus.PUBLISHED.value:
                    self.error_message = (
                        "This course is not open for enrolment."
                    )
                    return
                existing = await session.scalar(
                    select(Enrollment).where(
                        Enrollment.course_id == course_id,
                        Enrollment.trainee_id == uid,
                    )
                )
                if existing is not None:
                    self.error_message = (
                        f"You are already enrolled in {course.code}."
                    )
                    return
                today = dt.date.today()
                if (
                    course.enrollment_deadline
                    and course.enrollment_deadline < today
                ):
                    self.error_message = (
                        "The enrolment deadline for this course has passed."
                    )
                    return
                enrolled = int(
                    await session.scalar(
                        select(func.count(Enrollment.id)).where(
                            Enrollment.course_id == course_id
                        )
                    )
                    or 0
                )
                if course.capacity > 0 and enrolled >= course.capacity:
                    self.error_message = "This cohort is full. Watch announcements for the next batch."
                    return
                session.add(
                    Enrollment(
                        course_id=course_id,
                        trainee_id=uid,
                        status=EnrollmentStatus.ACTIVE.value,
                        last_activity_at=dt.datetime.now(dt.UTC),
                    )
                )
                await session.commit()
                await self._load_discovery(session, uid)
                code = course.code
        except Exception as exception:
            logging.exception(f"Error enrolling trainee: {exception}")
            self.error_message = "Could not complete the enrolment. Try again."
            return
        self.success_message = f"Enrolled in {code}. The module library is now available under My learning."

    # ---------------------------------------------------------- my learning
    async def _load_enrollments(self, session, uid: int) -> None:
        rows = (
            await session.execute(
                select(Enrollment, Course)
                .join(Course, Course.id == Enrollment.course_id)
                .where(Enrollment.trainee_id == uid)
                .order_by(Enrollment.enrolled_at.desc())
            )
        ).all()
        items: list[EnrolledCourse] = []
        for enrollment, course in rows:
            total = int(
                await session.scalar(
                    select(func.count(LearningResource.id)).where(
                        LearningResource.course_id == course.id,
                        LearningResource.is_published.is_(True),
                    )
                )
                or 0
            )
            done = int(
                await session.scalar(
                    select(func.count(ResourceProgress.id)).where(
                        ResourceProgress.enrollment_id == enrollment.id,
                        ResourceProgress.is_completed.is_(True),
                    )
                )
                or 0
            )
            trainer = await session.scalar(
                select(User.full_name)
                .join(
                    CourseTrainerAssignment,
                    CourseTrainerAssignment.trainer_id == User.id,
                )
                .where(CourseTrainerAssignment.course_id == course.id)
                .order_by(CourseTrainerAssignment.match_score.desc())
                .limit(1)
            )
            items.append(
                {
                    "enrollment_id": enrollment.id,
                    "course_id": course.id,
                    "code": course.code,
                    "title": course.title,
                    "category": course.category or "General",
                    "status": enrollment.status.replace("_", " ").capitalize(),
                    "status_key": enrollment.status,
                    "progress": int(enrollment.progress_percent),
                    "completed_resources": done,
                    "total_resources": total,
                    "enrolled_at": enrollment.enrolled_at.strftime("%d %b %Y"),
                    "last_activity": (
                        enrollment.last_activity_at.strftime("%d %b %Y")
                        if enrollment.last_activity_at
                        else "No activity yet"
                    ),
                    "trainer_name": trainer or "Trainer to be assigned",
                }
            )
        self.enrollments = items

    async def _load_modules(self, session, uid: int) -> None:
        self.modules = []
        if self.selected_enrollment_id <= 0:
            return
        enrollment = await session.scalar(
            select(Enrollment).where(
                Enrollment.id == self.selected_enrollment_id,
                Enrollment.trainee_id == uid,
            )
        )
        if enrollment is None:
            self.selected_enrollment_id = 0
            return
        resources = (
            await session.scalars(
                select(LearningResource)
                .where(
                    LearningResource.course_id == enrollment.course_id,
                    LearningResource.is_published.is_(True),
                )
                .order_by(
                    LearningResource.module_name,
                    LearningResource.sort_order,
                    LearningResource.id,
                )
            )
        ).all()
        progress_map = {
            row.resource_id: bool(row.is_completed)
            for row in (
                await session.scalars(
                    select(ResourceProgress).where(
                        ResourceProgress.enrollment_id == enrollment.id
                    )
                )
            ).all()
        }
        grouped: dict[str, list[ResourceItem]] = {}
        for resource in resources:
            module = resource.module_name or "General module"
            grouped.setdefault(module, []).append(
                {
                    "id": resource.id,
                    "title": resource.title,
                    "description": resource.description,
                    "resource_type": resource.resource_type.capitalize(),
                    "duration_minutes": int(resource.duration_minutes),
                    "external_url": resource.external_url,
                    "is_completed": progress_map.get(resource.id, False),
                }
            )
        modules: list[ModuleGroup] = []
        for name, items in grouped.items():
            done = len([item for item in items if item["is_completed"]])
            modules.append(
                {
                    "name": name,
                    "total": len(items),
                    "completed": done,
                    "percent": int(done / len(items) * 100) if items else 0,
                    "resources": items,
                }
            )
        self.modules = modules

    @rx.event
    async def load_my_learning(self):
        ensure_seed_data()
        uid = await self._uid()
        if uid <= 0:
            return
        self.is_loading = True
        self.error_message = ""
        yield
        try:
            async with rx.asession() as session:
                await self._load_enrollments(session, uid)
                if self.selected_enrollment_id <= 0 and self.enrollments:
                    self.selected_enrollment_id = self.enrollments[0][
                        "enrollment_id"
                    ]
                await self._load_modules(session, uid)
        except Exception as exception:
            logging.exception(f"Error loading trainee learning: {exception}")
            self.error_message = "Could not load your module library. Retry."
        self.is_loading = False

    @rx.event
    async def select_enrollment(self, enrollment_id: int):
        self.error_message = ""
        self.success_message = ""
        self.selected_enrollment_id = enrollment_id
        uid = await self._uid()
        if uid <= 0:
            return
        try:
            async with rx.asession() as session:
                await self._load_modules(session, uid)
        except Exception as exception:
            logging.exception(f"Error selecting enrollment: {exception}")
            self.error_message = "Could not open that course."

    async def _recalculate(self, session, enrollment: Enrollment) -> float:
        total = int(
            await session.scalar(
                select(func.count(LearningResource.id)).where(
                    LearningResource.course_id == enrollment.course_id,
                    LearningResource.is_published.is_(True),
                )
            )
            or 0
        )
        done = int(
            await session.scalar(
                select(func.count(ResourceProgress.id)).where(
                    ResourceProgress.enrollment_id == enrollment.id,
                    ResourceProgress.is_completed.is_(True),
                )
            )
            or 0
        )
        percent = (done / total * 100) if total else 0.0
        enrollment.progress_percent = round(percent, 1)
        enrollment.last_activity_at = dt.datetime.now(dt.UTC)
        if percent >= 100.0 and total > 0:
            enrollment.status = EnrollmentStatus.COMPLETED.value
            enrollment.completed_at = dt.datetime.now(dt.UTC)
        elif enrollment.status == EnrollmentStatus.COMPLETED.value:
            enrollment.status = EnrollmentStatus.ACTIVE.value
            enrollment.completed_at = None
        await session.commit()
        return percent

    async def _maybe_issue_certificate(
        self, session, enrollment: Enrollment, uid: int
    ) -> bool:
        if enrollment.status != EnrollmentStatus.COMPLETED.value:
            return False
        existing = await session.scalar(
            select(Certificate).where(
                Certificate.course_id == enrollment.course_id,
                Certificate.trainee_id == uid,
            )
        )
        if existing is not None:
            return False
        best = await session.scalar(
            select(func.max(AssessmentResult.percentage))
            .join(
                Assessment,
                Assessment.id == AssessmentResult.assessment_id,
            )
            .where(
                AssessmentResult.trainee_id == uid,
                AssessmentResult.is_passed.is_(True),
                Assessment.course_id == enrollment.course_id,
            )
        )
        final_score = float(best or 0.0)
        course = await session.get(Course, enrollment.course_id)
        if course is None:
            return False
        certificate = Certificate(
            certificate_number=f"CC-{course.code}-{uid}-{secrets.token_hex(2).upper()}",
            course_id=course.id,
            trainee_id=uid,
            final_score=final_score,
            grade=grade_for(final_score) if final_score else "P",
            verification_code=secrets.token_hex(32),
        )
        session.add(certificate)
        await session.flush()
        await enqueue(session, "certificate_issued", certificate)
        await session.commit()
        return True

    @rx.event
    async def toggle_resource(self, resource_id: int):
        self.error_message = ""
        self.success_message = ""
        uid = await self._uid()
        if uid <= 0:
            return rx.redirect("/login")
        percent = 0.0
        issued = False
        try:
            async with rx.asession() as session:
                enrollment = await session.scalar(
                    select(Enrollment).where(
                        Enrollment.id == self.selected_enrollment_id,
                        Enrollment.trainee_id == uid,
                    )
                )
                if enrollment is None:
                    self.error_message = "Open one of your courses first."
                    return
                resource = await session.scalar(
                    select(LearningResource).where(
                        LearningResource.id == resource_id,
                        LearningResource.course_id == enrollment.course_id,
                    )
                )
                if resource is None:
                    self.error_message = (
                        "That resource is not part of this course."
                    )
                    return
                record = await session.scalar(
                    select(ResourceProgress).where(
                        ResourceProgress.enrollment_id == enrollment.id,
                        ResourceProgress.resource_id == resource_id,
                    )
                )
                if record is None:
                    record = ResourceProgress(
                        enrollment_id=enrollment.id, resource_id=resource_id
                    )
                    session.add(record)
                record.is_completed = not record.is_completed
                record.completed_at = (
                    dt.datetime.now(dt.UTC) if record.is_completed else None
                )
                if record.is_completed:
                    record.time_spent_minutes = max(
                        record.time_spent_minutes, resource.duration_minutes
                    )
                await session.commit()
                percent = await self._recalculate(session, enrollment)
                issued = await self._maybe_issue_certificate(
                    session, enrollment, uid
                )
                await self._load_enrollments(session, uid)
                await self._load_modules(session, uid)
        except Exception as exception:
            logging.exception(f"Error toggling resource: {exception}")
            self.error_message = "Could not update the resource progress."
            return
        if issued:
            self.success_message = "Course completed at 100% — a certificate record has been issued."
        else:
            self.success_message = (
                f"Progress recalculated: {percent:.0f}% complete."
            )

    # ------------------------------------------------------------- feedback
    async def _load_feedback(self, session, uid: int) -> None:
        rows = (
            await session.execute(
                select(Enrollment, Course)
                .join(Course, Course.id == Enrollment.course_id)
                .where(
                    Enrollment.trainee_id == uid,
                    Enrollment.status == EnrollmentStatus.COMPLETED.value,
                )
                .order_by(Enrollment.completed_at.desc().nullslast())
            )
        ).all()
        items: list[FeedbackCourse] = []
        for _enrollment, course in rows:
            record = await session.scalar(
                select(CourseFeedback).where(
                    CourseFeedback.course_id == course.id,
                    CourseFeedback.trainee_id == uid,
                )
            )
            trainer = await session.scalar(
                select(User.full_name)
                .join(
                    CourseTrainerAssignment,
                    CourseTrainerAssignment.trainer_id == User.id,
                )
                .where(CourseTrainerAssignment.course_id == course.id)
                .order_by(CourseTrainerAssignment.match_score.desc())
                .limit(1)
            )
            items.append(
                {
                    "course_id": course.id,
                    "code": course.code,
                    "title": course.title,
                    "trainer_name": trainer or "Trainer to be assigned",
                    "submitted": record is not None,
                    "overall_rating": record.overall_rating if record else 5,
                    "content_rating": record.content_rating if record else 5,
                    "trainer_rating": record.trainer_rating if record else 5,
                    "relevance_rating": record.relevance_rating
                    if record
                    else 5,
                    "comments": record.comments if record else "",
                    "suggestions": record.suggestions if record else "",
                    "updated": (
                        record.updated_at.strftime("%d %b %Y") if record else ""
                    ),
                }
            )
        self.feedback_courses = items

    @rx.event
    async def load_feedback(self):
        ensure_seed_data()
        uid = await self._uid()
        if uid <= 0:
            return
        self.is_loading = True
        self.error_message = ""
        self.active_feedback = EMPTY_FEEDBACK
        yield
        try:
            async with rx.asession() as session:
                await self._load_feedback(session, uid)
        except Exception as exception:
            logging.exception(f"Error loading feedback: {exception}")
            self.error_message = "Could not load your feedback records."
        self.is_loading = False

    @rx.event
    def open_feedback(self, record: FeedbackCourse):
        self.error_message = ""
        self.success_message = ""
        self.active_feedback = record

    @rx.event
    def close_feedback(self):
        self.active_feedback = EMPTY_FEEDBACK

    @rx.event
    async def submit_feedback(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        uid = await self._uid()
        if uid <= 0:
            return rx.redirect("/login")
        course_id = self.active_feedback["course_id"]
        if course_id <= 0:
            self.error_message = "Select a completed course first."
            return
        ratings = {
            key: parse_int(str(form_data.get(key, "0")))
            for key in (
                "overall_rating",
                "content_rating",
                "trainer_rating",
                "relevance_rating",
            )
        }
        for key, value in ratings.items():
            if value < 1 or value > 5:
                self.error_message = (
                    "Every rating must be a whole number between 1 and 5."
                )
                return
        comments = str(form_data.get("comments", "")).strip()
        suggestions = str(form_data.get("suggestions", "")).strip()
        if len(comments) < 20:
            self.error_message = (
                "Please write at least 20 characters of feedback comments."
            )
            return
        if len(comments) > 1500:
            self.error_message = "Comments must be under 1500 characters."
            return
        updated = False
        try:
            async with rx.asession() as session:
                enrollment = await session.scalar(
                    select(Enrollment).where(
                        Enrollment.course_id == course_id,
                        Enrollment.trainee_id == uid,
                    )
                )
                if (
                    enrollment is None
                    or enrollment.status != EnrollmentStatus.COMPLETED.value
                ):
                    self.error_message = (
                        "Feedback opens once the course is completed."
                    )
                    return
                trainer_id = await session.scalar(
                    select(CourseTrainerAssignment.trainer_id)
                    .where(CourseTrainerAssignment.course_id == course_id)
                    .order_by(CourseTrainerAssignment.match_score.desc())
                    .limit(1)
                )
                record = await session.scalar(
                    select(CourseFeedback).where(
                        CourseFeedback.course_id == course_id,
                        CourseFeedback.trainee_id == uid,
                    )
                )
                updated = record is not None
                if record is None:
                    record = CourseFeedback(course_id=course_id, trainee_id=uid)
                    session.add(record)
                record.trainer_id = trainer_id
                record.overall_rating = ratings["overall_rating"]
                record.content_rating = ratings["content_rating"]
                record.trainer_rating = ratings["trainer_rating"]
                record.relevance_rating = ratings["relevance_rating"]
                record.comments = comments
                record.suggestions = suggestions
                record.is_anonymous = bool(form_data.get("is_anonymous"))
                await session.commit()
                await self._load_feedback(session, uid)
        except Exception as exception:
            logging.exception(f"Error saving feedback: {exception}")
            self.error_message = "Could not save your feedback. Try again."
            return
        self.active_feedback = EMPTY_FEEDBACK
        self.success_message = (
            "Feedback updated." if updated else "Thank you — feedback recorded."
        )

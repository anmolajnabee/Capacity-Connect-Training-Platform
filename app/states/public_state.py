"""Database-backed content for the public CAPACITY CONNECT routes."""

from __future__ import annotations

import logging
from typing import TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    Announcement,
    ApprovalStatus,
    Assessment,
    Certificate,
    Course,
    CourseRequiredSkill,
    CourseStatus,
    CourseTrainerAssignment,
    Enrollment,
    LearningResource,
    Skill,
    TrainerProfile,
    User,
    UserRole,
    UserSkill,
)
from app.seed import ensure_seed_data

logger = logging.getLogger(__name__)


class CourseCard(TypedDict):
    id: int
    code: str
    title: str
    summary: str
    category: str
    level: str
    mode: str
    duration_hours: float
    capacity: int
    enrolled: int
    seats_left: int
    start_date: str
    deadline: str
    trainer_name: str
    skills: list[str]
    resource_count: int
    assessment_count: int


class TrainerCard(TypedDict):
    id: int
    name: str
    designation: str
    department: str
    organization: str
    specialization: str
    years: float
    rating: float
    rating_count: int
    is_available: bool
    avatar_seed: str
    skills: list[str]
    courses: list[str]


class AnnouncementItem(TypedDict):
    id: int
    title: str
    body: str
    audience: str
    author: str
    course: str
    published: str
    is_pinned: bool


class PathwayStage(TypedDict):
    step: str
    stage: str
    icon: str
    headline: str
    detail: str
    metric: str


class PublicState(rx.State):
    is_loading: bool = False
    load_error: str = ""

    stats: dict[str, int] = {
        "courses": 0,
        "trainers": 0,
        "trainees": 0,
        "resources": 0,
        "assessments": 0,
        "certificates": 0,
        "enrollments": 0,
        "skills": 0,
    }
    courses: list[CourseCard] = []
    trainers: list[TrainerCard] = []
    announcements: list[AnnouncementItem] = []
    pathway: list[PathwayStage] = []
    categories: list[str] = []

    search_query: str = ""
    category_filter: str = "All"
    audience_filter: str = "all"

    @rx.var
    def has_content(self) -> bool:
        return len(self.courses) > 0

    @rx.var
    def filtered_courses(self) -> list[CourseCard]:
        needle = self.search_query.strip().lower()
        results: list[CourseCard] = []
        for course in self.courses:
            if (
                self.category_filter != "All"
                and course["category"] != self.category_filter
            ):
                continue
            if (
                needle
                and needle
                not in (
                    f"{course['title']} {course['code']} {course['summary']} "
                    f"{course['trainer_name']} {' '.join(course['skills'])}"
                ).lower()
            ):
                continue
            results.append(course)
        return results

    @rx.var
    def featured_courses(self) -> list[CourseCard]:
        return self.courses[:3]

    @rx.var
    def featured_trainers(self) -> list[TrainerCard]:
        return self.trainers[:3]

    @rx.var
    def latest_announcements(self) -> list[AnnouncementItem]:
        return self.announcements[:3]

    @rx.var
    def filtered_announcements(self) -> list[AnnouncementItem]:
        if self.audience_filter == "all":
            return self.announcements
        return [
            item
            for item in self.announcements
            if item["audience"] in (self.audience_filter, "all")
        ]

    @rx.event
    def set_search_query(self, value: str):
        self.search_query = value

    @rx.event
    def set_category_filter(self, value: str):
        self.category_filter = value

    @rx.event
    def set_audience_filter(self, value: str):
        self.audience_filter = value

    @rx.event
    def load_public_content(self):
        ensure_seed_data()
        self.is_loading = True
        self.load_error = ""
        yield
        try:
            with rx.session() as session:
                self._load_stats(session)
                self._load_courses(session)
                self._load_trainers(session)
                self._load_announcements(session)
                self._build_pathway()
        except Exception as exception:
            logging.exception(f"Error loading public content: {exception}")
            self.load_error = (
                "We could not reach the training registry. Please retry."
            )
        self.is_loading = False

    # ------------------------------------------------------------- internals
    def _count(self, session, statement) -> int:
        return int(session.scalar(statement) or 0)

    def _load_stats(self, session) -> None:
        self.stats = {
            "courses": self._count(
                session,
                select(func.count(Course.id)).where(
                    Course.status == CourseStatus.PUBLISHED.value
                ),
            ),
            "trainers": self._count(
                session,
                select(func.count(User.id)).where(
                    User.role == UserRole.TRAINER.value,
                    User.approval_status == ApprovalStatus.APPROVED.value,
                ),
            ),
            "trainees": self._count(
                session,
                select(func.count(User.id)).where(
                    User.role == UserRole.TRAINEE.value
                ),
            ),
            "resources": self._count(
                session, select(func.count(LearningResource.id))
            ),
            "assessments": self._count(
                session, select(func.count(Assessment.id))
            ),
            "certificates": self._count(
                session, select(func.count(Certificate.id))
            ),
            "enrollments": self._count(
                session, select(func.count(Enrollment.id))
            ),
            "skills": self._count(session, select(func.count(Skill.id))),
        }

    def _load_courses(self, session) -> None:
        rows = (
            session.scalars(
                select(Course)
                .where(Course.status == CourseStatus.PUBLISHED.value)
                .order_by(Course.start_date.desc().nullslast(), Course.id)
            )
            .unique()
            .all()
        )
        cards: list[CourseCard] = []
        categories: set[str] = set()
        for course in rows:
            skill_names = list(
                session.scalars(
                    select(Skill.name)
                    .join(
                        CourseRequiredSkill,
                        CourseRequiredSkill.skill_id == Skill.id,
                    )
                    .where(CourseRequiredSkill.course_id == course.id)
                    .order_by(CourseRequiredSkill.weight.desc())
                ).all()
            )
            lead_name = session.scalar(
                select(User.full_name)
                .join(
                    CourseTrainerAssignment,
                    CourseTrainerAssignment.trainer_id == User.id,
                )
                .where(CourseTrainerAssignment.course_id == course.id)
                .order_by(CourseTrainerAssignment.match_score.desc())
                .limit(1)
            )
            enrolled = self._count(
                session,
                select(func.count(Enrollment.id)).where(
                    Enrollment.course_id == course.id
                ),
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
                    "capacity": course.capacity,
                    "enrolled": enrolled,
                    "seats_left": max(course.capacity - enrolled, 0),
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
                    "trainer_name": lead_name or "Trainer to be assigned",
                    "skills": skill_names,
                    "resource_count": self._count(
                        session,
                        select(func.count(LearningResource.id)).where(
                            LearningResource.course_id == course.id
                        ),
                    ),
                    "assessment_count": self._count(
                        session,
                        select(func.count(Assessment.id)).where(
                            Assessment.course_id == course.id
                        ),
                    ),
                }
            )
            categories.add(course.category or "General")
        self.courses = cards
        self.categories = ["All", *sorted(categories)]

    def _load_trainers(self, session) -> None:
        rows = session.scalars(
            select(User)
            .where(
                User.role == UserRole.TRAINER.value,
                User.approval_status == ApprovalStatus.APPROVED.value,
            )
            .order_by(User.full_name)
        ).all()
        cards: list[TrainerCard] = []
        for user in rows:
            profile = session.scalar(
                select(TrainerProfile).where(TrainerProfile.user_id == user.id)
            )
            skill_names = list(
                session.scalars(
                    select(Skill.name)
                    .join(UserSkill, UserSkill.skill_id == Skill.id)
                    .where(
                        UserSkill.user_id == user.id,
                        UserSkill.is_teachable.is_(True),
                    )
                    .order_by(UserSkill.proficiency_score.desc())
                ).all()
            )
            course_titles = list(
                session.scalars(
                    select(Course.title)
                    .join(
                        CourseTrainerAssignment,
                        CourseTrainerAssignment.course_id == Course.id,
                    )
                    .where(CourseTrainerAssignment.trainer_id == user.id)
                    .order_by(Course.title)
                ).all()
            )
            cards.append(
                {
                    "id": user.id,
                    "name": user.full_name,
                    "designation": profile.designation if profile else "",
                    "department": profile.department if profile else "",
                    "organization": profile.organization if profile else "",
                    "specialization": profile.specialization if profile else "",
                    "years": float(profile.years_of_training)
                    if profile
                    else 0.0,
                    "rating": float(profile.rating_average) if profile else 0.0,
                    "rating_count": profile.rating_count if profile else 0,
                    "is_available": bool(profile.is_available)
                    if profile
                    else False,
                    "avatar_seed": user.avatar_seed or user.email,
                    "skills": skill_names,
                    "courses": course_titles,
                }
            )
        self.trainers = cards

    def _load_announcements(self, session) -> None:
        rows = session.scalars(
            select(Announcement)
            .where(
                Announcement.is_published.is_(True),
                Announcement.published_at <= func.now(),
            )
            .order_by(
                Announcement.is_pinned.desc(),
                Announcement.published_at.desc().nullslast(),
            )
        ).all()
        items: list[AnnouncementItem] = []
        for record in rows:
            author = (
                session.scalar(
                    select(User.full_name).where(User.id == record.author_id)
                )
                if record.author_id
                else None
            )
            course_title = (
                session.scalar(
                    select(Course.title).where(Course.id == record.course_id)
                )
                if record.course_id
                else None
            )
            items.append(
                {
                    "id": record.id,
                    "title": record.title,
                    "body": record.body,
                    "audience": record.audience,
                    "author": author or "Capacity Connect Secretariat",
                    "course": course_title or "",
                    "published": (
                        record.published_at.strftime("%d %b %Y")
                        if record.published_at
                        else "Unpublished"
                    ),
                    "is_pinned": bool(record.is_pinned),
                }
            )
        self.announcements = items

    def _build_pathway(self) -> None:
        first = self.courses[0] if self.courses else None
        self.pathway = [
            {
                "step": "01",
                "stage": "Course",
                "icon": "book-open",
                "headline": first["title"] if first else "Published courses",
                "detail": (
                    f"{first['code']} · {first['level']} · {first['duration_hours']:.0f} hours"
                    if first
                    else "Curriculum mapped to required competencies."
                ),
                "metric": f"{self.stats['courses']} published",
            },
            {
                "step": "02",
                "stage": "Trainer",
                "icon": "user-check",
                "headline": (
                    first["trainer_name"] if first else "Matched faculty"
                ),
                "detail": "Assigned by competency match score against required skills.",
                "metric": f"{self.stats['trainers']} approved trainers",
            },
            {
                "step": "03",
                "stage": "Resources",
                "icon": "library",
                "headline": "Structured module library",
                "detail": "Documents, datasets, slide decks and recorded sessions per module.",
                "metric": f"{self.stats['resources']} resources",
            },
            {
                "step": "04",
                "stage": "Assessment",
                "icon": "clipboard-check",
                "headline": "Timed questionnaires",
                "detail": "MCQ assessments with deadlines, attempts and scored results.",
                "metric": f"{self.stats['assessments']} assessments",
            },
            {
                "step": "05",
                "stage": "Certificate",
                "icon": "award",
                "headline": "Verified certification",
                "detail": "Numbered certificates with verification codes on completion.",
                "metric": f"{self.stats['certificates']} issued",
            },
        ]

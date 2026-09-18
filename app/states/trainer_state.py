"""Trainer identity, expertise profile, qualifications, experience and skills."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    ApprovalStatus,
    Assessment,
    Course,
    CourseTrainerAssignment,
    Enrollment,
    EnrollmentStatus,
    LearningResource,
    ProficiencyLevel,
    Qualification,
    Skill,
    TrainerProfile,
    UserRole,
    UserSkill,
    WorkExperience,
)
from app.states.auth_state import AuthState

logger = logging.getLogger(__name__)

LEVELS: list[str] = [level.value for level in ProficiencyLevel]


class QualificationRow(TypedDict):
    id: int
    degree: str
    field_of_study: str
    institution: str
    start_year: int
    end_year: int
    grade: str
    verified: bool


class ExperienceRow(TypedDict):
    id: int
    organization: str
    role_title: str
    location: str
    start_date: str
    end_date: str
    is_current: bool
    responsibilities: str


class SkillRow(TypedDict):
    id: int
    name: str
    category: str
    level: str
    score: int
    years: float


class DashboardCourse(TypedDict):
    id: int
    code: str
    title: str
    role: str
    cohort: int
    completed: int
    completion: int


async def trainer_guard(state: rx.State) -> int:
    """Return the authenticated approved trainer id, or 0."""
    from app.security import validate_role

    return await validate_role(state, "trainer")


async def trainer_course_ids(session, trainer_id: int) -> list[int]:
    rows = await session.scalars(
        select(CourseTrainerAssignment.course_id).where(
            CourseTrainerAssignment.trainer_id == trainer_id,
            CourseTrainerAssignment.status == "approved",
        )
    )
    return list(rows.all())


def days_since(value: dt.datetime | None) -> int:
    if value is None:
        return 999
    moment = value
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.UTC)
    return max(0, (dt.datetime.now(dt.UTC) - moment).days)


class TrainerState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    # profile fields
    designation: str = ""
    department: str = ""
    organization: str = ""
    specialization: str = ""
    years_of_training: float = 0.0
    highest_qualification: str = ""
    bio: str = ""
    languages: str = ""
    is_available: bool = True
    profile_completion: int = 0
    rating_average: float = 0.0
    rating_count: int = 0

    qualifications: list[QualificationRow] = []
    experiences: list[ExperienceRow] = []
    skills: list[SkillRow] = []
    skill_catalog: list[str] = []

    metrics: dict[str, int] = {
        "courses": 0,
        "trainees": 0,
        "completed": 0,
        "at_risk": 0,
        "resources": 0,
        "assessments": 0,
        "open_assessments": 0,
    }
    average_score: float = 0.0
    dashboard_courses: list[DashboardCourse] = []

    @rx.var
    def teachable_count(self) -> int:
        return len(self.skills)

    def _reset_messages(self) -> None:
        self.error_message = ""
        self.success_message = ""

    # ------------------------------------------------------------- loaders
    async def _load_profile(self, session, trainer_id: int) -> None:
        profile = await session.scalar(
            select(TrainerProfile).where(TrainerProfile.user_id == trainer_id)
        )
        if profile is None:
            profile = TrainerProfile(user_id=trainer_id, profile_completion=10)
            session.add(profile)
            await session.commit()
            await session.refresh(profile)
        self.designation = profile.designation
        self.department = profile.department
        self.organization = profile.organization
        self.specialization = profile.specialization
        self.years_of_training = float(profile.years_of_training)
        self.highest_qualification = profile.highest_qualification
        self.bio = profile.bio
        self.languages = profile.languages
        self.is_available = profile.is_available
        self.profile_completion = int(profile.profile_completion)
        self.rating_average = float(profile.rating_average)
        self.rating_count = int(profile.rating_count)

        qualification_rows = (
            await session.scalars(
                select(Qualification)
                .where(Qualification.user_id == trainer_id)
                .order_by(Qualification.end_year.desc())
            )
        ).all()
        experience_rows = (
            await session.scalars(
                select(WorkExperience)
                .where(WorkExperience.user_id == trainer_id)
                .order_by(WorkExperience.start_date.desc())
            )
        ).all()
        skill_rows = (
            await session.execute(
                select(UserSkill, Skill)
                .join(Skill, Skill.id == UserSkill.skill_id)
                .where(UserSkill.user_id == trainer_id)
                .order_by(UserSkill.proficiency_score.desc())
            )
        ).all()
        catalog_rows = (
            await session.scalars(select(Skill.name).order_by(Skill.name))
        ).all()
        self.qualifications = [
            {
                "id": row.id,
                "degree": row.degree,
                "field_of_study": row.field_of_study,
                "institution": row.institution,
                "start_year": int(row.start_year or 0),
                "end_year": int(row.end_year or 0),
                "grade": row.grade,
                "verified": row.is_verified,
            }
            for row in qualification_rows
        ]
        self.experiences = [
            {
                "id": row.id,
                "organization": row.organization,
                "role_title": row.role_title,
                "location": row.location,
                "start_date": row.start_date.strftime("%b %Y")
                if row.start_date
                else "—",
                "end_date": "Present"
                if row.is_current
                else (row.end_date.strftime("%b %Y") if row.end_date else "—"),
                "is_current": row.is_current,
                "responsibilities": row.responsibilities,
            }
            for row in experience_rows
        ]
        self.skills = [
            {
                "id": link.id,
                "name": skill.name,
                "category": skill.category,
                "level": link.level,
                "score": int(link.proficiency_score),
                "years": float(link.years_of_practice),
            }
            for link, skill in skill_rows
        ]
        self.skill_catalog = [name for name in catalog_rows]

    @rx.event
    async def load_profile(self):
        self._reset_messages()
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load_profile(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error loading trainer profile: {exception}")
            self.error_message = "Could not load your expertise profile."
        self.is_loading = False

    @rx.event
    async def load_dashboard(self):
        self._reset_messages()
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load_profile(session, trainer_id)
                course_ids = await trainer_course_ids(session, trainer_id)
                cards: list[DashboardCourse] = []
                total_trainees = 0
                total_completed = 0
                at_risk = 0
                assignment_pairs = (
                    await session.execute(
                        select(CourseTrainerAssignment, Course)
                        .join(
                            Course,
                            Course.id == CourseTrainerAssignment.course_id,
                        )
                        .where(
                            CourseTrainerAssignment.trainer_id == trainer_id,
                            CourseTrainerAssignment.status == "approved",
                        )
                        .order_by(Course.start_date.desc().nullslast())
                    )
                ).all()
                for assignment, course in assignment_pairs:
                    rows = (
                        await session.scalars(
                            select(Enrollment).where(
                                Enrollment.course_id == course.id
                            )
                        )
                    ).all()
                    cohort = len(rows)
                    completed = len(
                        [
                            row
                            for row in rows
                            if row.status == EnrollmentStatus.COMPLETED.value
                        ]
                    )
                    at_risk += len(
                        [
                            row
                            for row in rows
                            if row.status == EnrollmentStatus.AT_RISK.value
                            or days_since(row.last_activity_at) > 14
                        ]
                    )
                    total_trainees += cohort
                    total_completed += completed
                    cards.append(
                        {
                            "id": course.id,
                            "code": course.code,
                            "title": course.title,
                            "role": assignment.assignment_role.replace(
                                "_", " "
                            ),
                            "cohort": cohort,
                            "completed": completed,
                            "completion": int(round(completed * 100 / cohort))
                            if cohort
                            else 0,
                        }
                    )
                self.dashboard_courses = cards
                resources = 0
                assessments = 0
                open_assessments = 0
                average = 0.0
                if course_ids:
                    resources = int(
                        await session.scalar(
                            select(func.count())
                            .select_from(LearningResource)
                            .where(LearningResource.course_id.in_(course_ids))
                        )
                        or 0
                    )
                    assessment_rows = (
                        await session.scalars(
                            select(Assessment).where(
                                Assessment.course_id.in_(course_ids)
                            )
                        )
                    ).all()
                    assessments = len(assessment_rows)
                    open_assessments = len(
                        [row for row in assessment_rows if row.status == "open"]
                    )
                    average = float(
                        await session.scalar(
                            select(func.avg(Enrollment.progress_percent)).where(
                                Enrollment.course_id.in_(course_ids)
                            )
                        )
                        or 0.0
                    )
                self.metrics = {
                    "courses": len(cards),
                    "trainees": total_trainees,
                    "completed": total_completed,
                    "at_risk": at_risk,
                    "resources": resources,
                    "assessments": assessments,
                    "open_assessments": open_assessments,
                }
                self.average_score = average
        except Exception as exception:
            logging.exception(f"Error loading trainer dashboard: {exception}")
            self.error_message = "Could not load your workspace summary."
        self.is_loading = False

    # -------------------------------------------------------------- profile
    @rx.event
    async def save_profile(self, form_data: dict[str, Any]):
        self._reset_messages()
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        designation = str(form_data.get("designation", "")).strip()
        if len(designation) < 2:
            self.error_message = "Enter your designation."
            return
        try:
            years = float(form_data.get("years_of_training") or 0)
        except ValueError:
            self.error_message = "Years of training must be a number."
            return
        if years < 0 or years > 60:
            self.error_message = "Years of training must be between 0 and 60."
            return
        try:
            async with rx.asession() as session:
                profile = await session.scalar(
                    select(TrainerProfile).where(
                        TrainerProfile.user_id == trainer_id
                    )
                )
                if profile is None:
                    profile = TrainerProfile(user_id=trainer_id)
                    session.add(profile)
                profile.designation = designation
                profile.department = str(
                    form_data.get("department", "")
                ).strip()
                profile.organization = str(
                    form_data.get("organization", "")
                ).strip()
                profile.specialization = str(
                    form_data.get("specialization", "")
                ).strip()
                profile.years_of_training = years
                profile.highest_qualification = str(
                    form_data.get("highest_qualification", "")
                ).strip()
                profile.bio = str(form_data.get("bio", "")).strip()
                profile.languages = str(form_data.get("languages", "")).strip()
                profile.is_available = (
                    str(form_data.get("is_available", "")) == "available"
                )
                filled = [
                    profile.designation,
                    profile.department,
                    profile.organization,
                    profile.specialization,
                    profile.highest_qualification,
                    profile.bio,
                    profile.languages,
                ]
                profile.profile_completion = int(
                    round(
                        len([value for value in filled if value])
                        * 100
                        / len(filled)
                    )
                )
                await session.commit()
                await self._load_profile(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error saving trainer profile: {exception}")
            self.error_message = "Could not save the profile. Try again."
            return
        self.success_message = "Expertise profile saved."

    # ------------------------------------------------------- qualifications
    @rx.event
    async def add_qualification(self, form_data: dict[str, Any]):
        self._reset_messages()
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        degree = str(form_data.get("degree", "")).strip()
        institution = str(form_data.get("institution", "")).strip()
        if len(degree) < 2 or len(institution) < 2:
            self.error_message = "Degree and institution are required."
            return

        def to_year(key: str) -> int | None:
            raw = str(form_data.get(key, "")).strip()
            if not raw:
                return None
            try:
                year = int(raw)
            except ValueError:
                return None
            return year if 1950 <= year <= 2100 else None

        start_year = to_year("start_year")
        end_year = to_year("end_year")
        if start_year and end_year and end_year < start_year:
            self.error_message = "End year cannot precede the start year."
            return
        try:
            async with rx.asession() as session:
                session.add(
                    Qualification(
                        user_id=trainer_id,
                        degree=degree,
                        field_of_study=str(
                            form_data.get("field_of_study", "")
                        ).strip(),
                        institution=institution,
                        start_year=start_year,
                        end_year=end_year,
                        grade=str(form_data.get("grade", "")).strip(),
                    )
                )
                await session.commit()
                await self._load_profile(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error adding qualification: {exception}")
            self.error_message = "Could not add the qualification."
            return
        self.success_message = "Qualification added."

    @rx.event
    async def delete_qualification(self, record_id: int):
        self._reset_messages()
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        try:
            async with rx.asession() as session:
                record = await session.get(Qualification, record_id)
                if record is None or record.user_id != trainer_id:
                    self.error_message = "Qualification not found."
                    return
                await session.delete(record)
                await session.commit()
                await self._load_profile(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error deleting qualification: {exception}")
            self.error_message = "Could not remove the qualification."
            return
        self.success_message = "Qualification removed."

    # --------------------------------------------------------- experience
    @rx.event
    async def add_experience(self, form_data: dict[str, Any]):
        self._reset_messages()
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        organization = str(form_data.get("organization", "")).strip()
        role_title = str(form_data.get("role_title", "")).strip()
        if len(organization) < 2 or len(role_title) < 2:
            self.error_message = "Organization and role title are required."
            return

        def to_date(key: str) -> dt.date | None:
            raw = str(form_data.get(key, "")).strip()
            if not raw:
                return None
            try:
                return dt.date.fromisoformat(raw)
            except ValueError:
                return None

        start_date = to_date("start_date")
        end_date = to_date("end_date")
        is_current = str(form_data.get("is_current", "")) == "current"
        if start_date is None:
            self.error_message = "Enter a valid start date."
            return
        if not is_current and end_date is None:
            self.error_message = "Enter an end date or mark the role current."
            return
        if end_date and end_date < start_date:
            self.error_message = "End date cannot precede the start date."
            return
        try:
            async with rx.asession() as session:
                session.add(
                    WorkExperience(
                        user_id=trainer_id,
                        organization=organization,
                        role_title=role_title,
                        location=str(form_data.get("location", "")).strip(),
                        start_date=start_date,
                        end_date=None if is_current else end_date,
                        is_current=is_current,
                        responsibilities=str(
                            form_data.get("responsibilities", "")
                        ).strip(),
                    )
                )
                await session.commit()
                await self._load_profile(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error adding experience: {exception}")
            self.error_message = "Could not add the experience record."
            return
        self.success_message = "Work experience added."

    @rx.event
    async def delete_experience(self, record_id: int):
        self._reset_messages()
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        try:
            async with rx.asession() as session:
                record = await session.get(WorkExperience, record_id)
                if record is None or record.user_id != trainer_id:
                    self.error_message = "Experience record not found."
                    return
                await session.delete(record)
                await session.commit()
                await self._load_profile(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error deleting experience: {exception}")
            self.error_message = "Could not remove the experience record."
            return
        self.success_message = "Experience record removed."

    # ------------------------------------------------------------- skills
    @rx.event
    async def save_skill(self, form_data: dict[str, Any]):
        self._reset_messages()
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        name = str(form_data.get("skill_name", "")).strip()
        if len(name) < 2:
            self.error_message = "Enter the skill name."
            return
        level = str(form_data.get("level", "")).strip()
        if level not in LEVELS:
            level = ProficiencyLevel.INTERMEDIATE.value
        try:
            score = int(float(form_data.get("score") or 0))
            years = float(form_data.get("years") or 0)
        except ValueError:
            self.error_message = "Score and years must be numeric."
            return
        if score < 0 or score > 100:
            self.error_message = "Proficiency score must be 0–100."
            return
        if years < 0 or years > 60:
            self.error_message = "Years of practice must be 0–60."
            return
        try:
            async with rx.asession() as session:
                skill = await session.scalar(
                    select(Skill).where(Skill.name == name)
                )
                if skill is None:
                    skill = Skill(
                        name=name,
                        category=str(form_data.get("category", "")).strip()
                        or "General",
                        description=f"Competency area: {name}.",
                    )
                    session.add(skill)
                    await session.flush()
                link = await session.scalar(
                    select(UserSkill).where(
                        UserSkill.user_id == trainer_id,
                        UserSkill.skill_id == skill.id,
                    )
                )
                if link is None:
                    link = UserSkill(
                        user_id=trainer_id, skill_id=skill.id, is_teachable=True
                    )
                    session.add(link)
                link.level = level
                link.proficiency_score = score
                link.years_of_practice = years
                link.is_teachable = True
                await session.commit()
                await self._load_profile(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error saving skill: {exception}")
            self.error_message = "Could not save the teachable skill."
            return
        self.success_message = f"Teachable skill saved: {name}."

    @rx.event
    async def delete_skill(self, link_id: int):
        self._reset_messages()
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        try:
            async with rx.asession() as session:
                link = await session.get(UserSkill, link_id)
                if link is None or link.user_id != trainer_id:
                    self.error_message = "Skill not found."
                    return
                await session.delete(link)
                await session.commit()
                await self._load_profile(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error deleting skill: {exception}")
            self.error_message = "Could not remove the skill."
            return
        self.success_message = "Teachable skill removed."

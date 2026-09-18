"""Trainee profile, qualifications, experience, skill matrix and dashboard."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    Assessment,
    AssessmentResult,
    AssessmentStatus,
    Certificate,
    Course,
    CourseFeedback,
    Enrollment,
    EnrollmentStatus,
    LearningResource,
    ProficiencyLevel,
    Qualification,
    ResourceProgress,
    Skill,
    TraineeProfile,
    UserSkill,
    WorkExperience,
)
from app.seed import ensure_seed_data

logger = logging.getLogger(__name__)

LEVEL_OPTIONS: list[str] = [
    ProficiencyLevel.BEGINNER.value,
    ProficiencyLevel.INTERMEDIATE.value,
    ProficiencyLevel.ADVANCED.value,
    ProficiencyLevel.EXPERT.value,
]


def parse_date(value: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(value.strip())
    except Exception:
        logging.exception("Unexpected error")
        return None


def parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        logging.exception("Unexpected error")
        return default


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        logging.exception("Unexpected error")
        return default


def grade_for(percentage: float) -> str:
    if percentage >= 85:
        return "A"
    if percentage >= 70:
        return "B"
    if percentage >= 60:
        return "C"
    if percentage >= 50:
        return "D"
    return "F"


class ProfileForm(TypedDict):
    designation: str
    department: str
    organization: str
    employee_code: str
    station: str
    region: str
    date_of_joining: str
    total_experience_years: str
    bio: str
    career_goal: str


class QualificationItem(TypedDict):
    id: int
    degree: str
    field_of_study: str
    institution: str
    start_year: str
    end_year: str
    grade: str
    is_verified: bool


class ExperienceItem(TypedDict):
    id: int
    organization: str
    role_title: str
    location: str
    start_date: str
    end_date: str
    is_current: bool
    responsibilities: str


class SkillMeter(TypedDict):
    id: int
    skill_id: int
    name: str
    category: str
    level: str
    score: int
    years: float


class SkillOption(TypedDict):
    id: int
    name: str


class NextAction(TypedDict):
    icon: str
    title: str
    detail: str
    href: str
    cta: str


class ProgressRow(TypedDict):
    course_id: int
    code: str
    title: str
    status: str
    progress: int
    completed_resources: int
    total_resources: int


EMPTY_PROFILE: ProfileForm = {
    "designation": "",
    "department": "",
    "organization": "",
    "employee_code": "",
    "station": "",
    "region": "",
    "date_of_joining": "",
    "total_experience_years": "0",
    "bio": "",
    "career_goal": "",
}

EMPTY_QUALIFICATION: QualificationItem = {
    "id": 0,
    "degree": "",
    "field_of_study": "",
    "institution": "",
    "start_year": "",
    "end_year": "",
    "grade": "",
    "is_verified": False,
}

EMPTY_EXPERIENCE: ExperienceItem = {
    "id": 0,
    "organization": "",
    "role_title": "",
    "location": "",
    "start_date": "",
    "end_date": "",
    "is_current": False,
    "responsibilities": "",
}


class TraineeState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    profile: ProfileForm = EMPTY_PROFILE
    profile_completion: int = 0

    qualifications: list[QualificationItem] = []
    experiences: list[ExperienceItem] = []
    skills: list[SkillMeter] = []
    skill_catalog: list[SkillOption] = []
    level_options: list[str] = LEVEL_OPTIONS

    qualification_form: QualificationItem = EMPTY_QUALIFICATION
    experience_form: ExperienceItem = EMPTY_EXPERIENCE
    editing_qualification_id: int = 0
    editing_experience_id: int = 0

    metrics: dict[str, int] = {
        "enrollments": 0,
        "active": 0,
        "completed": 0,
        "resources_done": 0,
        "assessments_open": 0,
        "results": 0,
        "certificates": 0,
        "skills": 0,
        "avg_progress": 0,
        "avg_score": 0,
        "feedback_pending": 0,
    }
    next_actions: list[NextAction] = []
    progress_rows: list[ProgressRow] = []

    # --------------------------------------------------------------- helpers
    async def _uid(self) -> int:
        from app.states.auth_state import AuthState

        auth = await self.get_state(AuthState)
        if auth.role != "trainee":
            return 0
        return auth.user_id

    @rx.var
    def has_skills(self) -> bool:
        return len(self.skills) > 0

    @rx.var
    def strongest_skill(self) -> str:
        if not self.skills:
            return "No skills recorded"
        best = max(self.skills, key=lambda item: item["score"])
        return f"{best['name']} · {best['score']}%"

    @rx.var
    def weakest_skill(self) -> str:
        if not self.skills:
            return "No skills recorded"
        worst = min(self.skills, key=lambda item: item["score"])
        return f"{worst['name']} · {worst['score']}%"

    @rx.var
    def average_skill_score(self) -> int:
        if not self.skills:
            return 0
        return int(
            sum(item["score"] for item in self.skills) / len(self.skills)
        )

    @rx.var
    def qualification_form_title(self) -> str:
        return (
            "Update qualification"
            if self.editing_qualification_id > 0
            else "Add qualification"
        )

    @rx.var
    def experience_form_title(self) -> str:
        return (
            "Update experience record"
            if self.editing_experience_id > 0
            else "Add experience record"
        )

    def _clear_messages(self) -> None:
        self.error_message = ""
        self.success_message = ""

    async def _load_profile(self, session, uid: int) -> None:
        record = await session.scalar(
            select(TraineeProfile).where(TraineeProfile.user_id == uid)
        )
        if record is None:
            record = TraineeProfile(user_id=uid, profile_completion=10)
            session.add(record)
            await session.commit()
            await session.refresh(record)
        self.profile = {
            "designation": record.designation,
            "department": record.department,
            "organization": record.organization,
            "employee_code": record.employee_code,
            "station": record.station,
            "region": record.region,
            "date_of_joining": (
                record.date_of_joining.isoformat()
                if record.date_of_joining
                else ""
            ),
            "total_experience_years": f"{record.total_experience_years:.1f}",
            "bio": record.bio,
            "career_goal": record.career_goal,
        }
        self.profile_completion = int(record.profile_completion)

    async def _load_qualifications(self, session, uid: int) -> None:
        rows = (
            await session.scalars(
                select(Qualification)
                .where(Qualification.user_id == uid)
                .order_by(
                    Qualification.end_year.desc().nullslast(), Qualification.id
                )
            )
        ).all()
        self.qualifications = [
            {
                "id": row.id,
                "degree": row.degree,
                "field_of_study": row.field_of_study,
                "institution": row.institution,
                "start_year": str(row.start_year or ""),
                "end_year": str(row.end_year or ""),
                "grade": row.grade,
                "is_verified": bool(row.is_verified),
            }
            for row in rows
        ]

    async def _load_experiences(self, session, uid: int) -> None:
        rows = (
            await session.scalars(
                select(WorkExperience)
                .where(WorkExperience.user_id == uid)
                .order_by(
                    WorkExperience.start_date.desc().nullslast(),
                    WorkExperience.id,
                )
            )
        ).all()
        self.experiences = [
            {
                "id": row.id,
                "organization": row.organization,
                "role_title": row.role_title,
                "location": row.location,
                "start_date": (
                    row.start_date.isoformat() if row.start_date else ""
                ),
                "end_date": row.end_date.isoformat() if row.end_date else "",
                "is_current": bool(row.is_current),
                "responsibilities": row.responsibilities,
            }
            for row in rows
        ]

    async def _load_skills(self, session, uid: int) -> None:
        rows = (
            await session.execute(
                select(UserSkill, Skill)
                .join(Skill, Skill.id == UserSkill.skill_id)
                .where(UserSkill.user_id == uid)
                .order_by(UserSkill.proficiency_score.desc())
            )
        ).all()
        self.skills = [
            {
                "id": user_skill.id,
                "skill_id": skill.id,
                "name": skill.name,
                "category": skill.category or "General",
                "level": user_skill.level.capitalize(),
                "score": int(user_skill.proficiency_score),
                "years": float(user_skill.years_of_practice),
            }
            for user_skill, skill in rows
        ]
        catalog = (
            await session.scalars(
                select(Skill)
                .where(Skill.is_active.is_(True))
                .order_by(Skill.name)
            )
        ).all()
        self.skill_catalog = [
            {"id": row.id, "name": row.name} for row in catalog
        ]

    async def _recompute_completion(self, session, uid: int) -> None:
        record = await session.scalar(
            select(TraineeProfile).where(TraineeProfile.user_id == uid)
        )
        if record is None:
            return
        fields = [
            record.designation,
            record.department,
            record.organization,
            record.employee_code,
            record.station,
            record.region,
            record.bio,
            record.career_goal,
        ]
        filled = sum(1 for value in fields if str(value).strip())
        extras = 0
        if record.date_of_joining is not None:
            extras += 1
        if record.total_experience_years > 0:
            extras += 1
        quals = int(
            await session.scalar(
                select(func.count(Qualification.id)).where(
                    Qualification.user_id == uid
                )
            )
            or 0
        )
        exps = int(
            await session.scalar(
                select(func.count(WorkExperience.id)).where(
                    WorkExperience.user_id == uid
                )
            )
            or 0
        )
        skills = int(
            await session.scalar(
                select(func.count(UserSkill.id)).where(UserSkill.user_id == uid)
            )
            or 0
        )
        score = (filled + extras) * 8
        score += min(quals, 2) * 6
        score += min(exps, 2) * 6
        score += min(skills, 4) * 4
        record.profile_completion = max(5, min(100, score))
        await session.commit()
        self.profile_completion = record.profile_completion

    # ---------------------------------------------------------------- events
    @rx.event
    async def load_dashboard(self):
        ensure_seed_data()
        uid = await self._uid()
        if uid <= 0:
            return
        self.is_loading = True
        self.error_message = ""
        yield
        try:
            async with rx.asession() as session:
                await self._load_profile(session, uid)
                await self._load_skills(session, uid)
                await self._load_overview(session, uid)
        except Exception as exception:
            logging.exception(f"Error loading trainee dashboard: {exception}")
            self.error_message = (
                "We could not load your workspace. Please retry."
            )
        self.is_loading = False

    async def _load_overview(self, session, uid: int) -> None:
        enrollments = (
            await session.execute(
                select(Enrollment, Course)
                .join(Course, Course.id == Enrollment.course_id)
                .where(Enrollment.trainee_id == uid)
                .order_by(Enrollment.enrolled_at.desc())
            )
        ).all()
        rows: list[ProgressRow] = []
        total_progress = 0.0
        active = 0
        completed = 0
        for enrollment, course in enrollments:
            total_resources = int(
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
            total_progress += float(enrollment.progress_percent)
            if enrollment.status == EnrollmentStatus.COMPLETED.value:
                completed += 1
            elif enrollment.status != EnrollmentStatus.DROPPED.value:
                active += 1
            rows.append(
                {
                    "course_id": course.id,
                    "code": course.code,
                    "title": course.title,
                    "status": enrollment.status.replace("_", " ").capitalize(),
                    "progress": int(enrollment.progress_percent),
                    "completed_resources": done,
                    "total_resources": total_resources,
                }
            )
        self.progress_rows = rows

        course_ids = [course.id for _enrollment, course in enrollments]
        assessments_open = 0
        if course_ids:
            assessments_open = int(
                await session.scalar(
                    select(func.count(Assessment.id)).where(
                        Assessment.course_id.in_(course_ids),
                        Assessment.status == AssessmentStatus.OPEN.value,
                    )
                )
                or 0
            )
        results = (
            await session.scalars(
                select(AssessmentResult).where(
                    AssessmentResult.trainee_id == uid
                )
            )
        ).all()
        certificates = int(
            await session.scalar(
                select(func.count(Certificate.id)).where(
                    Certificate.trainee_id == uid
                )
            )
            or 0
        )
        resources_done = int(
            await session.scalar(
                select(func.count(ResourceProgress.id))
                .join(
                    Enrollment, Enrollment.id == ResourceProgress.enrollment_id
                )
                .where(
                    Enrollment.trainee_id == uid,
                    ResourceProgress.is_completed.is_(True),
                )
            )
            or 0
        )
        feedback_given = {
            row
            for row in (
                await session.scalars(
                    select(CourseFeedback.course_id).where(
                        CourseFeedback.trainee_id == uid
                    )
                )
            ).all()
        }
        completed_courses = [
            course.id
            for enrollment, course in enrollments
            if enrollment.status == EnrollmentStatus.COMPLETED.value
        ]
        feedback_pending = len(
            [cid for cid in completed_courses if cid not in feedback_given]
        )
        avg_score = (
            int(sum(r.percentage for r in results) / len(results))
            if results
            else 0
        )
        self.metrics = {
            "enrollments": len(enrollments),
            "active": active,
            "completed": completed,
            "resources_done": resources_done,
            "assessments_open": assessments_open,
            "results": len(results),
            "certificates": certificates,
            "skills": len(self.skills),
            "avg_progress": int(total_progress / len(enrollments))
            if enrollments
            else 0,
            "avg_score": avg_score,
            "feedback_pending": feedback_pending,
        }
        self._build_next_actions()

    def _build_next_actions(self) -> None:
        actions: list[NextAction] = []
        if self.profile_completion < 80:
            actions.append(
                {
                    "icon": "user-pen",
                    "title": "Complete your professional profile",
                    "detail": f"Profile completeness is at {self.profile_completion}%. Add station, qualifications and experience.",
                    "href": "/trainee/profile",
                    "cta": "Open profile",
                }
            )
        if not self.skills:
            actions.append(
                {
                    "icon": "grid-3x3",
                    "title": "Declare your competency matrix",
                    "detail": "Skill meters drive course recommendations and trainer matching.",
                    "href": "/trainee/profile",
                    "cta": "Add skills",
                }
            )
        if self.metrics["enrollments"] == 0:
            actions.append(
                {
                    "icon": "compass",
                    "title": "Enrol in your first course",
                    "detail": "Discover published courses filtered by category, level and competency.",
                    "href": "/trainee/courses",
                    "cta": "Discover courses",
                }
            )
        else:
            actions.append(
                {
                    "icon": "library",
                    "title": "Continue your module library",
                    "detail": f"{self.metrics['resources_done']} resources completed across {self.metrics['enrollments']} enrolments.",
                    "href": "/trainee/learning",
                    "cta": "Resume learning",
                }
            )
        if self.metrics["assessments_open"] > 0:
            actions.append(
                {
                    "icon": "clipboard-check",
                    "title": "Open assessments await",
                    "detail": f"{self.metrics['assessments_open']} timed questionnaire(s) are open for your courses.",
                    "href": "/trainee/assessments",
                    "cta": "Take assessment",
                }
            )
        if self.metrics["feedback_pending"] > 0:
            actions.append(
                {
                    "icon": "message-square",
                    "title": "Submit course feedback",
                    "detail": f"{self.metrics['feedback_pending']} completed course(s) still need your rating.",
                    "href": "/trainee/feedback",
                    "cta": "Give feedback",
                }
            )
        self.next_actions = actions

    @rx.event
    async def load_profile_workspace(self):
        ensure_seed_data()
        uid = await self._uid()
        if uid <= 0:
            return
        self.is_loading = True
        self._clear_messages()
        yield
        try:
            async with rx.asession() as session:
                await self._load_profile(session, uid)
                await self._load_qualifications(session, uid)
                await self._load_experiences(session, uid)
                await self._load_skills(session, uid)
        except Exception as exception:
            logging.exception(f"Error loading trainee profile: {exception}")
            self.error_message = "We could not load your profile. Please retry."
        self.is_loading = False

    @rx.event
    async def save_profile(self, form_data: dict[str, Any]):
        self._clear_messages()
        uid = await self._uid()
        if uid <= 0:
            return rx.redirect("/login")
        designation = str(form_data.get("designation", "")).strip()
        station = str(form_data.get("station", "")).strip()
        if len(designation) < 2:
            self.error_message = "Enter your designation."
            return
        if len(station) < 2:
            self.error_message = "Enter your posting station."
            return
        experience = parse_float(
            str(form_data.get("total_experience_years", "0"))
        )
        if experience < 0 or experience > 60:
            self.error_message = (
                "Total experience must be between 0 and 60 years."
            )
            return
        try:
            async with rx.asession() as session:
                record = await session.scalar(
                    select(TraineeProfile).where(TraineeProfile.user_id == uid)
                )
                if record is None:
                    record = TraineeProfile(user_id=uid)
                    session.add(record)
                    await session.flush()
                record.designation = designation
                record.department = str(form_data.get("department", "")).strip()
                record.organization = str(
                    form_data.get("organization", "")
                ).strip()
                record.employee_code = str(
                    form_data.get("employee_code", "")
                ).strip()
                record.station = station
                record.region = str(form_data.get("region", "")).strip()
                record.date_of_joining = parse_date(
                    str(form_data.get("date_of_joining", ""))
                )
                record.total_experience_years = experience
                record.bio = str(form_data.get("bio", "")).strip()
                record.career_goal = str(
                    form_data.get("career_goal", "")
                ).strip()
                await session.commit()
                await self._recompute_completion(session, uid)
                await self._load_profile(session, uid)
        except Exception as exception:
            logging.exception(f"Error saving trainee profile: {exception}")
            self.error_message = "Could not save your profile. Try again."
            return
        self.success_message = "Professional profile saved."

    # -------------------------------------------------------- qualifications
    @rx.event
    def edit_qualification(self, record: QualificationItem):
        self._clear_messages()
        self.editing_qualification_id = record["id"]
        self.qualification_form = record

    @rx.event
    def cancel_qualification_edit(self):
        self.editing_qualification_id = 0
        self.qualification_form = EMPTY_QUALIFICATION

    @rx.event
    async def save_qualification(self, form_data: dict[str, Any]):
        self._clear_messages()
        uid = await self._uid()
        if uid <= 0:
            return rx.redirect("/login")
        degree = str(form_data.get("degree", "")).strip()
        institution = str(form_data.get("institution", "")).strip()
        start_year = parse_int(str(form_data.get("start_year", "")))
        end_year = parse_int(str(form_data.get("end_year", "")))
        if len(degree) < 2:
            self.error_message = "Enter the degree or certification name."
            return
        if len(institution) < 2:
            self.error_message = "Enter the awarding institution."
            return
        if start_year and end_year and end_year < start_year:
            self.error_message = "End year cannot be before the start year."
            return
        try:
            async with rx.asession() as session:
                record = None
                if self.editing_qualification_id > 0:
                    record = await session.scalar(
                        select(Qualification).where(
                            Qualification.id == self.editing_qualification_id,
                            Qualification.user_id == uid,
                        )
                    )
                    if record is None:
                        self.error_message = (
                            "That qualification no longer exists."
                        )
                        return
                else:
                    record = Qualification(user_id=uid)
                    session.add(record)
                record.degree = degree
                record.field_of_study = str(
                    form_data.get("field_of_study", "")
                ).strip()
                record.institution = institution
                record.start_year = start_year or None
                record.end_year = end_year or None
                record.grade = str(form_data.get("grade", "")).strip()
                await session.commit()
                await self._recompute_completion(session, uid)
                await self._load_qualifications(session, uid)
        except Exception as exception:
            logging.exception(f"Error saving qualification: {exception}")
            self.error_message = "Could not save the qualification. Try again."
            return
        was_edit = self.editing_qualification_id > 0
        self.editing_qualification_id = 0
        self.qualification_form = EMPTY_QUALIFICATION
        self.success_message = (
            "Qualification updated." if was_edit else "Qualification added."
        )

    @rx.event
    async def delete_qualification(self, record_id: int):
        self._clear_messages()
        uid = await self._uid()
        if uid <= 0:
            return rx.redirect("/login")
        try:
            async with rx.asession() as session:
                record = await session.scalar(
                    select(Qualification).where(
                        Qualification.id == record_id,
                        Qualification.user_id == uid,
                    )
                )
                if record is None:
                    self.error_message = "That qualification no longer exists."
                    return
                await session.delete(record)
                await session.commit()
                await self._recompute_completion(session, uid)
                await self._load_qualifications(session, uid)
        except Exception as exception:
            logging.exception(f"Error deleting qualification: {exception}")
            self.error_message = "Could not remove the qualification."
            return
        self.success_message = "Qualification removed."

    # ----------------------------------------------------------- experience
    @rx.event
    def edit_experience(self, record: ExperienceItem):
        self._clear_messages()
        self.editing_experience_id = record["id"]
        self.experience_form = record

    @rx.event
    def cancel_experience_edit(self):
        self.editing_experience_id = 0
        self.experience_form = EMPTY_EXPERIENCE

    @rx.event
    async def save_experience(self, form_data: dict[str, Any]):
        self._clear_messages()
        uid = await self._uid()
        if uid <= 0:
            return rx.redirect("/login")
        organization = str(form_data.get("organization", "")).strip()
        role_title = str(form_data.get("role_title", "")).strip()
        start_date = parse_date(str(form_data.get("start_date", "")))
        end_date = parse_date(str(form_data.get("end_date", "")))
        is_current = bool(form_data.get("is_current"))
        if len(organization) < 2:
            self.error_message = "Enter the organization name."
            return
        if len(role_title) < 2:
            self.error_message = "Enter the role title."
            return
        if start_date is None:
            self.error_message = "Enter a valid start date."
            return
        if not is_current and end_date is None:
            self.error_message = (
                "Enter an end date or mark this role as current."
            )
            return
        if end_date is not None and end_date < start_date:
            self.error_message = "End date cannot be before the start date."
            return
        try:
            async with rx.asession() as session:
                if self.editing_experience_id > 0:
                    record = await session.scalar(
                        select(WorkExperience).where(
                            WorkExperience.id == self.editing_experience_id,
                            WorkExperience.user_id == uid,
                        )
                    )
                    if record is None:
                        self.error_message = "That record no longer exists."
                        return
                else:
                    record = WorkExperience(user_id=uid)
                    session.add(record)
                record.organization = organization
                record.role_title = role_title
                record.location = str(form_data.get("location", "")).strip()
                record.start_date = start_date
                record.end_date = None if is_current else end_date
                record.is_current = is_current
                record.responsibilities = str(
                    form_data.get("responsibilities", "")
                ).strip()
                await session.commit()
                await self._recompute_completion(session, uid)
                await self._load_experiences(session, uid)
        except Exception as exception:
            logging.exception(f"Error saving work experience: {exception}")
            self.error_message = "Could not save the experience record."
            return
        was_edit = self.editing_experience_id > 0
        self.editing_experience_id = 0
        self.experience_form = EMPTY_EXPERIENCE
        self.success_message = (
            "Experience record updated." if was_edit else "Experience added."
        )

    @rx.event
    async def delete_experience(self, record_id: int):
        self._clear_messages()
        uid = await self._uid()
        if uid <= 0:
            return rx.redirect("/login")
        try:
            async with rx.asession() as session:
                record = await session.scalar(
                    select(WorkExperience).where(
                        WorkExperience.id == record_id,
                        WorkExperience.user_id == uid,
                    )
                )
                if record is None:
                    self.error_message = "That record no longer exists."
                    return
                await session.delete(record)
                await session.commit()
                await self._recompute_completion(session, uid)
                await self._load_experiences(session, uid)
        except Exception as exception:
            logging.exception(f"Error deleting work experience: {exception}")
            self.error_message = "Could not remove the experience record."
            return
        self.success_message = "Experience record removed."

    # --------------------------------------------------------------- skills
    @rx.event
    async def save_skill(self, form_data: dict[str, Any]):
        self._clear_messages()
        uid = await self._uid()
        if uid <= 0:
            return rx.redirect("/login")
        skill_id = parse_int(str(form_data.get("skill_id", "0")))
        level = str(form_data.get("level", "")).strip().lower()
        score = parse_int(str(form_data.get("proficiency_score", "0")))
        years = parse_float(str(form_data.get("years_of_practice", "0")))
        if skill_id <= 0:
            self.error_message = "Select a skill from the competency library."
            return
        if level not in LEVEL_OPTIONS:
            self.error_message = "Select a valid proficiency level."
            return
        if score < 0 or score > 100:
            self.error_message = "Proficiency score must be between 0 and 100."
            return
        if years < 0 or years > 60:
            self.error_message = "Years of practice must be between 0 and 60."
            return
        created = False
        try:
            async with rx.asession() as session:
                record = await session.scalar(
                    select(UserSkill).where(
                        UserSkill.user_id == uid,
                        UserSkill.skill_id == skill_id,
                    )
                )
                created = record is None
                if record is None:
                    record = UserSkill(user_id=uid, skill_id=skill_id)
                    session.add(record)
                record.level = level
                record.proficiency_score = score
                record.years_of_practice = years
                await session.commit()
                await self._recompute_completion(session, uid)
                await self._load_skills(session, uid)
        except Exception as exception:
            logging.exception(f"Error saving skill: {exception}")
            self.error_message = "Could not save the skill. Try again."
            return
        self.success_message = (
            "Skill added to your competency matrix."
            if created
            else "Skill proficiency updated."
        )

    @rx.event
    async def delete_skill(self, record_id: int):
        self._clear_messages()
        uid = await self._uid()
        if uid <= 0:
            return rx.redirect("/login")
        try:
            async with rx.asession() as session:
                record = await session.scalar(
                    select(UserSkill).where(
                        UserSkill.id == record_id, UserSkill.user_id == uid
                    )
                )
                if record is None:
                    self.error_message = "That skill is no longer recorded."
                    return
                await session.delete(record)
                await session.commit()
                await self._recompute_completion(session, uid)
                await self._load_skills(session, uid)
        except Exception as exception:
            logging.exception(f"Error deleting skill: {exception}")
            self.error_message = "Could not remove the skill."
            return
        self.success_message = "Skill removed from your matrix."

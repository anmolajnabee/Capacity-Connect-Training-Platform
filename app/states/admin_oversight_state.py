"""Read-rich organization oversight: courses, trainers, assessments, records."""

from __future__ import annotations

import logging
from typing import TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentResult,
    AssignmentStatus,
    AssignmentSubmission,
    Certificate,
    CourseAssignment,
    Course,
    CourseTrainerAssignment,
    Enrollment,
    EnrollmentStatus,
    LearningResource,
    Question,
    Skill,
    TrainerProfile,
    User,
    UserRole,
    UserSkill,
)
from app.states.admin_state import admin_guard, day_stamp, stamp

logger = logging.getLogger(__name__)


class CourseOversight(TypedDict):
    id: int
    code: str
    title: str
    category: str
    level: str
    mode: str
    status: str
    window: str
    capacity: int
    enrolled: int
    active: int
    completed: int
    at_risk: int
    completion: int
    fill: int
    resources: int
    assessments: int
    certificates: int
    trainers: str
    trainer_count: int


class TrainerOversight(TypedDict):
    id: int
    name: str
    email: str
    designation: str
    department: str
    specialization: str
    years: float
    rating: float
    available: bool
    approval: str
    courses: int
    cohort: int
    teachable: int
    top_skill: str
    profile_completion: int


class AssessmentOversight(TypedDict):
    id: int
    title: str
    course: str
    code: str
    status: str
    total_marks: float
    passing_marks: float
    time_limit: int
    questions: int
    attempts: int
    results: int
    passes: int
    pass_rate: int
    avg_score: float
    deadline: str


class CertificateRow(TypedDict):
    number: str
    course: str
    trainee: str
    issued: str
    score: float
    grade: str
    verification: str
    revoked: bool


class AssignmentOversightRow(TypedDict):
    id: int
    title: str
    course: str
    code: str
    assignment_type: str
    status: str
    total_marks: float
    due: str
    trainer: str
    cohort: int
    submitted: int
    graded: int
    completion: int
    graded_percent: int
    late: int


class SubmissionOversightRow(TypedDict):
    id: int
    trainee: str
    assignment: str
    course: str
    status: str
    is_late: bool
    submitted: str
    marks: float
    total_marks: float
    grader: str


class EnrollmentRow(TypedDict):
    id: int
    trainee: str
    email: str
    course: str
    code: str
    status: str
    progress: int
    enrolled: str
    last_activity: str


class AdminOversightState(rx.State):
    is_loading: bool = False
    error_message: str = ""

    courses: list[CourseOversight] = []
    trainers: list[TrainerOversight] = []
    assessments: list[AssessmentOversight] = []
    certificates: list[CertificateRow] = []
    enrollments: list[EnrollmentRow] = []
    assignment_rows: list[AssignmentOversightRow] = []
    submission_rows: list[SubmissionOversightRow] = []

    assignment_metrics: dict[str, int] = {
        "assignments": 0,
        "published": 0,
        "submissions": 0,
        "graded": 0,
        "late": 0,
        "completion": 0,
        "graded_percent": 0,
    }

    course_query: str = ""
    course_status_filter: str = "All"
    assessment_status_filter: str = "All"
    enrollment_query: str = ""

    @rx.var
    def course_status_options(self) -> list[str]:
        return ["All", "published", "draft", "archived"]

    @rx.var
    def assessment_status_options(self) -> list[str]:
        return ["All", "open", "draft", "closed"]

    @rx.var
    def filtered_courses(self) -> list[CourseOversight]:
        query = self.course_query.strip().lower()
        rows: list[CourseOversight] = []
        for row in self.courses:
            if (
                self.course_status_filter != "All"
                and row["status"] != self.course_status_filter
            ):
                continue
            if query and query not in (
                f"{row['code']} {row['title']} {row['category']} {row['trainers']}".lower()
            ):
                continue
            rows.append(row)
        return rows

    @rx.var
    def filtered_assessments(self) -> list[AssessmentOversight]:
        if self.assessment_status_filter == "All":
            return self.assessments
        return [
            row
            for row in self.assessments
            if row["status"] == self.assessment_status_filter
        ]

    @rx.var
    def filtered_enrollments(self) -> list[EnrollmentRow]:
        query = self.enrollment_query.strip().lower()
        if not query:
            return self.enrollments
        return [
            row
            for row in self.enrollments
            if query
            in f"{row['trainee']} {row['email']} {row['code']} {row['course']}".lower()
        ]

    @rx.event
    def set_course_query(self, value: str):
        self.course_query = value

    @rx.event
    def set_course_status_filter(self, value: str):
        self.course_status_filter = value

    @rx.event
    def set_assessment_status_filter(self, value: str):
        self.assessment_status_filter = value

    @rx.event
    def set_enrollment_query(self, value: str):
        self.enrollment_query = value

    @rx.event
    async def load_oversight(self):
        self.error_message = ""
        if await admin_guard(self) == 0:
            self.error_message = "Administrator access is required."
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load_courses(session)
                await self._load_trainers(session)
                await self._load_assessments(session)
                await self._load_assignment_oversight(session)
                await self._load_records(session)
        except Exception as exception:
            logging.exception(f"Error loading oversight data: {exception}")
            self.error_message = "Could not load organization oversight data."
        self.is_loading = False

    async def _load_courses(self, session) -> None:
        rows: list[CourseOversight] = []
        courses = (
            await session.execute(select(Course).order_by(Course.title))
        ).scalars()
        for course in courses:
            enrollments = (
                (
                    await session.execute(
                        select(Enrollment).where(
                            Enrollment.course_id == course.id
                        )
                    )
                )
                .scalars()
                .all()
            )
            enrolled = len(enrollments)
            completed = len(
                [
                    row
                    for row in enrollments
                    if row.status == EnrollmentStatus.COMPLETED.value
                ]
            )
            active = len(
                [
                    row
                    for row in enrollments
                    if row.status == EnrollmentStatus.ACTIVE.value
                ]
            )
            at_risk = len(
                [
                    row
                    for row in enrollments
                    if row.status == EnrollmentStatus.AT_RISK.value
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
            assessments = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Assessment)
                    .where(Assessment.course_id == course.id)
                )
                or 0
            )
            certificates = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Certificate)
                    .where(Certificate.course_id == course.id)
                )
                or 0
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
            rows.append(
                {
                    "id": course.id,
                    "code": course.code,
                    "title": course.title,
                    "category": course.category or "General",
                    "level": course.level,
                    "mode": course.mode,
                    "status": course.status,
                    "window": (
                        f"{day_stamp(course.start_date)} → {day_stamp(course.end_date)}"
                        if course.start_date
                        else "Schedule pending"
                    ),
                    "capacity": course.capacity,
                    "enrolled": enrolled,
                    "active": active,
                    "completed": completed,
                    "at_risk": at_risk,
                    "completion": int(round(completed * 100 / enrolled))
                    if enrolled
                    else 0,
                    "fill": int(round(enrolled * 100 / course.capacity))
                    if course.capacity
                    else 0,
                    "resources": resources,
                    "assessments": assessments,
                    "certificates": certificates,
                    "trainers": ", ".join(trainer_names)
                    if trainer_names
                    else "Unassigned",
                    "trainer_count": len(trainer_names),
                }
            )
        self.courses = rows

    async def _load_trainers(self, session) -> None:
        rows: list[TrainerOversight] = []
        pairs = (
            await session.execute(
                select(User, TrainerProfile)
                .outerjoin(TrainerProfile, TrainerProfile.user_id == User.id)
                .where(User.role == UserRole.TRAINER.value)
                .order_by(User.full_name)
            )
        ).all()
        for user, profile in pairs:
            course_ids = list(
                (
                    await session.execute(
                        select(CourseTrainerAssignment.course_id).where(
                            CourseTrainerAssignment.trainer_id == user.id
                        )
                    )
                )
                .scalars()
                .all()
            )
            cohort = 0
            if course_ids:
                cohort = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(Enrollment)
                        .where(Enrollment.course_id.in_(course_ids))
                    )
                    or 0
                )
            skills = (
                (
                    await session.execute(
                        select(UserSkill)
                        .where(UserSkill.user_id == user.id)
                        .order_by(UserSkill.proficiency_score.desc())
                    )
                )
                .scalars()
                .all()
            )
            teachable = len([row for row in skills if row.is_teachable])
            top_skill = "No skills recorded"
            if skills:
                best = skills[0]
                skill_name = await session.scalar(
                    select(Skill.name).where(Skill.id == best.skill_id)
                )
                top_skill = (
                    f"{skill_name or 'Skill'} · {best.proficiency_score}%"
                )
            rows.append(
                {
                    "id": user.id,
                    "name": user.full_name,
                    "email": user.email,
                    "designation": profile.designation
                    if profile
                    else "Profile pending",
                    "department": profile.department if profile else "—",
                    "specialization": profile.specialization
                    if profile
                    else "—",
                    "years": float(profile.years_of_training)
                    if profile
                    else 0.0,
                    "rating": float(profile.rating_average) if profile else 0.0,
                    "available": bool(profile.is_available)
                    if profile
                    else False,
                    "approval": user.approval_status,
                    "courses": len(course_ids),
                    "cohort": cohort,
                    "teachable": teachable,
                    "top_skill": top_skill,
                    "profile_completion": profile.profile_completion
                    if profile
                    else 0,
                }
            )
        self.trainers = rows

    async def _load_assessments(self, session) -> None:
        rows: list[AssessmentOversight] = []
        pairs = (
            await session.execute(
                select(Assessment, Course)
                .join(Course, Course.id == Assessment.course_id)
                .order_by(Assessment.title)
            )
        ).all()
        for assessment, course in pairs:
            questions = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Question)
                    .where(Question.assessment_id == assessment.id)
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
            summary = (
                await session.execute(
                    select(
                        func.count(AssessmentResult.id),
                        func.avg(AssessmentResult.percentage),
                    ).where(AssessmentResult.assessment_id == assessment.id)
                )
            ).first()
            results = int(summary[0] or 0) if summary else 0
            avg_score = float(summary[1] or 0.0) if summary else 0.0
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
            rows.append(
                {
                    "id": assessment.id,
                    "title": assessment.title,
                    "course": course.title,
                    "code": course.code,
                    "status": assessment.status,
                    "total_marks": float(assessment.total_marks),
                    "passing_marks": float(assessment.passing_marks),
                    "time_limit": assessment.time_limit_minutes,
                    "questions": questions,
                    "attempts": attempts,
                    "results": results,
                    "passes": passes,
                    "pass_rate": int(round(passes * 100 / results))
                    if results
                    else 0,
                    "avg_score": avg_score,
                    "deadline": stamp(assessment.deadline_at),
                }
            )
        self.assessments = rows

    async def _load_assignment_oversight(self, session) -> None:
        rows: list[AssignmentOversightRow] = []
        metrics = {
            "assignments": 0,
            "published": 0,
            "submissions": 0,
            "graded": 0,
            "late": 0,
            "completion": 0,
            "graded_percent": 0,
        }
        cohort_total = 0
        pairs = (
            await session.execute(
                select(CourseAssignment, Course)
                .join(Course, Course.id == CourseAssignment.course_id)
                .order_by(CourseAssignment.created_at.desc())
                .limit(100)
            )
        ).all()
        for assignment, course in pairs:
            cohort = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Enrollment)
                    .where(Enrollment.course_id == course.id)
                )
                or 0
            )
            submitted = int(
                await session.scalar(
                    select(func.count())
                    .select_from(AssignmentSubmission)
                    .where(
                        AssignmentSubmission.assignment_id == assignment.id,
                        AssignmentSubmission.status != "draft",
                    )
                )
                or 0
            )
            graded = int(
                await session.scalar(
                    select(func.count())
                    .select_from(AssignmentSubmission)
                    .where(
                        AssignmentSubmission.assignment_id == assignment.id,
                        AssignmentSubmission.status == "graded",
                    )
                )
                or 0
            )
            late = int(
                await session.scalar(
                    select(func.count())
                    .select_from(AssignmentSubmission)
                    .where(
                        AssignmentSubmission.assignment_id == assignment.id,
                        AssignmentSubmission.is_late.is_(True),
                    )
                )
                or 0
            )
            trainer = (
                await session.scalar(
                    select(User.full_name).where(
                        User.id == assignment.created_by_id
                    )
                )
                if assignment.created_by_id
                else None
            ) or "Unassigned"
            metrics["assignments"] += 1
            metrics["submissions"] += submitted
            metrics["graded"] += graded
            metrics["late"] += late
            cohort_total += cohort
            if assignment.status == AssignmentStatus.PUBLISHED.value:
                metrics["published"] += 1
            rows.append(
                {
                    "id": assignment.id,
                    "title": assignment.title,
                    "course": course.title,
                    "code": course.code,
                    "assignment_type": assignment.assignment_type.replace(
                        "_", " "
                    ),
                    "status": assignment.status,
                    "total_marks": float(assignment.total_marks or 0.0),
                    "due": stamp(assignment.due_at),
                    "trainer": trainer,
                    "cohort": cohort,
                    "submitted": submitted,
                    "graded": graded,
                    "completion": int(round(submitted * 100 / cohort))
                    if cohort
                    else 0,
                    "graded_percent": int(round(graded * 100 / submitted))
                    if submitted
                    else 0,
                    "late": late,
                }
            )
        metrics["completion"] = (
            int(round(metrics["submissions"] * 100 / cohort_total))
            if cohort_total
            else 0
        )
        metrics["graded_percent"] = (
            int(round(metrics["graded"] * 100 / metrics["submissions"]))
            if metrics["submissions"]
            else 0
        )
        self.assignment_rows = rows
        self.assignment_metrics = metrics

        recent = (
            await session.execute(
                select(AssignmentSubmission, CourseAssignment, Course, User)
                .join(
                    CourseAssignment,
                    CourseAssignment.id == AssignmentSubmission.assignment_id,
                )
                .join(Course, Course.id == CourseAssignment.course_id)
                .join(User, User.id == AssignmentSubmission.trainee_id)
                .where(AssignmentSubmission.status != "draft")
                .order_by(AssignmentSubmission.submitted_at.desc().nulls_last())
                .limit(50)
            )
        ).all()
        submission_rows: list[SubmissionOversightRow] = []
        for submission, assignment, course, user in recent:
            grader = (
                await session.scalar(
                    select(User.full_name).where(
                        User.id == submission.graded_by_id
                    )
                )
                if submission.graded_by_id
                else None
            ) or "—"
            submission_rows.append(
                {
                    "id": submission.id,
                    "trainee": user.full_name,
                    "assignment": assignment.title,
                    "course": f"{course.code} · {course.title}",
                    "status": submission.status,
                    "is_late": bool(submission.is_late),
                    "submitted": stamp(submission.submitted_at),
                    "marks": float(submission.marks_awarded or 0.0),
                    "total_marks": float(assignment.total_marks or 0.0),
                    "grader": grader,
                }
            )
        self.submission_rows = submission_rows

    async def _load_records(self, session) -> None:
        certificate_rows = (
            await session.execute(
                select(Certificate, Course, User)
                .join(Course, Course.id == Certificate.course_id)
                .join(User, User.id == Certificate.trainee_id)
                .order_by(Certificate.issued_at.desc())
                .limit(100)
            )
        ).all()
        self.certificates = [
            {
                "number": certificate.certificate_number,
                "course": f"{course.code} · {course.title}",
                "trainee": user.full_name,
                "issued": stamp(certificate.issued_at),
                "score": float(certificate.final_score),
                "grade": certificate.grade or "—",
                "verification": certificate.verification_code or "—",
                "revoked": bool(certificate.is_revoked),
            }
            for certificate, course, user in certificate_rows
        ]
        enrollment_rows = (
            await session.execute(
                select(Enrollment, Course, User)
                .join(Course, Course.id == Enrollment.course_id)
                .join(User, User.id == Enrollment.trainee_id)
                .order_by(Enrollment.enrolled_at.desc())
                .limit(150)
            )
        ).all()
        self.enrollments = [
            {
                "id": enrollment.id,
                "trainee": user.full_name,
                "email": user.email,
                "course": course.title,
                "code": course.code,
                "status": enrollment.status.replace("_", " "),
                "progress": int(round(enrollment.progress_percent)),
                "enrolled": stamp(enrollment.enrolled_at),
                "last_activity": stamp(enrollment.last_activity_at),
            }
            for enrollment, course, user in enrollment_rows
        ]

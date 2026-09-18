"""CAPACITY CONNECT — database model layer.

Normalized SQLAlchemy declarative models for the institutional learning
platform: accounts, role-aware approval, trainee/trainer professional
profiles, skills & proficiency, courses, resources, enrollments,
assessments, attempts, certificates, feedback and announcements.

Schema only — no queries, no event handlers.
"""

from __future__ import annotations

import reflex as rx
import datetime as dt
import enum
import secrets

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)


class Base(MappedAsDataclass, DeclarativeBase, kw_only=True):
    pass


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


# --------------------------------------------------------------------------
# Enumerations (stored as short strings for portability / readability)
# --------------------------------------------------------------------------
class UserRole(str, enum.Enum):
    TRAINEE = "trainee"
    TRAINER = "trainer"
    ADMIN = "admin"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class ProficiencyLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class CourseStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EnrollmentStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DROPPED = "dropped"
    AT_RISK = "at_risk"


class AssessmentStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"


class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    GRADED = "graded"
    EXPIRED = "expired"


class ResourceType(str, enum.Enum):
    DOCUMENT = "document"
    VIDEO = "video"
    LINK = "link"
    SLIDES = "slides"
    DATASET = "dataset"


class TrainerAssignmentRole(str, enum.Enum):
    LEAD = "lead"
    CO_TRAINER = "co_trainer"
    GUEST = "guest"


class AnnouncementAudience(str, enum.Enum):
    ALL = "all"
    TRAINEES = "trainees"
    TRAINERS = "trainers"
    ADMINS = "admins"


class AssignmentType(str, enum.Enum):
    ESSAY = "essay"
    PROJECT = "project"
    CASE_STUDY = "case_study"
    FIELD_REPORT = "field_report"
    PRESENTATION = "presentation"
    PRACTICAL = "practical"


class AssignmentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"


class SubmissionStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    LATE = "late"
    GRADED = "graded"
    RETURNED = "returned"


class CertificateRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ISSUED = "issued"


# --------------------------------------------------------------------------
# Timestamp mixin
# --------------------------------------------------------------------------
class TimestampMixin(MappedAsDataclass, kw_only=True):
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=_utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=_utcnow,
        server_default=func.now(),
        onupdate=func.now(),
    )


# --------------------------------------------------------------------------
# Accounts & security
# --------------------------------------------------------------------------
class User(Base, TimestampMixin):
    __tablename__ = "cc_user"
    __table_args__ = (
        UniqueConstraint("email", name="uq_cc_user_email"),
        Index("ix_cc_user_role_status", "role", "approval_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    email: Mapped[str] = mapped_column(String(255), index=True)
    full_name: Mapped[str] = mapped_column(String(160), default="")
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    password_salt: Mapped[str] = mapped_column(String(64), default="")
    password_algorithm: Mapped[str] = mapped_column(
        String(32), default="pbkdf2_sha256"
    )
    password_updated_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    role: Mapped[str] = mapped_column(
        String(16), default=UserRole.TRAINEE.value, index=True
    )
    approval_status: Mapped[str] = mapped_column(
        String(16), default=ApprovalStatus.PENDING.value, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone: Mapped[str] = mapped_column(String(32), default="")
    avatar_seed: Mapped[str] = mapped_column(String(64), default="")
    last_login_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    trainee_profile: Mapped["TraineeProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        init=False,
        cascade="all, delete-orphan",
    )
    trainer_profile: Mapped["TrainerProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        init=False,
        cascade="all, delete-orphan",
    )
    reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", init=False, cascade="all, delete-orphan"
    )
    skills: Mapped[list["UserSkill"]] = relationship(
        back_populates="user",
        init=False,
        cascade="all, delete-orphan",
        foreign_keys=lambda: [UserSkill.user_id],
        primaryjoin=lambda: User.id == UserSkill.user_id,
    )


class PasswordResetToken(Base):
    __tablename__ = "cc_password_reset_token"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_cc_reset_token_hash"),
        Index("ix_cc_reset_user_active", "user_id", "used_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    requested_ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=_utcnow,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(
        back_populates="reset_tokens", init=False
    )


class ApprovalRequest(Base, TimestampMixin):
    """Audit record of admin approval / role decisions."""

    __tablename__ = "cc_approval_request"
    __table_args__ = (
        Index("ix_cc_approval_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    requested_role: Mapped[str] = mapped_column(
        String(16), default=UserRole.TRAINEE.value
    )
    status: Mapped[str] = mapped_column(
        String(16), default=ApprovalStatus.PENDING.value, index=True
    )
    decided_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )
    decided_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    note: Mapped[str] = mapped_column(Text, default="")


# --------------------------------------------------------------------------
# Professional profiles
# --------------------------------------------------------------------------
class TraineeProfile(Base, TimestampMixin):
    __tablename__ = "cc_trainee_profile"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_cc_trainee_profile_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    designation: Mapped[str] = mapped_column(String(120), default="")
    department: Mapped[str] = mapped_column(String(120), default="")
    organization: Mapped[str] = mapped_column(String(160), default="")
    employee_code: Mapped[str] = mapped_column(String(64), default="")
    station: Mapped[str] = mapped_column(String(120), default="")
    region: Mapped[str] = mapped_column(String(120), default="")
    date_of_joining: Mapped[dt.date | None] = mapped_column(default=None)
    total_experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    bio: Mapped[str] = mapped_column(Text, default="")
    career_goal: Mapped[str] = mapped_column(Text, default="")
    profile_completion: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship(
        back_populates="trainee_profile", init=False
    )


class TrainerProfile(Base, TimestampMixin):
    __tablename__ = "cc_trainer_profile"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_cc_trainer_profile_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    designation: Mapped[str] = mapped_column(String(120), default="")
    department: Mapped[str] = mapped_column(String(120), default="")
    organization: Mapped[str] = mapped_column(String(160), default="")
    specialization: Mapped[str] = mapped_column(String(200), default="")
    years_of_training: Mapped[float] = mapped_column(Float, default=0.0)
    highest_qualification: Mapped[str] = mapped_column(String(160), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    languages: Mapped[str] = mapped_column(String(200), default="")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    rating_average: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    profile_completion: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship(
        back_populates="trainer_profile", init=False
    )


class Qualification(Base, TimestampMixin):
    __tablename__ = "cc_qualification"
    __table_args__ = (
        Index("ix_cc_qualification_user_year", "user_id", "end_year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    degree: Mapped[str] = mapped_column(String(160), default="")
    field_of_study: Mapped[str] = mapped_column(String(160), default="")
    institution: Mapped[str] = mapped_column(String(200), default="")
    start_year: Mapped[int | None] = mapped_column(Integer, default=None)
    end_year: Mapped[int | None] = mapped_column(Integer, default=None)
    grade: Mapped[str] = mapped_column(String(40), default="")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)


class WorkExperience(Base, TimestampMixin):
    __tablename__ = "cc_work_experience"
    __table_args__ = (
        Index("ix_cc_experience_user_start", "user_id", "start_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    organization: Mapped[str] = mapped_column(String(200), default="")
    role_title: Mapped[str] = mapped_column(String(160), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    start_date: Mapped[dt.date | None] = mapped_column(default=None)
    end_date: Mapped[dt.date | None] = mapped_column(default=None)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    responsibilities: Mapped[str] = mapped_column(Text, default="")


class Interest(Base):
    __tablename__ = "cc_interest"
    __table_args__ = (UniqueConstraint("name", name="uq_cc_interest_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(80), default="")


class UserInterest(Base):
    __tablename__ = "cc_user_interest"
    __table_args__ = (
        UniqueConstraint("user_id", "interest_id", name="uq_cc_user_interest"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    interest_id: Mapped[int] = mapped_column(
        ForeignKey("cc_interest.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=_utcnow,
        server_default=func.now(),
    )


# --------------------------------------------------------------------------
# Skills & proficiency
# --------------------------------------------------------------------------
class Skill(Base, TimestampMixin):
    __tablename__ = "cc_skill"
    __table_args__ = (
        UniqueConstraint("name", name="uq_cc_skill_name"),
        Index("ix_cc_skill_category", "category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str] = mapped_column(String(140), index=True)
    category: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserSkill(Base, TimestampMixin):
    """Proficiency mapping for both trainees (current skills) and trainers (expertise)."""

    __tablename__ = "cc_user_skill"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_cc_user_skill"),
        CheckConstraint(
            "proficiency_score >= 0 AND proficiency_score <= 100",
            name="ck_cc_user_skill_score",
        ),
        Index("ix_cc_user_skill_skill_level", "skill_id", "level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("cc_skill.id", ondelete="CASCADE"), index=True
    )
    level: Mapped[str] = mapped_column(
        String(16), default=ProficiencyLevel.BEGINNER.value
    )
    proficiency_score: Mapped[int] = mapped_column(Integer, default=0)
    years_of_practice: Mapped[float] = mapped_column(Float, default=0.0)
    is_teachable: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )
    verified_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    user: Mapped["User"] = relationship(
        back_populates="skills", init=False, foreign_keys=[user_id]
    )
    skill: Mapped["Skill"] = relationship(init=False)


# --------------------------------------------------------------------------
# Courses
# --------------------------------------------------------------------------
class Course(Base, TimestampMixin):
    __tablename__ = "cc_course"
    __table_args__ = (
        UniqueConstraint("code", name="uq_cc_course_code"),
        Index("ix_cc_course_status_start", "status", "start_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    code: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(220), index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(100), default="", index=True)
    level: Mapped[str] = mapped_column(
        String(16), default=ProficiencyLevel.BEGINNER.value
    )
    mode: Mapped[str] = mapped_column(String(24), default="online")
    duration_hours: Mapped[float] = mapped_column(Float, default=0.0)
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(16), default=CourseStatus.DRAFT.value, index=True
    )
    start_date: Mapped[dt.date | None] = mapped_column(default=None)
    end_date: Mapped[dt.date | None] = mapped_column(default=None)
    enrollment_deadline: Mapped[dt.date | None] = mapped_column(default=None)
    banner_url: Mapped[str] = mapped_column(String(400), default="")
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )

    required_skills: Mapped[list["CourseRequiredSkill"]] = relationship(
        back_populates="course", init=False, cascade="all, delete-orphan"
    )
    trainer_assignments: Mapped[list["CourseTrainerAssignment"]] = relationship(
        back_populates="course", init=False, cascade="all, delete-orphan"
    )
    resources: Mapped[list["LearningResource"]] = relationship(
        back_populates="course", init=False, cascade="all, delete-orphan"
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="course", init=False, cascade="all, delete-orphan"
    )
    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="course", init=False, cascade="all, delete-orphan"
    )
    course_assignments: Mapped[list["CourseAssignment"]] = relationship(
        back_populates="course", init=False, cascade="all, delete-orphan"
    )


class CourseRequiredSkill(Base):
    __tablename__ = "cc_course_required_skill"
    __table_args__ = (
        UniqueConstraint("course_id", "skill_id", name="uq_cc_course_skill"),
        CheckConstraint(
            "weight >= 0 AND weight <= 10", name="ck_cc_course_skill_weight"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("cc_skill.id", ondelete="CASCADE"), index=True
    )
    minimum_level: Mapped[str] = mapped_column(
        String(16), default=ProficiencyLevel.BEGINNER.value
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)

    course: Mapped["Course"] = relationship(
        back_populates="required_skills", init=False
    )
    skill: Mapped["Skill"] = relationship(init=False)


class CourseTrainerAssignment(Base, TimestampMixin):
    __tablename__ = "cc_course_trainer_assignment"
    __table_args__ = (
        UniqueConstraint(
            "course_id", "trainer_id", name="uq_cc_course_trainer"
        ),
        Index("ix_cc_assignment_trainer_status", "trainer_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="CASCADE"), index=True
    )
    trainer_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    assignment_role: Mapped[str] = mapped_column(
        String(16), default=TrainerAssignmentRole.LEAD.value
    )
    status: Mapped[str] = mapped_column(
        String(16), default=ApprovalStatus.APPROVED.value
    )
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    assigned_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )
    notes: Mapped[str] = mapped_column(Text, default="")

    course: Mapped["Course"] = relationship(
        back_populates="trainer_assignments", init=False
    )
    trainer: Mapped["User"] = relationship(
        init=False, foreign_keys=[trainer_id]
    )


# --------------------------------------------------------------------------
# Learning resources, enrollment & progress
# --------------------------------------------------------------------------
class LearningResource(Base, TimestampMixin):
    __tablename__ = "cc_learning_resource"
    __table_args__ = (
        Index("ix_cc_resource_course_order", "course_id", "sort_order"),
        CheckConstraint(
            "file_size_bytes >= 0", name="ck_cc_resource_file_size_bytes"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="CASCADE"), index=True
    )
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )
    title: Mapped[str] = mapped_column(String(220), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    resource_type: Mapped[str] = mapped_column(
        String(16), default=ResourceType.DOCUMENT.value
    )
    module_name: Mapped[str] = mapped_column(String(160), default="")
    file_name: Mapped[str] = mapped_column(String(300), default="")
    file_size_bytes: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    content_type: Mapped[str] = mapped_column(
        String(255), default="", server_default=""
    )
    sha256_digest: Mapped[str] = mapped_column(
        String(64), default="", server_default=""
    )
    external_url: Mapped[str] = mapped_column(String(500), default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)

    course: Mapped["Course"] = relationship(
        back_populates="resources", init=False
    )


class Enrollment(Base, TimestampMixin):
    __tablename__ = "cc_enrollment"
    __table_args__ = (
        UniqueConstraint("course_id", "trainee_id", name="uq_cc_enrollment"),
        Index("ix_cc_enrollment_trainee_status", "trainee_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="CASCADE"), index=True
    )
    trainee_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), default=EnrollmentStatus.ACTIVE.value, index=True
    )
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    enrolled_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    last_activity_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )

    course: Mapped["Course"] = relationship(
        back_populates="enrollments", init=False
    )
    trainee: Mapped["User"] = relationship(
        init=False, foreign_keys=[trainee_id]
    )
    resource_progress: Mapped[list["ResourceProgress"]] = relationship(
        back_populates="enrollment", init=False, cascade="all, delete-orphan"
    )


class ResourceProgress(Base, TimestampMixin):
    __tablename__ = "cc_resource_progress"
    __table_args__ = (
        UniqueConstraint(
            "enrollment_id", "resource_id", name="uq_cc_resource_progress"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("cc_enrollment.id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("cc_learning_resource.id", ondelete="CASCADE"), index=True
    )
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    time_spent_minutes: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    enrollment: Mapped["Enrollment"] = relationship(
        back_populates="resource_progress", init=False
    )


# --------------------------------------------------------------------------
# Assessments
# --------------------------------------------------------------------------
class Assessment(Base, TimestampMixin):
    __tablename__ = "cc_assessment"
    __table_args__ = (
        Index("ix_cc_assessment_course_status", "course_id", "status"),
        CheckConstraint(
            "time_limit_minutes BETWEEN 1 AND 300",
            name="ck_cc_assessment_time_limit",
        ),
        CheckConstraint(
            "max_attempts BETWEEN 1 AND 10",
            name="ck_cc_assessment_max_attempts",
        ),
        CheckConstraint(
            "total_marks >= 0 AND passing_marks >= 0",
            name="ck_cc_assessment_nonnegative_marks",
        ),
        CheckConstraint(
            "total_marks = 0 OR passing_marks <= total_marks",
            name="ck_cc_assessment_passing_marks",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="CASCADE"), index=True
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )
    title: Mapped[str] = mapped_column(String(220), default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(
        String(16), default=AssessmentStatus.DRAFT.value
    )
    total_marks: Mapped[float] = mapped_column(Float, default=0.0)
    passing_marks: Mapped[float] = mapped_column(Float, default=0.0)
    time_limit_minutes: Mapped[int] = mapped_column(Integer, default=30)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1)
    opens_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    deadline_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True)

    course: Mapped["Course"] = relationship(
        back_populates="assessments", init=False
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="assessment", init=False, cascade="all, delete-orphan"
    )
    attempts: Mapped[list["AssessmentAttempt"]] = relationship(
        back_populates="assessment", init=False, cascade="all, delete-orphan"
    )


class Question(Base, TimestampMixin):
    __tablename__ = "cc_question"
    __table_args__ = (
        Index("ix_cc_question_assessment_order", "assessment_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("cc_assessment.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_skill.id", ondelete="SET NULL"), default=None
    )
    competency_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    prompt: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    marks: Mapped[float] = mapped_column(Float, default=1.0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_multi_select: Mapped[bool] = mapped_column(Boolean, default=False)

    assessment: Mapped["Assessment"] = relationship(
        back_populates="questions", init=False
    )
    options: Mapped[list["QuestionOption"]] = relationship(
        back_populates="question", init=False, cascade="all, delete-orphan"
    )


class QuestionOption(Base):
    __tablename__ = "cc_question_option"
    __table_args__ = (
        Index("ix_cc_option_question_order", "question_id", "sort_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("cc_question.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(8), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    question: Mapped["Question"] = relationship(
        back_populates="options", init=False
    )


class AssessmentAttempt(Base, TimestampMixin):
    __tablename__ = "cc_assessment_attempt"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "trainee_id",
            "attempt_number",
            name="uq_cc_attempt_number",
        ),
        Index("ix_cc_attempt_trainee_status", "trainee_id", "status"),
        CheckConstraint("attempt_number >= 1", name="ck_cc_attempt_number"),
        CheckConstraint(
            "time_taken_seconds >= 0", name="ck_cc_attempt_time_taken"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("cc_assessment.id", ondelete="CASCADE"), index=True
    )
    trainee_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(
        String(16), default=AttemptStatus.IN_PROGRESS.value
    )
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    submitted_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    expires_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=dt.datetime(1970, 1, 1, tzinfo=dt.UTC),
        server_default="1970-01-01 00:00:00+00:00",
        comment="Authoritative server expiry snapshot set at attempt start. Legacy or omitted values fail closed as already expired.",
    )
    time_taken_seconds: Mapped[int] = mapped_column(Integer, default=0)

    assessment: Mapped["Assessment"] = relationship(
        back_populates="attempts", init=False
    )
    trainee: Mapped["User"] = relationship(
        init=False, foreign_keys=[trainee_id]
    )
    answers: Mapped[list["AttemptAnswer"]] = relationship(
        back_populates="attempt", init=False, cascade="all, delete-orphan"
    )
    result: Mapped["AssessmentResult | None"] = relationship(
        back_populates="attempt",
        uselist=False,
        init=False,
        cascade="all, delete-orphan",
    )


class AttemptAnswer(Base):
    __tablename__ = "cc_attempt_answer"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "question_id",
            "selected_option_id",
            name="uq_cc_attempt_answer",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("cc_assessment_attempt.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("cc_question.id", ondelete="CASCADE"), index=True
    )
    selected_option_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_question_option.id", ondelete="SET NULL"), default=None
    )
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    marks_awarded: Mapped[float] = mapped_column(Float, default=0.0)
    answered_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )

    attempt: Mapped["AssessmentAttempt"] = relationship(
        back_populates="answers", init=False
    )


class AssessmentResult(Base, TimestampMixin):
    __tablename__ = "cc_assessment_result"
    __table_args__ = (
        UniqueConstraint("attempt_id", name="uq_cc_result_attempt"),
        Index("ix_cc_result_trainee_passed", "trainee_id", "is_passed"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("cc_assessment_attempt.id", ondelete="CASCADE"), index=True
    )
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("cc_assessment.id", ondelete="CASCADE"), index=True
    )
    trainee_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)
    percentage: Mapped[float] = mapped_column(Float, default=0.0)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0)
    unanswered_count: Mapped[int] = mapped_column(Integer, default=0)
    is_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    grade: Mapped[str] = mapped_column(String(8), default="")
    graded_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    remarks: Mapped[str] = mapped_column(Text, default="")

    attempt: Mapped["AssessmentAttempt"] = relationship(
        back_populates="result", init=False
    )


# --------------------------------------------------------------------------
# Certificates, feedback, announcements
# --------------------------------------------------------------------------
class Certificate(Base, TimestampMixin):
    __tablename__ = "cc_certificate"
    __table_args__ = (
        UniqueConstraint("certificate_number", name="uq_cc_certificate_number"),
        UniqueConstraint(
            "verification_code", name="uq_cc_certificate_verification_code"
        ),
        UniqueConstraint(
            "course_id", "trainee_id", name="uq_cc_certificate_course_trainee"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    certificate_number: Mapped[str] = mapped_column(String(64), index=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="CASCADE"), index=True
    )
    trainee_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    issued_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )
    issued_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    final_score: Mapped[float] = mapped_column(Float, default=0.0)
    grade: Mapped[str] = mapped_column(String(8), default="")
    verification_code: Mapped[str] = mapped_column(
        String(64),
        default_factory=lambda: secrets.token_hex(32),
        index=True,
        comment="Opaque random public verification token, never a certificate serial. Existing duplicate tokens require remediation before uniqueness is applied.",
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    file_name: Mapped[str] = mapped_column(String(300), default="")


class CourseFeedback(Base, TimestampMixin):
    __tablename__ = "cc_course_feedback"
    __table_args__ = (
        UniqueConstraint(
            "course_id", "trainee_id", name="uq_cc_feedback_course_trainee"
        ),
        CheckConstraint(
            "overall_rating >= 1 AND overall_rating <= 5",
            name="ck_cc_feedback_rating",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="CASCADE"), index=True
    )
    trainee_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    trainer_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )
    overall_rating: Mapped[int] = mapped_column(Integer, default=5)
    content_rating: Mapped[int] = mapped_column(Integer, default=5)
    trainer_rating: Mapped[int] = mapped_column(Integer, default=5)
    relevance_rating: Mapped[int] = mapped_column(Integer, default=5)
    comments: Mapped[str] = mapped_column(Text, default="")
    suggestions: Mapped[str] = mapped_column(Text, default="")
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)


class Announcement(Base, TimestampMixin):
    __tablename__ = "cc_announcement"
    __table_args__ = (
        Index("ix_cc_announcement_pub_audience", "published_at", "audience"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    title: Mapped[str] = mapped_column(String(220), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    audience: Mapped[str] = mapped_column(
        String(16), default=AnnouncementAudience.ALL.value, index=True
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_course.id", ondelete="SET NULL"), default=None
    )
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    published_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    expires_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


# --------------------------------------------------------------------------
# Assignments & submissions
# --------------------------------------------------------------------------
class CourseAssignment(Base, TimestampMixin):
    """Trainer-authored practical assignment attached to a course."""

    __tablename__ = "cc_course_assignment"
    __table_args__ = (
        CheckConstraint(
            "total_marks >= 0 AND total_marks <= 1000",
            name="ck_cc_assignment_total_marks",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'closed', 'archived')",
            name="ck_cc_assignment_status",
        ),
        CheckConstraint(
            "late_penalty_percent >= 0 AND late_penalty_percent <= 100",
            name="ck_cc_assignment_late_penalty",
        ),
        Index("ix_cc_assignment_course_status", "course_id", "status"),
        Index("ix_cc_assignment_creator_due", "created_by_id", "due_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="CASCADE"), index=True
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )
    title: Mapped[str] = mapped_column(String(220), default="")
    instructions: Mapped[str] = mapped_column(Text, default="")
    reference_url: Mapped[str] = mapped_column(String(500), default="")
    assignment_type: Mapped[str] = mapped_column(
        String(24), default=AssignmentType.ESSAY.value, index=True
    )
    total_marks: Mapped[float] = mapped_column(Float, default=100.0)
    passing_marks: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(
        String(16), default=AssignmentStatus.DRAFT.value, index=True
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    due_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    allow_late_submission: Mapped[bool] = mapped_column(Boolean, default=True)
    late_penalty_percent: Mapped[float] = mapped_column(Float, default=0.0)
    allow_resubmission: Mapped[bool] = mapped_column(Boolean, default=True)
    submission_note: Mapped[str] = mapped_column(Text, default="")

    course: Mapped["Course"] = relationship(
        back_populates="course_assignments", init=False
    )
    creator: Mapped["User | None"] = relationship(
        init=False, foreign_keys=[created_by_id]
    )
    submissions: Mapped[list["AssignmentSubmission"]] = relationship(
        back_populates="assignment", init=False, cascade="all, delete-orphan"
    )


class AssignmentSubmission(Base, TimestampMixin):
    """One submission record per assignment + trainee pair."""

    __tablename__ = "cc_assignment_submission"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "trainee_id",
            name="uq_cc_submission_assignment_trainee",
        ),
        CheckConstraint(
            "marks_awarded IS NULL OR marks_awarded >= 0",
            name="ck_cc_submission_marks_awarded",
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'late', 'graded', 'returned')",
            name="ck_cc_submission_status",
        ),
        CheckConstraint(
            "attempt_count >= 0", name="ck_cc_submission_attempt_count"
        ),
        Index("ix_cc_submission_trainee_status", "trainee_id", "status"),
        Index("ix_cc_submission_assignment_status", "assignment_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course_assignment.id", ondelete="CASCADE"), index=True
    )
    trainee_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    response_text: Mapped[str] = mapped_column(Text, default="")
    submission_url: Mapped[str] = mapped_column(String(500), default="")
    file_name: Mapped[str] = mapped_column(String(300), default="")
    file_size_kb: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(16), default=SubmissionStatus.DRAFT.value, index=True
    )
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    submitted_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    marks_awarded: Mapped[float | None] = mapped_column(Float, default=None)
    feedback: Mapped[str] = mapped_column(Text, default="")
    graded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )
    graded_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    assignment: Mapped["CourseAssignment"] = relationship(
        back_populates="submissions", init=False
    )
    trainee: Mapped["User"] = relationship(
        init=False, foreign_keys=[trainee_id]
    )
    grader: Mapped["User | None"] = relationship(
        init=False, foreign_keys=[graded_by_id]
    )


# --------------------------------------------------------------------------
# Certificate requests
# --------------------------------------------------------------------------
class CertificateRequest(Base, TimestampMixin):
    """Trainee-initiated certification request awaiting admin review."""

    __tablename__ = "cc_certificate_request"
    __table_args__ = (
        UniqueConstraint(
            "course_id", "trainee_id", name="uq_cc_cert_request_course_trainee"
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'issued')",
            name="ck_cc_cert_request_status",
        ),
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="ck_cc_cert_request_progress",
        ),
        CheckConstraint(
            "average_score >= 0 AND average_score <= 100",
            name="ck_cc_cert_request_score",
        ),
        Index("ix_cc_cert_request_status_created", "status", "created_at"),
        Index("ix_cc_cert_request_trainee_status", "trainee_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="CASCADE"), index=True
    )
    trainee_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    enrollment_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_enrollment.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    justification: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(
        String(16), default=CertificateRequestStatus.PENDING.value, index=True
    )
    requested_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    average_score: Mapped[float] = mapped_column(Float, default=0.0)
    assessments_passed: Mapped[int] = mapped_column(Integer, default=0)
    assessments_total: Mapped[int] = mapped_column(Integer, default=0)
    is_eligible_snapshot: Mapped[bool] = mapped_column(Boolean, default=False)
    eligibility_note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    decision_note: Mapped[str] = mapped_column(Text, default="")
    certificate_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_certificate.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )

    course: Mapped["Course"] = relationship(init=False)
    trainee: Mapped["User"] = relationship(
        init=False, foreign_keys=[trainee_id]
    )
    reviewer: Mapped["User | None"] = relationship(
        init=False, foreign_keys=[reviewed_by_id]
    )
    enrollment: Mapped["Enrollment | None"] = relationship(init=False)
    certificate: Mapped["Certificate | None"] = relationship(init=False)


# --------------------------------------------------------------------------
# SIH26075 additive schema. Legacy tables and their relationships stay intact.
# Required identity FKs apply only to new tables; no legacy data is backfilled.
# --------------------------------------------------------------------------
class Organization(Base, TimestampMixin):
    __tablename__ = "cc_organization"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, default="")
    name: Mapped[str] = mapped_column(String(200), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(default=True)


class Department(Base, TimestampMixin):
    __tablename__ = "cc_department"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "code", name="uq_cc_department_code"
        ),
        UniqueConstraint("id", "organization_id", name="uq_cc_department_org"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("cc_organization.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(64), default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(default=True)
    organization: Mapped["Organization"] = relationship(init=False)


class OrganizationalRole(Base, TimestampMixin):
    """Professional role, distinct from legacy authentication/authorization roles."""

    __tablename__ = "cc_organizational_role"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_cc_org_role_code"),
        UniqueConstraint("id", "organization_id", name="uq_cc_org_role_org"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("cc_organization.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(160), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(default=True)


class UserOrganizationAssignment(Base, TimestampMixin):
    __tablename__ = "cc_user_organization_assignment"
    __table_args__ = (
        ForeignKeyConstraint(
            ["department_id", "organization_id"],
            ["cc_department.id", "cc_department.organization_id"],
            ondelete="RESTRICT",
            name="fk_cc_user_org_department",
        ),
        ForeignKeyConstraint(
            ["role_id", "organization_id"],
            [
                "cc_organizational_role.id",
                "cc_organizational_role.organization_id",
            ],
            ondelete="RESTRICT",
            name="fk_cc_user_org_role",
        ),
        UniqueConstraint(
            "user_id",
            "department_id",
            "role_id",
            "starts_at",
            name="uq_cc_user_org_assignment",
        ),
        CheckConstraint(
            "status IN ('active', 'ended', 'pending')",
            name="ck_cc_user_org_status",
        ),
        CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at",
            name="ck_cc_user_org_dates",
        ),
        Index("ix_cc_user_org_active", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("cc_organization.id", ondelete="RESTRICT"), index=True
    )
    department_id: Mapped[int] = mapped_column(Integer, index=True)
    role_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    starts_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=_utcnow,
        server_default=func.now(),
    )
    ends_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class Subject(Base, TimestampMixin):
    __tablename__ = "cc_subject"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, default="")
    name: Mapped[str] = mapped_column(String(160), default="", index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(default=True)


class Competency(Base, TimestampMixin):
    """Fixed scale: 1 Awareness, 2 Basic, 3 Working, 4 Advanced, 5 Expert.

    NULL means unmeasured, never level zero. AI cannot assign proficiency.
    """

    __tablename__ = "cc_competency"
    __table_args__ = (
        CheckConstraint(
            "scale_version = 'sih26075_v1'", name="ck_cc_competency_scale"
        ),
        {
            "comment": "Scale v1: 1 Awareness; 2 Basic (guided); 3 Working (independent); 4 Advanced (complex work); 5 Expert (mentors others)."
        },
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("cc_subject.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    scale_version: Mapped[str] = mapped_column(
        String(24), default="sih26075_v1", server_default="sih26075_v1"
    )
    subject: Mapped["Subject"] = relationship(init=False)


class OrganizationalCapacityNeed(Base, TimestampMixin):
    __tablename__ = "cc_organizational_capacity_need"
    __table_args__ = (
        ForeignKeyConstraint(
            ["department_id", "organization_id"],
            ["cc_department.id", "cc_department.organization_id"],
            ondelete="RESTRICT",
            name="fk_cc_need_department",
        ),
        UniqueConstraint(
            "organization_id", "code", name="uq_cc_capacity_need_code"
        ),
        CheckConstraint(
            "required_level BETWEEN 1 AND 5", name="ck_cc_need_level"
        ),
        CheckConstraint(
            "population_count >= 0 AND demand_count >= 0 AND demand_count <= population_count",
            name="ck_cc_need_population",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'fulfilled', 'archived')",
            name="ck_cc_need_status",
        ),
        CheckConstraint(
            "ends_at IS NULL OR ends_at > starts_at", name="ck_cc_need_period"
        ),
        Index("ix_cc_need_org_status", "organization_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("cc_organization.id", ondelete="RESTRICT"), index=True
    )
    department_id: Mapped[int | None] = mapped_column(
        Integer, default=None, index=True
    )
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="RESTRICT"), index=True
    )
    code: Mapped[str] = mapped_column(String(64), default="")
    required_level: Mapped[int] = mapped_column(default=1)
    population_count: Mapped[int] = mapped_column(default=0)
    demand_count: Mapped[int] = mapped_column(default=0)
    population_context: Mapped[str] = mapped_column(Text, default="")
    demand_context: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    starts_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    ends_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class RoleCompetencyRequirement(Base, TimestampMixin):
    __tablename__ = "cc_role_competency_requirement"
    __table_args__ = (
        UniqueConstraint(
            "role_id", "competency_id", name="uq_cc_role_competency"
        ),
        CheckConstraint(
            "required_level BETWEEN 1 AND 5", name="ck_cc_role_comp_level"
        ),
        CheckConstraint(
            "population_count >= 0 AND demand_count >= 0 AND demand_count <= population_count",
            name="ck_cc_role_comp_population",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    role_id: Mapped[int] = mapped_column(
        ForeignKey("cc_organizational_role.id", ondelete="CASCADE"), index=True
    )
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="RESTRICT"), index=True
    )
    capacity_need_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_organizational_capacity_need.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    required_level: Mapped[int] = mapped_column(default=1)
    population_count: Mapped[int] = mapped_column(default=0)
    demand_count: Mapped[int] = mapped_column(default=0)
    population_context: Mapped[str] = mapped_column(Text, default="")
    demand_context: Mapped[str] = mapped_column(Text, default="")
    is_mandatory: Mapped[bool] = mapped_column(default=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class CompetencyEvidence(Base, TimestampMixin):
    """Human/official measurements only; AI output is never proficiency evidence.

    Practice is formative, not an official result. External questionnaire and
    evaluation references identify auditable records, not model-generated scores.
    """

    __tablename__ = "cc_competency_evidence"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "competency_id",
            "evidence_type",
            "source_system",
            "source_reference",
            name="uq_cc_evidence_source",
        ),
        UniqueConstraint(
            "id",
            "user_id",
            "competency_id",
            "measured_level",
            "verification_status",
            "verified_at",
            name="uq_cc_evidence_snapshot_basis",
        ),
        CheckConstraint(
            "evidence_type IN ('official_assessment', 'questionnaire', 'trainer_evaluation', 'course_completion', 'practice', 'final_assessment')",
            name="ck_cc_evidence_type",
        ),
        CheckConstraint(
            "verification_status IN ('pending', 'verified', 'rejected', 'revoked')",
            name="ck_cc_evidence_status",
        ),
        CheckConstraint(
            "measured_level BETWEEN 1 AND 5", name="ck_cc_evidence_level"
        ),
        CheckConstraint(
            "measured_score BETWEEN 0 AND 100", name="ck_cc_evidence_score"
        ),
        CheckConstraint(
            "measured_level IS NOT NULL OR measured_score IS NOT NULL",
            name="ck_cc_evidence_measurement",
        ),
        CheckConstraint(
            "verification_status <> 'verified' OR (verifier_id IS NOT NULL AND verified_at IS NOT NULL)",
            name="ck_cc_evidence_verified",
        ),
        CheckConstraint(
            "verified_at IS NULL OR verified_at >= observed_at",
            name="ck_cc_evidence_time",
        ),
        CheckConstraint(
            "length(source_reference) > 0 AND length(source_system) > 0",
            name="ck_cc_evidence_reference",
        ),
        CheckConstraint(
            "(evidence_type IN ('official_assessment', 'final_assessment') AND assessment_result_id IS NOT NULL AND practice_attempt_id IS NULL) OR (evidence_type = 'practice' AND practice_attempt_id IS NOT NULL AND assessment_result_id IS NULL) OR (evidence_type = 'course_completion' AND enrollment_id IS NOT NULL AND assessment_result_id IS NULL AND practice_attempt_id IS NULL) OR (evidence_type IN ('questionnaire', 'trainer_evaluation') AND assessment_result_id IS NULL AND practice_attempt_id IS NULL)",
            name="ck_cc_evidence_source_kind",
        ),
        Index(
            "ix_cc_evidence_user_status",
            "user_id",
            "competency_id",
            "verification_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="RESTRICT"), index=True
    )
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="RESTRICT"), index=True
    )
    evidence_type: Mapped[str] = mapped_column(
        String(24), default="questionnaire"
    )
    source_system: Mapped[str] = mapped_column(
        String(80), default="capacity_connect"
    )
    source_reference: Mapped[str] = mapped_column(String(200), default="")
    assessment_result_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_assessment_result.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    enrollment_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_enrollment.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    practice_attempt_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_practice_attempt.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    measured_level: Mapped[int | None] = mapped_column(Integer, default=None)
    measured_score: Mapped[float | None] = mapped_column(
        Float, default=None, comment="Percentage 0–100; not an AI score."
    )
    verifier_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="RESTRICT"), default=None, index=True
    )
    verification_status: Mapped[str] = mapped_column(
        String(16), default="pending"
    )
    observed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    verified_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    notes: Mapped[str] = mapped_column(Text, default="")


class UserCompetency(Base, TimestampMixin):
    """Current snapshot derives from verified evidence; AI cannot write proficiency.

    Composite FK binds a measured level to the same user's verified evidence.
    Clear/rederive this snapshot before revoking its supporting evidence.
    Database service permissions must separately forbid AI proficiency writes.
    """

    __tablename__ = "cc_user_competency"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "competency_id", name="uq_cc_user_competency"
        ),
        ForeignKeyConstraint(
            [
                "evidence_id",
                "user_id",
                "competency_id",
                "current_level",
                "verification_status",
                "last_verified_at",
            ],
            [
                "cc_competency_evidence.id",
                "cc_competency_evidence.user_id",
                "cc_competency_evidence.competency_id",
                "cc_competency_evidence.measured_level",
                "cc_competency_evidence.verification_status",
                "cc_competency_evidence.verified_at",
            ],
            ondelete="RESTRICT",
            name="fk_cc_snapshot_verified_evidence",
        ),
        CheckConstraint(
            "current_level BETWEEN 1 AND 5", name="ck_cc_user_comp_current"
        ),
        CheckConstraint(
            "target_level BETWEEN 1 AND 5", name="ck_cc_user_comp_target"
        ),
        CheckConstraint(
            "(verification_status = 'unmeasured' AND current_level IS NULL AND evidence_id IS NULL AND last_verified_at IS NULL) OR (verification_status = 'verified' AND current_level IS NOT NULL AND evidence_id IS NOT NULL AND last_verified_at IS NOT NULL)",
            name="ck_cc_snapshot_verified_only",
        ),
        Index("ix_cc_user_comp_level", "competency_id", "current_level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="RESTRICT"), index=True
    )
    current_level: Mapped[int | None] = mapped_column(Integer, default=None)
    target_level: Mapped[int | None] = mapped_column(Integer, default=None)
    evidence_id: Mapped[int | None] = mapped_column(
        Integer, default=None, index=True
    )
    verification_status: Mapped[str] = mapped_column(
        String(16), default="unmeasured"
    )
    last_verified_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class CourseCompetencyRequirement(Base, TimestampMixin):
    __tablename__ = "cc_course_competency_requirement"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "competency_id",
            "requirement_type",
            name="uq_cc_course_comp_req",
        ),
        CheckConstraint(
            "required_level BETWEEN 1 AND 5", name="ck_cc_course_comp_level"
        ),
        CheckConstraint(
            "weight BETWEEN 0 AND 100", name="ck_cc_course_comp_weight"
        ),
        CheckConstraint(
            "requirement_type IN ('prerequisite', 'outcome', 'trainer')",
            name="ck_cc_course_comp_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="CASCADE"), index=True
    )
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="RESTRICT"), index=True
    )
    requirement_type: Mapped[str] = mapped_column(String(16), default="outcome")
    required_level: Mapped[int] = mapped_column(default=1)
    weight: Mapped[float] = mapped_column(default=1.0)
    is_mandatory: Mapped[bool] = mapped_column(default=True)
    course: Mapped["Course"] = relationship(init=False)
    competency: Mapped["Competency"] = relationship(init=False)


class TrainingProgram(Base, TimestampMixin):
    __tablename__ = "cc_training_program"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'completed', 'archived')",
            name="ck_cc_program_status",
        ),
        CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at",
            name="ck_cc_program_period",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_organization.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, default="")
    title: Mapped[str] = mapped_column(String(220), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    starts_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    ends_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class TrainingProgramCourse(Base, TimestampMixin):
    __tablename__ = "cc_training_program_course"
    __table_args__ = (
        UniqueConstraint(
            "program_id", "course_id", name="uq_cc_program_course"
        ),
        UniqueConstraint(
            "program_id", "position", name="uq_cc_program_course_order"
        ),
        CheckConstraint("position >= 1", name="ck_cc_program_course_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("cc_training_program.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="RESTRICT"), index=True
    )
    position: Mapped[int] = mapped_column(default=1)
    program: Mapped["TrainingProgram"] = relationship(init=False)
    course: Mapped["Course"] = relationship(init=False)


class CourseModule(Base, TimestampMixin):
    __tablename__ = "cc_course_module"
    __table_args__ = (
        UniqueConstraint("course_id", "position", name="uq_cc_module_order"),
        CheckConstraint(
            "position >= 1 AND duration_minutes >= 0",
            name="ck_cc_module_numbers",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_cc_module_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(220), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(default=1)
    duration_minutes: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    course: Mapped["Course"] = relationship(init=False)


class Lesson(Base, TimestampMixin):
    """Belongs to an existing Course through CourseModule."""

    __tablename__ = "cc_lesson"
    __table_args__ = (
        UniqueConstraint("module_id", "position", name="uq_cc_lesson_order"),
        CheckConstraint(
            "position >= 1 AND duration_minutes >= 0",
            name="ck_cc_lesson_numbers",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_cc_lesson_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course_module.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(220), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(default=1)
    duration_minutes: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    module: Mapped["CourseModule"] = relationship(init=False)


class LessonResource(Base, TimestampMixin):
    __tablename__ = "cc_lesson_resource"
    __table_args__ = (
        UniqueConstraint(
            "lesson_id", "resource_id", name="uq_cc_lesson_resource"
        ),
        UniqueConstraint(
            "lesson_id", "position", name="uq_cc_lesson_resource_order"
        ),
        CheckConstraint("position >= 1", name="ck_cc_lesson_resource_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("cc_lesson.id", ondelete="CASCADE"), index=True
    )
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("cc_learning_resource.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(default=1)
    is_required: Mapped[bool] = mapped_column(default=True)
    lesson: Mapped["Lesson"] = relationship(init=False)
    resource: Mapped["LearningResource"] = relationship(init=False)


class CompetencyGap(Base, TimestampMixin):
    """Persisted planning gap; unknown baseline is NULL, not a fabricated level."""

    __tablename__ = "cc_competency_gap"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_cc_gap_user"),
        CheckConstraint(
            "baseline_level BETWEEN 1 AND 5 AND required_level BETWEEN 1 AND 5",
            name="ck_cc_gap_levels",
        ),
        CheckConstraint(
            "status IN ('identified', 'in_progress', 'closed', 'superseded')",
            name="ck_cc_gap_status",
        ),
        Index("ix_cc_gap_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="RESTRICT"), index=True
    )
    capacity_need_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_organizational_capacity_need.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    role_requirement_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_role_competency_requirement.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    baseline_level: Mapped[int | None] = mapped_column(Integer, default=None)
    required_level: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String(16), default="identified")
    identified_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    closed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class LearningPath(Base, TimestampMixin):
    __tablename__ = "cc_learning_path"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_cc_learning_path_user"),
        CheckConstraint(
            "status IN ('draft', 'active', 'completed', 'archived')",
            name="ck_cc_path_status",
        ),
        Index("ix_cc_path_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    program_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_training_program.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(220), default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    steps: Mapped[list["LearningPathStep"]] = relationship(
        init=False,
        back_populates="path",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PracticeQuestion(Base, TimestampMixin):
    """Formative question bank, intentionally unrelated to official Question."""

    __tablename__ = "cc_practice_question"
    __table_args__ = (
        CheckConstraint(
            "difficulty_level BETWEEN 1 AND 5",
            name="ck_cc_practice_question_level",
        ),
        CheckConstraint("max_marks > 0", name="ck_cc_practice_question_marks"),
        CheckConstraint(
            "question_type IN ('single_choice', 'multiple_choice', 'short_answer')",
            name="ck_cc_practice_question_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_cc_practice_question_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="RESTRICT"), index=True
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_lesson.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_course.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    prompt: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    answer_rubric: Mapped[str] = mapped_column(Text, default="")
    question_type: Mapped[str] = mapped_column(
        String(24), default="single_choice"
    )
    difficulty_level: Mapped[int] = mapped_column(default=1)
    max_marks: Mapped[float] = mapped_column(default=1.0)
    status: Mapped[str] = mapped_column(String(16), default="draft")


class PracticeQuestionOption(Base):
    __tablename__ = "cc_practice_question_option"
    __table_args__ = (
        UniqueConstraint(
            "question_id", "position", name="uq_cc_practice_option_position"
        ),
        UniqueConstraint(
            "id", "question_id", name="uq_cc_practice_option_question"
        ),
        CheckConstraint("position >= 1", name="ck_cc_practice_option_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("cc_practice_question.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text, default="")
    position: Mapped[int] = mapped_column(default=1)
    is_correct: Mapped[bool] = mapped_column(default=False)


class LearningPathStep(Base, TimestampMixin):
    __tablename__ = "cc_learning_path_step"
    __table_args__ = (
        ForeignKeyConstraint(
            ["path_id", "user_id"],
            ["cc_learning_path.id", "cc_learning_path.user_id"],
            ondelete="CASCADE",
            name="fk_cc_path_step_owner",
        ),
        ForeignKeyConstraint(
            ["gap_id", "user_id"],
            ["cc_competency_gap.id", "cc_competency_gap.user_id"],
            ondelete="RESTRICT",
            name="fk_cc_path_step_gap",
        ),
        UniqueConstraint("path_id", "position", name="uq_cc_path_step_order"),
        CheckConstraint("position >= 1", name="ck_cc_path_step_position"),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'skipped')",
            name="ck_cc_path_step_status",
        ),
        CheckConstraint(
            "(CASE WHEN course_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN module_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN lesson_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN resource_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN practice_question_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN assessment_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_cc_path_step_one_target",
        ),
        CheckConstraint(
            "(step_type = 'course' AND course_id IS NOT NULL) OR (step_type = 'module' AND module_id IS NOT NULL) OR (step_type = 'lesson' AND lesson_id IS NOT NULL) OR (step_type = 'resource' AND resource_id IS NOT NULL) OR (step_type = 'practice' AND practice_question_id IS NOT NULL) OR (step_type = 'assessment' AND assessment_id IS NOT NULL)",
            name="ck_cc_path_step_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    path_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    gap_id: Mapped[int | None] = mapped_column(
        Integer, default=None, index=True
    )
    position: Mapped[int] = mapped_column(default=1)
    step_type: Mapped[str] = mapped_column(String(16), default="course")
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_course.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    module_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_course_module.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_lesson.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    resource_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_learning_resource.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    practice_question_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_practice_question.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    assessment_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_assessment.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), default="pending")
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    path: Mapped["LearningPath"] = relationship(
        init=False, back_populates="steps"
    )


class PracticeAttempt(Base, TimestampMixin):
    """Formative scores never enter AssessmentResult or official pass rates."""

    __tablename__ = "cc_practice_attempt"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'submitted', 'graded', 'abandoned')",
            name="ck_cc_practice_attempt_status",
        ),
        CheckConstraint(
            "percentage BETWEEN 0 AND 100",
            name="ck_cc_practice_attempt_percentage",
        ),
        CheckConstraint(
            "max_marks >= 0 AND marks_awarded >= 0 AND marks_awarded <= max_marks",
            name="ck_cc_practice_attempt_marks",
        ),
        CheckConstraint(
            "submitted_at IS NULL OR submitted_at >= started_at",
            name="ck_cc_practice_attempt_time",
        ),
        Index("ix_cc_practice_user_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="RESTRICT"), index=True
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_lesson.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), default="in_progress")
    max_marks: Mapped[float] = mapped_column(default=0.0)
    marks_awarded: Mapped[float | None] = mapped_column(Float, default=None)
    percentage: Mapped[float | None] = mapped_column(Float, default=None)
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    submitted_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    graded_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class PracticeAnswer(Base, TimestampMixin):
    __tablename__ = "cc_practice_answer"
    __table_args__ = (
        UniqueConstraint(
            "attempt_id", "question_id", name="uq_cc_practice_answer"
        ),
        UniqueConstraint(
            "id", "question_id", name="uq_cc_practice_answer_question"
        ),
        CheckConstraint(
            "max_marks > 0 AND marks_awarded >= 0 AND marks_awarded <= max_marks",
            name="ck_cc_practice_answer_marks",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("cc_practice_attempt.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("cc_practice_question.id", ondelete="RESTRICT"), index=True
    )
    response_text: Mapped[str] = mapped_column(Text, default="")
    prompt_snapshot: Mapped[str] = mapped_column(Text, default="")
    rubric_snapshot: Mapped[str] = mapped_column(Text, default="")
    max_marks: Mapped[float] = mapped_column(default=1.0)
    marks_awarded: Mapped[float | None] = mapped_column(Float, default=None)
    feedback: Mapped[str] = mapped_column(Text, default="")
    grader_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None, index=True
    )
    answered_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )


class PracticeAnswerSelection(Base):
    __tablename__ = "cc_practice_answer_selection"
    __table_args__ = (
        ForeignKeyConstraint(
            ["answer_id", "question_id"],
            ["cc_practice_answer.id", "cc_practice_answer.question_id"],
            ondelete="CASCADE",
            name="fk_cc_practice_selection_answer",
        ),
        ForeignKeyConstraint(
            ["option_id", "question_id"],
            [
                "cc_practice_question_option.id",
                "cc_practice_question_option.question_id",
            ],
            ondelete="RESTRICT",
            name="fk_cc_practice_selection_option",
        ),
        UniqueConstraint(
            "answer_id", "option_id", name="uq_cc_practice_selection"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    answer_id: Mapped[int] = mapped_column(Integer, index=True)
    question_id: Mapped[int] = mapped_column(Integer, index=True)
    option_id: Mapped[int] = mapped_column(Integer, index=True)


class TrainerAvailability(Base, TimestampMixin):
    __tablename__ = "cc_trainer_availability"
    __table_args__ = (
        UniqueConstraint(
            "trainer_id",
            "starts_at",
            "ends_at",
            name="uq_cc_trainer_availability_window",
        ),
        CheckConstraint(
            "ends_at > starts_at", name="ck_cc_availability_window"
        ),
        CheckConstraint(
            "status IN ('available', 'unavailable', 'tentative')",
            name="ck_cc_availability_status",
        ),
        Index(
            "ix_cc_availability_trainer_window",
            "trainer_id",
            "starts_at",
            "ends_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    trainer_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    starts_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    ends_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    status: Mapped[str] = mapped_column(String(16), default="available")
    timezone_name: Mapped[str] = mapped_column(String(64), default="UTC")
    notes: Mapped[str] = mapped_column(Text, default="")


class TrainerCapacity(Base, TimestampMixin):
    __tablename__ = "cc_trainer_capacity"
    __table_args__ = (
        UniqueConstraint(
            "trainer_id",
            "starts_at",
            "ends_at",
            name="uq_cc_trainer_capacity_period",
        ),
        CheckConstraint("ends_at > starts_at", name="ck_cc_capacity_period"),
        CheckConstraint(
            "max_hours >= 0 AND allocated_hours >= 0 AND allocated_hours <= max_hours AND max_courses >= 0 AND allocated_courses >= 0 AND allocated_courses <= max_courses AND max_participants >= 0 AND allocated_participants >= 0 AND allocated_participants <= max_participants",
            name="ck_cc_capacity_nonnegative",
        ),
        Index(
            "ix_cc_capacity_trainer_period",
            "trainer_id",
            "starts_at",
            "ends_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    trainer_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    starts_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    ends_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    max_hours: Mapped[float] = mapped_column(default=0.0)
    allocated_hours: Mapped[float] = mapped_column(default=0.0)
    max_courses: Mapped[int] = mapped_column(default=0)
    allocated_courses: Mapped[int] = mapped_column(default=0)
    max_participants: Mapped[int] = mapped_column(default=0)
    allocated_participants: Mapped[int] = mapped_column(default=0)


class TrainerFitWeights(Base, TimestampMixin):
    """Versioned policy; create a new version instead of editing a used policy."""

    __tablename__ = "cc_trainer_fit_weights"
    __table_args__ = (
        UniqueConstraint(
            "policy_code", "version", name="uq_cc_fit_policy_version"
        ),
        UniqueConstraint(
            "id",
            "competency_weight",
            "experience_weight",
            "effectiveness_weight",
            "availability_weight",
            "capacity_weight",
            name="uq_cc_fit_policy_values",
        ),
        CheckConstraint("version >= 1", name="ck_cc_fit_policy_version"),
        CheckConstraint(
            "competency_weight BETWEEN 0 AND 100 AND experience_weight BETWEEN 0 AND 100 AND effectiveness_weight BETWEEN 0 AND 100 AND availability_weight BETWEEN 0 AND 100 AND capacity_weight BETWEEN 0 AND 100",
            name="ck_cc_fit_weight_ranges",
        ),
        CheckConstraint(
            "abs(competency_weight + experience_weight + effectiveness_weight + availability_weight + capacity_weight - 100) < 0.000001",
            name="ck_cc_fit_weight_sum",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_organization.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    policy_code: Mapped[str] = mapped_column(String(64), default="default")
    version: Mapped[int] = mapped_column(default=1)
    competency_weight: Mapped[float] = mapped_column(default=40.0)
    experience_weight: Mapped[float] = mapped_column(default=20.0)
    effectiveness_weight: Mapped[float] = mapped_column(default=20.0)
    availability_weight: Mapped[float] = mapped_column(default=10.0)
    capacity_weight: Mapped[float] = mapped_column(default=10.0)
    is_active: Mapped[bool] = mapped_column(default=True)
    description: Mapped[str] = mapped_column(Text, default="")


class TrainerFitEvaluation(Base, TimestampMixin):
    """Auditable fit recommendation, never a user proficiency measurement."""

    __tablename__ = "cc_trainer_fit_evaluation"
    __table_args__ = (
        ForeignKeyConstraint(
            [
                "weights_id",
                "competency_weight",
                "experience_weight",
                "effectiveness_weight",
                "availability_weight",
                "capacity_weight",
            ],
            [
                "cc_trainer_fit_weights.id",
                "cc_trainer_fit_weights.competency_weight",
                "cc_trainer_fit_weights.experience_weight",
                "cc_trainer_fit_weights.effectiveness_weight",
                "cc_trainer_fit_weights.availability_weight",
                "cc_trainer_fit_weights.capacity_weight",
            ],
            ondelete="RESTRICT",
            onupdate="RESTRICT",
            name="fk_cc_fit_evaluation_policy",
        ),
        CheckConstraint(
            "eligibility_status IN ('eligible', 'ineligible', 'insufficient_evidence')",
            name="ck_cc_fit_eligibility",
        ),
        CheckConstraint(
            "competency_score BETWEEN 0 AND 100 AND experience_score BETWEEN 0 AND 100 AND effectiveness_score BETWEEN 0 AND 100 AND availability_score BETWEEN 0 AND 100 AND capacity_score BETWEEN 0 AND 100 AND weighted_total BETWEEN 0 AND 100",
            name="ck_cc_fit_scores",
        ),
        CheckConstraint(
            "abs(weighted_total - (competency_score * competency_weight + experience_score * experience_weight + effectiveness_score * effectiveness_weight + availability_score * availability_weight + capacity_score * capacity_weight) / 100.0) < 0.0001",
            name="ck_cc_fit_weighted_total",
        ),
        Index(
            "ix_cc_fit_course_rank",
            "course_id",
            "eligibility_status",
            "weighted_total",
        ),
        Index("ix_cc_fit_trainer_time", "trainer_id", "evaluated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="RESTRICT"), index=True
    )
    trainer_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="RESTRICT"), index=True
    )
    weights_id: Mapped[int] = mapped_column(Integer, index=True)
    eligibility_status: Mapped[str] = mapped_column(
        String(24), default="insufficient_evidence"
    )
    competency_score: Mapped[float] = mapped_column(default=0.0)
    experience_score: Mapped[float] = mapped_column(default=0.0)
    effectiveness_score: Mapped[float] = mapped_column(default=0.0)
    availability_score: Mapped[float] = mapped_column(default=0.0)
    capacity_score: Mapped[float] = mapped_column(default=0.0)
    competency_weight: Mapped[float] = mapped_column(default=40.0)
    experience_weight: Mapped[float] = mapped_column(default=20.0)
    effectiveness_weight: Mapped[float] = mapped_column(default=20.0)
    availability_weight: Mapped[float] = mapped_column(default=10.0)
    capacity_weight: Mapped[float] = mapped_column(default=10.0)
    weighted_total: Mapped[float] = mapped_column(default=0.0)
    explanation: Mapped[str] = mapped_column(Text, default="")
    algorithm_version: Mapped[str] = mapped_column(String(64), default="v1")
    evaluated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=_utcnow,
        server_default=func.now(),
    )


class TrainerTeamMatch(Base, TimestampMixin):
    __tablename__ = "cc_trainer_team_match"
    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'superseded')",
            name="ck_cc_team_match_status",
        ),
        CheckConstraint(
            "coverage_percent BETWEEN 0 AND 100 AND weighted_total BETWEEN 0 AND 100",
            name="ck_cc_team_match_scores",
        ),
        CheckConstraint(
            "eligibility_status IN ('eligible', 'ineligible', 'insufficient_evidence')",
            name="ck_cc_team_match_eligibility",
        ),
        Index("ix_cc_team_course_status", "course_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="RESTRICT"), index=True
    )
    weights_id: Mapped[int] = mapped_column(
        ForeignKey("cc_trainer_fit_weights.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="proposed")
    eligibility_status: Mapped[str] = mapped_column(
        String(24), default="insufficient_evidence"
    )
    coverage_percent: Mapped[float] = mapped_column(default=0.0)
    weighted_total: Mapped[float] = mapped_column(default=0.0)
    explanation: Mapped[str] = mapped_column(Text, default="")
    evaluated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )


class TrainerTeamMember(Base, TimestampMixin):
    __tablename__ = "cc_trainer_team_member"
    __table_args__ = (
        UniqueConstraint(
            "team_match_id", "trainer_id", name="uq_cc_team_member"
        ),
        UniqueConstraint("id", "team_match_id", name="uq_cc_team_member_team"),
        CheckConstraint(
            "member_role IN ('lead', 'co_trainer', 'guest')",
            name="ck_cc_team_member_role",
        ),
        CheckConstraint("allocated_hours >= 0", name="ck_cc_team_member_hours"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    team_match_id: Mapped[int] = mapped_column(
        ForeignKey("cc_trainer_team_match.id", ondelete="CASCADE"), index=True
    )
    trainer_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="RESTRICT"), index=True
    )
    fit_evaluation_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_trainer_fit_evaluation.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    member_role: Mapped[str] = mapped_column(String(16), default="co_trainer")
    allocated_hours: Mapped[float] = mapped_column(default=0.0)


class TrainerTeamCompetencyCoverage(Base, TimestampMixin):
    """One row per team competency, including explicitly uncovered requirements."""

    __tablename__ = "cc_trainer_team_competency_coverage"
    __table_args__ = (
        ForeignKeyConstraint(
            ["member_id", "team_match_id"],
            [
                "cc_trainer_team_member.id",
                "cc_trainer_team_member.team_match_id",
            ],
            ondelete="RESTRICT",
            name="fk_cc_team_coverage_member",
        ),
        UniqueConstraint(
            "team_match_id",
            "competency_id",
            name="uq_cc_team_competency_coverage",
        ),
        CheckConstraint(
            "required_level BETWEEN 1 AND 5 AND covered_level BETWEEN 1 AND 5",
            name="ck_cc_team_coverage_levels",
        ),
        CheckConstraint(
            "(coverage_status = 'uncovered' AND member_id IS NULL AND covered_level IS NULL) OR (coverage_status = 'partial' AND member_id IS NOT NULL AND covered_level IS NOT NULL AND covered_level < required_level) OR (coverage_status = 'covered' AND member_id IS NOT NULL AND covered_level IS NOT NULL AND covered_level >= required_level)",
            name="ck_cc_team_coverage_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    team_match_id: Mapped[int] = mapped_column(
        ForeignKey("cc_trainer_team_match.id", ondelete="CASCADE"), index=True
    )
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="RESTRICT"), index=True
    )
    member_id: Mapped[int | None] = mapped_column(
        Integer, default=None, index=True
    )
    required_level: Mapped[int] = mapped_column(default=1)
    covered_level: Mapped[int | None] = mapped_column(Integer, default=None)
    coverage_status: Mapped[str] = mapped_column(
        String(16), default="uncovered"
    )
    explanation: Mapped[str] = mapped_column(Text, default="")


class CompetencyObservation(Base, TimestampMixin):
    """Pre/post observations are descriptive, not causal training effects."""

    __tablename__ = "cc_competency_observation"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "user_id",
            "competency_id",
            "phase",
            "observed_at",
            name="uq_cc_competency_observation",
        ),
        CheckConstraint(
            "phase IN ('pre', 'post', 'follow_up')",
            name="ck_cc_observation_phase",
        ),
        CheckConstraint(
            "observed_level BETWEEN 1 AND 5", name="ck_cc_observation_level"
        ),
        CheckConstraint(
            "verification_status IN ('pending', 'verified', 'rejected')",
            name="ck_cc_observation_status",
        ),
        CheckConstraint(
            "verification_status <> 'verified' OR (observer_id IS NOT NULL AND verified_at IS NOT NULL)",
            name="ck_cc_observation_verified",
        ),
        Index(
            "ix_cc_observation_course_phase",
            "course_id",
            "phase",
            "competency_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="RESTRICT"), index=True
    )
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="RESTRICT"), index=True
    )
    observer_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="RESTRICT"), default=None, index=True
    )
    evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_competency_evidence.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    phase: Mapped[str] = mapped_column(String(16), default="pre")
    observed_level: Mapped[int] = mapped_column(default=1)
    verification_status: Mapped[str] = mapped_column(
        String(16), default="pending"
    )
    observed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    verified_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    notes: Mapped[str] = mapped_column(Text, default="")


class TrainingEffectivenessSnapshot(Base, TimestampMixin):
    """Observational aggregates only; differences do not establish causation.

    Missing measurements stay NULL. Assessment deltas are percentage points;
    competency deltas are scale points. Practice is excluded from official metrics.
    """

    __tablename__ = "cc_training_effectiveness_snapshot"
    __table_args__ = (
        CheckConstraint(
            "interpretation = 'observational_not_causal'",
            name="ck_cc_effectiveness_interpretation",
        ),
        CheckConstraint(
            "participants >= 0 AND completions BETWEEN 0 AND participants AND assessment_pairs BETWEEN 0 AND participants AND observation_pairs BETWEEN 0 AND participants AND feedback_count BETWEEN 0 AND participants",
            name="ck_cc_effectiveness_counts",
        ),
        CheckConstraint(
            "pre_average BETWEEN 0 AND 100 AND post_average BETWEEN 0 AND 100 AND pass_rate BETWEEN 0 AND 100",
            name="ck_cc_effectiveness_percentages",
        ),
        CheckConstraint(
            "assessment_improvement BETWEEN -100 AND 100",
            name="ck_cc_effectiveness_assessment_delta",
        ),
        CheckConstraint(
            "feedback_average BETWEEN 1 AND 5 AND pre_competency_average BETWEEN 1 AND 5 AND post_competency_average BETWEEN 1 AND 5",
            name="ck_cc_effectiveness_averages",
        ),
        CheckConstraint(
            "observed_competency_improvement BETWEEN -4 AND 4",
            name="ck_cc_effectiveness_competency_delta",
        ),
        CheckConstraint(
            "period_end > period_start", name="ck_cc_effectiveness_period"
        ),
        Index("ix_cc_effectiveness_course_time", "course_id", "calculated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("cc_course.id", ondelete="RESTRICT"), index=True
    )
    competency_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    participants: Mapped[int] = mapped_column(default=0)
    completions: Mapped[int] = mapped_column(default=0)
    assessment_pairs: Mapped[int] = mapped_column(default=0)
    observation_pairs: Mapped[int] = mapped_column(default=0)
    feedback_count: Mapped[int] = mapped_column(default=0)
    pre_average: Mapped[float | None] = mapped_column(Float, default=None)
    post_average: Mapped[float | None] = mapped_column(Float, default=None)
    assessment_improvement: Mapped[float | None] = mapped_column(
        Float, default=None
    )
    pass_rate: Mapped[float | None] = mapped_column(Float, default=None)
    feedback_average: Mapped[float | None] = mapped_column(Float, default=None)
    feedback_summary: Mapped[str] = mapped_column(Text, default="")
    pre_competency_average: Mapped[float | None] = mapped_column(
        Float, default=None
    )
    post_competency_average: Mapped[float | None] = mapped_column(
        Float, default=None
    )
    observed_competency_improvement: Mapped[float | None] = mapped_column(
        Float, default=None
    )
    interpretation: Mapped[str] = mapped_column(
        String(32),
        default="observational_not_causal",
        server_default="observational_not_causal",
    )
    methodology: Mapped[str] = mapped_column(Text, default="")
    cohort_reference: Mapped[str] = mapped_column(String(160), default="")
    period_start: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    period_end: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    calculated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=_utcnow,
        server_default=func.now(),
    )


class Notification(Base, TimestampMixin):
    """Audience broadcasts use per-user receipts, never a shared read flag."""

    __tablename__ = "cc_notification"
    __table_args__ = (
        CheckConstraint(
            "audience IN ('all', 'trainees', 'trainers', 'admins', 'user', 'course', 'organization')",
            name="ck_cc_notification_audience",
        ),
        CheckConstraint(
            "(audience = 'user' AND user_id IS NOT NULL) OR (audience <> 'user' AND user_id IS NULL)",
            name="ck_cc_notification_user_target",
        ),
        CheckConstraint(
            "audience <> 'course' OR course_id IS NOT NULL",
            name="ck_cc_notification_course_target",
        ),
        CheckConstraint(
            "audience <> 'organization' OR organization_id IS NOT NULL",
            name="ck_cc_notification_org_target",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_cc_notification_status",
        ),
        Index("ix_cc_notification_feed", "audience", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    audience: Mapped[str] = mapped_column(String(16), default="all")
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), default=None, index=True
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_course.id", ondelete="CASCADE"), default=None, index=True
    )
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_organization.id", ondelete="CASCADE"),
        default=None,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(220), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    action_path: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    expires_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class EmailDelivery(Base, TimestampMixin):
    """Transactional email snapshot, independent of in-app notification receipts.

    event_key is the immutable logical delivery identity and must be reused on
    retries. Immutability is a writer contract here: ordinary SQL constraints
    cannot prevent changing an existing value without a trigger or write guard.
    accepted_at records provider acceptance, not inbox delivery or a read receipt.
    Error summaries must be redacted before persistence; never store raw SDK
    payloads, credentials, or message content in diagnostic fields.
    """

    __tablename__ = "cc_email_delivery"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_cc_email_delivery_event_key"),
        CheckConstraint(
            "length(event_key) BETWEEN 1 AND 256",
            name="ck_cc_email_delivery_event_key_length",
        ),
        CheckConstraint(
            "status IN ('pending', 'sending', 'accepted', 'retry', 'blocked', 'failed')",
            name="ck_cc_email_delivery_status",
        ),
        CheckConstraint(
            "attempt_count >= 0", name="ck_cc_email_delivery_attempt_count"
        ),
        Index("ix_cc_email_delivery_scheduled", "status", "scheduled_at", "id"),
        Index("ix_cc_email_delivery_retry", "status", "next_attempt_at", "id"),
        Index("ix_cc_email_delivery_event_type", "event_type", "created_at"),
        Index(
            "ix_cc_email_delivery_recipient_history",
            "recipient_user_id",
            "created_at",
        ),
        Index(
            "ix_cc_email_delivery_email_history",
            "recipient_email",
            "created_at",
        ),
        Index("ix_cc_email_delivery_provider_id", "provider_message_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    event_key: Mapped[str] = mapped_column(
        String(256),
        default="",
        comment="Immutable logical delivery identity; writers must never change or regenerate it on retry.",
        info={"immutable": True},
    )
    event_type: Mapped[str] = mapped_column(
        String(80), default="", server_default=""
    )
    recipient_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_user.id", ondelete="SET NULL"), default=None
    )
    recipient_email: Mapped[str] = mapped_column(
        String(255),
        default="",
        server_default="",
        repr=False,
        comment="Recipient email snapshot at enqueue time.",
    )
    recipient_name: Mapped[str] = mapped_column(
        String(160),
        default="",
        server_default="",
        repr=False,
        comment="Recipient name snapshot at enqueue time.",
    )
    recipient_role: Mapped[str] = mapped_column(
        String(16),
        default="",
        server_default="",
        comment="Recipient role snapshot at enqueue time, not a live authorization source.",
    )
    subject: Mapped[str] = mapped_column(
        String(998), default="", server_default="", repr=False
    )
    text_body: Mapped[str] = mapped_column(
        Text, default="", server_default="", repr=False
    )
    html_body: Mapped[str] = mapped_column(
        Text, default="", server_default="", repr=False
    )
    action_path: Mapped[str] = mapped_column(
        String(500), default="", server_default="", repr=False
    )
    status: Mapped[str] = mapped_column(
        String(16), default="pending", server_default="pending"
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    scheduled_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=_utcnow,
        server_default=func.now(),
    )
    next_attempt_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    accepted_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        comment="Provider accepted/sent time; not confirmation of inbox delivery.",
    )
    provider_message_id: Mapped[str | None] = mapped_column(
        String(256), default=None
    )
    last_error_category: Mapped[str] = mapped_column(
        String(80), default="", server_default=""
    )
    last_error_summary: Mapped[str] = mapped_column(
        String(1000),
        default="",
        server_default="",
        repr=False,
        comment="Redacted diagnostic summary only; sanitize before persistence.",
    )


class NotificationReceipt(Base, TimestampMixin):
    __tablename__ = "cc_notification_receipt"
    __table_args__ = (
        UniqueConstraint(
            "notification_id", "user_id", name="uq_cc_notification_receipt"
        ),
        CheckConstraint(
            "read_state IN ('unread', 'read', 'dismissed')",
            name="ck_cc_notification_read_state",
        ),
        CheckConstraint(
            "(read_state = 'unread' AND read_at IS NULL) OR (read_state IN ('read', 'dismissed') AND read_at IS NOT NULL)",
            name="ck_cc_notification_read_time",
        ),
        Index("ix_cc_notification_user_read", "user_id", "read_state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    notification_id: Mapped[int] = mapped_column(
        ForeignKey("cc_notification.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    read_state: Mapped[str] = mapped_column(String(16), default="unread")
    read_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class Achievement(Base, TimestampMixin):
    __tablename__ = "cc_achievement"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    criteria: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(default=True)


class UserAchievement(Base, TimestampMixin):
    __tablename__ = "cc_user_achievement"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "achievement_id", name="uq_cc_user_achievement"
        ),
        CheckConstraint(
            "status IN ('awarded', 'revoked')",
            name="ck_cc_user_achievement_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("cc_achievement.id", ondelete="RESTRICT"), index=True
    )
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_course.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_competency_evidence.id", ondelete="RESTRICT"),
        default=None,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), default="awarded")
    awarded_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default_factory=_utcnow
    )
    revoked_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class CertificateCompetency(Base, TimestampMixin):
    __tablename__ = "cc_certificate_competency"
    __table_args__ = (
        UniqueConstraint(
            "certificate_id",
            "competency_id",
            name="uq_cc_certificate_competency",
        ),
        CheckConstraint(
            "certified_level BETWEEN 1 AND 5",
            name="ck_cc_certificate_comp_level",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    certificate_id: Mapped[int] = mapped_column(
        ForeignKey("cc_certificate.id", ondelete="CASCADE"), index=True
    )
    competency_id: Mapped[int] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="RESTRICT"), index=True
    )
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("cc_competency_evidence.id", ondelete="RESTRICT"), index=True
    )
    certified_level: Mapped[int] = mapped_column(default=1)
    certificate: Mapped["Certificate"] = relationship(init=False)
    competency: Mapped["Competency"] = relationship(init=False)


class CapacityAIConversation(Base, TimestampMixin):
    """Advisory history only; never credentials, auth headers, or proficiency writes."""

    __tablename__ = "cc_capacity_ai_conversation"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_cc_ai_conversation_status",
        ),
        Index("ix_cc_ai_conversation_user_time", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("cc_user.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(16), default="active")
    messages: Mapped[list["CapacityAIMessage"]] = relationship(
        init=False,
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class CapacityAIMessage(Base, TimestampMixin):
    """One bounded request/response turn. Store sanitized text, not raw SDK payloads.

    Explicit context FKs bound retrieval scope. Application must authorize context
    ownership and redact secrets before persistence; schema cannot detect secrets.
    """

    __tablename__ = "cc_capacity_ai_message"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "position", name="uq_cc_ai_message_order"
        ),
        CheckConstraint("position >= 1", name="ck_cc_ai_message_position"),
        CheckConstraint(
            "user_action IN ('explain', 'summarize', 'recommend_learning', 'practice_help', 'explain_gap', 'explain_trainer_fit', 'general_help')",
            name="ck_cc_ai_message_action",
        ),
        CheckConstraint(
            "status IN ('pending', 'completed', 'blocked', 'failed')",
            name="ck_cc_ai_message_status",
        ),
        CheckConstraint(
            "length(request_text) <= 8000 AND length(response_text) <= 24000",
            name="ck_cc_ai_message_bounds",
        ),
        Index(
            "ix_cc_ai_message_conversation_time",
            "conversation_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("cc_capacity_ai_conversation.id", ondelete="CASCADE"),
        index=True,
    )
    position: Mapped[int] = mapped_column(default=1)
    user_action: Mapped[str] = mapped_column(String(32), default="general_help")
    request_text: Mapped[str] = mapped_column(String(8000), default="")
    response_text: Mapped[str] = mapped_column(String(24000), default="")
    model: Mapped[str] = mapped_column(String(120), default="")
    grounded: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_course.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_lesson.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    competency_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_competency.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    gap_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_competency_gap.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    learning_path_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_learning_path.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    resource_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_learning_resource.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    practice_question_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_practice_question.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    fit_evaluation_id: Mapped[int | None] = mapped_column(
        ForeignKey("cc_trainer_fit_evaluation.id", ondelete="SET NULL"),
        default=None,
        index=True,
    )
    responded_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    conversation: Mapped["CapacityAIConversation"] = relationship(
        init=False, back_populates="messages"
    )


class CapacityAIMessageSource(Base):
    """Allowlisted citation metadata only; no arbitrary credential-bearing JSON."""

    __tablename__ = "cc_capacity_ai_message_source"
    __table_args__ = (
        UniqueConstraint(
            "message_id", "position", name="uq_cc_ai_source_position"
        ),
        CheckConstraint(
            "position BETWEEN 1 AND 20", name="ck_cc_ai_source_bound"
        ),
        CheckConstraint(
            "source_type IN ('course', 'lesson', 'resource', 'competency', 'evidence', 'public_reference')",
            name="ck_cc_ai_source_type",
        ),
        CheckConstraint(
            "length(excerpt) <= 2000", name="ck_cc_ai_source_excerpt"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    message_id: Mapped[int] = mapped_column(
        ForeignKey("cc_capacity_ai_message.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(default=1)
    source_type: Mapped[str] = mapped_column(
        String(24), default="public_reference"
    )
    source_identifier: Mapped[str] = mapped_column(String(200), default="")
    source_version: Mapped[str] = mapped_column(String(64), default="")
    title: Mapped[str] = mapped_column(String(220), default="")
    page_locator: Mapped[str] = mapped_column(String(100), default="")
    excerpt: Mapped[str] = mapped_column(String(2000), default="")
    retrieved_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=_utcnow,
        server_default=func.now(),
    )

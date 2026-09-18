"""Idempotent CAPACITY CONNECT development seed data."""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import secrets

import reflex as rx
from sqlalchemy import select

from app.models import (
    Announcement,
    AnnouncementAudience,
    ApprovalRequest,
    ApprovalStatus,
    AssignmentStatus,
    AssignmentSubmission,
    AssignmentType,
    CourseAssignment,
    SubmissionStatus,
    Assessment,
    AssessmentAttempt,
    AssessmentResult,
    AssessmentStatus,
    AttemptAnswer,
    AttemptStatus,
    Certificate,
    CertificateRequest,
    CertificateRequestStatus,
    Course,
    CourseFeedback,
    CourseRequiredSkill,
    CourseStatus,
    CourseTrainerAssignment,
    Enrollment,
    EnrollmentStatus,
    LearningResource,
    ProficiencyLevel,
    Qualification,
    Question,
    QuestionOption,
    ResourceType,
    Skill,
    TraineeProfile,
    TrainerAssignmentRole,
    TrainerProfile,
    User,
    UserRole,
    UserSkill,
    WorkExperience,
)
from app.security import hash_password

logger = logging.getLogger(__name__)

DEMO_PASSWORD = os.environ.get("CAPACITY_CONNECT_DEMO_PASSWORD", "")

DEMO_ACCOUNTS: list[dict[str, str]] = [
    {
        "role": "Trainee",
        "email": "trainee@capacityconnect.gov",
        "note": "Enrolled learner with results and a certificate",
    },
    {
        "role": "Trainer",
        "email": "trainer@capacityconnect.gov",
        "note": "Lead trainer with courses, resources and assessments",
    },
    {
        "role": "Admin",
        "email": "admin@capacityconnect.gov",
        "note": "Control centre: approvals, competency mapping, notices",
    },
]

_seed_done = False
_assignment_seed_done = False
_certificate_request_seed_done = False
_normalized_seed_done = False
_NORMALIZED_SEED_SENTINEL = "capacity-connect-normalized-seed-complete-v2"


def _make_user(
    email: str,
    full_name: str,
    role: str,
    *,
    approval: str = ApprovalStatus.APPROVED.value,
    phone: str = "",
    seed: str = "",
) -> User:
    password = DEMO_PASSWORD
    if not password.strip():
        raise ValueError(
            "Demo account creation requires an explicitly configured password."
        )
    password_hash, salt = hash_password(password)
    return User(
        email=email,
        full_name=full_name,
        password_hash=password_hash,
        password_salt=salt,
        password_updated_at=dt.datetime.now(dt.UTC),
        role=role,
        approval_status=approval,
        is_active=True,
        email_verified=True,
        phone=phone,
        avatar_seed=seed or email,
    )


def ensure_seed_data() -> None:
    """Populate demo content exactly once; safe to call on every page load."""
    global _seed_done
    if not _seed_done:
        try:
            with rx.session() as session:
                existing = session.scalar(
                    select(User).where(User.email == DEMO_ACCOUNTS[2]["email"])
                )
                if (
                    existing is None
                    and os.environ.get(
                        "CAPACITY_CONNECT_DEMO_PASSWORD", ""
                    ).strip()
                    and session.scalar(select(User.id).limit(1)) is None
                ):
                    _seed_everything(session)
                    session.commit()
                    logger.info("CAPACITY CONNECT demo data seeded.")
            _seed_done = True
        except Exception as exception:
            logging.exception(f"Error seeding demo data: {exception}")
    ensure_assignment_seed_data()
    ensure_certificate_request_seed_data()
    ensure_normalized_seed_data()


def ensure_normalized_seed_data() -> None:
    """Resume additive backfill once, publishing completion atomically."""
    global _normalized_seed_done
    if _normalized_seed_done:
        return

    from app import models as m
    from app.services.evidence import refresh_evidence
    from app.services.learning_paths import generate_path
    from app.services.effectiveness import refresh_effectiveness
    from app.services.trainer_fit import evaluate
    from app.services.team_coverage import propose_team
    from sqlalchemy import text

    try:
        with rx.session() as session:
            # Reserved inactive policy record: unique indexed key, never used for scoring.
            completion = (
                select(m.TrainerFitWeights.id)
                .where(
                    m.TrainerFitWeights.policy_code
                    == _NORMALIZED_SEED_SENTINEL,
                    m.TrainerFitWeights.version == 1,
                )
                .limit(1)
            )
            if session.scalar(completion) is not None:
                _normalized_seed_done = True
                return
            session.execute(text("SELECT pg_advisory_xact_lock(26075)"))
            # A competing worker may have completed while this transaction waited.
            if session.scalar(completion) is not None:
                _normalized_seed_done = True
                return

            if (
                session.scalar(
                    select(m.User.id).where(
                        m.User.email == "admin@capacityconnect.gov"
                    )
                )
                is None
            ):
                return

            def ensure(model, keys, **values):
                row = session.scalar(select(model).filter_by(**keys).limit(1))
                if row is None:
                    row = model(**keys, **values)
                    session.add(row)
                    session.flush()
                return row

            moes = ensure(
                m.Organization,
                {"code": "MOES"},
                name="Ministry of Earth Sciences",
                description="National earth-system science capacity framework.",
            )
            imd = ensure(
                m.Organization,
                {"code": "IMD"},
                name="India Meteorological Department",
                description="Operational weather, climate and observation services.",
            )
            departments = [
                ensure(
                    m.Department,
                    {"organization_id": imd.id, "code": code},
                    name=name,
                )
                for code, name in [
                    ("PUNE-TRAINING", "Pune — Meteorological Training"),
                    ("CHENNAI-RADAR", "Chennai — Regional Radar Operations"),
                    (
                        "DELHI-FORECAST",
                        "New Delhi — National Forecasting Centre",
                    ),
                ]
            ]
            ensure(
                m.Department,
                {"organization_id": moes.id, "code": "CAPACITY"},
                name="Capacity Development Division",
            )
            roles = {
                key: ensure(
                    m.OrganizationalRole,
                    {"organization_id": imd.id, "code": key},
                    title=title,
                )
                for key, title in [
                    ("trainee", "Operational Forecaster"),
                    ("trainer", "Meteorological Training Faculty"),
                    ("admin", "Capacity Programme Coordinator"),
                ]
            }
            subjects = {
                key: ensure(m.Subject, {"code": key}, name=name)
                for key, name in [
                    ("RADAR", "Doppler Radar"),
                    ("OPS", "Operational Meteorology"),
                    ("NWP", "Numerical Weather Prediction"),
                    ("SAT", "Satellite Meteorology"),
                    ("COMMS", "Disaster Communication"),
                ]
            }
            radar = []
            for code, name in [
                ("FUNDAMENTALS", "Radar Fundamentals"),
                ("VELOCITY", "Velocity Interpretation"),
                ("REFLECTIVITY", "Reflectivity Analysis"),
                ("SIGNAL", "Doppler Signal Interpretation"),
                ("QUALITY", "Radar Data Quality Assessment"),
            ]:
                radar.append(
                    ensure(
                        m.Competency,
                        {"code": f"RADAR-{code}"},
                        subject_id=subjects["RADAR"].id,
                        name=name,
                        description="Scale: 1 Awareness; 2 Basic guided work; 3 Working independently; 4 Advanced complex work; 5 Expert mentoring. Requires measured, verified evidence.",
                    )
                )
            mapping = {}
            for skill in session.scalars(select(m.Skill).order_by(m.Skill.id)):
                name = skill.name.lower()
                domain = (
                    "RADAR"
                    if "radar" in name
                    else "SAT"
                    if "satellite" in name
                    else "NWP"
                    if "numerical" in name
                    else "COMMS"
                    if "communication" in name
                    else "OPS"
                )
                comp = ensure(
                    m.Competency,
                    {"code": f"LEGACY-SKILL-{skill.id}"},
                    subject_id=subjects[domain].id,
                    name=skill.name,
                    description=f"Explicit legacy mapping: cc_skill:{skill.id}. Legacy claims are retained; no proficiency inferred.",
                )
                mapping[skill.id] = comp
            level_map = {
                "beginner": 1,
                "intermediate": 3,
                "advanced": 4,
                "expert": 5,
            }
            for legacy in session.scalars(select(m.CourseRequiredSkill)):
                for kind in ["trainer", "outcome"]:
                    ensure(
                        m.CourseCompetencyRequirement,
                        {
                            "course_id": legacy.course_id,
                            "competency_id": mapping[legacy.skill_id].id,
                            "requirement_type": kind,
                        },
                        required_level=level_map.get(legacy.minimum_level, 1),
                        weight=legacy.weight,
                        is_mandatory=legacy.is_mandatory,
                    )
            users = session.scalars(
                select(m.User)
                .where(
                    m.User.email.in_(
                        [
                            "admin@capacityconnect.gov",
                            "trainer@capacityconnect.gov",
                            "meera.trainer@capacityconnect.gov",
                            "samuel.trainer@capacityconnect.gov",
                            "kavya.trainer@capacityconnect.gov",
                            "trainee@capacityconnect.gov",
                            "asha.trainee@capacityconnect.gov",
                            "imran.trainee@capacityconnect.gov",
                        ]
                    )
                )
                .order_by(m.User.id)
            ).all()
            epoch = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
            for i, user in enumerate(users):
                if not session.scalar(
                    select(m.UserOrganizationAssignment.id)
                    .where(m.UserOrganizationAssignment.user_id == user.id)
                    .limit(1)
                ):
                    session.add(
                        m.UserOrganizationAssignment(
                            user_id=user.id,
                            organization_id=imd.id,
                            department_id=departments[i % len(departments)].id,
                            role_id=roles.get(user.role, roles["trainee"]).id,
                            starts_at=epoch,
                        )
                    )
                if user.role == "trainer" and not session.scalar(
                    select(m.TrainerAvailability.id)
                    .where(m.TrainerAvailability.trainer_id == user.id)
                    .limit(1)
                ):
                    session.add(
                        m.TrainerAvailability(
                            trainer_id=user.id,
                            starts_at=epoch,
                            ends_at=dt.datetime(2030, 1, 1, tzinfo=dt.UTC),
                            status="tentative",
                            notes="Backfill planning example — trainer must explicitly confirm availability.",
                        )
                    )
                if user.role == "trainer" and not session.scalar(
                    select(m.TrainerCapacity.id)
                    .where(m.TrainerCapacity.trainer_id == user.id)
                    .limit(1)
                ):
                    session.add(
                        m.TrainerCapacity(
                            trainer_id=user.id,
                            starts_at=epoch,
                            ends_at=dt.datetime(2030, 1, 1, tzinfo=dt.UTC),
                            max_hours=0,
                            max_courses=0,
                            max_participants=0,
                        )
                    )
            for comp in list(mapping.values()) + radar:
                ensure(
                    m.RoleCompetencyRequirement,
                    {"role_id": roles["trainee"].id, "competency_id": comp.id},
                    required_level=3,
                    population_context="Operational development target; unmeasured staff require assessment.",
                )
            for comp in radar:
                ensure(
                    m.OrganizationalCapacityNeed,
                    {"organization_id": imd.id, "code": f"NEED-{comp.code}"},
                    competency_id=comp.id,
                    required_level=3,
                    status="active",
                    starts_at=epoch,
                    population_context="Radar interpretation readiness; measured population is reported separately.",
                )
            for legacy in session.scalars(select(m.UserSkill)):
                verified = (
                    legacy.verified_by_id is not None
                    and legacy.verified_at is not None
                )
                ensure(
                    m.CompetencyEvidence,
                    {
                        "user_id": legacy.user_id,
                        "competency_id": mapping[legacy.skill_id].id,
                        "evidence_type": "trainer_evaluation",
                        "source_system": "legacy_user_skill",
                        "source_reference": f"user-skill:{legacy.id}",
                    },
                    measured_level=level_map.get(legacy.level, 1),
                    measured_score=legacy.proficiency_score,
                    verifier_id=legacy.verified_by_id if verified else None,
                    verification_status="verified" if verified else "pending",
                    observed_at=legacy.verified_at
                    if verified
                    else legacy.created_at,
                    verified_at=legacy.verified_at if verified else None,
                    notes="Legacy measured level mapped by explicit scale crosswalk (beginner 1, intermediate 3, advanced 4, expert 5). Unverified claims remain pending.",
                )
            for course in session.scalars(
                select(m.Course).order_by(m.Course.id)
            ):
                program = ensure(
                    m.TrainingProgram,
                    {"code": f"COURSE-{course.id}"},
                    organization_id=imd.id,
                    title=course.title,
                    description="Backfilled delivery hierarchy; legacy course remains authoritative.",
                    status="active"
                    if course.status == "published"
                    else "draft",
                )
                ensure(
                    m.TrainingProgramCourse,
                    {"program_id": program.id, "course_id": course.id},
                    position=1,
                )
                resources = session.scalars(
                    select(m.LearningResource)
                    .where(
                        m.LearningResource.course_id == course.id,
                        m.LearningResource.is_published.is_(True),
                    )
                    .order_by(
                        m.LearningResource.sort_order, m.LearningResource.id
                    )
                ).all()
                for position, resource in enumerate(resources, 1):
                    module = ensure(
                        m.CourseModule,
                        {"course_id": course.id, "position": position},
                        title=resource.module_name or resource.title,
                        status="published",
                    )
                    lesson = ensure(
                        m.Lesson,
                        {"module_id": module.id, "position": 1},
                        title=resource.title,
                        content=resource.description,
                        status="published",
                    )
                    ensure(
                        m.LessonResource,
                        {"lesson_id": lesson.id, "resource_id": resource.id},
                        position=1,
                    )
            # Overall official percentages are preserved as scores, never invented scale levels.
            for result, assessment in session.execute(
                select(m.AssessmentResult, m.Assessment).join(
                    m.Assessment,
                    m.Assessment.id == m.AssessmentResult.assessment_id,
                )
            ):
                for req in session.scalars(
                    select(m.CourseCompetencyRequirement).where(
                        m.CourseCompetencyRequirement.course_id
                        == assessment.course_id,
                        m.CourseCompetencyRequirement.requirement_type
                        == "outcome",
                    )
                ):
                    ensure(
                        m.CompetencyEvidence,
                        {
                            "user_id": result.trainee_id,
                            "competency_id": req.competency_id,
                            "evidence_type": "official_assessment",
                            "source_system": "official_result",
                            "source_reference": f"result:{result.id}",
                        },
                        assessment_result_id=result.id,
                        measured_score=result.percentage,
                        verification_status="pending",
                        observed_at=result.graded_at or result.created_at,
                        notes="Official course result linked for review. No competency-specific level rubric or human verification is recorded; no mastery level inferred.",
                    )
            for user in users:
                refresh_evidence(session, user.id)
                if (
                    user.role != "trainee"
                    or session.scalar(
                        select(m.LearningPath.id)
                        .where(m.LearningPath.user_id == user.id)
                        .limit(1)
                    )
                    is not None
                ):
                    continue
                gap = session.scalar(
                    select(m.CompetencyGap)
                    .where(
                        m.CompetencyGap.user_id == user.id,
                        m.CompetencyGap.status == "identified",
                        select(m.CourseCompetencyRequirement.id)
                        .join(
                            m.Course,
                            m.Course.id
                            == m.CourseCompetencyRequirement.course_id,
                        )
                        .where(
                            m.CourseCompetencyRequirement.competency_id
                            == m.CompetencyGap.competency_id,
                            m.CourseCompetencyRequirement.requirement_type
                            == "outcome",
                            m.CourseCompetencyRequirement.required_level
                            >= m.CompetencyGap.required_level,
                            m.Course.status == "published",
                        )
                        .exists(),
                    )
                    .order_by(m.CompetencyGap.competency_id, m.CompetencyGap.id)
                    .limit(1)
                )
                if gap is not None:
                    try:
                        with session.begin_nested():
                            generate_path(session, user.id, gap.competency_id)
                    except ValueError:
                        logger.info(
                            "Initial demo pathway unavailable; prerequisites remain enforced."
                        )

            course = session.scalar(
                select(m.Course)
                .where(
                    m.Course.status == "published",
                    select(m.CourseCompetencyRequirement.id)
                    .where(
                        m.CourseCompetencyRequirement.course_id == m.Course.id,
                        m.CourseCompetencyRequirement.requirement_type
                        == "trainer",
                    )
                    .exists(),
                )
                .order_by(m.Course.id)
                .limit(1)
            )
            if course is not None:
                if (
                    session.scalar(
                        select(m.TrainingEffectivenessSnapshot.id)
                        .where(
                            m.TrainingEffectivenessSnapshot.course_id
                            == course.id
                        )
                        .limit(1)
                    )
                    is None
                ):
                    refresh_effectiveness(session, course.id)
                start = dt.datetime.combine(
                    course.start_date or epoch.date(),
                    dt.time.min,
                    tzinfo=dt.UTC,
                )
                end = max(
                    dt.datetime.combine(
                        course.end_date
                        or (start.date() + dt.timedelta(days=1)),
                        dt.time.max,
                        tzinfo=dt.UTC,
                    ),
                    start + dt.timedelta(days=1),
                )
                evaluations = []
                for trainer in users:
                    if trainer.role != "trainer":
                        continue
                    existing = session.scalar(
                        select(m.TrainerFitEvaluation)
                        .where(
                            m.TrainerFitEvaluation.course_id == course.id,
                            m.TrainerFitEvaluation.trainer_id == trainer.id,
                            m.TrainerFitEvaluation.algorithm_version
                            == "sih-five-factor-v2",
                        )
                        .order_by(m.TrainerFitEvaluation.id.desc())
                        .limit(1)
                    )
                    if existing is None:
                        evaluations.append(
                            evaluate(session, course, trainer, start, end)
                        )
                    else:
                        details = json.loads(existing.explanation)
                        evaluations.append(
                            (
                                existing,
                                {
                                    int(cid): level
                                    for cid, level in details["covered"].items()
                                },
                                details["failures"],
                            )
                        )
                if (
                    evaluations
                    and session.scalar(
                        select(m.TrainerTeamMatch.id)
                        .where(m.TrainerTeamMatch.course_id == course.id)
                        .limit(1)
                    )
                    is None
                ):
                    propose_team(session, course.id, evaluations)
            question_specs = [
                (
                    "RADAR-VELOCITY",
                    "What does Doppler radial velocity measure?",
                    "Motion toward or away from the radar along its beam",
                    "Total wind speed in every direction",
                    "Radial velocity is the component of motion along the radar beam, not the full wind vector.",
                ),
                (
                    "RADAR-REFLECTIVITY",
                    "Which statement about reflectivity is correct?",
                    "It depends on scatterer size, concentration and phase",
                    "It directly measures surface rainfall without uncertainty",
                    "Reflectivity is a backscatter measurement. Rainfall estimation requires assumptions and quality control.",
                ),
                (
                    "RADAR-QUALITY",
                    "Before interpreting a radar echo, what should be checked?",
                    "Clutter, beam blockage and calibration quality",
                    "Only the display colour palette",
                    "Quality control prevents non-meteorological signals and artefacts from being interpreted as weather.",
                ),
            ]
            for code, prompt, correct, incorrect, explanation in question_specs:
                comp = session.scalar(
                    select(m.Competency).where(m.Competency.code == code)
                )
                question = ensure(
                    m.PracticeQuestion,
                    {"competency_id": comp.id, "prompt": prompt},
                    explanation=explanation,
                    difficulty_level=2,
                    status="published",
                )
                ensure(
                    m.PracticeQuestionOption,
                    {"question_id": question.id, "position": 1},
                    text=correct,
                    is_correct=True,
                )
                ensure(
                    m.PracticeQuestionOption,
                    {"question_id": question.id, "position": 2},
                    text=incorrect,
                )
            _repair_sih_demo(session)
            notice = ensure(
                m.Notification,
                {
                    "title": "Competency development registry is available",
                    "audience": "all",
                },
                body="Review evidence, plan development and try formative practice. Unverified legacy claims are not mastery. Availability examples require trainer confirmation.",
                status="published",
            )
            for user in users:
                ensure(
                    m.NotificationReceipt,
                    {"notification_id": notice.id, "user_id": user.id},
                )
            achievement = ensure(
                m.Achievement,
                {"code": "VERIFIED-WORKING"},
                title="Verified working competency",
                description="A verified independent-working measurement.",
                criteria="Qualifying verified competency evidence with measured level at least 3.",
            )
            for snapshot in session.scalars(
                select(m.UserCompetency).where(
                    m.UserCompetency.verification_status == "verified",
                    m.UserCompetency.current_level >= 3,
                )
            ):
                ensure(
                    m.UserAchievement,
                    {
                        "user_id": snapshot.user_id,
                        "achievement_id": achievement.id,
                    },
                    evidence_id=snapshot.evidence_id,
                )
                evidence = session.get(
                    m.CompetencyEvidence, snapshot.evidence_id
                )
                if evidence.assessment_result_id:
                    result = session.get(
                        m.AssessmentResult, evidence.assessment_result_id
                    )
                    assessment = session.get(m.Assessment, result.assessment_id)
                    cert = session.scalar(
                        select(m.Certificate).where(
                            m.Certificate.trainee_id == snapshot.user_id,
                            m.Certificate.course_id == assessment.course_id,
                            m.Certificate.is_revoked.is_(False),
                        )
                    )
                    if cert:
                        ensure(
                            m.CertificateCompetency,
                            {
                                "certificate_id": cert.id,
                                "competency_id": snapshot.competency_id,
                            },
                            evidence_id=evidence.id,
                            certified_level=evidence.measured_level,
                        )
            session.add(
                m.TrainerFitWeights(
                    policy_code=_NORMALIZED_SEED_SENTINEL,
                    version=1,
                    is_active=False,
                    description="Normalized seed completed; reserved initialization marker, not a scoring policy.",
                )
            )
            session.commit()
        _normalized_seed_done = True
    except Exception as e:
        # Database exceptions may embed SQL parameters; retain frames, not their payload.
        safe_error = RuntimeError(
            "Normalized initialization failed; retry remains enabled."
        )
        logging.exception(
            f"Error: {type(e).__name__}",
            exc_info=(RuntimeError, safe_error, e.__traceback__),
        )


def _repair_sih_demo(session) -> None:
    """Deterministic, provenance-labelled SIH fixture; never reset passwords."""
    from app import models as m
    from app.services.evidence import refresh_evidence
    from app.services.learning_paths import generate_path
    from app.services.effectiveness import refresh_effectiveness
    from app.services.trainer_fit import evaluate
    from app.services.team_coverage import propose_team

    def ensure(model, keys, **values):
        row = session.scalar(select(model).filter_by(**keys).limit(1))
        if row is None:
            row = model(**keys, **values)
            session.add(row)
            session.flush()
        return row

    identities = {
        "admin@capacityconnect.gov": "System Administrator",
        "trainer@capacityconnect.gov": "Dr. Raj Sharma",
        "trainee@capacityconnect.gov": "Anmol Kumar",
    }
    users = {
        u.email: u
        for u in session.scalars(
            select(m.User).where(m.User.email.in_(identities))
        )
    }
    if len(users) != 3:
        return
    for email, name in identities.items():
        users[email].full_name = name
    admin = users["admin@capacityconnect.gov"]
    trainer = users["trainer@capacityconnect.gov"]
    trainee = users["trainee@capacityconnect.gov"]
    profile = ensure(m.TraineeProfile, {"user_id": trainee.id})
    profile.designation = "Weather Forecaster"
    subject = ensure(m.Subject, {"code": "RADAR"}, name="Doppler Radar")
    comps = []
    for code, name in (
        ("FUNDAMENTALS", "Radar Fundamentals"),
        ("VELOCITY", "Velocity Interpretation"),
        ("DATA", "Data Interpretation"),
    ):
        comps.append(
            ensure(
                m.Competency,
                {"code": f"RADAR-{code}"},
                subject_id=subject.id,
                name=name,
                description="Doppler Radar competency; measured evidence on the five-level SIH scale.",
            )
        )
    membership = session.scalar(
        select(m.UserOrganizationAssignment)
        .where(
            m.UserOrganizationAssignment.user_id == trainee.id,
            m.UserOrganizationAssignment.status == "active",
        )
        .order_by(m.UserOrganizationAssignment.id)
        .limit(1)
    )
    if membership:
        role = session.get(m.OrganizationalRole, membership.role_id)
        role.title = "Weather Forecaster"
        for comp in comps:
            requirement = ensure(
                m.RoleCompetencyRequirement,
                {"role_id": role.id, "competency_id": comp.id},
                required_level=4,
            )
            requirement.required_level = 4
    course = session.scalar(
        select(m.Course).where(m.Course.code == "CC-NOW-204")
    )
    baseline = dt.datetime(2025, 1, 1, tzinfo=dt.UTC)
    for comp, level in zip(comps, (4, 2, 2)):
        evidence = ensure(
            m.CompetencyEvidence,
            {
                "user_id": trainee.id,
                "competency_id": comp.id,
                "evidence_type": "trainer_evaluation",
                "source_system": "sih_demo_fixture_v2",
                "source_reference": f"baseline:{trainee.id}:{comp.code}",
            },
            measured_level=level,
            verifier_id=admin.id,
            verification_status="verified",
            observed_at=baseline,
            verified_at=baseline,
            notes="Deterministic SIH demonstration baseline, verified by the seeded administrator; not a production assessment claim.",
        )
        if course:
            ensure(
                m.CompetencyObservation,
                {
                    "course_id": course.id,
                    "user_id": trainee.id,
                    "competency_id": comp.id,
                    "phase": "pre",
                    "observed_at": baseline,
                },
                observer_id=admin.id,
                evidence_id=evidence.id,
                observed_level=level,
                verification_status="verified",
                verified_at=baseline,
                notes="SIH demonstration baseline linked to verified fixture evidence.",
            )
    if course is None:
        refresh_evidence(session, trainee.id)
        return
    for comp in comps:
        for kind in ("outcome", "trainer"):
            ensure(
                m.CourseCompetencyRequirement,
                {
                    "course_id": course.id,
                    "competency_id": comp.id,
                    "requirement_type": kind,
                },
                required_level=4,
                weight=5.0,
            )
    requirements = session.scalars(
        select(m.CourseCompetencyRequirement).where(
            m.CourseCompetencyRequirement.course_id == course.id,
            m.CourseCompetencyRequirement.requirement_type == "trainer",
        )
    ).all()
    for requirement in requirements:
        ensure(
            m.CompetencyEvidence,
            {
                "user_id": trainer.id,
                "competency_id": requirement.competency_id,
                "evidence_type": "trainer_evaluation",
                "source_system": "sih_demo_fixture_v2",
                "source_reference": f"faculty:{trainer.id}:{requirement.competency_id}",
            },
            measured_level=5,
            verifier_id=admin.id,
            verification_status="verified",
            observed_at=baseline,
            verified_at=baseline,
            notes="SIH demonstration faculty verification: Radar/Doppler and mapped Nowcasting expertise. Fixture only.",
        )
    faculty = ensure(m.TrainerProfile, {"user_id": trainer.id})
    faculty.specialization = (
        "Doppler Radar, Radar Meteorology, Weather Data Analysis"
    )
    faculty.is_available = True
    faculty.years_of_training = max(faculty.years_of_training, 10)
    qualification = session.scalar(
        select(m.Qualification)
        .where(m.Qualification.user_id == trainer.id)
        .order_by(m.Qualification.id)
        .limit(1)
    )
    if qualification is None:
        qualification = ensure(
            m.Qualification,
            {"user_id": trainer.id, "degree": "PhD in Atmospheric Sciences"},
            field_of_study="Radar Meteorology",
            institution="SIH demonstration faculty record",
        )
    qualification.is_verified = True
    experience = session.scalar(
        select(m.WorkExperience)
        .where(m.WorkExperience.user_id == trainer.id)
        .order_by(m.WorkExperience.id)
        .limit(1)
    )
    if experience is None:
        experience = ensure(
            m.WorkExperience,
            {"user_id": trainer.id, "role_title": "Radar training faculty"},
            organization="India Meteorological Department",
            start_date=dt.date(2015, 1, 1),
            is_current=True,
            responsibilities="SIH fixture: radar interpretation and operational forecasting instruction.",
        )
    epoch = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
    end_epoch = dt.datetime(2030, 1, 1, tzinfo=dt.UTC)
    availability = ensure(
        m.TrainerAvailability,
        {"trainer_id": trainer.id, "starts_at": epoch, "ends_at": end_epoch},
    )
    availability.status = "available"
    availability.notes = "Confirmed availability for the deterministic SIH demonstration dataset."
    capacity = ensure(
        m.TrainerCapacity,
        {"trainer_id": trainer.id, "starts_at": epoch, "ends_at": end_epoch},
    )
    capacity.max_hours = max(120.0, capacity.allocated_hours)
    capacity.max_courses = max(4, capacity.allocated_courses)
    capacity.max_participants = max(150, capacity.allocated_participants)
    assessments = session.scalars(
        select(m.Assessment).where(m.Assessment.course_id == course.id)
    ).all()
    for assessment in assessments:
        for question in session.scalars(
            select(m.Question).where(m.Question.assessment_id == assessment.id)
        ):
            if question.competency_id is None:
                prompt = question.prompt.lower()
                question.competency_id = (
                    comps[1].id
                    if any(
                        word in prompt
                        for word in ("velocity", "radial", "doppler")
                    )
                    else comps[0].id
                    if "radar" in prompt
                    else comps[2].id
                )
    official = ensure(
        m.Assessment,
        {
            "course_id": course.id,
            "title": "Doppler Radar competency assessment — SIH",
        },
        created_by_id=trainer.id,
        instructions="Choose one answer per question. Official server-scored competency assessment.",
        status="draft",
        total_marks=3,
        passing_marks=2,
        time_limit_minutes=15,
        max_attempts=3,
        opens_at=epoch,
        deadline_at=end_epoch,
        shuffle_questions=True,
    )
    specs = [
        (
            comps[0],
            "What does weather radar reflectivity primarily describe?",
            "Returned signal from atmospheric scatterers",
            "Surface pressure",
            "Wind direction at every height",
            "Station temperature",
            "Reflectivity describes backscattered energy, not a direct pressure or temperature measurement.",
        ),
        (
            comps[1],
            "What does Doppler radial velocity measure?",
            "Motion toward or away from the radar along its beam",
            "The full three-dimensional wind vector",
            "Rainfall accumulation",
            "Cloud temperature",
            "Radial velocity is the component along the radar beam.",
        ),
        (
            comps[2],
            "Before interpreting a radar dataset, which checks are necessary?",
            "Calibration, clutter and beam blockage checks",
            "Only the colour palette",
            "Only the file name",
            "No checks for digital data",
            "Quality checks are necessary before interpreting radar observations.",
        ),
    ]
    for position, (comp, prompt, correct, b, c, d, explanation) in enumerate(
        specs, 1
    ):
        question = ensure(
            m.Question,
            {"assessment_id": official.id, "sort_order": position},
            competency_id=comp.id,
            prompt=prompt,
            explanation=explanation,
            marks=1,
        )
        for index, value in enumerate((correct, b, c, d), 1):
            ensure(
                m.QuestionOption,
                {"question_id": question.id, "sort_order": index},
                label=chr(64 + index),
                text=value,
                is_correct=index == 1,
            )
    official.status = "open"
    session.flush()
    refresh_evidence(session, trainer.id)
    refresh_evidence(session, trainee.id)
    path = generate_path(session, trainee.id, comps[1].id)
    steps = session.scalars(
        select(m.LearningPathStep).where(m.LearningPathStep.path_id == path.id)
    ).all()
    if len(steps) == 1 and steps[0].course_id == course.id:
        position = 2

        def step(kind, **target):
            nonlocal position
            session.add(
                m.LearningPathStep(
                    path_id=path.id,
                    user_id=trainee.id,
                    gap_id=steps[0].gap_id,
                    position=position,
                    step_type=kind,
                    **target,
                )
            )
            position += 1

        for module in session.scalars(
            select(m.CourseModule)
            .where(
                m.CourseModule.course_id == course.id,
                m.CourseModule.status == "published",
            )
            .order_by(m.CourseModule.position)
        ):
            step("module", module_id=module.id)
            for lesson in session.scalars(
                select(m.Lesson)
                .where(
                    m.Lesson.module_id == module.id,
                    m.Lesson.status == "published",
                )
                .order_by(m.Lesson.position)
            ):
                step("lesson", lesson_id=lesson.id)
        for resource in session.scalars(
            select(m.LearningResource)
            .where(
                m.LearningResource.course_id == course.id,
                m.LearningResource.is_published.is_(True),
            )
            .order_by(m.LearningResource.sort_order)
        ):
            step("resource", resource_id=resource.id)
        practice = session.scalar(
            select(m.PracticeQuestion)
            .where(
                m.PracticeQuestion.competency_id == comps[1].id,
                m.PracticeQuestion.status == "published",
            )
            .limit(1)
        )
        if practice:
            step("practice", practice_question_id=practice.id)
        step("assessment", assessment_id=official.id)
    refresh_effectiveness(session, course.id)
    start = dt.datetime.combine(
        course.start_date or dt.date.today(), dt.time.min, tzinfo=dt.UTC
    )
    end = dt.datetime.combine(
        course.end_date or (start.date() + dt.timedelta(days=30)),
        dt.time.max,
        tzinfo=dt.UTC,
    )
    end = max(end, start + dt.timedelta(days=1))
    evaluations = [evaluate(session, course, trainer, start, end, True)]
    propose_team(session, course.id, evaluations)
    for cert in session.scalars(
        select(m.Certificate).where(m.Certificate.trainee_id == trainee.id)
    ):
        if len(cert.verification_code) < 32:
            cert.verification_code = secrets.token_hex(32)
    session.flush()


def ensure_assignment_seed_data() -> None:
    """Idempotently add demo assignments and submissions."""
    global _assignment_seed_done
    if _assignment_seed_done:
        return
    try:
        with rx.session() as session:
            existing = session.scalar(select(CourseAssignment).limit(1))
            if existing is None:
                _seed_assignments(session)
                session.commit()
                logger.info("CAPACITY CONNECT assignment demo data seeded.")
        _assignment_seed_done = True
    except Exception as exception:
        logging.exception(f"Error seeding assignment data: {exception}")


def ensure_certificate_request_seed_data() -> None:
    """Idempotently add demo certificate requests across every state."""
    global _certificate_request_seed_done
    if _certificate_request_seed_done:
        return
    try:
        with rx.session() as session:
            existing = session.scalar(select(CertificateRequest).limit(1))
            if existing is None:
                _seed_certificate_requests(session)
                session.commit()
                logger.info("CAPACITY CONNECT certificate requests seeded.")
        _certificate_request_seed_done = True
    except Exception as exception:
        logging.exception(f"Error seeding certificate requests: {exception}")


def _seed_certificate_requests(session) -> None:
    now = dt.datetime.now(dt.UTC)

    def course(code: str) -> Course | None:
        return session.scalar(select(Course).where(Course.code == code))

    def user(email: str) -> User | None:
        return session.scalar(select(User).where(User.email == email))

    def enrollment_for(course_id: int, trainee_id: int) -> Enrollment | None:
        return session.scalar(
            select(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.trainee_id == trainee_id,
            )
        )

    admin = user("admin@capacityconnect.gov")
    trainee = user("trainee@capacityconnect.gov")
    trainee_two = user("asha.trainee@capacityconnect.gov")
    trainee_three = user("imran.trainee@capacityconnect.gov")
    nwp = course("CC-NWP-101")
    climate = course("CC-CLM-310")
    observations = course("CC-OBS-118")
    if None in (
        admin,
        trainee,
        trainee_two,
        trainee_three,
        nwp,
        climate,
        observations,
    ):
        return

    requests: list[CertificateRequest] = []

    climate_asha = enrollment_for(climate.id, trainee_two.id)
    requests.append(
        CertificateRequest(
            course_id=climate.id,
            trainee_id=trainee_two.id,
            enrollment_id=climate_asha.id if climate_asha else None,
            justification=(
                "Required for my empanelment as a district climate advisory "
                "officer; the state authority needs the certificate number on "
                "file before the monsoon briefing cycle."
            ),
            status=CertificateRequestStatus.PENDING.value,
            requested_at=now - dt.timedelta(days=9),
            progress_percent=100.0,
            average_score=78.5,
            assessments_passed=1,
            assessments_total=1,
            is_eligible_snapshot=True,
            eligibility_note=(
                "Resources 2/2 (100%); assessments passed 1/1 with best score "
                "78.5%; assignments 1/1 submitted, 1 graded; profile "
                "completeness 64%; enrolment status active."
            ),
        )
    )

    nwp_rahul = enrollment_for(nwp.id, trainee.id)
    requests.append(
        CertificateRequest(
            course_id=nwp.id,
            trainee_id=trainee.id,
            enrollment_id=nwp_rahul.id if nwp_rahul else None,
            justification=(
                "Needed for my promotion dossier to Meteorologist-A; the board "
                "requires documented NWP competency with a verifiable number."
            ),
            status=CertificateRequestStatus.APPROVED.value,
            requested_at=now - dt.timedelta(days=5),
            progress_percent=100.0,
            average_score=82.0,
            assessments_passed=1,
            assessments_total=1,
            is_eligible_snapshot=True,
            eligibility_note=(
                "Resources 3/3 (100%); assessments passed 1/1 with best score "
                "82.0%; assignments 1/1 submitted, 1 graded; profile "
                "completeness 82%; enrolment status active."
            ),
            reviewed_by_id=admin.id,
            reviewed_at=now - dt.timedelta(days=2),
            decision_note=(
                "Completion evidence verified against the course record. "
                "Awaiting issuance in the next certification batch."
            ),
        )
    )

    climate_imran = enrollment_for(climate.id, trainee_three.id)
    requests.append(
        CertificateRequest(
            course_id=climate.id,
            trainee_id=trainee_three.id,
            enrollment_id=climate_imran.id if climate_imran else None,
            justification=(
                "Requesting the certificate to attach to my district disaster "
                "management deputation file."
            ),
            status=CertificateRequestStatus.REJECTED.value,
            requested_at=now - dt.timedelta(days=16),
            progress_percent=12.0,
            average_score=0.0,
            assessments_passed=0,
            assessments_total=1,
            is_eligible_snapshot=False,
            eligibility_note=(
                "Resources 0/2 (12% progress); no passing assessment result on "
                "record; enrolment flagged at risk."
            ),
            reviewed_by_id=admin.id,
            reviewed_at=now - dt.timedelta(days=13),
            decision_note=(
                "Returned: course progress is 12% and no assessment has been "
                "passed. Complete the two modules, pass the module check and "
                "resubmit — your trainer has been copied on the at-risk flag."
            ),
        )
    )

    certificate = session.scalar(
        select(Certificate).where(
            Certificate.course_id == observations.id,
            Certificate.trainee_id == trainee.id,
        )
    )
    obs_rahul = enrollment_for(observations.id, trainee.id)
    requests.append(
        CertificateRequest(
            course_id=observations.id,
            trainee_id=trainee.id,
            enrollment_id=obs_rahul.id if obs_rahul else None,
            justification=(
                "Calibration certification is mandatory for signing off station "
                "maintenance records at Pune observatory."
            ),
            status=CertificateRequestStatus.ISSUED.value,
            requested_at=now - dt.timedelta(days=6),
            progress_percent=100.0,
            average_score=66.7,
            assessments_passed=1,
            assessments_total=1,
            is_eligible_snapshot=True,
            eligibility_note=(
                "Resources 1/1 (100%); assessments passed 1/1 with best score "
                "66.7%; assignments 1/1 submitted, 1 graded; profile "
                "completeness 82%; enrolment status completed."
            ),
            reviewed_by_id=admin.id,
            reviewed_at=now - dt.timedelta(days=4),
            decision_note=(
                "Certificate CC-CERT-2024-000118 issued against verified "
                "evidence and recorded in the certification register."
            ),
            certificate_id=certificate.id if certificate else None,
        )
    )

    session.add_all(requests)


def _seed_assignments(session) -> None:
    now = dt.datetime.now(dt.UTC)

    def course(code: str) -> Course | None:
        return session.scalar(select(Course).where(Course.code == code))

    def user(email: str) -> User | None:
        return session.scalar(select(User).where(User.email == email))

    nwp = course("CC-NWP-101")
    climate = course("CC-CLM-310")
    observations = course("CC-OBS-118")
    trainer = user("trainer@capacityconnect.gov")
    trainer_two = user("meera.trainer@capacityconnect.gov")
    trainer_three = user("samuel.trainer@capacityconnect.gov")
    trainee = user("trainee@capacityconnect.gov")
    trainee_two = user("asha.trainee@capacityconnect.gov")
    if None in (nwp, climate, observations, trainer, trainee):
        return

    nwp_report = CourseAssignment(
        course_id=nwp.id,
        created_by_id=trainer.id,
        title="Ensemble guidance interpretation report",
        instructions=(
            "Using the archived ensemble output supplied in Module 3, prepare a "
            "1,200 word operational note explaining the spread evolution, the "
            "most likely scenario and the confidence you would communicate in a "
            "duty bulletin. Reference at least two verification metrics."
        ),
        reference_url="https://library.capacityconnect.gov/ensemble-brief.pdf",
        assignment_type=AssignmentType.FIELD_REPORT.value,
        total_marks=100.0,
        passing_marks=50.0,
        status=AssignmentStatus.PUBLISHED.value,
        is_published=True,
        published_at=now - dt.timedelta(days=5),
        due_at=now + dt.timedelta(days=7),
        allow_late_submission=True,
        late_penalty_percent=10.0,
        allow_resubmission=True,
        submission_note="Submit as a shared PDF link plus a short summary here.",
    )
    nwp_project = CourseAssignment(
        course_id=nwp.id,
        created_by_id=trainer.id,
        title="Data assimilation case study design",
        instructions=(
            "Draft a case study proposal for a regional assimilation experiment: "
            "state the hypothesis, observation sources, cycling strategy and the "
            "diagnostics you would use to evaluate the outcome."
        ),
        assignment_type=AssignmentType.CASE_STUDY.value,
        total_marks=50.0,
        passing_marks=25.0,
        status=AssignmentStatus.DRAFT.value,
        is_published=False,
        due_at=now + dt.timedelta(days=21),
        allow_late_submission=False,
        late_penalty_percent=0.0,
        allow_resubmission=True,
    )
    climate_advisory = CourseAssignment(
        course_id=climate.id,
        created_by_id=(trainer_two or trainer).id,
        title="District agro-advisory drafting exercise",
        instructions=(
            "Using the seasonal outlook provided, draft a district level agro "
            "advisory for the next four weeks. Include the climate rationale, "
            "the actionable recommendation and the uncertainty statement."
        ),
        reference_url="https://library.capacityconnect.gov/seasonal-outlook.pdf",
        assignment_type=AssignmentType.ESSAY.value,
        total_marks=80.0,
        passing_marks=40.0,
        status=AssignmentStatus.PUBLISHED.value,
        is_published=True,
        published_at=now - dt.timedelta(days=18),
        due_at=now - dt.timedelta(days=3),
        allow_late_submission=True,
        late_penalty_percent=5.0,
        allow_resubmission=True,
    )
    calibration_practical = CourseAssignment(
        course_id=observations.id,
        created_by_id=(trainer_three or trainer).id,
        title="AWS calibration log and drift analysis",
        instructions=(
            "Submit your completed calibration log for the assigned station and "
            "a short drift analysis comparing reference and station readings "
            "over the workshop period."
        ),
        assignment_type=AssignmentType.PRACTICAL.value,
        total_marks=60.0,
        passing_marks=30.0,
        status=AssignmentStatus.PUBLISHED.value,
        is_published=True,
        published_at=now - dt.timedelta(days=28),
        due_at=now - dt.timedelta(days=10),
        allow_late_submission=False,
        late_penalty_percent=0.0,
        allow_resubmission=False,
    )
    session.add_all(
        [nwp_report, nwp_project, climate_advisory, calibration_practical]
    )
    session.flush()

    submissions = [
        AssignmentSubmission(
            assignment_id=nwp_report.id,
            trainee_id=trainee.id,
            response_text=(
                "Ensemble spread widened from T+48 onwards, driven by the "
                "upstream trough timing. The operational note attached argues "
                "for the cluster mean with a medium confidence statement and "
                "uses CRPS and spread-skill ratio for verification."
            ),
            submission_url="https://drive.capacityconnect.gov/rahul/ensemble-note.pdf",
            status=SubmissionStatus.SUBMITTED.value,
            is_late=False,
            attempt_count=1,
            submitted_at=now - dt.timedelta(days=1),
        ),
        AssignmentSubmission(
            assignment_id=calibration_practical.id,
            trainee_id=trainee.id,
            response_text=(
                "Calibration log completed for station PUN-04. Temperature "
                "sensor showed a 0.3 C positive drift over three weeks; the "
                "analysis attributes it to shelter ventilation and recommends "
                "a reference comparison every fortnight."
            ),
            status=SubmissionStatus.GRADED.value,
            is_late=False,
            attempt_count=1,
            submitted_at=now - dt.timedelta(days=12),
            marks_awarded=52.0,
            feedback=(
                "Excellent documentation discipline and a clear drift argument. "
                "Strengthen the next report by quantifying the uncertainty of "
                "the reference instrument itself."
            ),
            graded_by_id=(trainer_three or trainer).id,
            graded_at=now - dt.timedelta(days=9),
        ),
    ]
    if trainee_two is not None:
        submissions.append(
            AssignmentSubmission(
                assignment_id=climate_advisory.id,
                trainee_id=trainee_two.id,
                response_text=(
                    "Advisory drafted for Kancheepuram district recommending "
                    "staggered sowing given the below-normal rainfall tercile, "
                    "with an explicit statement of forecast uncertainty."
                ),
                submission_url="https://drive.capacityconnect.gov/asha/agro-advisory.pdf",
                status=SubmissionStatus.GRADED.value,
                is_late=True,
                attempt_count=2,
                submitted_at=now - dt.timedelta(days=1, hours=6),
                marks_awarded=58.0,
                feedback=(
                    "Strong climate rationale and a usable recommendation. The "
                    "late submission attracted the stated penalty; tighten the "
                    "uncertainty wording for non-technical readers."
                ),
                graded_by_id=(trainer_two or trainer).id,
                graded_at=now - dt.timedelta(hours=8),
            )
        )
    session.add_all(submissions)


def _seed_everything(session) -> None:
    today = dt.date.today()
    now = dt.datetime.now(dt.UTC)

    # ------------------------------------------------------------------ users
    admin = _make_user(
        "admin@capacityconnect.gov",
        "Dr. Vandana Rao",
        UserRole.ADMIN.value,
        phone="+91 98450 11001",
    )
    trainer = _make_user(
        "trainer@capacityconnect.gov",
        "Prof. Anil Kulkarni",
        UserRole.TRAINER.value,
        phone="+91 98450 22002",
    )
    trainer_two = _make_user(
        "meera.trainer@capacityconnect.gov",
        "Dr. Meera Iyer",
        UserRole.TRAINER.value,
        phone="+91 98450 22010",
    )
    trainer_three = _make_user(
        "samuel.trainer@capacityconnect.gov",
        "Samuel Fernandes",
        UserRole.TRAINER.value,
        phone="+91 98450 22011",
    )
    pending_trainer = _make_user(
        "kavya.trainer@capacityconnect.gov",
        "Kavya Nair",
        UserRole.TRAINER.value,
        approval=ApprovalStatus.PENDING.value,
    )
    trainee = _make_user(
        "trainee@capacityconnect.gov",
        "Rahul Deshmukh",
        UserRole.TRAINEE.value,
        phone="+91 98450 33003",
    )
    trainee_two = _make_user(
        "asha.trainee@capacityconnect.gov",
        "Asha Pillai",
        UserRole.TRAINEE.value,
    )
    trainee_three = _make_user(
        "imran.trainee@capacityconnect.gov",
        "Imran Sheikh",
        UserRole.TRAINEE.value,
    )
    users = [
        admin,
        trainer,
        trainer_two,
        trainer_three,
        pending_trainer,
        trainee,
        trainee_two,
        trainee_three,
    ]
    session.add_all(users)
    session.flush()

    session.add(
        ApprovalRequest(
            user_id=pending_trainer.id,
            requested_role=UserRole.TRAINER.value,
            status=ApprovalStatus.PENDING.value,
            note="Requesting trainer access for hydrology modules.",
        )
    )

    # --------------------------------------------------------------- profiles
    session.add_all(
        [
            TrainerProfile(
                user_id=trainer.id,
                designation="Senior Scientist (Training)",
                department="Weather Forecasting & Modelling",
                organization="National Institute of Meteorological Training",
                specialization="Numerical weather prediction, satellite meteorology",
                years_of_training=14.0,
                highest_qualification="Ph.D. Atmospheric Sciences",
                bio="Designs competency-based capacity building programmes for regional forecasting offices.",
                languages="English, Hindi, Marathi",
                rating_average=4.7,
                rating_count=68,
                profile_completion=94,
            ),
            TrainerProfile(
                user_id=trainer_two.id,
                designation="Scientist-D",
                department="Climate Services",
                organization="Regional Climate Centre",
                specialization="Climate risk analytics, seasonal outlooks",
                years_of_training=9.5,
                highest_qualification="Ph.D. Climatology",
                bio="Leads climate services training for agriculture and disaster management stakeholders.",
                languages="English, Tamil",
                rating_average=4.5,
                rating_count=41,
                profile_completion=88,
            ),
            TrainerProfile(
                user_id=trainer_three.id,
                designation="Instrumentation Specialist",
                department="Observation Networks",
                organization="Coastal Observatory Division",
                specialization="AWS calibration, radar maintenance",
                years_of_training=6.0,
                highest_qualification="M.Tech Electronics",
                bio="Hands-on trainer for automatic weather station and radar upkeep.",
                languages="English, Konkani",
                rating_average=4.3,
                rating_count=22,
                profile_completion=76,
            ),
            TrainerProfile(
                user_id=pending_trainer.id,
                designation="Hydrology Officer",
                department="Water Resources",
                organization="State Hydrology Cell",
                specialization="Flood forecasting",
                years_of_training=3.0,
                highest_qualification="M.Sc. Hydrology",
                bio="Awaiting approval to publish flood forecasting modules.",
                languages="English, Malayalam",
                is_available=False,
                profile_completion=52,
            ),
            TraineeProfile(
                user_id=trainee.id,
                designation="Meteorologist-B",
                department="Regional Forecasting Office",
                organization="India Meteorological Department",
                employee_code="IMD-RF-4471",
                station="Pune",
                region="West",
                date_of_joining=dt.date(2019, 7, 1),
                total_experience_years=5.5,
                bio="Duty forecaster working on short-range guidance for the western region.",
                career_goal="Lead nowcasting operations for the western region by 2027.",
                profile_completion=82,
            ),
            TraineeProfile(
                user_id=trainee_two.id,
                designation="Scientific Assistant",
                department="Observation Networks",
                organization="Regional Climate Centre",
                employee_code="RCC-ON-1182",
                station="Chennai",
                region="South",
                total_experience_years=3.0,
                bio="Maintains coastal observation stations and telemetry links.",
                profile_completion=64,
            ),
            TraineeProfile(
                user_id=trainee_three.id,
                designation="Junior Analyst",
                department="Climate Services",
                organization="State Disaster Management Authority",
                employee_code="SDMA-CS-0912",
                station="Bhopal",
                region="Central",
                total_experience_years=1.5,
                bio="Supports district level climate advisories.",
                profile_completion=48,
            ),
        ]
    )

    session.add_all(
        [
            Qualification(
                user_id=trainee.id,
                degree="M.Sc.",
                field_of_study="Atmospheric Sciences",
                institution="Savitribai Phule Pune University",
                start_year=2015,
                end_year=2017,
                grade="A",
                is_verified=True,
            ),
            Qualification(
                user_id=trainer.id,
                degree="Ph.D.",
                field_of_study="Atmospheric Sciences",
                institution="Indian Institute of Tropical Meteorology",
                start_year=2006,
                end_year=2011,
                grade="Distinction",
                is_verified=True,
            ),
            WorkExperience(
                user_id=trainee.id,
                organization="India Meteorological Department",
                role_title="Meteorologist-B",
                location="Pune",
                start_date=dt.date(2019, 7, 1),
                is_current=True,
                responsibilities="Short range forecasting, aviation briefings, nowcast bulletins.",
            ),
            WorkExperience(
                user_id=trainer.id,
                organization="National Institute of Meteorological Training",
                role_title="Senior Scientist (Training)",
                location="New Delhi",
                start_date=dt.date(2012, 4, 1),
                is_current=True,
                responsibilities="Curriculum design, trainer certification, competency audits.",
            ),
        ]
    )

    # ----------------------------------------------------------------- skills
    skill_specs = [
        ("Numerical Weather Prediction", "Forecasting"),
        ("Satellite Image Interpretation", "Remote Sensing"),
        ("Radar Meteorology", "Remote Sensing"),
        ("Nowcasting", "Forecasting"),
        ("Climate Data Analytics", "Climate Services"),
        ("Station Calibration", "Instrumentation"),
        ("Flood Forecasting", "Hydrology"),
        ("Risk Communication", "Outreach"),
    ]
    skills = {
        name: Skill(
            name=name,
            category=category,
            description=f"Competency area: {name}.",
        )
        for name, category in skill_specs
    }
    session.add_all(list(skills.values()))
    session.flush()

    def user_skill(
        user: User,
        skill_name: str,
        level: str,
        score: int,
        years: float,
        teachable: bool,
    ) -> UserSkill:
        return UserSkill(
            user_id=user.id,
            skill_id=skills[skill_name].id,
            level=level,
            proficiency_score=score,
            years_of_practice=years,
            is_teachable=teachable,
        )

    session.add_all(
        [
            user_skill(
                trainer,
                "Numerical Weather Prediction",
                ProficiencyLevel.EXPERT.value,
                95,
                14,
                True,
            ),
            user_skill(
                trainer,
                "Satellite Image Interpretation",
                ProficiencyLevel.EXPERT.value,
                92,
                12,
                True,
            ),
            user_skill(
                trainer,
                "Nowcasting",
                ProficiencyLevel.ADVANCED.value,
                84,
                9,
                True,
            ),
            user_skill(
                trainer_two,
                "Climate Data Analytics",
                ProficiencyLevel.EXPERT.value,
                93,
                10,
                True,
            ),
            user_skill(
                trainer_two,
                "Risk Communication",
                ProficiencyLevel.ADVANCED.value,
                80,
                7,
                True,
            ),
            user_skill(
                trainer_three,
                "Station Calibration",
                ProficiencyLevel.EXPERT.value,
                90,
                6,
                True,
            ),
            user_skill(
                trainer_three,
                "Radar Meteorology",
                ProficiencyLevel.ADVANCED.value,
                78,
                5,
                True,
            ),
            user_skill(
                pending_trainer,
                "Flood Forecasting",
                ProficiencyLevel.INTERMEDIATE.value,
                62,
                3,
                True,
            ),
            user_skill(
                trainee,
                "Nowcasting",
                ProficiencyLevel.INTERMEDIATE.value,
                58,
                3,
                False,
            ),
            user_skill(
                trainee,
                "Satellite Image Interpretation",
                ProficiencyLevel.INTERMEDIATE.value,
                64,
                4,
                False,
            ),
            user_skill(
                trainee,
                "Numerical Weather Prediction",
                ProficiencyLevel.BEGINNER.value,
                38,
                1,
                False,
            ),
            user_skill(
                trainee_two,
                "Station Calibration",
                ProficiencyLevel.INTERMEDIATE.value,
                55,
                3,
                False,
            ),
            user_skill(
                trainee_three,
                "Climate Data Analytics",
                ProficiencyLevel.BEGINNER.value,
                30,
                1,
                False,
            ),
        ]
    )

    # ---------------------------------------------------------------- courses
    course_nwp = Course(
        code="CC-NWP-101",
        title="Numerical Weather Prediction Foundations",
        summary="Model physics, data assimilation and interpretation of ensemble guidance for duty forecasters.",
        description=(
            "A structured six-week programme covering model configuration, data assimilation "
            "cycles, ensemble spread interpretation and operational bias correction. Includes "
            "hands-on laboratories using archived model output."
        ),
        category="Forecasting",
        level=ProficiencyLevel.INTERMEDIATE.value,
        mode="blended",
        duration_hours=48.0,
        capacity=40,
        status=CourseStatus.PUBLISHED.value,
        start_date=today + dt.timedelta(days=12),
        end_date=today + dt.timedelta(days=54),
        enrollment_deadline=today + dt.timedelta(days=7),
        created_by_id=admin.id,
    )
    course_nowcast = Course(
        code="CC-NOW-204",
        title="Radar & Satellite Nowcasting Practicum",
        summary="Severe weather nowcasting workflows using radar volume scans and rapid-scan satellite imagery.",
        description=(
            "Practitioner course focused on convective initiation signatures, storm tracking, "
            "warning thresholds and bulletin drafting under time pressure."
        ),
        category="Forecasting",
        level=ProficiencyLevel.ADVANCED.value,
        mode="onsite",
        duration_hours=36.0,
        capacity=25,
        status=CourseStatus.PUBLISHED.value,
        start_date=today + dt.timedelta(days=25),
        end_date=today + dt.timedelta(days=45),
        enrollment_deadline=today + dt.timedelta(days=18),
        created_by_id=admin.id,
    )
    course_climate = Course(
        code="CC-CLM-310",
        title="Climate Data Analytics for Advisories",
        summary="Turning long-period climate records into district-level agro and disaster advisories.",
        description=(
            "Covers quality control of climate records, trend and anomaly analysis, seasonal "
            "outlook interpretation and advisory communication for decision makers."
        ),
        category="Climate Services",
        level=ProficiencyLevel.INTERMEDIATE.value,
        mode="online",
        duration_hours=30.0,
        capacity=60,
        status=CourseStatus.PUBLISHED.value,
        start_date=today + dt.timedelta(days=5),
        end_date=today + dt.timedelta(days=40),
        enrollment_deadline=today + dt.timedelta(days=3),
        created_by_id=admin.id,
    )
    course_instruments = Course(
        code="CC-OBS-118",
        title="Automatic Weather Station Calibration",
        summary="Field maintenance, sensor calibration and telemetry troubleshooting for observation networks.",
        description=(
            "Workshop style course for observation staff: sensor drift detection, calibration "
            "protocols, telemetry diagnostics and documentation discipline."
        ),
        category="Instrumentation",
        level=ProficiencyLevel.BEGINNER.value,
        mode="onsite",
        duration_hours=24.0,
        capacity=30,
        status=CourseStatus.PUBLISHED.value,
        start_date=today - dt.timedelta(days=30),
        end_date=today - dt.timedelta(days=5),
        enrollment_deadline=today - dt.timedelta(days=35),
        created_by_id=admin.id,
    )
    course_flood = Course(
        code="CC-HYD-220",
        title="Flood Forecasting & Early Warning",
        summary="Catchment response modelling and inter-agency early warning coordination.",
        description="Draft programme pending trainer approval and curriculum sign-off.",
        category="Hydrology",
        level=ProficiencyLevel.INTERMEDIATE.value,
        mode="blended",
        duration_hours=32.0,
        capacity=28,
        status=CourseStatus.DRAFT.value,
        created_by_id=admin.id,
    )
    courses = [
        course_nwp,
        course_nowcast,
        course_climate,
        course_instruments,
        course_flood,
    ]
    session.add_all(courses)
    session.flush()

    required = [
        (
            course_nwp,
            "Numerical Weather Prediction",
            ProficiencyLevel.ADVANCED.value,
            5.0,
        ),
        (
            course_nwp,
            "Satellite Image Interpretation",
            ProficiencyLevel.INTERMEDIATE.value,
            3.0,
        ),
        (
            course_nowcast,
            "Radar Meteorology",
            ProficiencyLevel.ADVANCED.value,
            5.0,
        ),
        (course_nowcast, "Nowcasting", ProficiencyLevel.ADVANCED.value, 4.0),
        (
            course_climate,
            "Climate Data Analytics",
            ProficiencyLevel.ADVANCED.value,
            5.0,
        ),
        (
            course_climate,
            "Risk Communication",
            ProficiencyLevel.INTERMEDIATE.value,
            2.0,
        ),
        (
            course_instruments,
            "Station Calibration",
            ProficiencyLevel.INTERMEDIATE.value,
            5.0,
        ),
        (
            course_flood,
            "Flood Forecasting",
            ProficiencyLevel.INTERMEDIATE.value,
            5.0,
        ),
    ]
    session.add_all(
        [
            CourseRequiredSkill(
                course_id=course.id,
                skill_id=skills[skill_name].id,
                minimum_level=level,
                weight=weight,
            )
            for course, skill_name, level, weight in required
        ]
    )

    session.add_all(
        [
            CourseTrainerAssignment(
                course_id=course_nwp.id,
                trainer_id=trainer.id,
                assignment_role=TrainerAssignmentRole.LEAD.value,
                match_score=93.5,
                assigned_by_id=admin.id,
                notes="Strong NWP and satellite competency match.",
            ),
            CourseTrainerAssignment(
                course_id=course_nowcast.id,
                trainer_id=trainer.id,
                assignment_role=TrainerAssignmentRole.CO_TRAINER.value,
                match_score=81.0,
                assigned_by_id=admin.id,
            ),
            CourseTrainerAssignment(
                course_id=course_nowcast.id,
                trainer_id=trainer_three.id,
                assignment_role=TrainerAssignmentRole.LEAD.value,
                match_score=86.0,
                assigned_by_id=admin.id,
            ),
            CourseTrainerAssignment(
                course_id=course_climate.id,
                trainer_id=trainer_two.id,
                assignment_role=TrainerAssignmentRole.LEAD.value,
                match_score=91.0,
                assigned_by_id=admin.id,
            ),
            CourseTrainerAssignment(
                course_id=course_instruments.id,
                trainer_id=trainer_three.id,
                assignment_role=TrainerAssignmentRole.LEAD.value,
                match_score=90.0,
                assigned_by_id=admin.id,
            ),
        ]
    )

    # -------------------------------------------------------------- resources
    resource_specs = [
        (
            course_nwp,
            "Model Physics Primer",
            ResourceType.DOCUMENT.value,
            "Module 1 — Fundamentals",
            45,
            1,
        ),
        (
            course_nwp,
            "Data Assimilation Walkthrough",
            ResourceType.VIDEO.value,
            "Module 2 — Assimilation",
            62,
            2,
        ),
        (
            course_nwp,
            "Ensemble Spread Case Files",
            ResourceType.DATASET.value,
            "Module 3 — Ensembles",
            30,
            3,
        ),
        (
            course_nowcast,
            "Radar Volume Scan Atlas",
            ResourceType.SLIDES.value,
            "Module 1 — Radar",
            40,
            1,
        ),
        (
            course_nowcast,
            "Rapid Scan Satellite Loops",
            ResourceType.VIDEO.value,
            "Module 2 — Satellite",
            35,
            2,
        ),
        (
            course_climate,
            "Climate Record QC Checklist",
            ResourceType.DOCUMENT.value,
            "Module 1 — Data Quality",
            25,
            1,
        ),
        (
            course_climate,
            "Seasonal Outlook Reading Guide",
            ResourceType.LINK.value,
            "Module 2 — Outlooks",
            20,
            2,
        ),
        (
            course_instruments,
            "AWS Calibration Field Manual",
            ResourceType.DOCUMENT.value,
            "Module 1 — Field Work",
            55,
            1,
        ),
    ]
    session.add_all(
        [
            LearningResource(
                course_id=course.id,
                uploaded_by_id=trainer.id,
                title=title,
                description=f"{module}: curated study material prepared by the course faculty.",
                resource_type=resource_type,
                module_name=module,
                duration_minutes=minutes,
                sort_order=order,
                is_published=True,
            )
            for course, title, resource_type, module, minutes, order in resource_specs
        ]
    )

    # ------------------------------------------------------------ enrollments
    enrollment_nwp = Enrollment(
        course_id=course_nwp.id,
        trainee_id=trainee.id,
        status=EnrollmentStatus.ACTIVE.value,
        progress_percent=62.0,
        last_activity_at=now - dt.timedelta(days=1),
        approved_by_id=admin.id,
    )
    enrollment_obs = Enrollment(
        course_id=course_instruments.id,
        trainee_id=trainee.id,
        status=EnrollmentStatus.COMPLETED.value,
        progress_percent=100.0,
        last_activity_at=now - dt.timedelta(days=6),
        completed_at=now - dt.timedelta(days=5),
        approved_by_id=admin.id,
    )
    enrollment_climate = Enrollment(
        course_id=course_climate.id,
        trainee_id=trainee_two.id,
        status=EnrollmentStatus.ACTIVE.value,
        progress_percent=41.0,
        last_activity_at=now - dt.timedelta(days=2),
    )
    enrollment_risk = Enrollment(
        course_id=course_climate.id,
        trainee_id=trainee_three.id,
        status=EnrollmentStatus.AT_RISK.value,
        progress_percent=12.0,
        last_activity_at=now - dt.timedelta(days=21),
    )
    enrollment_nowcast = Enrollment(
        course_id=course_nowcast.id,
        trainee_id=trainee_two.id,
        status=EnrollmentStatus.ACTIVE.value,
        progress_percent=18.0,
        last_activity_at=now - dt.timedelta(days=4),
    )
    session.add_all(
        [
            enrollment_nwp,
            enrollment_obs,
            enrollment_climate,
            enrollment_risk,
            enrollment_nowcast,
        ]
    )

    # ------------------------------------------------------------ assessments
    assessment_nwp = Assessment(
        course_id=course_nwp.id,
        created_by_id=trainer.id,
        title="NWP Foundations — Module 1 & 2 Check",
        instructions="Twelve minutes, single best answer. Attempt all questions.",
        status=AssessmentStatus.OPEN.value,
        total_marks=3.0,
        passing_marks=2.0,
        time_limit_minutes=12,
        max_attempts=2,
        opens_at=now - dt.timedelta(days=2),
        deadline_at=now + dt.timedelta(days=10),
    )
    assessment_obs = Assessment(
        course_id=course_instruments.id,
        created_by_id=trainer_three.id,
        title="AWS Calibration Certification Test",
        instructions="Closed book. Pass mark is 60 percent.",
        status=AssessmentStatus.CLOSED.value,
        total_marks=3.0,
        passing_marks=2.0,
        time_limit_minutes=20,
        max_attempts=1,
        opens_at=now - dt.timedelta(days=20),
        deadline_at=now - dt.timedelta(days=6),
    )
    session.add_all([assessment_nwp, assessment_obs])
    session.flush()

    question_specs = [
        (
            assessment_nwp,
            "Which process assimilates observations into the model background state?",
            "Numerical Weather Prediction",
            1,
            [
                ("A", "Data assimilation", True),
                ("B", "Post-processing", False),
                ("C", "Downscaling", False),
            ],
        ),
        (
            assessment_nwp,
            "A large ensemble spread most directly indicates what?",
            "Numerical Weather Prediction",
            2,
            [
                ("A", "High forecast confidence", False),
                ("B", "Greater forecast uncertainty", True),
                ("C", "Sensor failure", False),
            ],
        ),
        (
            assessment_nwp,
            "Water vapour satellite channels are most useful for identifying which feature?",
            "Satellite Image Interpretation",
            3,
            [
                ("A", "Mid-level dry intrusions", True),
                ("B", "Soil moisture", False),
                ("C", "Sea surface salinity", False),
            ],
        ),
        (
            assessment_obs,
            "Sensor drift in an AWS thermometer is best detected by which practice?",
            "Station Calibration",
            1,
            [
                ("A", "Periodic reference comparison", True),
                ("B", "Increasing sampling rate", False),
                ("C", "Repainting the shelter", False),
            ],
        ),
        (
            assessment_obs,
            "Telemetry gaps at a coastal station most often originate from which cause?",
            "Station Calibration",
            2,
            [
                ("A", "Power and link failure", True),
                ("B", "Barometer offset", False),
                ("C", "Incorrect station name", False),
            ],
        ),
        (
            assessment_obs,
            "Calibration records should be retained to support which outcome?",
            "Station Calibration",
            3,
            [
                ("A", "Data traceability and audit", True),
                ("B", "Faster telemetry", False),
                ("C", "Lower rainfall bias", False),
            ],
        ),
    ]
    created_questions: dict[int, list[Question]] = {
        assessment_nwp.id: [],
        assessment_obs.id: [],
    }
    for assessment, prompt, skill_name, order, options in question_specs:
        question = Question(
            assessment_id=assessment.id,
            skill_id=skills[skill_name].id,
            prompt=prompt,
            explanation="Refer to the module resources for the detailed rationale.",
            marks=1.0,
            sort_order=order,
        )
        session.add(question)
        session.flush()
        session.add_all(
            [
                QuestionOption(
                    question_id=question.id,
                    label=label,
                    text=text,
                    is_correct=is_correct,
                    sort_order=index + 1,
                )
                for index, (label, text, is_correct) in enumerate(options)
            ]
        )
        created_questions[assessment.id].append(question)
    session.flush()

    attempt = AssessmentAttempt(
        assessment_id=assessment_obs.id,
        trainee_id=trainee.id,
        attempt_number=1,
        status=AttemptStatus.GRADED.value,
        started_at=now - dt.timedelta(days=7, minutes=25),
        submitted_at=now - dt.timedelta(days=7),
        time_taken_seconds=980,
    )
    session.add(attempt)
    session.flush()

    for index, question in enumerate(created_questions[assessment_obs.id]):
        correct_option = session.scalar(
            select(QuestionOption).where(
                QuestionOption.question_id == question.id,
                QuestionOption.is_correct.is_(True),
            )
        )
        awarded = index < 2
        session.add(
            AttemptAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option_id=correct_option.id
                if correct_option
                else None,
                is_correct=awarded,
                marks_awarded=1.0 if awarded else 0.0,
            )
        )
    session.add(
        AssessmentResult(
            attempt_id=attempt.id,
            assessment_id=assessment_obs.id,
            trainee_id=trainee.id,
            score=2.0,
            percentage=66.7,
            correct_count=2,
            incorrect_count=1,
            unanswered_count=0,
            is_passed=True,
            grade="B",
            graded_at=now - dt.timedelta(days=7),
            remarks="Solid field practice; revise documentation discipline.",
        )
    )

    session.add(
        Certificate(
            certificate_number="CC-CERT-2024-000118",
            course_id=course_instruments.id,
            trainee_id=trainee.id,
            issued_by_id=admin.id,
            issued_at=now - dt.timedelta(days=4),
            final_score=66.7,
            grade="B",
            verification_code=secrets.token_hex(32),
        )
    )

    session.add(
        CourseFeedback(
            course_id=course_instruments.id,
            trainee_id=trainee.id,
            trainer_id=trainer_three.id,
            overall_rating=5,
            content_rating=5,
            trainer_rating=5,
            relevance_rating=4,
            comments="Field sessions were extremely practical and well sequenced.",
            suggestions="Add a longer telemetry troubleshooting lab.",
        )
    )

    session.add_all(
        [
            Announcement(
                title="Enrolment window open: NWP Foundations (CC-NWP-101)",
                body=(
                    "Regional forecasting offices may nominate duty forecasters for the "
                    "blended Numerical Weather Prediction Foundations programme. Nominations "
                    "close one week before the start date."
                ),
                audience=AnnouncementAudience.ALL.value,
                course_id=course_nwp.id,
                author_id=admin.id,
                is_pinned=True,
                published_at=now - dt.timedelta(days=1),
            ),
            Announcement(
                title="Competency matrix refresh for 2024-25",
                body=(
                    "All trainers are requested to update teachable skills and proficiency "
                    "scores so that course-to-trainer matching reflects current expertise."
                ),
                audience=AnnouncementAudience.TRAINERS.value,
                author_id=admin.id,
                published_at=now - dt.timedelta(days=4),
            ),
            Announcement(
                title="Certificates issued for AWS Calibration cohort",
                body=(
                    "Certificates for the Automatic Weather Station Calibration workshop are "
                    "now available in each trainee's certificate record."
                ),
                audience=AnnouncementAudience.TRAINEES.value,
                course_id=course_instruments.id,
                author_id=admin.id,
                published_at=now - dt.timedelta(days=6),
            ),
            Announcement(
                title="Nowcasting practicum moves to the coastal observatory",
                body=(
                    "The Radar & Satellite Nowcasting Practicum will be conducted at the "
                    "coastal observatory to allow live radar console sessions."
                ),
                audience=AnnouncementAudience.ALL.value,
                course_id=course_nowcast.id,
                author_id=admin.id,
                published_at=now - dt.timedelta(days=9),
            ),
        ]
    )

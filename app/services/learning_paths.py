import reflex as rx
import datetime as dt
from sqlalchemy import select
from app import models as m


def generate_path(session, uid: int, cid: int) -> m.LearningPath:
    gap = session.scalar(
        select(m.CompetencyGap)
        .where(
            m.CompetencyGap.user_id == uid,
            m.CompetencyGap.competency_id == cid,
            m.CompetencyGap.status.in_(["identified", "in_progress"]),
        )
        .with_for_update()
    )
    if not gap:
        raise ValueError(
            "No open owned gap is available. Refresh competency evidence first."
        )
    existing = session.scalar(
        select(m.LearningPath)
        .join(
            m.LearningPathStep, m.LearningPathStep.path_id == m.LearningPath.id
        )
        .where(
            m.LearningPath.user_id == uid,
            m.LearningPathStep.gap_id == gap.id,
            m.LearningPath.status.in_(["draft", "active"]),
        )
        .limit(1)
    )
    if existing:
        existing.status = "active"
        gap.status = "in_progress"
        return existing
    courses = session.scalars(
        select(m.Course)
        .join(
            m.CourseCompetencyRequirement,
            m.CourseCompetencyRequirement.course_id == m.Course.id,
        )
        .where(
            m.CourseCompetencyRequirement.competency_id == cid,
            m.CourseCompetencyRequirement.requirement_type == "outcome",
            m.CourseCompetencyRequirement.required_level >= gap.required_level,
            m.Course.status == "published",
        )
        .order_by(m.Course.duration_hours, m.Course.id)
        .limit(20)
    ).all()
    course = None
    for candidate in courses:
        unmet = session.execute(
            select(m.CourseCompetencyRequirement.id)
            .outerjoin(
                m.UserCompetency,
                (
                    m.UserCompetency.competency_id
                    == m.CourseCompetencyRequirement.competency_id
                )
                & (m.UserCompetency.user_id == uid),
            )
            .where(
                m.CourseCompetencyRequirement.course_id == candidate.id,
                m.CourseCompetencyRequirement.requirement_type
                == "prerequisite",
                m.CourseCompetencyRequirement.is_mandatory.is_(True),
                (
                    m.UserCompetency.current_level.is_(None)
                    | (
                        m.UserCompetency.current_level
                        < m.CourseCompetencyRequirement.required_level
                    )
                ),
            )
            .limit(1)
        ).first()
        if not unmet:
            course = candidate
            break
    if not course:
        raise ValueError(
            "No published course meets this target and your verified prerequisites. Ask a curriculum owner to add a suitable pathway."
        )
    comp = session.get(m.Competency, cid)
    path = m.LearningPath(
        user_id=uid,
        title=f"{comp.name}: development pathway",
        rationale="Shortest mapped published course meeting the target and verified prerequisites. Completion is not proficiency evidence.",
        status="active",
    )
    session.add(path)
    session.flush()
    session.add(
        m.LearningPathStep(
            path_id=path.id,
            user_id=uid,
            gap_id=gap.id,
            position=1,
            step_type="course",
            course_id=course.id,
        )
    )
    gap.status = "in_progress"
    return path


def complete_step(session, uid: int, step_id: int) -> None:
    step = session.scalar(
        select(m.LearningPathStep)
        .where(
            m.LearningPathStep.id == step_id, m.LearningPathStep.user_id == uid
        )
        .with_for_update()
    )
    if not step:
        raise ValueError("Step unavailable.")
    path = session.scalar(
        select(m.LearningPath)
        .where(m.LearningPath.id == step.path_id, m.LearningPath.user_id == uid)
        .with_for_update()
    )
    if path.status != "active":
        raise ValueError("Start an active pathway first.")
    earlier = session.scalar(
        select(m.LearningPathStep.id)
        .where(
            m.LearningPathStep.path_id == path.id,
            m.LearningPathStep.position < step.position,
            m.LearningPathStep.status != "completed",
        )
        .limit(1)
    )
    if earlier:
        raise ValueError(
            "Complete earlier steps first; skipped steps do not satisfy prerequisites."
        )
    eligible = False
    if step.step_type == "course":
        eligible = (
            session.scalar(
                select(m.Enrollment.id)
                .where(
                    m.Enrollment.trainee_id == uid,
                    m.Enrollment.course_id == step.course_id,
                    m.Enrollment.status == "completed",
                )
                .limit(1)
            )
            is not None
        )
    elif step.step_type == "resource":
        eligible = (
            session.scalar(
                select(m.ResourceProgress.id)
                .join(m.Enrollment)
                .where(
                    m.Enrollment.trainee_id == uid,
                    m.Enrollment.status != "dropped",
                    m.ResourceProgress.resource_id == step.resource_id,
                    m.ResourceProgress.is_completed.is_(True),
                )
                .limit(1)
            )
            is not None
        )
    elif step.step_type == "practice":
        eligible = (
            session.scalar(
                select(m.PracticeAnswer.id)
                .join(m.PracticeAttempt)
                .where(
                    m.PracticeAttempt.user_id == uid,
                    m.PracticeAttempt.status == "graded",
                    m.PracticeAnswer.question_id == step.practice_question_id,
                )
                .limit(1)
            )
            is not None
        )
    elif step.step_type == "assessment":
        eligible = (
            session.scalar(
                select(m.AssessmentResult.id)
                .where(
                    m.AssessmentResult.trainee_id == uid,
                    m.AssessmentResult.assessment_id == step.assessment_id,
                    m.AssessmentResult.is_passed.is_(True),
                )
                .limit(1)
            )
            is not None
        )
    elif step.step_type in {"module", "lesson"}:
        resources = (
            select(m.LessonResource.resource_id)
            .join(m.Lesson)
            .where(m.Lesson.status == "published")
        )
        resources = (
            resources.where(m.Lesson.id == step.lesson_id)
            if step.lesson_id
            else resources.where(m.Lesson.module_id == step.module_id)
        )
        ids = set(session.scalars(resources))
        completed = set(
            session.scalars(
                select(m.ResourceProgress.resource_id)
                .join(m.Enrollment)
                .where(
                    m.Enrollment.trainee_id == uid,
                    m.Enrollment.status != "dropped",
                    m.ResourceProgress.resource_id.in_(ids),
                    m.ResourceProgress.is_completed.is_(True),
                )
            )
        )
        eligible = bool(ids) and ids <= completed
    if not eligible:
        raise ValueError(
            "Complete the linked learning activity in My Learning / Practice / Assessments before confirming this step."
        )
    step.status = "completed"
    step.completed_at = dt.datetime.now(dt.UTC)
    session.flush()
    remaining = session.scalar(
        select(m.LearningPathStep.id)
        .where(
            m.LearningPathStep.path_id == path.id,
            m.LearningPathStep.status != "completed",
        )
        .limit(1)
    )
    if not remaining:
        path.status = "completed"
        path.completed_at = dt.datetime.now(dt.UTC)

import reflex as rx
import datetime as dt
from sqlalchemy import select
from app import models as m


def refresh_effectiveness(
    session, course_id: int
) -> m.TrainingEffectivenessSnapshot:
    enrollments = session.scalars(
        select(m.Enrollment).where(
            m.Enrollment.course_id == course_id,
            m.Enrollment.status != "dropped",
        )
    ).all()
    uids = {e.trainee_id for e in enrollments}
    observations = session.scalars(
        select(m.CompetencyObservation)
        .where(
            m.CompetencyObservation.course_id == course_id,
            m.CompetencyObservation.user_id.in_(uids),
            m.CompetencyObservation.verification_status == "verified",
            m.CompetencyObservation.observer_id.is_not(None),
            m.CompetencyObservation.verified_at.is_not(None),
        )
        .order_by(
            m.CompetencyObservation.observed_at.desc(),
            m.CompetencyObservation.id.desc(),
        )
    ).all()
    latest = {}
    for o in observations:
        latest.setdefault((o.user_id, o.competency_id, o.phase), o)
    pairs = {}
    for (uid, cid, phase), pre in latest.items():
        post = latest.get((uid, cid, "post"))
        if phase == "pre" and post and post.observed_at > pre.observed_at:
            pairs.setdefault(uid, []).append(
                (pre.observed_level, post.observed_level)
            )
    pre_values = [
        sum(x[0] for x in rows) / len(rows) for rows in pairs.values()
    ]
    post_values = [
        sum(x[1] for x in rows) / len(rows) for rows in pairs.values()
    ]
    results = session.scalars(
        select(m.AssessmentResult)
        .join(m.Assessment, m.Assessment.id == m.AssessmentResult.assessment_id)
        .join(
            m.AssessmentAttempt,
            m.AssessmentAttempt.id == m.AssessmentResult.attempt_id,
        )
        .where(
            m.Assessment.course_id == course_id,
            m.AssessmentResult.trainee_id.in_(uids),
            m.AssessmentAttempt.status.in_(["submitted", "graded"]),
            m.AssessmentAttempt.submitted_at.is_not(None),
        )
        .order_by(
            m.AssessmentResult.graded_at.desc(), m.AssessmentResult.id.desc()
        )
    ).all()
    official = {}
    for r in results:
        official.setdefault((r.trainee_id, r.assessment_id), r.is_passed)
    feedback = session.scalars(
        select(m.CourseFeedback).where(
            m.CourseFeedback.course_id == course_id,
            m.CourseFeedback.trainee_id.in_(uids),
        )
    ).all()
    now = dt.datetime.now(dt.UTC)
    snapshot = m.TrainingEffectivenessSnapshot(
        course_id=course_id,
        participants=len(uids),
        completions=sum(e.status == "completed" for e in enrollments),
        observation_pairs=len(pairs),
        feedback_count=len(feedback),
        feedback_average=sum(f.overall_rating for f in feedback) / len(feedback)
        if feedback
        else None,
        pass_rate=100 * sum(official.values()) / len(official)
        if official
        else None,
        pre_competency_average=sum(pre_values) / len(pre_values)
        if pre_values
        else None,
        post_competency_average=sum(post_values) / len(post_values)
        if post_values
        else None,
        observed_competency_improvement=(sum(post_values) - sum(pre_values))
        / len(pairs)
        if pairs
        else None,
        period_start=min(
            [e.enrolled_at for e in enrollments]
            or [now - dt.timedelta(seconds=1)]
        ),
        period_end=now + dt.timedelta(microseconds=1),
        methodology="Latest chronological verified pre/post per competency, averaged within learner then across learners. Latest official result per learner/assessment for pass rate. No assessment pre/post labels exist: assessment delta remains unmeasured. Practice excluded. Observational, not causal.",
    )
    session.add(snapshot)
    return snapshot

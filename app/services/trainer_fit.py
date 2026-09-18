import reflex as rx
import datetime as dt
import json
from sqlalchemy import select
from app import models as m
from app.services.evidence import qualifying

WEIGHTS = {
    "competency_coverage": 40,
    "domain_alignment": 25,
    "experience": 15,
    "qualification": 10,
    "observed_effectiveness": 10,
}


def weighted_score(factors: dict[str, float]) -> float:
    return (
        sum(max(0.0, min(100.0, factors[k])) * v for k, v in WEIGHTS.items())
        / 100
    )


def evaluate(
    session,
    course: m.Course,
    trainer: m.User,
    start: dt.datetime,
    end: dt.datetime,
    require_qualification: bool = False,
) -> tuple[m.TrainerFitEvaluation, dict[int, int], list[str]]:
    requirements = session.scalars(
        select(m.CourseCompetencyRequirement).where(
            m.CourseCompetencyRequirement.course_id == course.id,
            m.CourseCompetencyRequirement.requirement_type == "trainer",
        )
    ).all()
    evidence = session.scalars(
        select(m.CompetencyEvidence)
        .where(m.CompetencyEvidence.user_id == trainer.id)
        .order_by(
            m.CompetencyEvidence.verified_at.desc(),
            m.CompetencyEvidence.id.desc(),
        )
    ).all()
    levels = {}
    for e in evidence:
        if qualifying(e) and e.competency_id not in levels:
            levels[e.competency_id] = e.measured_level
    subjects = dict(
        session.execute(select(m.Competency.id, m.Competency.subject_id)).all()
    )
    required_domains = {subjects[r.competency_id] for r in requirements}
    trainer_domains = {subjects[cid] for cid in levels}
    covered = {
        r.competency_id: levels[r.competency_id]
        for r in requirements
        if levels.get(r.competency_id, 0) >= r.required_level
    }
    failures = []
    if (
        trainer.role != "trainer"
        or not trainer.is_active
        or trainer.approval_status != "approved"
    ):
        failures.append("Trainer must be active and approved.")
    if not requirements:
        failures.append("No trainer competency requirements configured.")
    if not required_domains or not required_domains <= trainer_domains:
        failures.append("Verified domain coverage is incomplete.")
    for r in requirements:
        if r.is_mandatory and r.competency_id not in covered:
            failures.append(
                f"Competency {r.competency_id}: verified level {r.required_level} required."
            )
    available = session.scalar(
        select(m.TrainerAvailability.id)
        .where(
            m.TrainerAvailability.trainer_id == trainer.id,
            m.TrainerAvailability.starts_at <= start,
            m.TrainerAvailability.ends_at >= end,
            m.TrainerAvailability.status == "available",
        )
        .limit(1)
    )
    blocked = session.scalar(
        select(m.TrainerAvailability.id)
        .where(
            m.TrainerAvailability.trainer_id == trainer.id,
            m.TrainerAvailability.starts_at < end,
            m.TrainerAvailability.ends_at > start,
            m.TrainerAvailability.status != "available",
        )
        .limit(1)
    )
    if not available or blocked:
        failures.append(
            "No confirmed availability covering the requested period, or a conflicting window exists."
        )
    capacity = session.scalar(
        select(m.TrainerCapacity)
        .where(
            m.TrainerCapacity.trainer_id == trainer.id,
            m.TrainerCapacity.starts_at <= start,
            m.TrainerCapacity.ends_at >= end,
        )
        .order_by(m.TrainerCapacity.id)
        .limit(1)
        .with_for_update()
    )
    assignments = session.scalars(
        select(m.Course)
        .join(m.CourseTrainerAssignment)
        .where(
            m.CourseTrainerAssignment.trainer_id == trainer.id,
            m.CourseTrainerAssignment.status == "approved",
            m.Course.id != course.id,
            m.Course.status != "archived",
            (
                m.Course.start_date.is_(None)
                | (m.Course.start_date <= end.date())
            ),
            (m.Course.end_date.is_(None) | (m.Course.end_date >= start.date())),
        )
    ).all()
    hours = sum(c.duration_hours for c in assignments)
    participants = sum(c.capacity for c in assignments)
    if (
        not capacity
        or max(capacity.allocated_hours, hours) + course.duration_hours
        > capacity.max_hours
        or max(capacity.allocated_courses, len(assignments)) + 1
        > capacity.max_courses
        or max(capacity.allocated_participants, participants) + course.capacity
        > capacity.max_participants
    ):
        failures.append(
            "Insufficient recorded remaining hours, course slots or participant capacity."
        )
    qualification = session.scalar(
        select(m.Qualification.id)
        .where(
            m.Qualification.user_id == trainer.id,
            m.Qualification.is_verified.is_(True),
        )
        .limit(1)
    )
    if require_qualification and not qualification:
        failures.append(
            "A verified qualification is required by this evaluation policy."
        )
    profile = session.scalar(
        select(m.TrainerProfile).where(m.TrainerProfile.user_id == trainer.id)
    )
    snapshots = session.scalars(
        select(m.TrainingEffectivenessSnapshot)
        .join(
            m.CourseTrainerAssignment,
            m.CourseTrainerAssignment.course_id
            == m.TrainingEffectivenessSnapshot.course_id,
        )
        .where(
            m.CourseTrainerAssignment.trainer_id == trainer.id,
            m.CourseTrainerAssignment.status == "approved",
            m.TrainingEffectivenessSnapshot.observation_pairs > 0,
        )
        .order_by(m.TrainingEffectivenessSnapshot.calculated_at.desc())
        .limit(30)
    ).all()
    latest = {}
    for snap in snapshots:
        latest.setdefault(snap.course_id, snap)
    changes = [
        s.observed_competency_improvement
        for s in latest.values()
        if s.observed_competency_improvement is not None
    ]
    factors = {
        "competency_coverage": 100
        * sum(r.weight for r in requirements if r.competency_id in covered)
        / max(sum(r.weight for r in requirements), 1),
        "domain_alignment": 100
        * len(required_domains & trainer_domains)
        / max(len(required_domains), 1),
        "experience": min(
            100.0, (profile.years_of_training if profile else 0) * 10
        ),
        "qualification": 100.0 if qualification else 0.0,
        "observed_effectiveness": max(
            0.0, min(100.0, sum(changes) / len(changes) * 25)
        )
        if changes
        else 0.0,
    }
    policy = session.scalar(
        select(m.TrainerFitWeights).where(
            m.TrainerFitWeights.policy_code == "sih-five-factor-compat",
            m.TrainerFitWeights.version == 1,
        )
    )
    if not policy:
        policy = m.TrainerFitWeights(
            policy_code="sih-five-factor-compat",
            competency_weight=75,
            experience_weight=15,
            effectiveness_weight=10,
            availability_weight=0,
            capacity_weight=0,
            description="Compatibility storage: competency_score is the normalized coverage/domain/qualification composite. Exact five factors and weights are in evaluation explanation. Availability and capacity are gates, not scored factors.",
        )
        session.add(policy)
        session.flush()
    composite = (
        40 * factors["competency_coverage"]
        + 25 * factors["domain_alignment"]
        + 10 * factors["qualification"]
    ) / 75
    details = {
        "factors": factors,
        "weights": WEIGHTS,
        "contributions": {k: factors[k] * WEIGHTS[k] / 100 for k in WEIGHTS},
        "failures": failures,
        "covered": covered,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "require_verified_qualification": require_qualification,
        "method": "Experience: 10 points per training year capped at 100. Qualification: verified record 100, otherwise 0. Effectiveness: latest paired observed scale improvement per assigned course / 4 × 100, clipped; missing evidence contributes 0, not a measured zero effect. Domain: required subjects with verified evidence. Coverage: requirement-weighted minimum-level coverage. Compatibility composite = (40×coverage + 25×domain + 10×qualification)/75.",
    }
    evaluation = m.TrainerFitEvaluation(
        course_id=course.id,
        trainer_id=trainer.id,
        weights_id=policy.id,
        eligibility_status="ineligible" if failures else "eligible",
        competency_score=composite,
        competency_weight=75,
        experience_score=factors["experience"],
        experience_weight=15,
        effectiveness_score=factors["observed_effectiveness"],
        effectiveness_weight=10,
        availability_score=100 if available and not blocked else 0,
        availability_weight=0,
        capacity_score=0 if any("capacity" in x for x in failures) else 100,
        capacity_weight=0,
        weighted_total=weighted_score(factors),
        explanation=json.dumps(details),
        algorithm_version="sih-five-factor-v2",
    )
    session.add(evaluation)
    session.flush()
    return evaluation, covered, failures


def recalculate(
    session,
    course_id: int,
    start: dt.datetime,
    end: dt.datetime,
    qualification: bool = False,
):
    course = session.get(m.Course, course_id)
    if not course or end <= start:
        raise ValueError("Select a valid course and chronological dates.")
    trainers = session.scalars(
        select(m.User)
        .where(m.User.role == "trainer")
        .order_by(m.User.id)
        .limit(500)
    ).all()
    return [
        evaluate(session, course, t, start, end, qualification)
        for t in trainers
    ]

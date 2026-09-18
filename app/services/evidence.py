import reflex as rx
import datetime as dt
from sqlalchemy import select
from app import models as m


def score_to_level(score: float) -> int:
    """Official rubric v1: >=90:5, >=75:4, >=60:3, >=40:2, otherwise 1."""
    for threshold, level in ((90, 5), (75, 4), (60, 3), (40, 2)):
        if score >= threshold:
            return level
    return 1


def record_official_evidence(session, result_id: int) -> None:
    """Called only by the server scorer in its locked submission transaction."""
    import json
    from sqlalchemy import func

    result = session.get(m.AssessmentResult, result_id)
    if result is None or not result.is_passed:
        return
    assessment = session.get(m.Assessment, result.assessment_id)
    author = (
        session.get(m.User, assessment.created_by_id)
        if assessment and assessment.created_by_id
        else None
    )
    if (
        author is None
        or not author.is_active
        or author.approval_status != "approved"
        or author.role not in {"trainer", "admin"}
    ):
        return
    attempt = session.get(m.AssessmentAttempt, result.attempt_id)
    if attempt.status != "graded" or attempt.trainee_id != result.trainee_id:
        return
    rows = session.execute(
        select(
            m.Question.competency_id,
            m.Question.id,
            m.Question.marks,
            m.AttemptAnswer.marks_awarded,
        )
        .join(m.AttemptAnswer, m.AttemptAnswer.question_id == m.Question.id)
        .where(
            m.AttemptAnswer.attempt_id == attempt.id,
            m.Question.assessment_id == assessment.id,
            m.Question.competency_id.is_not(None),
        )
    ).all()
    grouped = {}
    for cid, qid, marks, awarded in rows:
        grouped.setdefault(cid, []).append((qid, float(marks), float(awarded)))
    moment = dt.datetime.now(dt.UTC)
    for cid, measurements in grouped.items():
        total = sum(item[1] for item in measurements)
        if total <= 0:
            continue
        reference = f"result:{result.id}:competency:{cid}:rubric-v1"
        if session.scalar(
            select(m.CompetencyEvidence.id).where(
                m.CompetencyEvidence.user_id == result.trainee_id,
                m.CompetencyEvidence.competency_id == cid,
                m.CompetencyEvidence.source_system
                == "official_question_scoring",
                m.CompetencyEvidence.source_reference == reference,
            )
        ):
            continue
        score = 100 * sum(item[2] for item in measurements) / total
        evidence = m.CompetencyEvidence(
            user_id=result.trainee_id,
            competency_id=cid,
            evidence_type="official_assessment",
            source_system="official_question_scoring",
            source_reference=reference,
            assessment_result_id=result.id,
            measured_score=score,
            measured_level=score_to_level(score),
            verifier_id=author.id,
            verification_status="verified",
            observed_at=result.graded_at or moment,
            verified_at=moment,
            notes=json.dumps(
                {
                    "rubric": ">=90:5; >=75:4; >=60:3; >=40:2; otherwise:1",
                    "assessment_id": assessment.id,
                    "result_id": result.id,
                    "questions": [
                        {"id": q, "marks": t, "awarded": a}
                        for q, t, a in measurements
                    ],
                }
            ),
        )
        session.add(evidence)
        session.flush()
        session.add(
            m.CompetencyObservation(
                course_id=assessment.course_id,
                user_id=result.trainee_id,
                competency_id=cid,
                observer_id=author.id,
                evidence_id=evidence.id,
                phase="post",
                observed_level=evidence.measured_level,
                verification_status="verified",
                observed_at=moment,
                verified_at=moment,
                notes=reference,
            )
        )
    session.flush()
    refresh_evidence(session, result.trainee_id)
    from app.services.effectiveness import refresh_effectiveness

    refresh_effectiveness(session, assessment.course_id)


def qualifying(e: m.CompetencyEvidence) -> bool:
    return bool(
        e.verification_status == "verified"
        and e.verifier_id
        and e.verified_at
        and e.measured_level is not None
        and e.evidence_type
        in {
            "official_assessment",
            "final_assessment",
            "trainer_evaluation",
            "questionnaire",
        }
    )


def refresh_evidence(session, uid: int) -> None:
    evidence = session.scalars(
        select(m.CompetencyEvidence)
        .where(m.CompetencyEvidence.user_id == uid)
        .order_by(
            m.CompetencyEvidence.verified_at.desc(),
            m.CompetencyEvidence.id.desc(),
        )
    ).all()
    chosen = {}
    for item in evidence:
        if qualifying(item) and item.competency_id not in chosen:
            chosen[item.competency_id] = item
    snapshots = {
        s.competency_id: s
        for s in session.scalars(
            select(m.UserCompetency).where(m.UserCompetency.user_id == uid)
        )
    }
    requirements = (
        session.execute(
            select(m.RoleCompetencyRequirement)
            .join(
                m.UserOrganizationAssignment,
                m.UserOrganizationAssignment.role_id
                == m.RoleCompetencyRequirement.role_id,
            )
            .where(
                m.UserOrganizationAssignment.user_id == uid,
                m.UserOrganizationAssignment.status == "active",
                m.UserOrganizationAssignment.starts_at
                <= dt.datetime.now(dt.UTC),
                (
                    m.UserOrganizationAssignment.ends_at.is_(None)
                    | (
                        m.UserOrganizationAssignment.ends_at
                        > dt.datetime.now(dt.UTC)
                    )
                ),
                m.RoleCompetencyRequirement.is_active.is_(True),
            )
        )
        .scalars()
        .all()
    )
    targets = {}
    for r in requirements:
        targets[r.competency_id] = max(
            targets.get(r.competency_id, 1), r.required_level
        )
    needs = session.scalars(
        select(m.OrganizationalCapacityNeed)
        .join(
            m.UserOrganizationAssignment,
            m.UserOrganizationAssignment.organization_id
            == m.OrganizationalCapacityNeed.organization_id,
        )
        .where(
            m.UserOrganizationAssignment.user_id == uid,
            m.UserOrganizationAssignment.status == "active",
            m.UserOrganizationAssignment.starts_at <= dt.datetime.now(dt.UTC),
            (
                m.UserOrganizationAssignment.ends_at.is_(None)
                | (
                    m.UserOrganizationAssignment.ends_at
                    > dt.datetime.now(dt.UTC)
                )
            ),
            m.OrganizationalCapacityNeed.status == "active",
            m.OrganizationalCapacityNeed.starts_at <= dt.datetime.now(dt.UTC),
            (
                m.OrganizationalCapacityNeed.ends_at.is_(None)
                | (
                    m.OrganizationalCapacityNeed.ends_at
                    > dt.datetime.now(dt.UTC)
                )
            ),
            (
                m.OrganizationalCapacityNeed.department_id.is_(None)
                | (
                    m.OrganizationalCapacityNeed.department_id
                    == m.UserOrganizationAssignment.department_id
                )
            ),
        )
    ).all()
    for n in needs:
        targets[n.competency_id] = max(
            targets.get(n.competency_id, 1), n.required_level
        )
    for cid in set(chosen) | set(snapshots) | set(targets):
        s = snapshots.get(cid)
        if s is None:
            s = m.UserCompetency(user_id=uid, competency_id=cid)
            session.add(s)
        e = chosen.get(cid)
        s.current_level = e.measured_level if e else None
        s.evidence_id = e.id if e else None
        s.last_verified_at = e.verified_at if e else None
        s.verification_status = "verified" if e else "unmeasured"
        target = max(targets.get(cid, 0), s.target_level or 0)
        if target:
            s.target_level = target
            gap = session.scalar(
                select(m.CompetencyGap)
                .where(
                    m.CompetencyGap.user_id == uid,
                    m.CompetencyGap.competency_id == cid,
                    m.CompetencyGap.status != "superseded",
                )
                .order_by(m.CompetencyGap.id.desc())
                .limit(1)
            )
            if gap is None:
                gap = m.CompetencyGap(
                    user_id=uid, competency_id=cid, required_level=target
                )
                session.add(gap)
            gap.baseline_level = s.current_level
            gap.required_level = target
            if s.current_level is not None and s.current_level >= target:
                gap.status = "closed"
                gap.closed_at = dt.datetime.now(dt.UTC)
            elif gap.status == "closed":
                gap.status = "identified"
                gap.closed_at = None
    session.flush()

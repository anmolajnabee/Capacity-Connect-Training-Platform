import reflex as rx
import datetime as dt
from sqlalchemy import select
from app import models as m


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

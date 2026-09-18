import reflex as rx
from sqlalchemy import select
from app import models as m


def greedy_cover(
    required: set[int], candidates: dict[int, set[int]]
) -> list[int]:
    missing = set(required)
    selected = []
    while missing:
        options = sorted(
            candidates, key=lambda k: (-len(candidates[k] & missing), k)
        )
        if not options or not (candidates[options[0]] & missing):
            break
        best = options[0]
        selected.append(best)
        missing -= candidates[best]
    for member in list(reversed(selected)):
        others = set().union(*(candidates[k] for k in selected if k != member))
        if required <= others:
            selected.remove(member)
    return selected


def propose_team(session, course_id: int, evaluations) -> m.TrainerTeamMatch:
    requirements = session.scalars(
        select(m.CourseCompetencyRequirement).where(
            m.CourseCompetencyRequirement.course_id == course_id,
            m.CourseCompetencyRequirement.requirement_type == "trainer",
        )
    ).all()
    required = {r.competency_id for r in requirements}
    eligible = {
        e.trainer_id: (e, coverage)
        for e, coverage, failures in evaluations
        if not any(
            not f.startswith("Competency ")
            and not f.startswith("Verified domain")
            for f in failures
        )
        and coverage
    }
    chosen = greedy_cover(
        required, {uid: set(cov) for uid, (_, cov) in eligible.items()}
    )
    if not evaluations:
        raise ValueError("No trainers available for evaluation.")
    covered = set().union(*(set(eligible[k][1]) for k in chosen))
    team = m.TrainerTeamMatch(
        course_id=course_id,
        weights_id=evaluations[0][0].weights_id,
        eligibility_status="eligible"
        if required and required <= covered
        else "insufficient_evidence",
        coverage_percent=100 * len(required & covered) / max(len(required), 1),
        weighted_total=sum(eligible[k][0].weighted_total for k in chosen)
        / max(len(chosen), 1),
        explanation="Deterministic maximum-new-coverage greedy selection with redundant-member removal; practical small team, not a claim of globally optimal set cover. All non-competency gates enforced per member.",
    )
    session.add(team)
    session.flush()
    members = {}
    for uid in chosen:
        member = m.TrainerTeamMember(
            team_match_id=team.id,
            trainer_id=uid,
            fit_evaluation_id=eligible[uid][0].id,
            member_role="lead" if not members else "co_trainer",
        )
        session.add(member)
        session.flush()
        members[uid] = member
    for r in requirements:
        uid = next(
            (uid for uid in chosen if r.competency_id in eligible[uid][1]), None
        )
        session.add(
            m.TrainerTeamCompetencyCoverage(
                team_match_id=team.id,
                competency_id=r.competency_id,
                required_level=r.required_level,
                member_id=members[uid].id if uid else None,
                covered_level=eligible[uid][1][r.competency_id]
                if uid
                else None,
                coverage_status="covered" if uid else "uncovered",
                explanation="Verified minimum met by named member."
                if uid
                else "No eligible team member meets this requirement.",
            )
        )
    return team

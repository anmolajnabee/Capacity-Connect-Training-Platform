import reflex as rx
import logging
from typing import Any, TypedDict
from sqlalchemy import text
from app.security import read_session
from app.states.auth_state import AuthState


class GapRow(TypedDict):
    competency_id: int
    organization_id: int
    department_id: int
    role_id: int
    name: str
    subject: str
    organization: str
    department: str
    role: str
    current: str
    target: int
    gap: str
    severity: str
    population: int
    affected: int
    unmeasured: int
    verified: int


GAP_CTE = """
WITH verified AS (
 SELECT uc.user_id, uc.competency_id, uc.current_level, uc.last_verified_at
 FROM cc_user_competency uc JOIN cc_competency_evidence e
 ON e.id=uc.evidence_id AND e.user_id=uc.user_id AND e.competency_id=uc.competency_id
 AND e.measured_level=uc.current_level AND e.verified_at=uc.last_verified_at
 WHERE uc.verification_status='verified' AND e.verification_status='verified'
 AND e.verifier_id IS NOT NULL AND e.evidence_type NOT IN ('practice','course_completion')
), targets AS (
 SELECT a.user_id, r.competency_id, r.required_level
 FROM cc_user_organization_assignment a JOIN cc_role_competency_requirement r ON r.role_id=a.role_id
 WHERE a.status='active' AND a.starts_at<=CURRENT_TIMESTAMP
 AND (a.ends_at IS NULL OR a.ends_at>CURRENT_TIMESTAMP) AND r.is_active=true
 UNION ALL SELECT user_id, competency_id, target_level FROM cc_user_competency WHERE target_level IS NOT NULL
 UNION ALL SELECT user_id, competency_id, required_level FROM cc_competency_gap WHERE status IN ('identified','in_progress')
 UNION ALL SELECT a.user_id,n.competency_id,n.required_level
 FROM cc_user_organization_assignment a JOIN cc_organizational_capacity_need n
 ON n.organization_id=a.organization_id AND (n.department_id IS NULL OR n.department_id=a.department_id)
 WHERE a.status='active' AND a.starts_at<=CURRENT_TIMESTAMP AND (a.ends_at IS NULL OR a.ends_at>CURRENT_TIMESTAMP)
 AND n.status='active' AND n.starts_at<=CURRENT_TIMESTAMP AND (n.ends_at IS NULL OR n.ends_at>CURRENT_TIMESTAMP)
), target AS (
 SELECT user_id,competency_id,MAX(required_level) AS required_level FROM targets GROUP BY user_id,competency_id
), pairs AS (
 SELECT user_id,competency_id FROM target UNION SELECT user_id,competency_id FROM cc_user_competency
), basis AS (
 SELECT DISTINCT p.user_id,u.full_name,p.competency_id,c.name,s.name AS subject,
 COALESCE(o.id,0) AS organization_id,COALESCE(d.id,0) AS department_id,COALESCE(r.id,0) AS role_id,
 COALESCE(o.name,'Unassigned') AS organization,COALESCE(d.name,'Unassigned') AS department,
 COALESCE(r.title,'Unassigned') AS role,v.current_level,v.last_verified_at,t.required_level
 FROM pairs p JOIN cc_user u ON u.id=p.user_id JOIN cc_competency c ON c.id=p.competency_id
 JOIN cc_subject s ON s.id=c.subject_id
 LEFT JOIN target t ON t.user_id=p.user_id AND t.competency_id=p.competency_id
 LEFT JOIN verified v ON v.user_id=p.user_id AND v.competency_id=p.competency_id
 LEFT JOIN cc_user_organization_assignment a ON a.user_id=p.user_id AND a.status='active'
 AND a.starts_at<=CURRENT_TIMESTAMP AND (a.ends_at IS NULL OR a.ends_at>CURRENT_TIMESTAMP)
 LEFT JOIN cc_organization o ON o.id=a.organization_id
 LEFT JOIN cc_department d ON d.id=a.department_id
 LEFT JOIN cc_organizational_role r ON r.id=a.role_id
 WHERE c.is_active=true AND u.is_active=true
 AND ((:admin=true AND u.role='trainee') OR (:admin=false AND u.id=:uid))
)
"""


class CompetencyWorkspaceState(rx.State):
    rows: list[GapRow] = []
    evidence: list[dict[str, str]] = []
    learners: list[dict[str, str]] = []
    recommendations: list[dict[str, str]] = []
    error: str = ""
    loading: bool = False
    search: str = ""
    organization: str = ""
    department: str = ""
    role_filter: str = ""
    subject: str = ""
    offset: int = 0
    has_more: bool = False
    selected_name: str = ""
    selected_competency: int = 0
    selected_org: int = 0
    selected_department: int = 0
    selected_role: int = 0
    is_admin: bool = False
    is_trainer: bool = False

    async def _actor(self) -> tuple[int, str]:
        auth = await self.get_state(AuthState)
        uid = read_session(auth.session_cookie)
        try:
            async with rx.asession() as session:
                row = (
                    await session.execute(
                        text(
                            "SELECT id,role FROM cc_user WHERE id=:uid AND is_active=true AND approval_status='approved'"
                        ),
                        {"uid": uid},
                    )
                ).first()
            return (int(row[0]), str(row[1])) if row else (0, "")
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            raise

    @rx.event
    async def load(self):
        self.loading = True
        self.rows = []
        self.evidence = []
        self.learners = []
        self.recommendations = []
        self.selected_name = ""
        self.error = ""
        yield
        try:
            uid, role = await self._actor()
            if not uid:
                yield rx.redirect("/login")
                return
            self.is_admin = role == "admin"
            self.is_trainer = role == "trainer"
            async with rx.asession() as session:
                from app.services.evidence import refresh_evidence
                from app import models as m
                from sqlalchemy import select

                ids = [uid]
                if self.is_admin:
                    ids = list(
                        (
                            await session.scalars(
                                select(m.User.id)
                                .where(
                                    m.User.role == "trainee",
                                    m.User.is_active.is_(True),
                                )
                                .limit(1000)
                            )
                        ).all()
                    )
                for learner_id in ids:
                    await session.run_sync(
                        lambda s: refresh_evidence(s, learner_id)
                    )
                await session.commit()
                rows = (
                    await session.execute(
                        text(f"""{GAP_CTE}
                    SELECT competency_id,organization_id,department_id,role_id,name,subject,organization,department,role,
                    AVG(current_level),MAX(required_level),AVG(CASE WHEN current_level IS NOT NULL AND required_level IS NOT NULL THEN CASE WHEN required_level>current_level THEN required_level-current_level ELSE 0 END END),
                    COUNT(DISTINCT user_id),COUNT(DISTINCT CASE WHEN current_level<required_level THEN user_id END),
                    COUNT(DISTINCT CASE WHEN current_level IS NULL THEN user_id END),COUNT(DISTINCT CASE WHEN current_level IS NOT NULL THEN user_id END)
                    FROM basis WHERE LOWER(name) LIKE :search AND LOWER(organization) LIKE :org
                    AND LOWER(department) LIKE :dept AND LOWER(role) LIKE :role_filter AND LOWER(subject) LIKE :subject
                    GROUP BY competency_id,organization_id,department_id,role_id,name,subject,organization,department,role
                    ORDER BY organization,department,role,subject,name,competency_id LIMIT 51 OFFSET :offset
                """),
                        {
                            "uid": uid,
                            "admin": self.is_admin,
                            "search": f"%{self.search.lower()}%",
                            "org": f"%{self.organization.lower()}%",
                            "dept": f"%{self.department.lower()}%",
                            "role_filter": f"%{self.role_filter.lower()}%",
                            "subject": f"%{self.subject.lower()}%",
                            "offset": self.offset,
                        },
                    )
                ).all()
            self.has_more = len(rows) > 50
            self.rows = [
                {
                    "competency_id": r[0],
                    "organization_id": r[1],
                    "department_id": r[2],
                    "role_id": r[3],
                    "name": r[4],
                    "subject": r[5],
                    "organization": r[6],
                    "department": r[7],
                    "role": r[8],
                    "current": f"{r[9]:.1f}"
                    if r[9] is not None
                    else "Unmeasured",
                    "target": int(r[10] or 0),
                    "gap": f"{r[11]:.1f}"
                    if r[11] is not None
                    else "Not measurable",
                    "severity": "Unmeasured"
                    if r[9] is None
                    else (
                        "High"
                        if (r[11] or 0) >= 2
                        else (
                            "Develop"
                            if (r[11] or 0) > 0
                            else "Target met"
                            if r[10]
                            else "No target"
                        )
                    ),
                    "population": r[12],
                    "affected": r[13],
                    "unmeasured": r[14],
                    "verified": r[15],
                }
                for r in rows[:50]
            ]
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.error = "The competency registry could not be loaded. Retry to refresh the evidence."
        finally:
            self.loading = False

    @rx.event
    def filter_rows(self, data: dict[str, Any]):
        self.search = str(data.get("search", "")).strip()[:100]
        self.organization = str(data.get("organization", "")).strip()[:100]
        self.department = str(data.get("department", "")).strip()[:100]
        self.role_filter = str(data.get("role", "")).strip()[:100]
        self.subject = str(data.get("subject", "")).strip()[:100]
        self.offset = 0
        return CompetencyWorkspaceState.load

    @rx.event
    def next_page(self):
        if self.has_more:
            self.offset += 50
        return CompetencyWorkspaceState.load

    @rx.event
    def previous_page(self):
        self.offset = max(0, self.offset - 50)
        return CompetencyWorkspaceState.load

    @rx.event
    async def inspect_gap(
        self, competency_id: int, org: int, dept: int, role_id: int
    ):
        self.evidence = []
        self.learners = []
        self.recommendations = []
        self.error = ""
        try:
            uid, role = await self._actor()
            if not uid:
                return rx.redirect("/login")
            params = {
                "uid": uid,
                "admin": role == "admin",
                "cid": competency_id,
                "org": org,
                "dept": dept,
                "rid": role_id,
            }
            async with rx.asession() as session:
                people = (
                    await session.execute(
                        text(f"""{GAP_CTE}
                    SELECT user_id,full_name,name,current_level,required_level,last_verified_at FROM basis
                    WHERE competency_id=:cid AND organization_id=:org AND department_id=:dept AND role_id=:rid
                    ORDER BY current_level ASC NULLS FIRST,user_id LIMIT 50
                """),
                        params,
                    )
                ).all()
                if not people:
                    self.error = "This competency is not available in your current scope."
                    return
                evidence = (
                    await session.execute(
                        text(f"""{GAP_CTE}
                    SELECT u.full_name,e.evidence_type,e.verification_status,e.measured_level,e.observed_at,e.verified_at,e.source_reference,e.notes
                    FROM cc_competency_evidence e JOIN cc_user u ON u.id=e.user_id
                    WHERE e.competency_id=:cid AND EXISTS(SELECT 1 FROM basis b WHERE b.user_id=e.user_id
                    AND b.competency_id=:cid AND b.organization_id=:org AND b.department_id=:dept AND b.role_id=:rid)
                    ORDER BY e.observed_at DESC,e.id DESC LIMIT 50
                """),
                        params,
                    )
                ).all()
                courses = (
                    await session.execute(
                        text("""
                    SELECT c.title,c.code,r.required_level,r.requirement_type,
                    (SELECT COUNT(*) FROM cc_learning_resource lr WHERE lr.course_id=c.id AND lr.is_published=true),
                    (SELECT COUNT(*) FROM cc_assessment a WHERE a.course_id=c.id AND a.status='open')
                    FROM cc_course_competency_requirement r JOIN cc_course c ON c.id=r.course_id
                    WHERE r.competency_id=:cid AND r.requirement_type='outcome' AND c.status='published'
                    ORDER BY r.required_level,c.id LIMIT 20
                """),
                        params,
                    )
                ).all()
            self.selected_name = str(people[0][2])
            self.selected_competency = competency_id
            self.selected_org = org
            self.selected_department = dept
            self.selected_role = role_id
            self.learners = [
                {
                    "name": str(r[1]),
                    "current": str(r[3]) if r[3] is not None else "Unmeasured",
                    "target": str(r[4])
                    if r[4] is not None
                    else "Not configured",
                    "verified": str(r[5])
                    if r[5]
                    else "No verified measurement",
                    "gap": str(max(0, r[4] - r[3]))
                    if r[3] is not None and r[4] is not None
                    else "Not measurable",
                }
                for r in people
            ]
            self.evidence = [
                {
                    "name": str(r[0]),
                    "type": str(r[1]).replace("_", " "),
                    "status": str(r[2]),
                    "level": str(r[3])
                    if r[3] is not None
                    else "No measured level",
                    "observed": str(r[4]),
                    "verified": str(r[5]) if r[5] else "Not verified",
                    "reference": str(r[6]),
                    "notes": str(r[7]),
                }
                for r in evidence
            ]
            self.recommendations = [
                {
                    "title": r[0],
                    "code": r[1],
                    "detail": f"Outcome level {r[2]} · {r[4]} published resources · {r[5]} open official assessments",
                }
                for r in courses
            ]
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.error = "Could not load the evidence trail."

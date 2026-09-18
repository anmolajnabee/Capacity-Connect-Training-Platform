import reflex as rx
import csv
import io
import logging
from sqlalchemy import text
from app.security import read_session
from app.states.auth_state import AuthState


COURSE_SCOPE = """(:role='admin' OR EXISTS(SELECT 1 FROM cc_course_trainer_assignment ca WHERE ca.course_id=c.id AND ca.trainer_id=:uid AND ca.status='approved'))"""

QUERIES: dict[str, str] = {
    "trainees": """SELECT u.full_name,u.email,COUNT(DISTINCT e.id) AS enrollments,COUNT(DISTINCT CASE WHEN e.status='completed' THEN e.id END) AS completions,COUNT(DISTINCT CASE WHEN g.status IN ('identified','in_progress') THEN g.id END) AS open_gaps,COUNT(DISTINCT CASE WHEN uc.verification_status='verified' THEN uc.id END) AS verified_competencies FROM cc_user u LEFT JOIN cc_enrollment e ON e.trainee_id=u.id LEFT JOIN cc_competency_gap g ON g.user_id=u.id LEFT JOIN cc_user_competency uc ON uc.user_id=u.id WHERE :role='admin' AND u.role='trainee' GROUP BY u.id,u.full_name,u.email ORDER BY u.full_name,u.id""",
    "notifications": """SELECT n.title,n.body,COALESCE(r.read_state,'unread') AS read_state,n.created_at,n.action_path
        FROM cc_notification n LEFT JOIN cc_notification_receipt r ON r.notification_id=n.id AND r.user_id=:uid
        WHERE n.status='published' AND (n.expires_at IS NULL OR n.expires_at>CURRENT_TIMESTAMP)
        AND (n.audience='all' OR (n.audience='user' AND n.user_id=:uid)
        OR n.audience=CASE :role WHEN 'trainee' THEN 'trainees' WHEN 'trainer' THEN 'trainers' ELSE 'admins' END
        OR (n.audience='course' AND (EXISTS(SELECT 1 FROM cc_enrollment e WHERE e.course_id=n.course_id AND e.trainee_id=:uid AND e.status<>'dropped')
        OR EXISTS(SELECT 1 FROM cc_course_trainer_assignment a WHERE a.course_id=n.course_id AND a.trainer_id=:uid AND a.status='approved')))
        OR (n.audience='organization' AND EXISTS(SELECT 1 FROM cc_user_organization_assignment a WHERE a.organization_id=n.organization_id AND a.user_id=:uid AND a.status='active' AND a.starts_at<=CURRENT_TIMESTAMP AND (a.ends_at IS NULL OR a.ends_at>CURRENT_TIMESTAMP))))
        ORDER BY n.created_at DESC,n.id DESC""",
    "participation": f"""SELECT c.code,c.title,COUNT(e.id) AS enrollments,
        COALESCE(SUM(CASE WHEN e.status='completed' THEN 1 ELSE 0 END),0) AS completed,
        COALESCE(SUM(CASE WHEN e.status='at_risk' THEN 1 ELSE 0 END),0) AS at_risk,
        COALESCE(SUM(CASE WHEN e.status='dropped' THEN 1 ELSE 0 END),0) AS dropped,
        COALESCE(AVG(e.progress_percent),0) AS average_progress_percent
        FROM cc_course c LEFT JOIN cc_enrollment e ON e.course_id=c.id WHERE {COURSE_SCOPE}
        GROUP BY c.id,c.code,c.title ORDER BY c.code,c.id""",
    "feedback": f"""SELECT c.code,c.title,f.overall_rating,f.content_rating,f.trainer_rating,f.relevance_rating,f.comments,f.suggestions,f.created_at
        FROM cc_course_feedback f JOIN cc_course c ON c.id=f.course_id
        WHERE {COURSE_SCOPE} ORDER BY f.created_at DESC,f.id DESC""",
    "programs": f"""SELECT p.code AS program_code,p.title AS program,p.status AS program_status,c.code,c.title AS course,c.status,
        c.start_date,c.end_date,c.enrollment_deadline,c.capacity,
        (SELECT COUNT(*) FROM cc_course_module m WHERE m.course_id=c.id) AS modules,
        (SELECT COUNT(*) FROM cc_lesson l JOIN cc_course_module m ON m.id=l.module_id WHERE m.course_id=c.id) AS lessons
        FROM cc_training_program p JOIN cc_training_program_course pc ON pc.program_id=p.id JOIN cc_course c ON c.id=pc.course_id
        WHERE {COURSE_SCOPE} ORDER BY p.id,pc.position""",
    "learning-content": f"""SELECT c.code,c.title AS course,m.title AS module,l.title AS lesson,l.content,l.status,
        lr.title AS resource,lr.resource_type,lr.external_url
        FROM cc_course c JOIN cc_course_module m ON m.course_id=c.id LEFT JOIN cc_lesson l ON l.module_id=m.id
        LEFT JOIN cc_lesson_resource link ON link.lesson_id=l.id LEFT JOIN cc_learning_resource lr ON lr.id=link.resource_id
        WHERE {COURSE_SCOPE} ORDER BY c.id,m.position,l.position,link.position""",
    "achievements": """SELECT a.code,a.title,a.description,a.criteria,a.is_active,COUNT(ua.id) AS awarded
        FROM cc_achievement a LEFT JOIN cc_user_achievement ua ON ua.achievement_id=a.id AND ua.status='awarded'
        WHERE :role='admin' GROUP BY a.id,a.code,a.title,a.description,a.criteria,a.is_active ORDER BY a.code,a.id""",
    "framework": """SELECT 'Organization' AS record_type,o.id,o.code,o.name AS title,o.description,o.is_active,'—' AS parent
        FROM cc_organization o WHERE :role='admin'
        UNION ALL SELECT 'Department',d.id,d.code,d.name,d.description,d.is_active,o.name FROM cc_department d JOIN cc_organization o ON o.id=d.organization_id WHERE :role='admin'
        UNION ALL SELECT 'Role',r.id,r.code,r.title,r.description,r.is_active,o.name FROM cc_organizational_role r JOIN cc_organization o ON o.id=r.organization_id WHERE :role='admin'
        UNION ALL SELECT 'Subject',s.id,s.code,s.name,s.description,s.is_active,'—' FROM cc_subject s WHERE :role='admin'
        UNION ALL SELECT 'Competency',c.id,c.code,c.name,c.description,c.is_active,s.name FROM cc_competency c JOIN cc_subject s ON s.id=c.subject_id WHERE :role='admin'
        ORDER BY record_type,parent,title,id""",
    "requirements": """SELECT 'Role requirement' AS record_type,r.id,o.title AS owner,c.name AS competency,r.required_level,r.is_mandatory
        FROM cc_role_competency_requirement r JOIN cc_organizational_role o ON o.id=r.role_id JOIN cc_competency c ON c.id=r.competency_id WHERE :role='admin' AND r.is_active=true
        UNION ALL SELECT r.requirement_type,r.id,co.title,c.name,r.required_level,r.is_mandatory FROM cc_course_competency_requirement r JOIN cc_course co ON co.id=r.course_id JOIN cc_competency c ON c.id=r.competency_id WHERE :role='admin'
        UNION ALL SELECT 'Capacity need',n.id,o.name,c.name,n.required_level,true FROM cc_organizational_capacity_need n JOIN cc_organization o ON o.id=n.organization_id JOIN cc_competency c ON c.id=n.competency_id WHERE :role='admin' AND n.status='active'
        ORDER BY record_type,owner,competency,id""",
    "trainer-fit": """SELECT c.code,c.title,u.full_name AS trainer,f.eligibility_status,f.weighted_total AS trainer_fit_score,
        f.competency_score AS coverage_domain_qualification_composite,f.competency_weight AS composite_weight,f.experience_score,f.experience_weight,f.effectiveness_score,f.effectiveness_weight,
        f.availability_score,f.availability_weight,f.capacity_score,f.capacity_weight,f.explanation,f.algorithm_version,f.evaluated_at
        FROM cc_trainer_fit_evaluation f JOIN cc_course c ON c.id=f.course_id JOIN cc_user u ON u.id=f.trainer_id
        WHERE :role='admin' ORDER BY f.evaluated_at DESC,f.weighted_total DESC,f.id DESC""",
    "teams": """SELECT c.code,t.id AS proposal,t.status,t.eligibility_status,t.coverage_percent,t.weighted_total AS trainer_fit_score,
        comp.name AS competency,cov.required_level,cov.covered_level,cov.coverage_status,u.full_name AS covering_trainer,t.explanation,t.evaluated_at
        FROM cc_trainer_team_match t JOIN cc_course c ON c.id=t.course_id
        LEFT JOIN cc_trainer_team_competency_coverage cov ON cov.team_match_id=t.id
        LEFT JOIN cc_competency comp ON comp.id=cov.competency_id
        LEFT JOIN cc_trainer_team_member m ON m.id=cov.member_id AND m.team_match_id=t.id LEFT JOIN cc_user u ON u.id=m.trainer_id
        WHERE :role='admin' ORDER BY t.evaluated_at DESC,t.id,comp.name""",
    "availability": """SELECT u.full_name,a.starts_at,a.ends_at,a.status,a.timezone_name,a.notes,
        cap.max_hours,cap.allocated_hours,cap.max_courses,cap.allocated_courses,cap.max_participants,cap.allocated_participants
        FROM cc_user u JOIN cc_trainer_availability a ON a.trainer_id=u.id
        LEFT JOIN cc_trainer_capacity cap ON cap.trainer_id=u.id AND cap.starts_at<=a.starts_at AND cap.ends_at>=a.ends_at
        WHERE (:role='admin' OR (:role='trainer' AND u.id=:uid)) ORDER BY u.full_name,a.starts_at,a.id""",
    "certifications": """SELECT cert.certificate_number,u.full_name AS trainee,c.title AS training,cert.issued_at,
        issuer.full_name AS issuer,CASE WHEN cert.is_revoked THEN 'Revoked' ELSE 'Valid' END AS status,
        comp.name AS competency,cc.certified_level,e.verification_status AS evidence_status
        FROM cc_certificate cert JOIN cc_user u ON u.id=cert.trainee_id JOIN cc_course c ON c.id=cert.course_id
        LEFT JOIN cc_user issuer ON issuer.id=cert.issued_by_id LEFT JOIN cc_certificate_competency cc ON cc.certificate_id=cert.id
        LEFT JOIN cc_competency comp ON comp.id=cc.competency_id LEFT JOIN cc_competency_evidence e ON e.id=cc.evidence_id
        WHERE :role='admin' ORDER BY cert.issued_at DESC,cert.id,comp.name""",
    "paths": """SELECT p.title,p.rationale,p.status AS path_status,s.position,s.step_type,s.status AS step_status,
        COALESCE(c.title,m.title,l.title,r.title,pq.prompt,a.title,'Target unavailable') AS learning_step,s.completed_at
        FROM cc_learning_path p LEFT JOIN cc_learning_path_step s ON s.path_id=p.id AND s.user_id=p.user_id
        LEFT JOIN cc_course c ON c.id=s.course_id LEFT JOIN cc_course_module m ON m.id=s.module_id
        LEFT JOIN cc_lesson l ON l.id=s.lesson_id LEFT JOIN cc_learning_resource r ON r.id=s.resource_id
        LEFT JOIN cc_practice_question pq ON pq.id=s.practice_question_id LEFT JOIN cc_assessment a ON a.id=s.assessment_id
        WHERE p.user_id=:uid ORDER BY p.created_at DESC,p.id,s.position""",
    "practice": """SELECT pa.id AS attempt,pa.status,pa.started_at,pa.submitted_at,pa.percentage AS practice_percentage,
        comp.name AS competency,a.prompt_snapshot,a.response_text,a.marks_awarded,a.max_marks,a.feedback
        FROM cc_practice_attempt pa LEFT JOIN cc_practice_answer a ON a.attempt_id=pa.id
        LEFT JOIN cc_practice_question q ON q.id=a.question_id LEFT JOIN cc_competency comp ON comp.id=q.competency_id
        WHERE pa.user_id=:uid ORDER BY pa.started_at DESC,pa.id,a.id""",
}

QUERIES["effectiveness"] = f"""
WITH obs AS (
 SELECT o.course_id,o.user_id,o.competency_id,o.phase,o.observed_level,o.observed_at,
 ROW_NUMBER() OVER(PARTITION BY o.course_id,o.user_id,o.competency_id,o.phase ORDER BY o.observed_at DESC,o.id DESC) AS rn
 FROM cc_competency_observation o WHERE o.verification_status='verified' AND o.observer_id IS NOT NULL AND o.verified_at IS NOT NULL
 AND EXISTS(SELECT 1 FROM cc_enrollment e WHERE e.course_id=o.course_id AND e.trainee_id=o.user_id AND e.status<>'dropped')
), paired AS (
 SELECT pre.course_id,pre.user_id,AVG(post.observed_level-pre.observed_level) AS improvement
 FROM obs pre JOIN obs post ON post.course_id=pre.course_id AND post.user_id=pre.user_id AND post.competency_id=pre.competency_id
 WHERE pre.phase='pre' AND post.phase='post' AND pre.rn=1 AND post.rn=1 AND post.observed_at>pre.observed_at
 GROUP BY pre.course_id,pre.user_id
), improvement AS (SELECT course_id,COUNT(*) AS paired_trainees,AVG(improvement) AS observed_competency_improvement FROM paired GROUP BY course_id),
participants AS (SELECT course_id,COUNT(*) AS participants,SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completions FROM cc_enrollment WHERE status<>'dropped' GROUP BY course_id),
latest AS (SELECT a.course_id,r.trainee_id,r.is_passed,r.percentage,
 ROW_NUMBER() OVER(PARTITION BY r.assessment_id,r.trainee_id ORDER BY r.graded_at DESC,r.id DESC) AS rn
 FROM cc_assessment_result r JOIN cc_assessment a ON a.id=r.assessment_id JOIN cc_assessment_attempt at ON at.id=r.attempt_id
 WHERE at.status IN ('submitted','graded') AND at.submitted_at IS NOT NULL),
results AS (SELECT course_id,COUNT(*) AS assessed_pairs,AVG(CASE WHEN is_passed THEN 100.0 ELSE 0.0 END) AS pass_rate,AVG(percentage) AS average_official_score FROM latest WHERE rn=1 GROUP BY course_id),
feedback AS (SELECT course_id,COUNT(*) AS responses,AVG(overall_rating) AS rating FROM cc_course_feedback GROUP BY course_id)
SELECT c.code,c.title,COALESCE(p.participants,0) AS participants,COALESCE(p.completions,0) AS completions,
COALESCE(i.paired_trainees,0) AS verified_pre_post_pairs,i.observed_competency_improvement,
COALESCE(r.assessed_pairs,0) AS latest_official_assessment_pairs,r.pass_rate,r.average_official_score,
COALESCE(f.responses,0) AS feedback_responses,f.rating AS feedback_average
FROM cc_course c LEFT JOIN participants p ON p.course_id=c.id LEFT JOIN improvement i ON i.course_id=c.id
LEFT JOIN results r ON r.course_id=c.id LEFT JOIN feedback f ON f.course_id=c.id
WHERE {COURSE_SCOPE} ORDER BY c.code,c.id
"""


class RegistryWorkspaceState(rx.State):
    view: str = "notifications"
    headings: list[str] = []
    rows: list[list[str]] = []
    actions: list[dict[str, str]] = []
    error: str = ""
    loading: bool = False
    offset: int = 0
    has_more: bool = False
    role: str = ""

    @rx.event
    def open_view(self, view: str):
        if view not in QUERIES:
            return
        self.view = view
        self.offset = 0
        self.rows = []
        self.headings = []
        return RegistryWorkspaceState.load

    @rx.event
    async def load(self):
        self.loading = True
        self.error = ""
        self.rows = []
        self.actions = []
        yield
        try:
            auth = await self.get_state(AuthState)
            uid = read_session(auth.session_cookie)
            async with rx.asession() as session:
                actor = (
                    await session.execute(
                        text(
                            "SELECT role FROM cc_user WHERE id=:uid AND is_active=true AND approval_status='approved'"
                        ),
                        {"uid": uid},
                    )
                ).first()
                if not actor:
                    yield rx.redirect("/login")
                    return
                role = str(actor[0])
                self.role = role
                allowed = {"notifications", "paths", "practice"}
                if role == "trainer":
                    allowed.update(
                        {
                            "participation",
                            "effectiveness",
                            "feedback",
                            "programs",
                            "learning-content",
                            "availability",
                        }
                    )
                elif role == "admin":
                    allowed = set(QUERIES)
                if self.view not in allowed:
                    self.error = "This registry is not available for your role."
                    return
                if self.view == "notifications":
                    from app.services.notifications import receipts

                    await session.run_sync(lambda s: receipts(s, uid, role))
                    await session.commit()
                query = QUERIES[self.view]
                result = await session.execute(
                    text(f"{query} LIMIT 51 OFFSET :offset"),
                    {"uid": uid, "role": role, "offset": self.offset},
                )
                keys = list(result.keys())
                values = result.all()
            self.headings = [key.replace("_", " ").capitalize() for key in keys]
            self.has_more = len(values) > 50
            self.rows = [
                [
                    (
                        "Not measured"
                        if value is None
                        else f"{value:.2f}"
                        if isinstance(value, float)
                        else str(value)
                    )
                    for value in row
                ]
                for row in values[:50]
            ]
            if self.view == "notifications":
                self.actions = [
                    {"title": str(row[0]), "path": str(row[4])}
                    for row in values[:50]
                    if row[4]
                    and str(row[4]).startswith(f"/{role}/")
                    and not any(ch in str(row[4]) for ch in ("\\", "\n", "\r"))
                ]
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.error = "The registry is temporarily unavailable. Retry to load current records."
        finally:
            self.loading = False
        from app.states.capacity_operations_state import CapacityOperationsState

        operations = await self.get_state(CapacityOperationsState)
        operations.view = self.view
        yield CapacityOperationsState.load
        if self.view == "practice":
            from app.states.practice_state import PracticeState

            yield PracticeState.load

    @rx.event
    def next_page(self):
        if self.has_more:
            self.offset += 50
        return RegistryWorkspaceState.load

    @rx.event
    def previous_page(self):
        self.offset = max(0, self.offset - 50)
        return RegistryWorkspaceState.load

    @rx.event
    async def export_csv(self):
        try:
            auth = await self.get_state(AuthState)
            uid = read_session(auth.session_cookie)
            async with rx.asession() as session:
                actor = (
                    await session.execute(
                        text(
                            "SELECT id FROM cc_user WHERE id=:uid AND role='admin' AND is_active=true AND approval_status='approved'"
                        ),
                        {"uid": uid},
                    )
                ).first()
                if not actor:
                    self.error = (
                        "Only an approved administrator can export reports."
                    )
                    return
                if self.view not in QUERIES:
                    return
                result = await session.execute(
                    text(f"{QUERIES[self.view]} LIMIT 10001"),
                    {"uid": uid, "role": "admin"},
                )
                keys = list(result.keys())
                values = result.all()
            if len(values) > 10000:
                self.error = "This report exceeds the 10,000-row export limit. No truncated report was downloaded."
                return
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(keys)
            for row in values:
                cells = []
                for value in row:
                    cell = (
                        ""
                        if value is None
                        else f"{value:.2f}"
                        if isinstance(value, float)
                        else str(value)
                    )
                    if cell.lstrip().startswith(
                        ("=", "+", "-", "@", "\t", "\r")
                    ):
                        cell = f"'{cell}"
                    cells.append(cell)
                writer.writerow(cells)
            return rx.download(
                data=output.getvalue(),
                filename=f"capacity-connect-{self.view}.csv",
            )
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.error = "The report could not be exported."

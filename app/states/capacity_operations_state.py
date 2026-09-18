import reflex as rx
import datetime as dt
import json
import logging
from typing import Any
from sqlalchemy import select, func
from app import models as m
from app.security import read_session
from app.states.auth_state import AuthState
from app.services.notifications import receipts
from app.services.learning_paths import generate_path, complete_step
from app.services.evidence import refresh_evidence
from app.services.trainer_fit import recalculate, evaluate
from app.services.team_coverage import propose_team
from app.services.effectiveness import refresh_effectiveness


class CapacityOperationsState(rx.State):
    view: str = ""
    role: str = ""
    error: str = ""
    success: str = ""
    busy: bool = False
    options: list[dict[str, str]] = []
    notices: list[dict[str, str]] = []
    steps: list[dict[str, str]] = []
    fits: list[dict[str, str]] = []
    drafts: list[dict[str, str]] = []

    async def _actor(self) -> tuple[int, str]:
        auth = await self.get_state(AuthState)
        uid = read_session(auth.session_cookie)
        async with rx.asession() as session:
            actor = (
                await session.execute(
                    select(m.User.id, m.User.role).where(
                        m.User.id == uid,
                        m.User.is_active.is_(True),
                        m.User.approval_status == "approved",
                    )
                )
            ).first()
        if not actor:
            raise ValueError("Approved account access is required.")
        return actor[0], actor[1]

    @rx.event
    async def open_view(self, view: str):
        self.view = view
        self.error = ""
        self.success = ""
        yield CapacityOperationsState.load

    @rx.event
    async def load(self):
        self.options = []
        self.notices = []
        self.steps = []
        self.fits = []
        self.drafts = []
        try:
            uid, role = await self._actor()
            self.role = role
            async with rx.asession() as session:
                if self.view == "notifications":
                    self.notices = await session.run_sync(
                        lambda s: receipts(s, uid, role)
                    )
                    await session.commit()
                if self.view == "paths":
                    rows = (
                        await session.execute(
                            select(
                                m.LearningPathStep.id,
                                m.LearningPath.title,
                                m.LearningPathStep.position,
                                m.LearningPathStep.step_type,
                                m.LearningPathStep.status,
                                m.LearningPathStep.course_id,
                            )
                            .join(
                                m.LearningPath,
                                m.LearningPath.id == m.LearningPathStep.path_id,
                            )
                            .where(
                                m.LearningPath.user_id == uid,
                                m.LearningPathStep.user_id == uid,
                            )
                            .order_by(
                                m.LearningPath.id.desc(),
                                m.LearningPathStep.position,
                            )
                            .limit(100)
                        )
                    ).all()
                    self.steps = [
                        {
                            "id": str(r[0]),
                            "title": r[1],
                            "position": str(r[2]),
                            "kind": r[3],
                            "status": r[4],
                            "course": str(r[5] or ""),
                        }
                        for r in rows
                    ]
                if role in {"trainer", "admin"}:
                    scope = select(m.Course)
                    if role == "trainer":
                        scope = scope.join(m.CourseTrainerAssignment).where(
                            m.CourseTrainerAssignment.trainer_id == uid,
                            m.CourseTrainerAssignment.status == "approved",
                        )
                    courses = (
                        await session.scalars(
                            scope.order_by(m.Course.title).limit(100)
                        )
                    ).all()
                    self.options = [
                        {
                            "kind": "course",
                            "id": str(c.id),
                            "label": f"{c.code} · {c.title}",
                        }
                        for c in courses
                    ]
                    drafts = (
                        await session.scalars(
                            select(m.PracticeQuestion)
                            .where(
                                m.PracticeQuestion.course_id.in_(
                                    [c.id for c in courses]
                                ),
                                m.PracticeQuestion.status == "draft",
                            )
                            .order_by(m.PracticeQuestion.id.desc())
                            .limit(30)
                        )
                    ).all()
                    self.drafts = [
                        {
                            "id": str(q.id),
                            "prompt": q.prompt,
                            "course": str(q.course_id),
                        }
                        for q in drafts
                    ]
                    if role == "admin":
                        for model, kind, title in [
                            (
                                m.Organization,
                                "organization",
                                m.Organization.name,
                            ),
                            (m.Subject, "subject", m.Subject.name),
                            (m.Competency, "competency", m.Competency.name),
                            (
                                m.OrganizationalRole,
                                "role",
                                m.OrganizationalRole.title,
                            ),
                            (m.Department, "department", m.Department.name),
                        ]:
                            rows = (
                                await session.execute(
                                    select(model.id, title)
                                    .order_by(model.id)
                                    .limit(100)
                                )
                            ).all()
                            self.options.extend(
                                {"kind": kind, "id": str(r[0]), "label": r[1]}
                                for r in rows
                            )
                        evaluations = (
                            await session.execute(
                                select(
                                    m.TrainerFitEvaluation,
                                    m.User.full_name,
                                    m.Course.title,
                                )
                                .join(
                                    m.User,
                                    m.User.id
                                    == m.TrainerFitEvaluation.trainer_id,
                                )
                                .join(
                                    m.Course,
                                    m.Course.id
                                    == m.TrainerFitEvaluation.course_id,
                                )
                                .where(
                                    m.TrainerFitEvaluation.algorithm_version
                                    == "sih-five-factor-v2"
                                )
                                .order_by(
                                    m.TrainerFitEvaluation.evaluated_at.desc(),
                                    m.TrainerFitEvaluation.weighted_total.desc(),
                                )
                                .limit(50)
                            )
                        ).all()
                        self.fits = [
                            {
                                "id": str(e.id),
                                "trainer": name,
                                "course": course,
                                "status": e.eligibility_status,
                                "score": f"{e.weighted_total:.2f}",
                                "detail": json.dumps(
                                    json.loads(e.explanation), indent=2
                                ),
                            }
                            for e, name, course in evaluations
                        ]
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.error = (
                "Could not load operational controls. Refresh to retry."
            )

    @rx.event
    async def act(self, data: dict[str, Any]):
        if self.busy:
            return
        self.busy = True
        self.error = ""
        self.success = ""
        yield
        try:
            uid, role = await self._actor()
            async with rx.asession() as session:
                self.success = await session.run_sync(
                    lambda s: self._mutate(s, uid, role, data)
                )
                await session.commit()
            yield CapacityOperationsState.load
            from app.states.registry_workspace_state import (
                RegistryWorkspaceState,
            )

            yield RegistryWorkspaceState.load
        except ValueError as e:
            logging.exception(f"Error: {e}")
            self.error = str(e)
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.error = "Nothing was saved. Check unique codes, parent records and required fields, then retry."
        finally:
            self.busy = False

    @rx.event
    async def mark_read(self, notification_id: int):
        yield CapacityOperationsState.act(
            {"action": "read", "id": str(notification_id)}
        )

    @rx.event
    async def finish_step(self, step_id: int):
        yield CapacityOperationsState.act(
            {"action": "step", "id": str(step_id)}
        )

    @rx.event
    async def generate_learning(self, competency_id: int):
        yield CapacityOperationsState.act(
            {"action": "path", "id": str(competency_id)}
        )

    @rx.event
    async def assign_fit(self, evaluation_id: int):
        yield CapacityOperationsState.act(
            {"action": "assign", "id": str(evaluation_id)}
        )

    def _mutate(
        self, session, uid: int, role: str, data: dict[str, Any]
    ) -> str:
        actor = session.scalar(
            select(m.User)
            .where(
                m.User.id == uid,
                m.User.role == role,
                m.User.is_active.is_(True),
                m.User.approval_status == "approved",
            )
            .with_for_update()
        )
        if not actor:
            raise ValueError("Your access changed; sign in again.")
        action = str(data.get("action", ""))
        allowed = {"read"}
        if role == "trainee":
            allowed |= {"path", "step"}
        if role == "trainer":
            allowed |= {"availability", "training", "lesson", "review_practice"}
        if role == "admin":
            allowed |= {
                "framework",
                "requirement",
                "fit",
                "team",
                "assign",
                "notice",
                "achievement",
                "lesson",
                "training",
                "effectiveness",
                "review_practice",
            }
        if action not in allowed:
            raise ValueError("This action is not permitted for your role.")
        identifier = int(data.get("id", 0) or 0)
        title = str(data.get("title", "")).strip()[:200]
        description = str(data.get("description", "")).strip()[:6000]
        code = str(data.get("code", "")).strip()[:40]
        now = dt.datetime.now(dt.UTC)
        if action == "read":
            receipts(session, uid, role, identifier)
            return "Recipient receipts updated."
        if action == "path":
            refresh_evidence(session, uid)
            path = generate_path(session, uid, identifier)
            return f"Pathway started: {path.title}. Open Learning Paths to continue."
        if action == "step":
            complete_step(session, uid, identifier)
            return "Eligible learning step completed. Proficiency remains evidence-only."
        if action == "availability":
            start = dt.datetime.fromisoformat(
                str(data.get("start", ""))
            ).replace(tzinfo=dt.UTC)
            end = dt.datetime.fromisoformat(str(data.get("end", ""))).replace(
                tzinfo=dt.UTC
            )
            status = str(data.get("status", ""))
            hours = float(data.get("hours", 0))
            slots = int(data.get("slots", 0))
            participants = int(data.get("participants", 0))
            if (
                end <= start
                or status not in {"available", "unavailable", "tentative"}
                or not 0 <= hours <= 10000
                or not 0 <= slots <= 1000
                or not 0 <= participants <= 100000
            ):
                raise ValueError(
                    "Use chronological UTC dates and nonnegative bounded capacities."
                )
            availability = session.scalar(
                select(m.TrainerAvailability)
                .where(
                    m.TrainerAvailability.trainer_id == uid,
                    m.TrainerAvailability.starts_at == start,
                    m.TrainerAvailability.ends_at == end,
                )
                .with_for_update()
            )
            if not availability:
                availability = m.TrainerAvailability(
                    trainer_id=uid, starts_at=start, ends_at=end
                )
                session.add(availability)
            availability.status = status
            availability.notes = description
            capacity = session.scalar(
                select(m.TrainerCapacity)
                .where(
                    m.TrainerCapacity.trainer_id == uid,
                    m.TrainerCapacity.starts_at == start,
                    m.TrainerCapacity.ends_at == end,
                )
                .with_for_update()
            )
            if not capacity:
                capacity = m.TrainerCapacity(
                    trainer_id=uid, starts_at=start, ends_at=end
                )
                session.add(capacity)
            if (
                capacity.allocated_hours > hours
                or capacity.allocated_courses > slots
                or capacity.allocated_participants > participants
            ):
                raise ValueError(
                    "Capacity cannot be lowered below recorded allocations."
                )
            (
                capacity.max_hours,
                capacity.max_courses,
                capacity.max_participants,
            ) = hours, slots, participants
            return "Your availability and capacity window has been saved. Matching uses current assignments as well as recorded allocations."
        if action == "framework":
            kind = str(data.get("kind", ""))
            models = {
                "organization": m.Organization,
                "department": m.Department,
                "subject": m.Subject,
                "competency": m.Competency,
                "role": m.OrganizationalRole,
            }
            model = models.get(kind)
            if not model or not code or not title:
                raise ValueError(
                    "Choose a framework type and provide a stable code and title."
                )
            parent = int(data.get("parent", 0) or 0)
            values = {
                "code": code,
                "description": description,
                "is_active": str(data.get("active", "true")) == "true",
                "title" if kind == "role" else "name": title,
            }
            if kind in {"department", "role"}:
                if not session.scalar(
                    select(m.Organization.id).where(
                        m.Organization.id == parent,
                        m.Organization.is_active.is_(True),
                    )
                ):
                    raise ValueError("Select an active parent organization.")
                values["organization_id"] = parent
            if kind == "competency":
                if not session.scalar(
                    select(m.Subject.id).where(
                        m.Subject.id == parent, m.Subject.is_active.is_(True)
                    )
                ):
                    raise ValueError("Select an active parent subject.")
                values["subject_id"] = parent
            row = session.get(model, identifier) if identifier else None
            if identifier and not row:
                raise ValueError("Framework record not found.")
            if row:
                if (
                    kind in {"department", "role"}
                    and row.organization_id != parent
                ):
                    raise ValueError(
                        "Existing organizational records cannot be moved between organizations."
                    )
                for key, value in values.items():
                    setattr(row, key, value)
            else:
                session.add(model(**values))
            return "Framework record saved. Existing evidence and legacy records are preserved."
        if action == "requirement":
            kind = str(data.get("kind", ""))
            owner = int(data.get("owner", 0))
            cid = int(data.get("competency", 0))
            level = int(data.get("level", 0))
            if not 1 <= level <= 5 or not session.scalar(
                select(m.Competency.id).where(
                    m.Competency.id == cid, m.Competency.is_active.is_(True)
                )
            ):
                raise ValueError(
                    "Choose an active competency and a target from 1 to 5."
                )
            if kind == "role":
                if not session.get(m.OrganizationalRole, owner):
                    raise ValueError("Role does not exist.")
                row = session.scalar(
                    select(m.RoleCompetencyRequirement).where(
                        m.RoleCompetencyRequirement.role_id == owner,
                        m.RoleCompetencyRequirement.competency_id == cid,
                    )
                )
                if not row:
                    row = m.RoleCompetencyRequirement(
                        role_id=owner, competency_id=cid
                    )
                    session.add(row)
            elif kind in {"outcome", "trainer", "prerequisite"}:
                if not session.get(m.Course, owner):
                    raise ValueError("Course does not exist.")
                row = session.scalar(
                    select(m.CourseCompetencyRequirement).where(
                        m.CourseCompetencyRequirement.course_id == owner,
                        m.CourseCompetencyRequirement.competency_id == cid,
                        m.CourseCompetencyRequirement.requirement_type == kind,
                    )
                )
                if not row:
                    row = m.CourseCompetencyRequirement(
                        course_id=owner,
                        competency_id=cid,
                        requirement_type=kind,
                    )
                    session.add(row)
            elif kind == "need":
                if not code or not session.get(m.Organization, owner):
                    raise ValueError(
                        "Provide a capacity need code and valid organization."
                    )
                row = session.scalar(
                    select(m.OrganizationalCapacityNeed).where(
                        m.OrganizationalCapacityNeed.organization_id == owner,
                        m.OrganizationalCapacityNeed.code == code,
                    )
                )
                if not row:
                    row = m.OrganizationalCapacityNeed(
                        organization_id=owner,
                        competency_id=cid,
                        code=code,
                        status="active",
                    )
                    session.add(row)
                row.competency_id = cid
            else:
                raise ValueError("Choose a supported requirement type.")
            row.required_level = level
            return "Requirement saved. Refresh competency evidence to recalculate gaps."
        if action in {"fit", "team"}:
            cid = int(data.get("course", 0))
            start = dt.datetime.combine(
                dt.date.fromisoformat(str(data.get("start", ""))),
                dt.time.min,
                tzinfo=dt.UTC,
            )
            end = dt.datetime.combine(
                dt.date.fromisoformat(str(data.get("end", ""))),
                dt.time.max,
                tzinfo=dt.UTC,
            )
            evaluations = recalculate(
                session,
                cid,
                start,
                end,
                str(data.get("qualification", "false")) == "true",
            )
            if action == "team":
                team = propose_team(session, cid, evaluations)
                return f"Team proposal saved: {team.coverage_percent:.1f}% verified coverage. Review uncovered requirements before assignment."
            return f"{len(evaluations)} trainer evaluations saved with exact factors and eligibility failures."
        if action == "assign":
            original = session.get(m.TrainerFitEvaluation, identifier)
            if (
                not original
                or original.algorithm_version != "sih-five-factor-v2"
            ):
                raise ValueError("Choose a current five-factor evaluation.")
            details = json.loads(original.explanation)
            trainer = session.scalar(
                select(m.User)
                .where(m.User.id == original.trainer_id)
                .with_for_update()
            )
            course = session.get(m.Course, original.course_id)
            evaluation, coverage, failures = evaluate(
                session,
                course,
                trainer,
                dt.datetime.fromisoformat(details["start"]),
                dt.datetime.fromisoformat(details["end"]),
                details.get("require_verified_qualification", False),
            )
            if failures:
                raise ValueError(
                    "Assignment blocked: current eligibility or capacity checks failed. Recalculate to inspect failures."
                )
            assignment = session.scalar(
                select(m.CourseTrainerAssignment).where(
                    m.CourseTrainerAssignment.course_id == course.id,
                    m.CourseTrainerAssignment.trainer_id == trainer.id,
                )
            )
            if not assignment:
                assignment = m.CourseTrainerAssignment(
                    course_id=course.id, trainer_id=trainer.id
                )
                session.add(assignment)
            assignment.status = "approved"
            assignment.match_score = evaluation.weighted_total
            assignment.assigned_by_id = uid
            assignment.notes = f"Revalidated five-factor evaluation {evaluation.id}; date and capacity gates passed."
            return "Trainer assignment saved after current eligibility and capacity revalidation."
        if action == "effectiveness":
            course_id = int(data.get("course", 0))
            if not session.get(m.Course, course_id):
                raise ValueError("Choose a course.")
            snapshot = refresh_effectiveness(session, course_id)
            return f"Effectiveness snapshot saved: {snapshot.observation_pairs} verified paired learners. Unmeasured deltas remain blank."
        if action == "notice":
            audience = str(data.get("audience", "all"))
            if (
                not title
                or not description
                or audience not in {"all", "trainees", "trainers", "admins"}
            ):
                raise ValueError(
                    "A title, body and valid audience are required."
                )
            session.add(
                m.Notification(
                    title=title,
                    body=description,
                    audience=audience,
                    status="published",
                )
            )
            return "Notification published. Recipient receipts are created when eligible users open notifications."
        if action == "achievement":
            criteria = str(data.get("criteria", "")).strip()[:4000]
            if not title or not code or not criteria:
                raise ValueError(
                    "Achievement code, title and explicit award criteria are required."
                )
            session.add(
                m.Achievement(
                    code=code,
                    title=title,
                    description=description,
                    criteria=criteria,
                )
            )
            return "Achievement definition published. No awards or mastery claims were fabricated."
        if action == "training":
            if not title or not code:
                raise ValueError("A unique course code and title are required.")
            course = m.Course(
                code=code,
                title=title,
                summary=description,
                created_by_id=uid,
                status="draft",
            )
            session.add(course)
            session.flush()
            session.add(
                m.CourseTrainerAssignment(
                    course_id=course.id,
                    trainer_id=uid,
                    assigned_by_id=uid,
                    status="approved",
                )
            ) if role == "trainer" else None
            program = m.TrainingProgram(
                code=f"PROGRAM-{course.id}",
                title=title,
                description=description,
                status="draft",
            )
            session.add(program)
            session.flush()
            session.add(
                m.TrainingProgramCourse(
                    program_id=program.id, course_id=course.id, position=1
                )
            )
            module = m.CourseModule(
                course_id=course.id,
                title=str(data.get("module", "Introduction")).strip()[:200]
                or "Introduction",
                position=1,
            )
            session.add(module)
            session.flush()
            session.add(
                m.Lesson(
                    module_id=module.id,
                    title=str(
                        data.get("lesson", "Learning objectives")
                    ).strip()[:200]
                    or "Learning objectives",
                    content=str(data.get("content", ""))[:12000],
                    position=1,
                )
            )
            return "Draft program, course, module and lesson created. Course lifecycle review and publishing remain in Courses."
        if action in {"lesson", "review_practice"}:
            course_id = int(data.get("course", 0))
            course = session.get(m.Course, course_id)
            scoped = role == "admin" or session.scalar(
                select(m.CourseTrainerAssignment.id)
                .where(
                    m.CourseTrainerAssignment.course_id == course_id,
                    m.CourseTrainerAssignment.trainer_id == uid,
                    m.CourseTrainerAssignment.status == "approved",
                )
                .limit(1)
            )
            if not course or not scoped:
                raise ValueError(
                    "Only approved assigned trainers or administrators can author this course."
                )
            if action == "review_practice":
                question = session.get(m.PracticeQuestion, identifier)
                correct = str(data.get("correct", "")).strip()[:1000]
                incorrect = str(data.get("incorrect", "")).strip()[:1000]
                if (
                    not question
                    or question.course_id != course_id
                    or question.status != "draft"
                    or not title
                    or not description
                    or not correct
                    or not incorrect
                    or correct == incorrect
                ):
                    raise ValueError(
                        "Choose a draft in your course and supply a reviewed prompt, explanation and two distinct options."
                    )
                (
                    question.prompt,
                    question.explanation,
                    question.question_type,
                    question.status,
                ) = title, description, "single_choice", "published"
                session.add_all(
                    [
                        m.PracticeQuestionOption(
                            question_id=question.id,
                            position=1,
                            text=correct,
                            is_correct=True,
                        ),
                        m.PracticeQuestionOption(
                            question_id=question.id, position=2, text=incorrect
                        ),
                    ]
                )
                return "Reviewed formative question published to the practice bank only."
            if not title or not description:
                raise ValueError("Lesson title and content are required.")
            position = (
                session.scalar(
                    select(func.max(m.CourseModule.position)).where(
                        m.CourseModule.course_id == course_id
                    )
                )
                or 0
            ) + 1
            module = m.CourseModule(
                course_id=course_id,
                title=str(data.get("module", "")).strip()[:200] or title,
                position=position,
                status="published" if role == "admin" else "draft",
            )
            session.add(module)
            session.flush()
            session.add(
                m.Lesson(
                    module_id=module.id,
                    title=title,
                    content=description,
                    position=1,
                    status=module.status,
                )
            )
            return (
                "Learning content published."
                if role == "admin"
                else "Draft module and lesson saved for curriculum review."
            )
        raise ValueError("Unsupported operation.")

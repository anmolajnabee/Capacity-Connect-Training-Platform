import reflex as rx
import datetime as dt
import logging
from typing import Any
from sqlalchemy import select
from app import models as m
from app.security import read_session
from app.states.auth_state import AuthState
from app.services.capacity_ai import ACTIONS, answer, sanitize


class CapacityAIState(rx.State):
    opened: bool = False
    busy: bool = False
    error: str = ""
    response: str = ""
    model_label: str = ""
    courses: list[dict[str, str]] = []
    sources: list[dict[str, str]] = []
    last_request: float = 0.0
    _course_id: int = 0
    _action: str = "Explain Concept"

    @rx.event
    async def toggle(self):
        self.opened = not self.opened
        if not self.opened:
            return
        self.error = ""
        try:
            auth = await self.get_state(AuthState)
            uid = read_session(auth.session_cookie)
            async with rx.asession() as session:
                rows = (
                    await session.execute(
                        select(m.Course.id, m.Course.title)
                        .join(m.Enrollment)
                        .join(m.User, m.User.id == m.Enrollment.trainee_id)
                        .where(
                            m.User.id == uid,
                            m.User.is_active.is_(True),
                            m.User.approval_status == "approved",
                            m.User.role == "trainee",
                            m.Enrollment.status != "dropped",
                            m.Course.status == "published",
                        )
                        .order_by(m.Course.title)
                        .limit(100)
                    )
                ).all()
            self.courses = [{"id": str(r[0]), "title": r[1]} for r in rows]
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.error = "Authorized learning contexts could not be loaded."

    @rx.event
    def request(self, data: dict[str, Any]):
        if self.busy:
            return
        action = str(data.get("action", ""))
        course = str(data.get("course", ""))
        if action not in ACTIONS or not course.isdigit():
            self.error = (
                "Choose an enrolled course and a supported learning action."
            )
            return
        now = dt.datetime.now(dt.UTC).timestamp()
        if now - self.last_request < 10:
            self.error = "Please wait a few seconds before the next request."
            return
        self.last_request = now
        self._action = action
        self._course_id = int(course)
        self.busy = True
        self.error = ""
        self.response = ""
        self.sources = []
        return CapacityAIState.generate

    @rx.event(background=True)
    async def generate(self):
        async with self:
            auth = await self.get_state(AuthState)
            cookie = str(auth.session_cookie)
            action = self._action
            course_id = self._course_id
        try:
            uid = read_session(cookie)
            async with rx.asession() as session:
                course = await session.scalar(
                    select(m.Course)
                    .join(m.Enrollment)
                    .join(m.User, m.User.id == m.Enrollment.trainee_id)
                    .where(
                        m.Course.id == course_id,
                        m.Course.status == "published",
                        m.Enrollment.trainee_id == uid,
                        m.Enrollment.status != "dropped",
                        m.User.role == "trainee",
                        m.User.is_active.is_(True),
                        m.User.approval_status == "approved",
                    )
                )
                if not course:
                    raise ValueError(
                        "This course is outside your authorized learning context."
                    )
                resources = (
                    await session.scalars(
                        select(m.LearningResource)
                        .where(
                            m.LearningResource.course_id == course.id,
                            m.LearningResource.is_published.is_(True),
                        )
                        .order_by(m.LearningResource.sort_order)
                        .limit(5)
                    )
                ).all()
                sources = [
                    {
                        "id": str(r.id),
                        "title": sanitize(r.title),
                        "module": sanitize(r.module_name),
                        "course": sanitize(course.title),
                        "excerpt": sanitize(r.description)[:2000],
                    }
                    for r in resources
                ]
                comps = (
                    await session.execute(
                        select(
                            m.Competency.id,
                            m.Competency.name,
                            m.CompetencyGap.required_level,
                            m.CompetencyGap.baseline_level,
                        )
                        .join(
                            m.CourseCompetencyRequirement,
                            m.CourseCompetencyRequirement.competency_id
                            == m.Competency.id,
                        )
                        .outerjoin(
                            m.CompetencyGap,
                            (m.CompetencyGap.competency_id == m.Competency.id)
                            & (m.CompetencyGap.user_id == uid),
                        )
                        .where(
                            m.CourseCompetencyRequirement.course_id
                            == course.id,
                            m.CourseCompetencyRequirement.requirement_type
                            == "outcome",
                        )
                        .limit(20)
                    )
                ).all()
                practice = (
                    await session.scalars(
                        select(m.PracticeQuestion.prompt)
                        .where(
                            m.PracticeQuestion.competency_id.in_(
                                [c[0] for c in comps]
                            ),
                            m.PracticeQuestion.status == "published",
                            (
                                m.PracticeQuestion.course_id.is_(None)
                                | (m.PracticeQuestion.course_id == course.id)
                            ),
                        )
                        .limit(3)
                    )
                ).all()
                results = (
                    await session.execute(
                        select(
                            m.Assessment.title, m.AssessmentResult.percentage
                        )
                        .join(m.AssessmentResult)
                        .where(
                            m.Assessment.course_id == course.id,
                            m.AssessmentResult.trainee_id == uid,
                        )
                        .order_by(m.AssessmentResult.graded_at.desc())
                        .limit(3)
                    )
                ).all()
                step = await session.scalar(
                    select(m.LearningPath.title)
                    .where(
                        m.LearningPath.user_id == uid,
                        m.LearningPath.status == "active",
                    )
                    .order_by(m.LearningPath.id.desc())
                    .limit(1)
                )
                context = f"Course: {course.title}\nSummary: {course.summary[:1200]}\nCompetencies and measured gaps: {list(comps)}\nRecent official percentages (not answer keys): {list(results)}\nApproved resource excerpts: {sources}\nPractice bank: {practice}\nNext pathway: {step or 'None recorded'}"
                competency_id = comps[0][0] if comps else None
            response, model = await answer(
                action, context, sources, list(practice), step or ""
            )
            async with rx.asession() as session:
                allowed = await session.scalar(
                    select(m.User.id)
                    .join(m.Enrollment, m.Enrollment.trainee_id == m.User.id)
                    .where(
                        m.User.id == uid,
                        m.User.role == "trainee",
                        m.User.is_active.is_(True),
                        m.User.approval_status == "approved",
                        m.Enrollment.course_id == course_id,
                        m.Enrollment.status != "dropped",
                    )
                )
                if not allowed:
                    raise ValueError(
                        "Your learning access changed. Please refresh."
                    )
                conversation = m.CapacityAIConversation(
                    user_id=uid, title=f"{action} — {course.title}"[:200]
                )
                session.add(conversation)
                await session.flush()
                message = m.CapacityAIMessage(
                    conversation_id=conversation.id,
                    user_action=ACTIONS[action],
                    request_text=action,
                    response_text=response,
                    model=model,
                    grounded=bool(sources),
                    status="completed",
                    course_id=course_id,
                    competency_id=competency_id,
                    responded_at=dt.datetime.now(dt.UTC),
                )
                session.add(message)
                await session.flush()
                for i, source in enumerate(sources, 1):
                    session.add(
                        m.CapacityAIMessageSource(
                            message_id=message.id,
                            position=i,
                            source_type="resource",
                            source_identifier=source["id"],
                            title=source["title"][:220],
                            page_locator=source["module"][:100],
                            excerpt=source["excerpt"],
                        )
                    )
                if (
                    action == "Generate Practice Questions"
                    and model != "database-fallback"
                    and competency_id
                ):
                    session.add(
                        m.PracticeQuestion(
                            competency_id=competency_id,
                            course_id=course_id,
                            prompt=response[:8000],
                            explanation="CAPACITY AI draft: trainer must validate question, options and explanation before publication.",
                            question_type="short_answer",
                            status="draft",
                        )
                    )
                    response = f"{response}\n\nSaved as a practice-only draft for trainer review. Not published and not an official assessment."
                    message.response_text = response[:24000]
                await session.commit()
            async with self:
                self.response = response
                self.model_label = (
                    "Database-grounded fallback"
                    if model == "database-fallback"
                    else "CAPACITY AI · advisory generation"
                )
                self.sources = sources
        except Exception as e:
            logging.exception(
                f"Error: assistant request ({type(e).__name__})", exc_info=False
            )
            async with self:
                self.error = "This learning context is unavailable or the response could not be saved. Refresh and try again."
        finally:
            async with self:
                self.busy = False

import reflex as rx
import datetime as dt
import logging
from typing import Any, TypedDict
from sqlalchemy import select, delete, or_
from app import models as m
from app.security import read_session
from app.states.auth_state import AuthState


class PracticeItem(TypedDict):
    id: str
    prompt: str
    selected: str
    feedback: str
    options: list[dict[str, str]]


class PracticeState(rx.State):
    items: list[PracticeItem] = []
    attempt_id: int = 0
    status: str = ""
    message: str = ""
    busy: bool = False

    async def _uid(self) -> int:
        auth = await self.get_state(AuthState)
        uid = read_session(auth.session_cookie)
        async with rx.asession() as session:
            actor = await session.scalar(
                select(m.User.id).where(
                    m.User.id == uid,
                    m.User.role == "trainee",
                    m.User.is_active.is_(True),
                    m.User.approval_status == "approved",
                )
            )
        if not actor:
            raise ValueError("Approved trainee access is required.")
        return actor

    @rx.event
    async def load(self):
        self.items = []
        self.attempt_id = 0
        self.status = ""
        try:
            uid = await self._uid()
            async with rx.asession() as session:
                attempt = await session.scalar(
                    select(m.PracticeAttempt)
                    .where(m.PracticeAttempt.user_id == uid)
                    .order_by(m.PracticeAttempt.id.desc())
                    .limit(1)
                )
                if not attempt:
                    return
                self.attempt_id = attempt.id
                self.status = attempt.status
                answers = (
                    await session.scalars(
                        select(m.PracticeAnswer)
                        .where(m.PracticeAnswer.attempt_id == attempt.id)
                        .order_by(m.PracticeAnswer.id)
                    )
                ).all()
                qids = [a.question_id for a in answers]
                options = (
                    await session.scalars(
                        select(m.PracticeQuestionOption)
                        .where(m.PracticeQuestionOption.question_id.in_(qids))
                        .order_by(m.PracticeQuestionOption.position)
                    )
                ).all()
                selections = dict(
                    (
                        await session.execute(
                            select(
                                m.PracticeAnswerSelection.answer_id,
                                m.PracticeAnswerSelection.option_id,
                            ).where(
                                m.PracticeAnswerSelection.answer_id.in_(
                                    [a.id for a in answers]
                                )
                            )
                        )
                    ).all()
                )
                self.items = [
                    {
                        "id": str(a.id),
                        "prompt": a.prompt_snapshot,
                        "selected": str(selections.get(a.id, "")),
                        "feedback": a.feedback
                        if attempt.status == "graded"
                        else "",
                        "options": [
                            {"id": str(o.id), "text": o.text}
                            for o in options
                            if o.question_id == a.question_id
                        ],
                    }
                    for a in answers
                ]
                if attempt.status == "graded":
                    self.message = f"Practice only: {attempt.percentage or 0:.1f}%. Official results and competency levels are unchanged."
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.message = "Practice could not be loaded. Approved trainee access is required."

    @rx.event
    async def start(self):
        if self.busy:
            return
        self.busy = True
        self.message = ""
        yield
        try:
            uid = await self._uid()
            async with rx.asession() as session:
                await session.scalar(
                    select(m.User).where(m.User.id == uid).with_for_update()
                )
                existing = await session.scalar(
                    select(m.PracticeAttempt.id)
                    .where(
                        m.PracticeAttempt.user_id == uid,
                        m.PracticeAttempt.status == "in_progress",
                    )
                    .limit(1)
                )
                if not existing:
                    gaps = select(m.CompetencyGap.competency_id).where(
                        m.CompetencyGap.user_id == uid,
                        m.CompetencyGap.status.in_(
                            ["identified", "in_progress"]
                        ),
                    )
                    enrolled = select(m.Enrollment.course_id).where(
                        m.Enrollment.trainee_id == uid,
                        m.Enrollment.status != "dropped",
                    )
                    questions = (
                        await session.scalars(
                            select(m.PracticeQuestion)
                            .where(
                                m.PracticeQuestion.status == "published",
                                m.PracticeQuestion.question_type
                                == "single_choice",
                                m.PracticeQuestion.competency_id.in_(gaps),
                                or_(
                                    m.PracticeQuestion.course_id.is_(None),
                                    m.PracticeQuestion.course_id.in_(enrolled),
                                ),
                            )
                            .order_by(
                                m.PracticeQuestion.difficulty_level,
                                m.PracticeQuestion.id,
                            )
                            .limit(5)
                        )
                    ).all()
                    if not questions:
                        raise ValueError(
                            "No published single-choice practice questions match your open gaps. A trainer must publish reviewed practice first."
                        )
                    attempt = m.PracticeAttempt(
                        user_id=uid,
                        max_marks=sum(q.max_marks for q in questions),
                    )
                    session.add(attempt)
                    await session.flush()
                    for q in questions:
                        session.add(
                            m.PracticeAnswer(
                                attempt_id=attempt.id,
                                question_id=q.id,
                                prompt_snapshot=q.prompt,
                                rubric_snapshot=q.explanation,
                                max_marks=q.max_marks,
                            )
                        )
                    await session.commit()
            yield PracticeState.load
        except ValueError as e:
            logging.exception(f"Error: {e}")
            self.message = str(e)
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.message = "Practice could not be started."
        finally:
            self.busy = False

    @rx.event
    async def save(self, data: dict[str, Any]):
        if self.busy:
            return
        self.busy = True
        yield
        try:
            uid = await self._uid()
            async with rx.asession() as session:
                attempt = await session.scalar(
                    select(m.PracticeAttempt)
                    .where(
                        m.PracticeAttempt.id == self.attempt_id,
                        m.PracticeAttempt.user_id == uid,
                    )
                    .with_for_update()
                )
                if not attempt or attempt.status != "in_progress":
                    raise ValueError(
                        "Only your active practice attempt can be answered."
                    )
                answers = (
                    await session.scalars(
                        select(m.PracticeAnswer).where(
                            m.PracticeAnswer.attempt_id == attempt.id
                        )
                    )
                ).all()
                options = (
                    await session.scalars(
                        select(m.PracticeQuestionOption).where(
                            m.PracticeQuestionOption.question_id.in_(
                                [a.question_id for a in answers]
                            )
                        )
                    )
                ).all()
                score = 0.0
                for answer in answers:
                    selected = int(data.get(str(answer.id), 0) or 0)
                    valid = next(
                        (
                            o
                            for o in options
                            if o.id == selected
                            and o.question_id == answer.question_id
                        ),
                        None,
                    )
                    if not valid:
                        raise ValueError(
                            "Choose one valid option for every practice question."
                        )
                    await session.execute(
                        delete(m.PracticeAnswerSelection).where(
                            m.PracticeAnswerSelection.answer_id == answer.id
                        )
                    )
                    session.add(
                        m.PracticeAnswerSelection(
                            answer_id=answer.id,
                            question_id=answer.question_id,
                            option_id=valid.id,
                        )
                    )
                    answer.response_text = valid.text
                    answer.marks_awarded = (
                        answer.max_marks if valid.is_correct else 0.0
                    )
                    answer.feedback = f"{'Correct.' if valid.is_correct else 'Review this concept.'} {answer.rubric_snapshot}"
                    score += answer.marks_awarded
                attempt.status = "graded"
                attempt.submitted_at = dt.datetime.now(dt.UTC)
                attempt.graded_at = attempt.submitted_at
                attempt.marks_awarded = score
                attempt.percentage = (
                    100 * score / attempt.max_marks if attempt.max_marks else 0
                )
                await session.commit()
            yield PracticeState.load
        except ValueError as e:
            logging.exception(f"Error: {e}")
            self.message = str(e)
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.message = "Answers were not saved. Please retry."
        finally:
            self.busy = False

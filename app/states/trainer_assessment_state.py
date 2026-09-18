"""Assessment studio: MCQ authoring, publishing and monitoring."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentResult,
    AssessmentStatus,
    Course,
    Enrollment,
    Question,
    QuestionOption,
    User,
)
from app.states.trainer_state import trainer_course_ids, trainer_guard

logger = logging.getLogger(__name__)

OPTION_LABELS: list[str] = ["A", "B", "C", "D"]


class AssessmentRow(TypedDict):
    id: int
    title: str
    course_id: int
    course: str
    course_code: str
    status: str
    questions: int
    total_marks: float
    passing_marks: float
    time_limit: int
    max_attempts: int
    deadline: str
    attempts: int
    submissions: int
    participation: int
    pass_rate: int
    average: int
    is_owner: bool


class OptionRow(TypedDict):
    id: int
    label: str
    text: str
    is_correct: bool


class QuestionRow(TypedDict):
    id: int
    prompt: str
    explanation: str
    marks: float
    order: int
    options: list[OptionRow]


class ResultRow(TypedDict):
    trainee: str
    email: str
    assessment: str
    score: float
    percentage: int
    passed: bool
    grade: str
    submitted: str


class CourseOption(TypedDict):
    id: int
    label: str


class TrainerAssessmentState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    assessments: list[AssessmentRow] = []
    course_options: list[CourseOption] = []
    results: list[ResultRow] = []

    selected_id: int = 0
    selected_title: str = ""
    questions: list[QuestionRow] = []
    editing_question_id: int = 0

    @rx.var
    def has_courses(self) -> bool:
        return len(self.course_options) > 0

    @rx.var
    def has_selection(self) -> bool:
        return self.selected_id > 0

    @rx.var
    def editing_question(self) -> QuestionRow:
        for question in self.questions:
            if question["id"] == self.editing_question_id:
                return question
        return {
            "id": 0,
            "prompt": "",
            "explanation": "",
            "marks": 1.0,
            "order": 0,
            "options": [],
        }

    # ------------------------------------------------------------- loading
    async def _load(self, session, trainer_id: int) -> None:
        course_ids = await trainer_course_ids(session, trainer_id)
        courses = (
            (
                await session.scalars(
                    select(Course)
                    .where(Course.id.in_(course_ids))
                    .order_by(Course.title)
                )
            ).all()
            if course_ids
            else []
        )
        self.course_options = [
            {"id": course.id, "label": f"{course.code} · {course.title}"}
            for course in courses
        ]
        lookup = {course.id: (course.title, course.code) for course in courses}
        rows: list[AssessmentRow] = []
        results: list[ResultRow] = []
        if course_ids:
            assessment_rows = (
                await session.scalars(
                    select(Assessment)
                    .where(Assessment.course_id.in_(course_ids))
                    .order_by(Assessment.created_at.desc())
                )
            ).all()
            for assessment in assessment_rows:
                title, code = lookup.get(assessment.course_id, ("Course", ""))
                question_count = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(Question)
                        .where(Question.assessment_id == assessment.id)
                    )
                    or 0
                )
                attempts = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(AssessmentAttempt)
                        .where(AssessmentAttempt.assessment_id == assessment.id)
                    )
                    or 0
                )
                result_rows = (
                    await session.execute(
                        select(AssessmentResult, User)
                        .join(User, User.id == AssessmentResult.trainee_id)
                        .where(AssessmentResult.assessment_id == assessment.id)
                        .order_by(AssessmentResult.percentage.desc())
                    )
                ).all()
                cohort = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(Enrollment)
                        .where(Enrollment.course_id == assessment.course_id)
                    )
                    or 0
                )
                passed = len(
                    [row for row, _user in result_rows if row.is_passed]
                )
                average = (
                    sum(float(row.percentage) for row, _user in result_rows)
                    / len(result_rows)
                    if result_rows
                    else 0.0
                )
                for result, user in result_rows:
                    results.append(
                        {
                            "trainee": user.full_name,
                            "email": user.email,
                            "assessment": assessment.title,
                            "score": float(result.score),
                            "percentage": int(round(result.percentage)),
                            "passed": result.is_passed,
                            "grade": result.grade or "—",
                            "submitted": result.graded_at.strftime("%d %b %Y")
                            if result.graded_at
                            else "Pending",
                        }
                    )
                rows.append(
                    {
                        "id": assessment.id,
                        "title": assessment.title,
                        "course_id": assessment.course_id,
                        "course": title,
                        "course_code": code,
                        "status": assessment.status,
                        "questions": question_count,
                        "total_marks": float(assessment.total_marks),
                        "passing_marks": float(assessment.passing_marks),
                        "time_limit": int(assessment.time_limit_minutes),
                        "max_attempts": int(assessment.max_attempts),
                        "deadline": assessment.deadline_at.strftime(
                            "%d %b %Y, %H:%M"
                        )
                        if assessment.deadline_at
                        else "Not set",
                        "attempts": attempts,
                        "submissions": len(result_rows),
                        "participation": int(
                            round(len(result_rows) * 100 / cohort)
                        )
                        if cohort
                        else 0,
                        "pass_rate": int(round(passed * 100 / len(result_rows)))
                        if result_rows
                        else 0,
                        "average": int(round(average)),
                        "is_owner": assessment.created_by_id == trainer_id,
                    }
                )
        self.assessments = rows
        self.results = results
        if self.selected_id and not any(
            row["id"] == self.selected_id for row in rows
        ):
            self.selected_id = 0
            self.selected_title = ""
            self.questions = []
        if self.selected_id:
            await self._load_questions(session, self.selected_id)

    async def _load_questions(self, session, assessment_id: int) -> None:
        questions: list[QuestionRow] = []
        question_rows = (
            await session.scalars(
                select(Question)
                .where(Question.assessment_id == assessment_id)
                .order_by(Question.sort_order)
            )
        ).all()
        for question in question_rows:
            option_rows = (
                await session.scalars(
                    select(QuestionOption)
                    .where(QuestionOption.question_id == question.id)
                    .order_by(QuestionOption.sort_order)
                )
            ).all()
            options = [
                {
                    "id": option.id,
                    "label": option.label,
                    "text": option.text,
                    "is_correct": option.is_correct,
                }
                for option in option_rows
            ]
            questions.append(
                {
                    "id": question.id,
                    "prompt": question.prompt,
                    "explanation": question.explanation,
                    "marks": float(question.marks),
                    "order": int(question.sort_order),
                    "options": options,
                }
            )
        self.questions = questions

    @rx.event
    async def load_studio(self):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error loading assessment studio: {exception}")
            self.error_message = "Could not load your assessments."
        self.is_loading = False

    @rx.event
    async def select_assessment(self, assessment_id: int):
        self.error_message = ""
        self.success_message = ""
        self.editing_question_id = 0
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        try:
            async with rx.asession() as session:
                assessment = await session.get(Assessment, assessment_id)
                if assessment is None or assessment.course_id not in (
                    await trainer_course_ids(session, trainer_id)
                ):
                    self.error_message = "Assessment not available to you."
                    return
                self.selected_id = assessment.id
                self.selected_title = assessment.title
                await self._load_questions(session, assessment.id)
        except Exception as exception:
            logging.exception(f"Error selecting assessment: {exception}")
            self.error_message = "Could not open that assessment."

    @rx.event
    def close_assessment(self):
        self.selected_id = 0
        self.selected_title = ""
        self.questions = []
        self.editing_question_id = 0

    @rx.event
    def edit_question(self, question_id: int):
        self.editing_question_id = question_id
        self.error_message = ""
        self.success_message = ""

    @rx.event
    def cancel_edit(self):
        self.editing_question_id = 0

    # ------------------------------------------------------------ authoring
    @rx.event
    async def create_assessment(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        title = str(form_data.get("title", "")).strip()
        if len(title) < 4:
            self.error_message = "Enter an assessment title."
            return
        try:
            course_id = int(form_data.get("course_id") or 0)
            time_limit = int(float(form_data.get("time_limit") or 0))
            passing_marks = float(form_data.get("passing_marks") or 0)
            max_attempts = int(float(form_data.get("max_attempts") or 1))
        except ValueError:
            self.error_message = "Numeric fields must contain numbers."
            return
        if time_limit < 5 or time_limit > 300:
            self.error_message = "Time limit must be between 5 and 300 minutes."
            return
        if passing_marks <= 0:
            self.error_message = "Passing mark must be greater than zero."
            return
        if max_attempts < 1 or max_attempts > 10:
            self.error_message = "Max attempts must be between 1 and 10."
            return
        deadline_raw = str(form_data.get("deadline", "")).strip()
        deadline: dt.datetime | None = None
        if deadline_raw:
            try:
                deadline = dt.datetime.fromisoformat(deadline_raw).replace(
                    tzinfo=dt.UTC
                )
            except ValueError:
                self.error_message = "Enter a valid deadline."
                return
            if deadline <= dt.datetime.now(dt.UTC):
                self.error_message = "The deadline must be in the future."
                return
        try:
            async with rx.asession() as session:
                if course_id not in await trainer_course_ids(
                    session, trainer_id
                ):
                    self.error_message = "You are not assigned to that course."
                    return
                assessment = Assessment(
                    course_id=course_id,
                    created_by_id=trainer_id,
                    title=title,
                    instructions=str(form_data.get("instructions", "")).strip(),
                    status=AssessmentStatus.DRAFT.value,
                    total_marks=0.0,
                    passing_marks=passing_marks,
                    time_limit_minutes=time_limit,
                    max_attempts=max_attempts,
                    opens_at=dt.datetime.now(dt.UTC),
                    deadline_at=deadline,
                )
                session.add(assessment)
                await session.commit()
                await session.refresh(assessment)
                self.selected_id = assessment.id
                self.selected_title = assessment.title
                await self._load(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error creating assessment: {exception}")
            self.error_message = "Could not create the assessment."
            return
        self.success_message = (
            f"Draft created: {title}. Add questions before publishing."
        )

    @rx.event
    async def save_question(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        if self.selected_id == 0:
            self.error_message = "Open an assessment first."
            return
        prompt = str(form_data.get("prompt", "")).strip()
        if len(prompt) < 8:
            self.error_message = (
                "Question prompt must be at least 8 characters."
            )
            return
        options = [
            str(form_data.get(f"option_{label.lower()}", "")).strip()
            for label in OPTION_LABELS
        ]
        if any(not text for text in options):
            self.error_message = "All four options are required."
            return
        correct = str(form_data.get("correct", "")).strip().upper()
        if correct not in OPTION_LABELS:
            self.error_message = "Select exactly one correct option."
            return
        try:
            marks = float(form_data.get("marks") or 1)
        except ValueError:
            self.error_message = "Marks must be numeric."
            return
        if marks <= 0 or marks > 20:
            self.error_message = "Marks must be between 0 and 20."
            return
        question_id = self.editing_question_id
        try:
            async with rx.asession() as session:
                assessment = await session.get(Assessment, self.selected_id)
                if assessment is None or assessment.course_id not in (
                    await trainer_course_ids(session, trainer_id)
                ):
                    self.error_message = "Assessment not available to you."
                    return
                if question_id:
                    question = await session.get(Question, question_id)
                    if (
                        question is None
                        or question.assessment_id != assessment.id
                    ):
                        self.error_message = "Question not found."
                        return
                    stale_options = (
                        await session.scalars(
                            select(QuestionOption).where(
                                QuestionOption.question_id == question.id
                            )
                        )
                    ).all()
                    for option in stale_options:
                        await session.delete(option)
                    question.prompt = prompt
                    question.marks = marks
                    question.explanation = str(
                        form_data.get("explanation", "")
                    ).strip()
                    await session.flush()
                else:
                    last = await session.scalar(
                        select(Question.sort_order)
                        .where(Question.assessment_id == assessment.id)
                        .order_by(Question.sort_order.desc())
                    )
                    question = Question(
                        assessment_id=assessment.id,
                        prompt=prompt,
                        explanation=str(
                            form_data.get("explanation", "")
                        ).strip(),
                        marks=marks,
                        sort_order=int(last or 0) + 1,
                    )
                    session.add(question)
                    await session.flush()
                for index, label in enumerate(OPTION_LABELS):
                    session.add(
                        QuestionOption(
                            question_id=question.id,
                            label=label,
                            text=options[index],
                            is_correct=label == correct,
                            sort_order=index + 1,
                        )
                    )
                assessment.total_marks = float(
                    await session.scalar(
                        select(func.sum(Question.marks)).where(
                            Question.assessment_id == assessment.id
                        )
                    )
                    or 0.0
                )
                await session.commit()
                self.editing_question_id = 0
                await self._load(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error saving question: {exception}")
            self.error_message = "Could not save the question."
            return
        self.success_message = "Question saved."

    @rx.event
    async def delete_question(self, question_id: int):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        try:
            async with rx.asession() as session:
                question = await session.get(Question, question_id)
                if question is None:
                    self.error_message = "Question not found."
                    return
                assessment = await session.get(
                    Assessment, question.assessment_id
                )
                if assessment is None or assessment.course_id not in (
                    await trainer_course_ids(session, trainer_id)
                ):
                    self.error_message = "You cannot edit that assessment."
                    return
                await session.delete(question)
                await session.flush()
                assessment.total_marks = float(
                    await session.scalar(
                        select(func.sum(Question.marks)).where(
                            Question.assessment_id == assessment.id
                        )
                    )
                    or 0.0
                )
                await session.commit()
                self.editing_question_id = 0
                await self._load(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error deleting question: {exception}")
            self.error_message = "Could not remove the question."
            return
        self.success_message = "Question removed."

    @rx.event
    async def publish_assessment(self, assessment_id: int):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        try:
            async with rx.asession() as session:
                assessment = await session.get(Assessment, assessment_id)
                if assessment is None or assessment.course_id not in (
                    await trainer_course_ids(session, trainer_id)
                ):
                    self.error_message = "Assessment not available to you."
                    return
                questions = (
                    await session.scalars(
                        select(Question).where(
                            Question.assessment_id == assessment.id
                        )
                    )
                ).all()
                if not questions:
                    self.error_message = (
                        "Add at least one question before publishing."
                    )
                    return
                total = sum(float(question.marks) for question in questions)
                if assessment.passing_marks <= 0 or (
                    assessment.passing_marks > total
                ):
                    self.error_message = (
                        "Passing mark must be greater than zero and no more "
                        f"than the total marks ({total:.1f})."
                    )
                    return
                if assessment.deadline_at is None:
                    self.error_message = "Set a deadline before publishing."
                    return
                deadline = assessment.deadline_at
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=dt.UTC)
                if deadline <= dt.datetime.now(dt.UTC):
                    self.error_message = "The deadline has already passed."
                    return
                for question in questions:
                    correct = (
                        await session.scalars(
                            select(QuestionOption).where(
                                QuestionOption.question_id == question.id,
                                QuestionOption.is_correct.is_(True),
                            )
                        )
                    ).all()
                    if len(correct) != 1:
                        self.error_message = (
                            "Each question needs exactly one correct option."
                        )
                        return
                assessment.total_marks = total
                assessment.status = AssessmentStatus.OPEN.value
                await session.commit()
                await self._load(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error publishing assessment: {exception}")
            self.error_message = "Could not publish the assessment."
            return
        self.success_message = "Assessment published to the cohort."

    @rx.event
    async def close_assessment_window(self, assessment_id: int):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        try:
            async with rx.asession() as session:
                assessment = await session.get(Assessment, assessment_id)
                if assessment is None or assessment.course_id not in (
                    await trainer_course_ids(session, trainer_id)
                ):
                    self.error_message = "Assessment not available to you."
                    return
                assessment.status = AssessmentStatus.CLOSED.value
                await session.commit()
                await self._load(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error closing assessment: {exception}")
            self.error_message = "Could not close the assessment."
            return
        self.success_message = "Assessment closed."

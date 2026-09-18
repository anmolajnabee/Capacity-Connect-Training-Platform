"""Assessment discovery, timed MCQ attempts, scoring, results and certificates."""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from typing import TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentResult,
    AssessmentStatus,
    AttemptAnswer,
    AttemptStatus,
    Certificate,
    Course,
    Enrollment,
    Question,
    QuestionOption,
    User,
)
from app.seed import ensure_seed_data
from app.services.email_notifications import enqueue
from app.states.trainee_state import grade_for

logger = logging.getLogger(__name__)


class AssessmentItem(TypedDict):
    id: int
    title: str
    instructions: str
    course_id: int
    course_code: str
    course_title: str
    status: str
    total_marks: float
    passing_marks: float
    time_limit_minutes: int
    max_attempts: int
    attempts_used: int
    question_count: int
    deadline: str
    best_percentage: int
    is_passed: bool
    can_attempt: bool
    blocked_reason: str


class OptionItem(TypedDict):
    id: int
    label: str
    text: str


class QuestionItem(TypedDict):
    id: int
    prompt: str
    marks: float
    options: list[OptionItem]


class ResultItem(TypedDict):
    id: int
    assessment_title: str
    course_code: str
    course_title: str
    attempt_number: int
    score: float
    total_marks: float
    percentage: int
    grade: str
    is_passed: bool
    correct_count: int
    incorrect_count: int
    unanswered_count: int
    graded_at: str
    time_taken: str


class CertificateItem(TypedDict):
    id: int
    certificate_number: str
    course_code: str
    course_title: str
    issued_at: str
    final_score: float
    grade: str
    verification_code: str
    issued_by: str
    is_revoked: bool


EMPTY_SUMMARY: dict[str, str] = {
    "title": "",
    "score": "0",
    "total": "0",
    "percentage": "0",
    "grade": "-",
    "correct": "0",
    "incorrect": "0",
    "unanswered": "0",
    "time_taken": "0m 00s",
}


class TraineeAssessmentState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    assessments: list[AssessmentItem] = []
    results: list[ResultItem] = []
    certificates: list[CertificateItem] = []

    attempt_active: bool = False
    attempt_id: int = 0
    active_assessment_id: int = 0
    active_title: str = ""
    active_course: str = ""
    active_instructions: str = ""
    attempt_number: int = 0
    questions: list[QuestionItem] = []
    answers: dict[str, int] = {}
    current_index: int = 0
    seconds_remaining: int = 0
    is_submitting: bool = False

    show_summary: bool = False
    summary: dict[str, str] = EMPTY_SUMMARY
    summary_passed: bool = False

    async def _uid(self) -> int:
        from app.states.auth_state import AuthState

        auth = await self.get_state(AuthState)
        if auth.role != "trainee":
            return 0
        return auth.user_id

    # ------------------------------------------------------------ computed
    @rx.var
    def question_count(self) -> int:
        return len(self.questions)

    @rx.var
    def current_question(self) -> QuestionItem | None:
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    @rx.var
    def current_prompt(self) -> str:
        question = self.current_question
        return question["prompt"] if question else ""

    @rx.var
    def current_options(self) -> list[OptionItem]:
        question = self.current_question
        return question["options"] if question else []

    @rx.var
    def current_selected(self) -> int:
        question = self.current_question
        if question is None:
            return 0
        return self.answers.get(str(question["id"]), 0)

    @rx.var
    def position_label(self) -> str:
        return f"Question {self.current_index + 1} of {len(self.questions)}"

    @rx.var
    def answered_count(self) -> int:
        return len([value for value in self.answers.values() if value > 0])

    @rx.var
    def answered_label(self) -> str:
        return f"{self.answered_count} of {len(self.questions)} answered"

    @rx.var
    def progress_percent(self) -> int:
        if not self.questions:
            return 0
        return int(self.answered_count / len(self.questions) * 100)

    @rx.var
    def time_display(self) -> str:
        minutes = self.seconds_remaining // 60
        seconds = self.seconds_remaining % 60
        return f"{minutes:02d}:{seconds:02d}"

    @rx.var
    def time_is_critical(self) -> bool:
        return self.attempt_active and self.seconds_remaining <= 60

    @rx.var
    def is_last_question(self) -> bool:
        return self.current_index >= len(self.questions) - 1

    @rx.var
    def has_assessments(self) -> bool:
        return len(self.assessments) > 0

    @rx.var
    def average_percentage(self) -> int:
        if not self.results:
            return 0
        return int(
            sum(item["percentage"] for item in self.results) / len(self.results)
        )

    @rx.var
    def passed_count(self) -> int:
        return len([item for item in self.results if item["is_passed"]])

    # ------------------------------------------------------------- loaders
    async def _load_assessments(self, session, uid: int) -> None:
        now = dt.datetime.now(dt.UTC)
        rows = (
            await session.execute(
                select(Assessment, Course)
                .join(Course, Course.id == Assessment.course_id)
                .join(Enrollment, Enrollment.course_id == Course.id)
                .where(
                    Enrollment.trainee_id == uid,
                    Assessment.status != AssessmentStatus.DRAFT.value,
                )
                .order_by(
                    Assessment.deadline_at.asc().nullslast(), Assessment.id
                )
            )
        ).all()
        items: list[AssessmentItem] = []
        for assessment, course in rows:
            question_count = int(
                await session.scalar(
                    select(func.count(Question.id)).where(
                        Question.assessment_id == assessment.id
                    )
                )
                or 0
            )
            attempts_used = int(
                await session.scalar(
                    select(func.count(AssessmentAttempt.id)).where(
                        AssessmentAttempt.assessment_id == assessment.id,
                        AssessmentAttempt.trainee_id == uid,
                    )
                )
                or 0
            )
            best = await session.scalar(
                select(func.max(AssessmentResult.percentage)).where(
                    AssessmentResult.assessment_id == assessment.id,
                    AssessmentResult.trainee_id == uid,
                )
            )
            passed = bool(
                await session.scalar(
                    select(func.count(AssessmentResult.id)).where(
                        AssessmentResult.assessment_id == assessment.id,
                        AssessmentResult.trainee_id == uid,
                        AssessmentResult.is_passed.is_(True),
                    )
                )
            )
            reason = ""
            if assessment.status != AssessmentStatus.OPEN.value:
                reason = "This questionnaire is closed."
            elif question_count == 0:
                reason = "No questions have been published yet."
            elif assessment.opens_at is not None and assessment.opens_at > now:
                reason = f"Opens {assessment.opens_at.strftime('%d %b %Y, %H:%M UTC')}"
            elif (
                assessment.deadline_at is not None
                and assessment.deadline_at < now
            ):
                reason = f"Deadline passed on {assessment.deadline_at.strftime('%d %b %Y')}"
            elif attempts_used >= assessment.max_attempts:
                reason = f"Attempt limit reached ({attempts_used}/{assessment.max_attempts})"
            items.append(
                {
                    "id": assessment.id,
                    "title": assessment.title,
                    "instructions": assessment.instructions,
                    "course_id": course.id,
                    "course_code": course.code,
                    "course_title": course.title,
                    "status": assessment.status.capitalize(),
                    "total_marks": float(assessment.total_marks),
                    "passing_marks": float(assessment.passing_marks),
                    "time_limit_minutes": int(assessment.time_limit_minutes),
                    "max_attempts": int(assessment.max_attempts),
                    "attempts_used": attempts_used,
                    "question_count": question_count,
                    "deadline": (
                        assessment.deadline_at.strftime("%d %b %Y, %H:%M UTC")
                        if assessment.deadline_at
                        else "No deadline"
                    ),
                    "best_percentage": int(best or 0),
                    "is_passed": passed,
                    "can_attempt": reason == "",
                    "blocked_reason": reason,
                }
            )
        self.assessments = items

    async def _load_results(self, session, uid: int) -> None:
        rows = (
            await session.execute(
                select(AssessmentResult, AssessmentAttempt, Assessment, Course)
                .join(
                    AssessmentAttempt,
                    AssessmentAttempt.id == AssessmentResult.attempt_id,
                )
                .join(
                    Assessment,
                    Assessment.id == AssessmentResult.assessment_id,
                )
                .join(Course, Course.id == Assessment.course_id)
                .where(AssessmentResult.trainee_id == uid)
                .order_by(AssessmentResult.id.desc())
            )
        ).all()
        items: list[ResultItem] = []
        for result, attempt, assessment, course in rows:
            seconds = int(attempt.time_taken_seconds)
            items.append(
                {
                    "id": result.id,
                    "assessment_title": assessment.title,
                    "course_code": course.code,
                    "course_title": course.title,
                    "attempt_number": int(attempt.attempt_number),
                    "score": float(result.score),
                    "total_marks": float(assessment.total_marks),
                    "percentage": int(result.percentage),
                    "grade": result.grade or grade_for(result.percentage),
                    "is_passed": bool(result.is_passed),
                    "correct_count": int(result.correct_count),
                    "incorrect_count": int(result.incorrect_count),
                    "unanswered_count": int(result.unanswered_count),
                    "graded_at": (
                        result.graded_at.strftime("%d %b %Y, %H:%M UTC")
                        if result.graded_at
                        else "Pending"
                    ),
                    "time_taken": f"{seconds // 60}m {seconds % 60:02d}s",
                }
            )
        self.results = items

    async def _load_certificates(self, session, uid: int) -> None:
        rows = (
            await session.execute(
                select(Certificate, Course)
                .join(Course, Course.id == Certificate.course_id)
                .where(Certificate.trainee_id == uid)
                .order_by(Certificate.issued_at.desc())
            )
        ).all()
        items: list[CertificateItem] = []
        for certificate, course in rows:
            issuer = (
                await session.scalar(
                    select(User.full_name).where(
                        User.id == certificate.issued_by_id
                    )
                )
                if certificate.issued_by_id
                else None
            )
            items.append(
                {
                    "id": certificate.id,
                    "certificate_number": certificate.certificate_number,
                    "course_code": course.code,
                    "course_title": course.title,
                    "issued_at": certificate.issued_at.strftime(
                        "%d %b %Y, %H:%M UTC"
                    ),
                    "final_score": float(certificate.final_score),
                    "grade": certificate.grade or "P",
                    "verification_code": certificate.verification_code,
                    "issued_by": issuer or "Capacity Connect Secretariat",
                    "is_revoked": bool(certificate.is_revoked),
                }
            )
        self.certificates = items

    @rx.event
    async def load_assessments(self):
        ensure_seed_data()
        uid = await self._uid()
        if uid <= 0:
            return
        self.is_loading = True
        self.error_message = ""
        self.attempt_active = False
        yield
        try:
            async with rx.asession() as session:
                await self._load_assessments(session, uid)
        except Exception as exception:
            logging.exception(f"Error loading assessments: {exception}")
            self.error_message = "Could not load your assessments. Retry."
        self.is_loading = False

    @rx.event
    async def load_results(self):
        ensure_seed_data()
        uid = await self._uid()
        if uid <= 0:
            return
        self.is_loading = True
        self.error_message = ""
        yield
        try:
            async with rx.asession() as session:
                await self._load_results(session, uid)
        except Exception as exception:
            logging.exception(f"Error loading results: {exception}")
            self.error_message = "Could not load your results history."
        self.is_loading = False

    @rx.event
    async def load_certificates(self):
        ensure_seed_data()
        uid = await self._uid()
        if uid <= 0:
            return
        self.is_loading = True
        self.error_message = ""
        yield
        try:
            async with rx.asession() as session:
                await self._load_certificates(session, uid)
        except Exception as exception:
            logging.exception(f"Error loading certificates: {exception}")
            self.error_message = "Could not load your certificate records."
        self.is_loading = False

    # -------------------------------------------------------- attempt flow
    def _reset_attempt(self) -> None:
        self.attempt_active = False
        self.attempt_id = 0
        self.active_assessment_id = 0
        self.questions = []
        self.answers = {}
        self.current_index = 0
        self.seconds_remaining = 0
        self.is_submitting = False

    @rx.event
    async def start_attempt(self, assessment_id: int):
        self.error_message = ""
        self.success_message = ""
        self.show_summary = False
        uid = await self._uid()
        if uid <= 0:
            return rx.redirect("/login")
        if self.attempt_active:
            self.error_message = (
                "Finish or submit your current attempt before starting another."
            )
            return
        now = dt.datetime.now(dt.UTC)
        try:
            async with rx.asession() as session:
                assessment = await session.get(Assessment, assessment_id)
                if assessment is None:
                    self.error_message = "That assessment no longer exists."
                    return
                enrolled = await session.scalar(
                    select(func.count(Enrollment.id)).where(
                        Enrollment.course_id == assessment.course_id,
                        Enrollment.trainee_id == uid,
                    )
                )
                if not enrolled:
                    self.error_message = (
                        "You must be enrolled in the course to attempt this."
                    )
                    return
                if assessment.status != AssessmentStatus.OPEN.value:
                    self.error_message = "This questionnaire is not open."
                    return
                if (
                    assessment.opens_at is not None
                    and assessment.opens_at > now
                ):
                    self.error_message = (
                        "This questionnaire has not opened yet."
                    )
                    return
                if (
                    assessment.deadline_at is not None
                    and assessment.deadline_at < now
                ):
                    self.error_message = (
                        "The deadline for this questionnaire has passed."
                    )
                    return
                attempts_used = int(
                    await session.scalar(
                        select(func.count(AssessmentAttempt.id)).where(
                            AssessmentAttempt.assessment_id == assessment_id,
                            AssessmentAttempt.trainee_id == uid,
                        )
                    )
                    or 0
                )
                if attempts_used >= assessment.max_attempts:
                    self.error_message = "You have used all permitted attempts for this assessment."
                    return
                questions = (
                    await session.scalars(
                        select(Question)
                        .where(Question.assessment_id == assessment_id)
                        .order_by(Question.sort_order, Question.id)
                    )
                ).all()
                if not questions:
                    self.error_message = (
                        "No questions have been published for this assessment."
                    )
                    return
                attempt = AssessmentAttempt(
                    assessment_id=assessment_id,
                    trainee_id=uid,
                    attempt_number=attempts_used + 1,
                    status=AttemptStatus.IN_PROGRESS.value,
                    started_at=now,
                )
                session.add(attempt)
                await session.commit()
                await session.refresh(attempt)
                payload: list[QuestionItem] = []
                for question in questions:
                    options = (
                        await session.scalars(
                            select(QuestionOption)
                            .where(QuestionOption.question_id == question.id)
                            .order_by(
                                QuestionOption.sort_order, QuestionOption.id
                            )
                        )
                    ).all()
                    payload.append(
                        {
                            "id": question.id,
                            "prompt": question.prompt,
                            "marks": float(question.marks),
                            "options": [
                                {
                                    "id": option.id,
                                    "label": option.label or "",
                                    "text": option.text,
                                }
                                for option in options
                            ],
                        }
                    )
                course_code = await session.scalar(
                    select(Course.code).where(Course.id == assessment.course_id)
                )
                self.attempt_id = attempt.id
                self.attempt_number = attempt.attempt_number
                self.active_assessment_id = assessment_id
                self.active_title = assessment.title
                self.active_course = course_code or ""
                self.active_instructions = assessment.instructions
                self.questions = payload
                self.answers = {}
                self.current_index = 0
                self.seconds_remaining = max(
                    60, int(assessment.time_limit_minutes) * 60
                )
                self.attempt_active = True
        except Exception as exception:
            logging.exception(f"Error starting attempt: {exception}")
            self.error_message = "Could not start the assessment. Try again."
            return
        return TraineeAssessmentState.countdown

    @rx.event(background=True)
    async def countdown(self):
        while True:
            await asyncio.sleep(1)
            async with self:
                if not self.attempt_active or self.attempt_id == 0:
                    return
                self.seconds_remaining -= 1
                if self.seconds_remaining <= 0:
                    self.seconds_remaining = 0
                    break
        async with self:
            self.error_message = (
                "Time expired — your attempt was submitted automatically."
            )
        return TraineeAssessmentState.submit_attempt

    @rx.event
    def select_answer(self, question_id: int, option_id: int):
        if not self.attempt_active:
            return
        self.answers[str(question_id)] = option_id

    @rx.event
    def go_to_question(self, index: int):
        if 0 <= index < len(self.questions):
            self.current_index = index

    @rx.event
    def next_question(self):
        if self.current_index < len(self.questions) - 1:
            self.current_index += 1

    @rx.event
    def previous_question(self):
        if self.current_index > 0:
            self.current_index -= 1

    @rx.event
    async def abandon_attempt(self):
        uid = await self._uid()
        attempt_id = self.attempt_id
        self._reset_attempt()
        if uid <= 0 or attempt_id <= 0:
            return
        try:
            async with rx.asession() as session:
                attempt = await session.scalar(
                    select(AssessmentAttempt).where(
                        AssessmentAttempt.id == attempt_id,
                        AssessmentAttempt.trainee_id == uid,
                    )
                )
                if attempt is not None and attempt.status == (
                    AttemptStatus.IN_PROGRESS.value
                ):
                    attempt.status = AttemptStatus.EXPIRED.value
                    await session.commit()
                await self._load_assessments(session, uid)
        except Exception as exception:
            logging.exception(f"Error abandoning attempt: {exception}")
        self.success_message = "Attempt discarded. No score was recorded."

    @rx.event
    async def submit_attempt(self):
        uid = await self._uid()
        if uid <= 0:
            self.error_message = "Your session expired. Sign in again."
            return
        if not self.attempt_active or self.attempt_id <= 0:
            return
        self.attempt_active = False
        self.is_submitting = True
        attempt_id = self.attempt_id
        answers = dict(self.answers)
        yield
        try:
            async with rx.asession() as session:
                attempt = await session.scalar(
                    select(AssessmentAttempt).where(
                        AssessmentAttempt.id == attempt_id,
                        AssessmentAttempt.trainee_id == uid,
                    )
                )
                if attempt is None:
                    self.is_submitting = False
                    self.error_message = "That attempt could not be found."
                    return
                if attempt.status in (
                    AttemptStatus.SUBMITTED.value,
                    AttemptStatus.GRADED.value,
                ):
                    self.is_submitting = False
                    self.error_message = (
                        "This attempt has already been submitted."
                    )
                    return
                assessment = await session.get(
                    Assessment, attempt.assessment_id
                )
                questions = (
                    await session.scalars(
                        select(Question)
                        .where(Question.assessment_id == attempt.assessment_id)
                        .order_by(Question.sort_order, Question.id)
                    )
                ).all()
                score = 0.0
                correct = 0
                incorrect = 0
                unanswered = 0
                total_marks = 0.0
                for question in questions:
                    total_marks += float(question.marks)
                    selected = answers.get(str(question.id), 0)
                    if selected <= 0:
                        unanswered += 1
                        session.add(
                            AttemptAnswer(
                                attempt_id=attempt.id,
                                question_id=question.id,
                                selected_option_id=None,
                                is_correct=False,
                                marks_awarded=0.0,
                            )
                        )
                        continue
                    option = await session.scalar(
                        select(QuestionOption).where(
                            QuestionOption.id == selected,
                            QuestionOption.question_id == question.id,
                        )
                    )
                    is_correct = bool(option is not None and option.is_correct)
                    awarded = float(question.marks) if is_correct else 0.0
                    score += awarded
                    if is_correct:
                        correct += 1
                    else:
                        incorrect += 1
                    session.add(
                        AttemptAnswer(
                            attempt_id=attempt.id,
                            question_id=question.id,
                            selected_option_id=option.id
                            if option is not None
                            else None,
                            is_correct=is_correct,
                            marks_awarded=awarded,
                        )
                    )
                now = dt.datetime.now(dt.UTC)
                started = attempt.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=dt.UTC)
                elapsed = int(max((now - started).total_seconds(), 0))
                denominator = (
                    float(assessment.total_marks)
                    if assessment is not None and assessment.total_marks > 0
                    else total_marks
                )
                percentage = (
                    round(score / denominator * 100, 1)
                    if denominator > 0
                    else 0.0
                )
                passing = (
                    float(assessment.passing_marks)
                    if assessment is not None
                    else 0.0
                )
                is_passed = (
                    score >= passing if passing > 0 else percentage >= 50
                )
                attempt.status = AttemptStatus.GRADED.value
                attempt.submitted_at = now
                attempt.time_taken_seconds = elapsed
                result = AssessmentResult(
                    attempt_id=attempt.id,
                    assessment_id=attempt.assessment_id,
                    trainee_id=uid,
                    score=score,
                    percentage=percentage,
                    correct_count=correct,
                    incorrect_count=incorrect,
                    unanswered_count=unanswered,
                    is_passed=is_passed,
                    grade=grade_for(percentage),
                    graded_at=now,
                    remarks=(
                        "Automatically graded on submission."
                        if is_passed
                        else "Automatically graded — below the passing mark."
                    ),
                )
                session.add(result)
                await session.flush()
                await enqueue(session, "assessment_result", result)
                await session.commit()
                self.summary = {
                    "title": assessment.title if assessment else "Assessment",
                    "score": f"{score:.1f}",
                    "total": f"{denominator:.1f}",
                    "percentage": f"{percentage:.1f}",
                    "grade": grade_for(percentage),
                    "correct": str(correct),
                    "incorrect": str(incorrect),
                    "unanswered": str(unanswered),
                    "time_taken": f"{elapsed // 60}m {elapsed % 60:02d}s",
                }
                self.summary_passed = is_passed
                await self._load_assessments(session, uid)
        except Exception as exception:
            logging.exception(f"Error submitting attempt: {exception}")
            self.is_submitting = False
            self.error_message = "Could not submit the attempt. Try again."
            return
        self._reset_attempt()
        self.show_summary = True
        self.success_message = "Attempt submitted and graded automatically."

    @rx.event
    def dismiss_summary(self):
        self.show_summary = False
        self.summary = EMPTY_SUMMARY
        self.summary_passed = False

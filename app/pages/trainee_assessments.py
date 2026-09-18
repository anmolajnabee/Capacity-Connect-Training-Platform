"""Assessment list and the timed MCQ attempt flow."""

from __future__ import annotations

import reflex as rx

from app.components.trainee_shell import trainee_page
from app.components.trainee_ui import (
    chip,
    empty_block,
    ghost_button,
    loading_rows,
    panel,
    primary_button,
    progress_bar,
    status_chip,
)
from app.states.trainee_assessment_state import (
    AssessmentItem,
    OptionItem,
    QuestionItem,
    TraineeAssessmentState,
)


def _assessment_card(item: AssessmentItem) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            chip(item["course_code"], "navy"),
            status_chip(item["status"], item["can_attempt"]),
            rx.cond(
                item["is_passed"],
                chip("Passed", "green"),
                rx.fragment(),
            ),
            class_name="flex flex-wrap items-center gap-2",
        ),
        rx.el.h3(
            item["title"],
            class_name="mt-3 text-base font-semibold leading-snug text-[#0A1B33]",
        ),
        rx.el.p(
            item["course_title"],
            class_name="mt-0.5 truncate text-xs font-medium text-slate-500",
        ),
        rx.el.p(
            item["instructions"],
            class_name="mt-2 line-clamp-2 text-xs font-medium leading-relaxed text-slate-600",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Questions",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    item["question_count"].to_string(),
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Time limit",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    f"{item['time_limit_minutes']} min",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Marks",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    f"{item['total_marks']:.0f} (pass {item['passing_marks']:.0f})",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Attempts",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    f"{item['attempts_used']}/{item['max_attempts']}",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Deadline",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    item["deadline"],
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Best score",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    f"{item['best_percentage']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            class_name="mt-3 grid w-full grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3 sm:grid-cols-3",
        ),
        rx.el.div(
            rx.cond(
                item["can_attempt"],
                rx.el.button(
                    rx.icon("play", class_name="h-4 w-4"),
                    "Start attempt",
                    on_click=lambda: TraineeAssessmentState.start_attempt(
                        item["id"]
                    ),
                    class_name="flex items-center gap-2 rounded-lg bg-teal-600 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-teal-500",
                ),
                rx.el.div(
                    rx.icon("lock", class_name="h-3.5 w-3.5 text-amber-700"),
                    rx.el.span(
                        item["blocked_reason"],
                        class_name="text-xs font-semibold text-amber-800",
                    ),
                    class_name="flex w-full items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2",
                ),
            ),
            class_name="mt-4 w-full",
        ),
        class_name="flex h-full w-full min-w-0 flex-col rounded-xl border border-slate-200 bg-white p-4",
    )


def _pill(question: QuestionItem, index: rx.Var) -> rx.Component:
    return rx.el.button(
        (index + 1).to_string(),
        on_click=lambda: TraineeAssessmentState.go_to_question(index),
        class_name=rx.cond(
            TraineeAssessmentState.current_index == index,
            "size-8 shrink-0 rounded-md bg-[#0A1B33] text-xs font-semibold text-white",
            rx.cond(
                TraineeAssessmentState.answers.get(
                    question["id"].to_string(), 0
                )
                > 0,
                "size-8 shrink-0 rounded-md border border-teal-500 bg-teal-50 text-xs font-semibold text-teal-800",
                "size-8 shrink-0 rounded-md border border-slate-300 bg-white text-xs font-semibold text-slate-600 hover:bg-slate-100",
            ),
        ),
    )


def _option_row(option: OptionItem) -> rx.Component:
    return rx.el.button(
        rx.el.span(
            option["label"],
            class_name=rx.cond(
                TraineeAssessmentState.current_selected == option["id"],
                "flex size-7 shrink-0 items-center justify-center rounded-md bg-teal-600 text-xs font-semibold text-white",
                "flex size-7 shrink-0 items-center justify-center rounded-md border border-slate-300 bg-white text-xs font-semibold text-slate-600",
            ),
        ),
        rx.el.span(
            option["text"],
            class_name="text-left text-sm font-medium text-slate-800",
        ),
        on_click=lambda: TraineeAssessmentState.select_answer(
            TraineeAssessmentState.questions[
                TraineeAssessmentState.current_index
            ]["id"],
            option["id"],
        ),
        class_name=rx.cond(
            TraineeAssessmentState.current_selected == option["id"],
            "flex w-full items-start gap-3 rounded-lg border-2 border-teal-500 bg-teal-50 p-3",
            "flex w-full items-start gap-3 rounded-lg border border-slate-200 bg-white p-3 transition-colors hover:border-teal-300",
        ),
    )


def _attempt_view() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                chip(TraineeAssessmentState.active_course, "navy"),
                rx.el.p(
                    TraineeAssessmentState.active_title,
                    class_name="truncate text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.span(
                    f"Attempt {TraineeAssessmentState.attempt_number}",
                    class_name="text-[0.7rem] font-medium text-slate-500",
                ),
                class_name="flex min-w-0 flex-wrap items-center gap-2",
            ),
            rx.el.div(
                rx.icon("timer", class_name="h-4 w-4"),
                rx.el.span(
                    TraineeAssessmentState.time_display,
                    class_name="text-sm font-semibold tabular-nums",
                ),
                class_name=rx.cond(
                    TraineeAssessmentState.time_is_critical,
                    "flex shrink-0 items-center gap-2 rounded-lg border border-red-300 bg-red-100 px-3 py-1.5 text-red-700",
                    "flex shrink-0 items-center gap-2 rounded-lg border border-teal-300 bg-teal-50 px-3 py-1.5 text-teal-800",
                ),
            ),
            class_name="flex w-full flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    TraineeAssessmentState.answered_label,
                    class_name="text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.div(
                    progress_bar(TraineeAssessmentState.progress_percent),
                    class_name="mt-1",
                ),
                class_name="w-full",
            ),
            rx.el.div(
                rx.foreach(
                    TraineeAssessmentState.questions,
                    lambda question, index: _pill(question, index),
                ),
                class_name="mt-3 flex w-full flex-wrap gap-2",
            ),
            rx.el.div(
                rx.el.span(
                    TraineeAssessmentState.position_label,
                    class_name="text-[0.7rem] font-semibold uppercase tracking-wider text-teal-700",
                ),
                rx.el.p(
                    TraineeAssessmentState.current_prompt,
                    class_name="mt-2 text-base font-semibold leading-snug text-[#0A1B33]",
                ),
                rx.el.div(
                    rx.foreach(
                        TraineeAssessmentState.current_options, _option_row
                    ),
                    class_name="mt-3 flex w-full flex-col gap-2",
                ),
                class_name="mt-4 w-full rounded-lg border border-slate-200 bg-[#FBFAF7] p-4",
            ),
            rx.el.div(
                ghost_button(
                    "Previous",
                    on_click=TraineeAssessmentState.previous_question,
                    disabled=TraineeAssessmentState.current_index == 0,
                ),
                rx.el.div(
                    rx.cond(
                        TraineeAssessmentState.is_last_question,
                        rx.fragment(),
                        ghost_button(
                            "Next question",
                            on_click=TraineeAssessmentState.next_question,
                        ),
                    ),
                    primary_button(
                        "Submit attempt",
                        on_click=TraineeAssessmentState.submit_attempt,
                        disabled=TraineeAssessmentState.is_submitting,
                    ),
                    class_name="flex flex-wrap items-center gap-2",
                ),
                class_name="mt-4 flex w-full flex-wrap items-center justify-between gap-2",
            ),
            rx.el.button(
                "Discard this attempt",
                on_click=TraineeAssessmentState.abandon_attempt,
                class_name="mt-3 w-fit text-xs font-semibold text-red-600 underline hover:text-red-500",
            ),
            class_name="w-full min-w-0 px-4 py-4",
        ),
        class_name="w-full min-w-0 rounded-xl border border-slate-200 bg-white",
    )


def _summary_view() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.cond(
                TraineeAssessmentState.summary_passed,
                chip("Passed", "green"),
                chip("Not passed", "red"),
            ),
            rx.el.p(
                TraineeAssessmentState.summary["title"],
                class_name="truncate text-sm font-semibold text-[#0A1B33]",
            ),
            class_name="flex min-w-0 flex-wrap items-center gap-2",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Score",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    f"{TraineeAssessmentState.summary['score']} / {TraineeAssessmentState.summary['total']}",
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Percentage",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    f"{TraineeAssessmentState.summary['percentage']}%",
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Grade",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    TraineeAssessmentState.summary["grade"],
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Correct",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    TraineeAssessmentState.summary["correct"],
                    class_name="text-sm font-semibold text-teal-700",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Incorrect",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    TraineeAssessmentState.summary["incorrect"],
                    class_name="text-sm font-semibold text-red-600",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Unanswered",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    TraineeAssessmentState.summary["unanswered"],
                    class_name="text-sm font-semibold text-amber-700",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Time taken",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    TraineeAssessmentState.summary["time_taken"],
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
            ),
            class_name="mt-3 grid w-full grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3 sm:grid-cols-4",
        ),
        rx.el.div(
            rx.el.a(
                "View results history",
                rx.icon("arrow-right", class_name="h-3.5 w-3.5"),
                href="/trainee/results",
                class_name="flex items-center gap-1 rounded-lg bg-[#0A1B33] px-3 py-2 text-xs font-semibold text-white hover:bg-[#12304f]",
            ),
            ghost_button(
                "Dismiss", on_click=TraineeAssessmentState.dismiss_summary
            ),
            class_name="mt-4 flex flex-wrap items-center gap-2",
        ),
        class_name="w-full min-w-0 rounded-xl border border-teal-200 bg-white p-4",
    )


def trainee_assessments_page() -> rx.Component:
    return trainee_page(
        "Assessments",
        "Assessments & questionnaires",
        "Timed MCQ questionnaires for your enrolled courses, with attempt limits, deadlines and automatic scoring.",
        TraineeAssessmentState.error_message,
        TraineeAssessmentState.success_message,
        rx.cond(
            TraineeAssessmentState.show_summary,
            _summary_view(),
            rx.fragment(),
        ),
        rx.cond(
            TraineeAssessmentState.attempt_active,
            _attempt_view(),
            rx.cond(
                TraineeAssessmentState.is_loading,
                loading_rows(3),
                rx.cond(
                    TraineeAssessmentState.has_assessments,
                    panel(
                        "Available questionnaires",
                        "Only assessments for courses you are enrolled in appear here.",
                        rx.el.div(
                            rx.foreach(
                                TraineeAssessmentState.assessments,
                                _assessment_card,
                            ),
                            class_name="grid w-full min-w-0 grid-cols-1 gap-4 xl:grid-cols-2",
                        ),
                        icon="clipboard-check",
                    ),
                    empty_block(
                        "No assessments available",
                        "Enrol in a course — published questionnaires for your courses will appear here.",
                        "clipboard-check",
                    ),
                ),
            ),
        ),
    )

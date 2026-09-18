"""Assessment studio: MCQ authoring, publishing and monitoring."""

from __future__ import annotations

import reflex as rx

from app.components.trainee_ui import (
    chip,
    empty_block,
    field,
    ghost_button,
    loading_rows,
    panel,
    primary_button,
    progress_bar,
    select_field,
    teal_button,
    textarea_field,
)
from app.components.trainer_shell import trainer_page
from app.states.trainer_assessment_state import (
    OPTION_LABELS,
    TrainerAssessmentState,
)


def _status_chip(status: rx.Var) -> rx.Component:
    return rx.match(
        status,
        ("open", chip("open", "green")),
        ("closed", chip("closed", "navy")),
        chip("draft", "amber"),
    )


def _create_form() -> rx.Component:
    return rx.el.form(
        rx.el.div(
            select_field(
                "Course",
                "course_id",
                rx.foreach(
                    TrainerAssessmentState.course_options,
                    lambda option: rx.el.option(
                        option["label"], value=option["id"].to_string()
                    ),
                ),
            ),
            field(
                "Title",
                "title",
                "",
                "Module 1 & 2 knowledge check",
                required=True,
            ),
            field(
                "Deadline",
                "deadline",
                "",
                input_type="datetime-local",
                required=True,
            ),
            field(
                "Time limit (minutes)",
                "time_limit",
                "30",
                "30",
                input_type="number",
            ),
            field(
                "Passing mark",
                "passing_marks",
                "2",
                "2",
                input_type="number",
                step="0.5",
            ),
            field(
                "Max attempts",
                "max_attempts",
                "1",
                "1",
                input_type="number",
            ),
            class_name="grid w-full grid-cols-1 gap-4 md:grid-cols-3",
        ),
        textarea_field(
            "Instructions",
            "instructions",
            "",
            "Single best answer. Attempt all questions within the time limit.",
        ),
        primary_button("Create draft assessment", type="submit"),
        on_submit=TrainerAssessmentState.create_assessment,
        reset_on_submit=True,
        class_name="flex w-full flex-col gap-4",
    )


def _assessment_card(row) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    row["course_code"],
                    class_name="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-teal-700",
                ),
                rx.el.h3(
                    row["title"],
                    class_name="mt-1 text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    row["course"],
                    class_name="text-xs font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            _status_chip(row["status"]),
            class_name="flex items-start justify-between gap-3",
        ),
        rx.el.div(
            chip(f"{row['questions']} questions", "navy"),
            chip(f"{row['total_marks']:.1f} marks", "navy"),
            chip(f"pass {row['passing_marks']:.1f}", "teal"),
            chip(f"{row['time_limit']} min", "navy"),
            chip(f"{row['max_attempts']} attempts", "navy"),
            class_name="mt-3 flex flex-wrap items-center gap-2",
        ),
        rx.el.p(
            f"Deadline · {row['deadline']}",
            class_name="mt-2 text-xs font-medium text-slate-600",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Participation",
                    class_name="text-xs font-medium text-slate-600",
                ),
                rx.el.span(
                    f"{row['participation']}%",
                    class_name="text-xs font-semibold text-teal-700",
                ),
                class_name="flex items-center justify-between gap-2",
            ),
            progress_bar(row["participation"]),
            rx.el.p(
                f"{row['submissions']} submissions · {row['attempts']} attempts · pass rate {row['pass_rate']}% · mean {row['average']}%",
                class_name="mt-1 text-[0.7rem] font-medium text-slate-500",
            ),
            class_name="mt-3 flex w-full flex-col gap-1",
        ),
        rx.el.div(
            teal_button(
                "Open questions",
                on_click=lambda: TrainerAssessmentState.select_assessment(
                    row["id"]
                ),
            ),
            rx.cond(
                row["status"] == "open",
                ghost_button(
                    "Close window",
                    on_click=lambda: (
                        TrainerAssessmentState.close_assessment_window(
                            row["id"]
                        )
                    ),
                ),
                primary_button(
                    "Publish",
                    on_click=lambda: TrainerAssessmentState.publish_assessment(
                        row["id"]
                    ),
                ),
            ),
            class_name="mt-4 flex flex-wrap items-center gap-3",
        ),
        class_name="w-full min-w-0 rounded-xl border border-slate-200 bg-white p-4",
    )


def _option_line(option) -> rx.Component:
    return rx.el.div(
        rx.el.span(
            option["label"],
            class_name="flex size-6 shrink-0 items-center justify-center rounded-md border border-slate-300 bg-white text-[0.7rem] font-semibold text-slate-600",
        ),
        rx.el.p(
            option["text"],
            class_name="text-xs font-medium text-slate-700",
        ),
        rx.cond(
            option["is_correct"],
            rx.icon(
                "circle-check", class_name="ml-auto h-4 w-4 text-green-600"
            ),
            rx.fragment(),
        ),
        class_name="flex w-full items-center gap-2",
    )


def _question_card(question) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    f"Q{question['order']} · {question['marks']:.1f} marks",
                    class_name="text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.p(
                    question["prompt"],
                    class_name="mt-1 text-sm font-semibold text-[#0A1B33]",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("pencil", class_name="h-4 w-4"),
                    on_click=lambda: TrainerAssessmentState.edit_question(
                        question["id"]
                    ),
                    title="Edit question",
                    class_name="flex size-8 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-600 hover:border-teal-300 hover:text-teal-700",
                ),
                rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda: TrainerAssessmentState.delete_question(
                        question["id"]
                    ),
                    title="Remove question",
                    class_name="flex size-8 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-500 hover:border-red-300 hover:text-red-600",
                ),
                class_name="flex shrink-0 items-center gap-2",
            ),
            class_name="flex items-start justify-between gap-3",
        ),
        rx.el.div(
            rx.foreach(question["options"], _option_line),
            class_name="mt-3 flex w-full flex-col gap-2",
        ),
        rx.cond(
            question["explanation"] != "",
            rx.el.p(
                question["explanation"],
                class_name="mt-2 text-[0.7rem] font-medium italic text-slate-500",
            ),
            rx.fragment(),
        ),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def _question_form() -> rx.Component:
    return rx.el.form(
        textarea_field(
            "Question prompt",
            "prompt",
            TrainerAssessmentState.editing_question["prompt"],
            "Which process assimilates observations into the model background state?",
        ),
        rx.el.div(
            field("Option A", "option_a", "", "First option", required=True),
            field("Option B", "option_b", "", "Second option", required=True),
            field("Option C", "option_c", "", "Third option", required=True),
            field("Option D", "option_d", "", "Fourth option", required=True),
            class_name="grid w-full grid-cols-1 gap-4 md:grid-cols-2",
        ),
        rx.el.div(
            select_field(
                "Correct option",
                "correct",
                rx.foreach(
                    OPTION_LABELS,
                    lambda label: rx.el.option(label, value=label),
                ),
                "A",
            ),
            field(
                "Marks",
                "marks",
                TrainerAssessmentState.editing_question["marks"].to_string(),
                "1",
                input_type="number",
                step="0.5",
            ),
            class_name="grid w-full grid-cols-1 gap-4 md:grid-cols-2",
        ),
        textarea_field(
            "Explanation (optional)",
            "explanation",
            TrainerAssessmentState.editing_question["explanation"],
            "Why the correct option is right.",
            rows="2",
        ),
        rx.el.div(
            teal_button(
                rx.cond(
                    TrainerAssessmentState.editing_question_id > 0,
                    "Update question",
                    "Add question",
                ),
                type="submit",
            ),
            rx.cond(
                TrainerAssessmentState.editing_question_id > 0,
                ghost_button(
                    "Cancel edit",
                    type="button",
                    on_click=TrainerAssessmentState.cancel_edit,
                ),
                rx.fragment(),
            ),
            class_name="flex flex-wrap items-center gap-3",
        ),
        on_submit=TrainerAssessmentState.save_question,
        reset_on_submit=True,
        class_name="flex w-full flex-col gap-4",
    )


def _results_row(row) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.p(
                row["trainee"],
                class_name="text-sm font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                row["email"],
                class_name="text-xs font-medium text-slate-500",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.span(
                row["assessment"],
                class_name="text-xs font-medium text-slate-700",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.span(
                f"{row['score']:.1f}",
                class_name="text-xs font-semibold text-slate-700",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.span(
                    f"{row['percentage']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["percentage"]),
                class_name="flex w-28 flex-col gap-1",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.cond(
                row["passed"],
                chip("passed", "green"),
                chip("not passed", "red"),
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.span(
                row["grade"],
                class_name="text-xs font-semibold text-slate-700",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.span(
                row["submitted"],
                class_name="text-xs font-medium text-slate-600",
            ),
            class_name="px-3 py-2",
        ),
        class_name="border-b border-slate-100 odd:bg-white even:bg-[#FBFAF7]",
    )


def _th(label: str, icon: str) -> rx.Component:
    return rx.el.th(
        rx.el.div(
            rx.icon(icon, class_name="h-3.5 w-3.5 text-slate-400"),
            rx.el.span(label),
            class_name="flex items-center gap-1.5",
        ),
        class_name="px-3 py-2 text-left text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
    )


def trainer_studio_page() -> rx.Component:
    return trainer_page(
        "Create Assessment",
        "Create assessment",
        "Author MCQ questionnaires with deadlines, time limits and pass marks, then monitor participation and results.",
        TrainerAssessmentState.error_message,
        TrainerAssessmentState.success_message,
        panel(
            "New questionnaire",
            "Assessments start as drafts. Publishing requires questions, a valid pass mark and a future deadline.",
            rx.cond(
                TrainerAssessmentState.has_courses,
                _create_form(),
                empty_block(
                    "No assigned courses",
                    "Assessments can only be authored for courses you are assigned to teach.",
                    "presentation",
                ),
            ),
            icon="file-plus-2",
        ),
        rx.cond(
            TrainerAssessmentState.has_selection,
            panel(
                "Question editor",
                "Each question needs four options and exactly one correct answer.",
                rx.el.div(
                    rx.el.p(
                        TrainerAssessmentState.selected_title,
                        class_name="text-sm font-semibold text-[#0A1B33]",
                    ),
                    ghost_button(
                        "Close editor",
                        on_click=TrainerAssessmentState.close_assessment,
                    ),
                    class_name="flex w-full flex-wrap items-center justify-between gap-3",
                ),
                rx.el.div(
                    _question_form(),
                    rx.cond(
                        TrainerAssessmentState.questions.length() > 0,
                        rx.el.div(
                            rx.foreach(
                                TrainerAssessmentState.questions,
                                _question_card,
                            ),
                            class_name="flex w-full flex-col gap-3",
                        ),
                        empty_block(
                            "No questions yet",
                            "Add your first MCQ question to make this assessment publishable.",
                            "list-checks",
                        ),
                    ),
                    class_name="grid w-full grid-cols-1 gap-6 xl:grid-cols-2",
                ),
                icon="list-checks",
            ),
            rx.fragment(),
        ),
        panel(
            "Your assessments",
            "Participation is submissions over the enrolled cohort.",
            rx.cond(
                TrainerAssessmentState.is_loading,
                loading_rows(3),
                rx.cond(
                    TrainerAssessmentState.assessments.length() > 0,
                    rx.el.div(
                        rx.foreach(
                            TrainerAssessmentState.assessments,
                            _assessment_card,
                        ),
                        class_name="grid w-full grid-cols-1 gap-5 xl:grid-cols-2",
                    ),
                    empty_block(
                        "No assessments yet",
                        "Create a draft questionnaire above to begin evaluating your cohort.",
                        "clipboard-list",
                    ),
                ),
            ),
            icon="clipboard-list",
        ),
        panel(
            "Results monitoring",
            "Graded submissions across the assessments on your courses.",
            rx.cond(
                TrainerAssessmentState.results.length() > 0,
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                _th("Trainee", "user"),
                                _th("Assessment", "clipboard-check"),
                                _th("Score", "hash"),
                                _th("Percentage", "percent"),
                                _th("Outcome", "flag"),
                                _th("Grade", "award"),
                                _th("Graded", "calendar"),
                            ),
                            class_name="bg-[#F1F5F9]",
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                TrainerAssessmentState.results, _results_row
                            )
                        ),
                        class_name="w-full table-auto",
                    ),
                    class_name="w-full overflow-x-auto overflow-hidden rounded-lg border border-slate-200",
                ),
                empty_block(
                    "No graded results",
                    "Results appear here as soon as trainees submit a published assessment.",
                    "chart-line",
                ),
            ),
            icon="chart-line",
        ),
    )

"""Trainer assignment authoring, deadline tracking and submission grading."""

from __future__ import annotations

import reflex as rx

from app.components.admin_shell import filter_select
from app.components.trainer_shell import trainer_page
from app.components.trainee_ui import (
    chip,
    empty_block,
    field,
    ghost_button,
    loading_rows,
    metric_tile,
    panel,
    primary_button,
    progress_bar,
    select_field,
    textarea_field,
)
from app.states.trainer_assignment_workflow_state import (
    CourseOption,
    SubmissionRow,
    TrainerAssignmentRow,
    TrainerAssignmentWorkflowState,
)


def _metrics() -> rx.Component:
    return rx.el.div(
        metric_tile(
            "Assignments",
            TrainerAssignmentWorkflowState.metrics["assignments"].to_string(),
            "clipboard-list",
            "Authored by you",
        ),
        metric_tile(
            "Published",
            TrainerAssignmentWorkflowState.metrics["published"].to_string(),
            "send",
            "Visible to trainees",
        ),
        metric_tile(
            "Drafts",
            TrainerAssignmentWorkflowState.metrics["drafts"].to_string(),
            "file-pen",
            "Not yet released",
        ),
        metric_tile(
            "Submissions",
            TrainerAssignmentWorkflowState.metrics["submissions"].to_string(),
            "inbox",
            "Received from the cohort",
        ),
        metric_tile(
            "Awaiting grade",
            TrainerAssignmentWorkflowState.metrics["awaiting"].to_string(),
            "hourglass",
            "Needs your review",
        ),
        class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-5",
    )


def _grading_band() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    "Grading progress",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-slate-500",
                ),
                rx.el.p(
                    f"{TrainerAssignmentWorkflowState.grading_progress}% of received submissions graded",
                    class_name="mt-1 text-sm font-semibold text-[#0A1B33]",
                ),
                class_name="min-w-0",
            ),
            rx.el.span(
                f"{TrainerAssignmentWorkflowState.metrics['graded']} graded · {TrainerAssignmentWorkflowState.metrics['awaiting']} pending",
                class_name="shrink-0 text-[0.7rem] font-semibold text-amber-700",
            ),
            class_name="flex w-full flex-wrap items-end justify-between gap-2",
        ),
        rx.el.div(
            progress_bar(
                TrainerAssignmentWorkflowState.grading_progress, "amber"
            ),
            class_name="mt-2 w-full",
        ),
        class_name="cc-card w-full min-w-0 p-4",
    )


def _course_option(option: CourseOption) -> rx.Component:
    return rx.el.option(option["label"], value=option["id"].to_string())


def _type_option(value: rx.Var) -> rx.Component:
    return rx.el.option(value, value=value)


def _create_form() -> rx.Component:
    return rx.el.form(
        rx.el.div(
            select_field(
                "Course (assigned to you)",
                "course_id",
                rx.foreach(
                    TrainerAssignmentWorkflowState.course_options,
                    _course_option,
                ),
            ),
            select_field(
                "Assignment type",
                "assignment_type",
                rx.foreach(
                    TrainerAssignmentWorkflowState.type_options, _type_option
                ),
            ),
            class_name="grid w-full grid-cols-1 gap-3 sm:grid-cols-2",
        ),
        field(
            "Title",
            "title",
            placeholder="Ensemble bias correction field report",
            required=True,
        ),
        textarea_field(
            "Instructions",
            "instructions",
            placeholder="State the deliverable, expected structure and assessment criteria (minimum 30 characters).",
            rows="4",
        ),
        rx.el.div(
            field(
                "Reference URL (optional, HTTPS)",
                "reference_url",
                placeholder="https://library.example.gov/brief.pdf",
                input_type="url",
            ),
            field(
                "Due date & time (UTC)",
                "due_at",
                input_type="datetime-local",
                required=True,
            ),
            class_name="grid w-full grid-cols-1 gap-3 sm:grid-cols-2",
        ),
        rx.el.div(
            field(
                "Total marks",
                "total_marks",
                default_value="100",
                input_type="number",
                required=True,
                step="1",
            ),
            field(
                "Pass mark",
                "passing_marks",
                default_value="50",
                input_type="number",
                step="1",
            ),
            field(
                "Late penalty %",
                "late_penalty_percent",
                default_value="10",
                input_type="number",
                step="1",
            ),
            select_field(
                "Release state",
                "publish_state",
                rx.fragment(
                    rx.el.option("Save as draft", value="draft"),
                    rx.el.option("Publish to cohort", value="published"),
                ),
            ),
            class_name="grid w-full grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4",
        ),
        textarea_field(
            "Submission note (optional)",
            "submission_note",
            placeholder="Any submission format guidance shown to trainees.",
            rows="2",
        ),
        rx.el.div(
            rx.el.label(
                rx.el.input(
                    type="checkbox",
                    name="allow_late_submission",
                    default_checked=True,
                    class_name="size-4 rounded border-slate-300 accent-amber-600",
                ),
                rx.el.span(
                    "Accept late submissions",
                    class_name="text-xs font-semibold text-slate-700",
                ),
                class_name="flex w-fit items-center gap-2",
            ),
            rx.el.label(
                rx.el.input(
                    type="checkbox",
                    name="allow_resubmission",
                    default_checked=True,
                    class_name="size-4 rounded border-slate-300 accent-amber-600",
                ),
                rx.el.span(
                    "Allow resubmission",
                    class_name="text-xs font-semibold text-slate-700",
                ),
                class_name="flex w-fit items-center gap-2",
            ),
            class_name="flex w-full flex-wrap items-center gap-5",
        ),
        primary_button(
            "Create assignment",
            type="submit",
            disabled=TrainerAssignmentWorkflowState.is_saving,
        ),
        on_submit=TrainerAssignmentWorkflowState.create_assignment,
        reset_on_submit=True,
        class_name="flex w-full min-w-0 flex-col gap-3",
    )


def _assignment_row(item: TrainerAssignmentRow) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            chip(item["course_code"], "navy"),
            chip(item["assignment_type"], "amber"),
            rx.match(
                item["status"],
                ("published", chip("published", "green")),
                ("closed", chip("closed", "red")),
                chip("draft", "navy"),
            ),
            rx.cond(
                item["is_overdue"],
                chip("deadline passed", "red"),
                rx.fragment(),
            ),
            class_name="flex flex-wrap items-center gap-2",
        ),
        rx.el.h3(
            item["title"],
            class_name="mt-2 text-sm font-semibold leading-snug text-[#0A1B33]",
        ),
        rx.el.p(
            f"{item['course_title']} · due {item['due_display']} · {item['late_policy']}",
            class_name="mt-0.5 text-[0.7rem] font-medium text-slate-500",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Submitted",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    f"{item['submitted']} of {item['cohort']}",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(item["submitted_percent"], "amber"),
                class_name="flex min-w-0 flex-col gap-1",
            ),
            rx.el.div(
                rx.el.span(
                    "Graded",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    f"{item['graded']} graded · {item['pending_review']} pending",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(item["graded_percent"], "navy"),
                class_name="flex min-w-0 flex-col gap-1",
            ),
            rx.el.div(
                rx.el.span(
                    "Deadline timeline",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    f"{item['late']} late · {item['awaiting']} not started",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(item["timeline"], "amber"),
                class_name="flex min-w-0 flex-col gap-1",
            ),
            class_name="mt-3 grid w-full grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3 sm:grid-cols-3",
        ),
        rx.el.div(
            ghost_button(
                "Review submissions",
                on_click=lambda: (
                    TrainerAssignmentWorkflowState.select_assignment(item["id"])
                ),
            ),
            rx.cond(
                item["status"] == "draft",
                primary_button(
                    "Publish",
                    on_click=lambda: (
                        TrainerAssignmentWorkflowState.publish_assignment(
                            item["id"]
                        )
                    ),
                ),
                rx.cond(
                    item["status"] == "published",
                    ghost_button(
                        "Close submissions",
                        on_click=lambda: (
                            TrainerAssignmentWorkflowState.close_assignment(
                                item["id"]
                            )
                        ),
                    ),
                    rx.fragment(),
                ),
            ),
            class_name="mt-3 flex flex-wrap items-center gap-2",
        ),
        class_name=rx.cond(
            TrainerAssignmentWorkflowState.selected_assignment_id == item["id"],
            "cc-card cc-hover w-full min-w-0 border-amber-300 p-4",
            "cc-card cc-hover w-full min-w-0 p-4",
        ),
    )


def _grade_form(row: SubmissionRow) -> rx.Component:
    return rx.el.form(
        rx.el.input(
            type="hidden",
            name="submission_id",
            default_value=row["id"].to_string(),
        ),
        field(
            f"Marks awarded (0 – {row['total_marks']:.0f})",
            "marks_awarded",
            default_value=row["marks_awarded"].to_string(),
            input_type="number",
            required=True,
            step="0.5",
        ),
        textarea_field(
            "Constructive feedback (required)",
            "feedback",
            default_value=row["feedback"],
            placeholder="Explain what was done well and what to improve (minimum 20 characters).",
            rows="3",
        ),
        rx.el.div(
            primary_button(
                "Record grade",
                type="submit",
                disabled=TrainerAssignmentWorkflowState.is_saving,
            ),
            ghost_button(
                "Cancel",
                type="button",
                on_click=lambda: TrainerAssignmentWorkflowState.toggle_grading(
                    row["id"]
                ),
            ),
            class_name="flex flex-wrap items-center gap-2",
        ),
        on_submit=TrainerAssignmentWorkflowState.grade_submission,
        class_name="mt-3 flex w-full min-w-0 flex-col gap-3 rounded-lg border border-amber-200 bg-[#FBFAF7] p-3",
    )


def _submission_card(row: SubmissionRow) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.el.div(
                rx.image(
                    src=f"https://api.dicebear.com/9.x/initials/svg?seed={row['email']}",
                    class_name="size-9 shrink-0 rounded-full bg-slate-100",
                ),
                rx.el.div(
                    rx.el.p(
                        row["trainee"],
                        class_name="truncate text-sm font-semibold text-[#0A1B33]",
                    ),
                    rx.el.p(
                        row["email"],
                        class_name="truncate text-[0.7rem] font-medium text-slate-500",
                    ),
                    class_name="min-w-0",
                ),
                class_name="flex min-w-0 items-center gap-3",
            ),
            rx.el.div(
                rx.cond(
                    row["is_graded"],
                    chip("graded", "green"),
                    chip("awaiting grade", "amber"),
                ),
                rx.cond(row["is_late"], chip("late", "red"), rx.fragment()),
                class_name="flex shrink-0 flex-wrap items-center gap-2",
            ),
            class_name="flex w-full flex-wrap items-start justify-between gap-3",
        ),
        rx.el.p(
            f"Attempt {row['attempt_count']} · submitted {row['submitted_at']}",
            class_name="mt-2 text-[0.68rem] font-semibold uppercase tracking-wider text-slate-500",
        ),
        rx.el.p(
            row["response_text"],
            class_name="mt-1.5 text-xs font-medium leading-relaxed text-slate-700",
        ),
        rx.cond(
            row["submission_url"],
            rx.el.a(
                rx.icon("link", class_name="h-3.5 w-3.5"),
                "Open submitted evidence",
                href=row["submission_url"],
                target="_blank",
                rel="noopener noreferrer",
                class_name="cc-focus-amber mt-2 flex w-fit items-center gap-1.5 text-[0.7rem] font-semibold text-amber-700 underline outline-hidden hover:text-amber-600",
            ),
            rx.fragment(),
        ),
        rx.cond(
            row["is_graded"],
            rx.el.div(
                rx.el.span(
                    f"{row['marks_awarded']:.1f} / {row['total_marks']:.0f} marks · {row['graded_at']}",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    row["feedback"],
                    class_name="mt-1 text-xs font-medium leading-relaxed text-slate-700",
                ),
                class_name="mt-3 w-full rounded-lg border border-green-200 bg-green-50/70 p-3",
            ),
            rx.fragment(),
        ),
        rx.el.div(
            rx.cond(
                TrainerAssignmentWorkflowState.grading_submission_id
                == row["id"],
                ghost_button(
                    "Close grading form",
                    on_click=lambda: (
                        TrainerAssignmentWorkflowState.toggle_grading(row["id"])
                    ),
                ),
                primary_button(
                    rx.cond(row["is_graded"], "Revise grade", "Grade work"),
                    on_click=lambda: (
                        TrainerAssignmentWorkflowState.toggle_grading(row["id"])
                    ),
                ),
            ),
            class_name="mt-3 w-full",
        ),
        rx.cond(
            TrainerAssignmentWorkflowState.grading_submission_id == row["id"],
            _grade_form(row),
            rx.fragment(),
        ),
        class_name="cc-card w-full min-w-0 p-4",
    )


def _review_panel() -> rx.Component:
    return panel(
        "Submission review",
        "Learner identity, timestamps, submitted work and grading with bounded marks and required written feedback.",
        rx.cond(
            TrainerAssignmentWorkflowState.selected_assignment_id > 0,
            rx.el.div(
                rx.el.p(
                    TrainerAssignmentWorkflowState.selected_title,
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    TrainerAssignmentWorkflowState.selected_course,
                    class_name="text-[0.7rem] font-medium text-slate-500",
                ),
                class_name="w-full rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
            ),
            rx.fragment(),
        ),
        rx.cond(
            TrainerAssignmentWorkflowState.is_loading,
            loading_rows(2),
            rx.cond(
                TrainerAssignmentWorkflowState.has_submissions,
                rx.el.div(
                    rx.foreach(
                        TrainerAssignmentWorkflowState.submissions,
                        _submission_card,
                    ),
                    class_name="grid w-full min-w-0 grid-cols-1 gap-4 xl:grid-cols-2",
                ),
                empty_block(
                    "No submissions yet",
                    "Select a published assignment — trainee submissions appear here for grading as they arrive.",
                    "inbox",
                ),
            ),
        ),
        icon="check-check",
    )


def trainer_assignments_page() -> rx.Component:
    return trainer_page(
        "Assignments",
        "Assignments & grading",
        "Author practical assignments for the courses assigned to you, track deadline and submission progress, and grade learner work with written feedback.",
        TrainerAssignmentWorkflowState.error_message,
        TrainerAssignmentWorkflowState.success_message,
        _metrics(),
        _grading_band(),
        panel(
            "Create assignment",
            "Assignments can only be created for courses you are assigned to. Save as a draft or publish straight to the cohort.",
            rx.cond(
                TrainerAssignmentWorkflowState.has_courses,
                _create_form(),
                empty_block(
                    "No assigned courses",
                    "An administrator must assign you to a course before you can publish assignments.",
                    "book-open",
                ),
            ),
            icon="file-pen",
        ),
        panel(
            "My assignments",
            "Real submission counts, grading progress and deadline timelines for every assignment you authored.",
            rx.el.div(
                filter_select(
                    TrainerAssignmentWorkflowState.status_options,
                    TrainerAssignmentWorkflowState.status_filter,
                    TrainerAssignmentWorkflowState.set_status_filter,
                ),
                class_name="flex w-full flex-col gap-3 sm:flex-row sm:items-center",
            ),
            rx.cond(
                TrainerAssignmentWorkflowState.is_loading,
                loading_rows(3),
                rx.cond(
                    TrainerAssignmentWorkflowState.has_assignments,
                    rx.el.div(
                        rx.foreach(
                            TrainerAssignmentWorkflowState.filtered_assignments,
                            _assignment_row,
                        ),
                        class_name="grid w-full min-w-0 grid-cols-1 gap-4",
                    ),
                    empty_block(
                        "No assignments authored yet",
                        "Use the form above to create your first draft or published assignment.",
                        "clipboard-list",
                    ),
                ),
            ),
            icon="clipboard-list",
        ),
        _review_panel(),
    )

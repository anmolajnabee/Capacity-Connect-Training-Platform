"""Trainee assignment workspace: deadlines, submissions, grades and feedback."""

from __future__ import annotations

import reflex as rx

from app.components.trainee_shell import trainee_page
from app.components.trainee_ui import (
    chip,
    empty_block,
    ghost_button,
    loading_rows,
    metric_tile,
    panel,
    progress_bar,
    teal_button,
    textarea_field,
)
from app.states.trainee_assignment_state import (
    AssignmentCard,
    TraineeAssignmentState,
)


def _metrics() -> rx.Component:
    return rx.el.div(
        metric_tile(
            "Assignments",
            TraineeAssignmentState.metrics["total"].to_string(),
            "clipboard-list",
            "Published for your courses",
        ),
        metric_tile(
            "Pending",
            TraineeAssignmentState.metrics["pending"].to_string(),
            "hourglass",
            "Awaiting your submission",
        ),
        metric_tile(
            "Submitted",
            TraineeAssignmentState.metrics["submitted"].to_string(),
            "send",
            "With the trainer for review",
        ),
        metric_tile(
            "Graded",
            TraineeAssignmentState.metrics["graded"].to_string(),
            "badge-check",
            f"Mean score {TraineeAssignmentState.metrics['average']}%",
        ),
        metric_tile(
            "Overdue",
            TraineeAssignmentState.metrics["overdue"].to_string(),
            "triangle-alert",
            "Past the deadline",
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
                    f"{TraineeAssignmentState.grading_progress}% of your assignments have been graded",
                    class_name="mt-1 text-sm font-semibold text-[#0A1B33]",
                ),
                class_name="min-w-0",
            ),
            rx.el.span(
                TraineeAssignmentState.result_label,
                class_name="shrink-0 text-[0.7rem] font-semibold text-teal-700",
            ),
            class_name="flex w-full flex-wrap items-end justify-between gap-2",
        ),
        rx.el.div(
            progress_bar(TraineeAssignmentState.grading_progress),
            class_name="mt-2 w-full",
        ),
        class_name="cc-card w-full min-w-0 p-4",
    )


def _filter_chip(label: rx.Var) -> rx.Component:
    return rx.el.button(
        label,
        on_click=lambda: TraineeAssignmentState.set_bucket_filter(label),
        class_name=rx.cond(
            TraineeAssignmentState.bucket_filter == label,
            "cc-focus cc-press w-fit rounded-full border border-teal-600 bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white outline-hidden",
            "cc-focus cc-press w-fit rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 outline-hidden transition-colors hover:border-teal-400 hover:text-teal-700",
        ),
    )


def _bucket_chip(item: AssignmentCard) -> rx.Component:
    return rx.match(
        item["bucket"],
        ("graded", chip(item["status_label"], "green")),
        ("submitted", chip(item["status_label"], "teal")),
        ("overdue", chip(item["status_label"], "red")),
        chip(item["status_label"], "amber"),
    )


def _meta(label: str, value: rx.Var | str) -> rx.Component:
    return rx.el.div(
        rx.el.span(
            label,
            class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
        ),
        rx.el.span(
            value,
            class_name="text-xs font-semibold text-[#0A1B33]",
        ),
        class_name="min-w-0",
    )


def _timeline(item: AssignmentCard) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                "Deadline timeline",
                class_name="text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
            ),
            rx.cond(
                item["is_overdue"],
                rx.el.span(
                    "Deadline passed",
                    class_name="text-[0.7rem] font-semibold text-red-600",
                ),
                rx.el.span(
                    f"{item['days_left']} days remaining",
                    class_name="text-[0.7rem] font-semibold text-teal-700",
                ),
            ),
            class_name="flex items-center justify-between gap-2",
        ),
        rx.el.div(
            progress_bar(
                item["timeline"],
                "amber",
            ),
            class_name="mt-1.5",
        ),
        rx.el.p(
            f"Due {item['due_display']}",
            class_name="mt-1.5 text-[0.7rem] font-medium text-slate-500",
        ),
        class_name="mt-3 w-full rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def _grade_block(item: AssignmentCard) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.cond(
                item["is_passed"],
                chip("Pass", "green"),
                chip("Below pass mark", "amber"),
            ),
            rx.el.span(
                f"{item['marks_awarded']:.0f} / {item['total_marks']:.0f} marks · {item['score_percent']}%",
                class_name="text-xs font-semibold text-[#0A1B33]",
            ),
            class_name="flex flex-wrap items-center gap-2",
        ),
        rx.el.div(
            progress_bar(item["score_percent"]),
            class_name="mt-2",
        ),
        rx.el.p(
            item["feedback"],
            class_name="mt-2 text-xs font-medium leading-relaxed text-slate-700",
        ),
        rx.el.p(
            f"Graded by {item['graded_by']} · {item['graded_at']}",
            class_name="mt-1 text-[0.68rem] font-medium text-slate-500",
        ),
        class_name="mt-3 w-full rounded-lg border border-teal-200 bg-teal-50/60 p-3",
    )


def _submission_block(item: AssignmentCard) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                f"Attempt {item['attempt_count']} · {item['submitted_at']}",
                class_name="text-[0.68rem] font-semibold uppercase tracking-wider text-slate-500",
            ),
            rx.cond(item["is_late"], chip("late", "red"), rx.fragment()),
            class_name="flex flex-wrap items-center gap-2",
        ),
        rx.el.p(
            item["response_text"],
            class_name="mt-1.5 line-clamp-4 text-xs font-medium leading-relaxed text-slate-700",
        ),
        rx.cond(
            item["submission_url"],
            rx.el.a(
                rx.icon("link", class_name="h-3.5 w-3.5"),
                "Open submitted evidence",
                href=item["submission_url"],
                target="_blank",
                rel="noopener noreferrer",
                class_name="cc-focus mt-2 flex w-fit items-center gap-1.5 text-[0.7rem] font-semibold text-teal-700 underline outline-hidden hover:text-teal-600",
            ),
            rx.fragment(),
        ),
        class_name="mt-3 w-full rounded-lg border border-slate-200 bg-white p-3",
    )


def _form(item: AssignmentCard) -> rx.Component:
    return rx.el.form(
        rx.el.input(
            type="hidden",
            name="assignment_id",
            default_value=item["id"].to_string(),
        ),
        textarea_field(
            "Your submitted work",
            "response_text",
            default_value=item["response_text"],
            placeholder="Summarise your analysis, methodology and findings (minimum 40 characters).",
            rows="5",
        ),
        rx.el.label(
            rx.el.span(
                "Evidence / submission link (optional, HTTPS)",
                class_name="block text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
            ),
            rx.el.input(
                name="submission_url",
                type="url",
                placeholder="https://drive.example.gov/report.pdf",
                default_value=item["submission_url"],
                class_name="cc-focus mt-1 w-full rounded-[0.875rem] border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-900 outline-hidden transition-colors duration-200 focus:border-teal-600",
            ),
            class_name="flex w-full min-w-0 flex-col",
        ),
        rx.el.div(
            teal_button(
                rx.cond(
                    item["submission_id"] > 0,
                    "Resubmit work",
                    "Submit work",
                ),
                type="submit",
                disabled=TraineeAssignmentState.is_saving,
            ),
            ghost_button(
                "Cancel",
                type="button",
                on_click=TraineeAssignmentState.close_form,
            ),
            class_name="flex flex-wrap items-center gap-2",
        ),
        on_submit=TraineeAssignmentState.submit_work,
        class_name="mt-3 flex w-full min-w-0 flex-col gap-3 rounded-lg border border-teal-200 bg-[#FBFAF7] p-3",
    )


def _card(item: AssignmentCard) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            chip(item["course_code"], "navy"),
            chip(item["assignment_type"], "teal"),
            _bucket_chip(item),
            rx.cond(
                item["allow_late"],
                rx.fragment(),
                chip("no late work", "red"),
            ),
            class_name="flex flex-wrap items-center gap-2",
        ),
        rx.el.h3(
            item["title"],
            class_name="mt-3 text-base font-semibold leading-snug text-[#0A1B33]",
        ),
        rx.el.p(
            f"{item['course_title']} · {item['trainer_name']}",
            class_name="mt-0.5 truncate text-xs font-medium text-slate-500",
        ),
        rx.el.p(
            item["instructions"],
            class_name="mt-2 text-xs font-medium leading-relaxed text-slate-600",
        ),
        rx.cond(
            item["reference_url"],
            rx.el.a(
                rx.icon("external-link", class_name="h-3.5 w-3.5"),
                "Reference material",
                href=item["reference_url"],
                target="_blank",
                rel="noopener noreferrer",
                class_name="cc-focus mt-2 flex w-fit items-center gap-1.5 text-[0.7rem] font-semibold text-teal-700 underline outline-hidden hover:text-teal-600",
            ),
            rx.fragment(),
        ),
        rx.el.div(
            _meta(
                "Marks",
                f"{item['total_marks']:.0f} (pass {item['passing_marks']:.0f})",
            ),
            _meta("Late policy", item["late_policy"]),
            _meta(
                "Resubmission",
                rx.cond(item["allow_resubmission"], "Allowed", "Not allowed"),
            ),
            class_name="mt-3 grid w-full grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3 sm:grid-cols-3",
        ),
        _timeline(item),
        rx.cond(
            item["submission_note"],
            rx.el.p(
                item["submission_note"],
                class_name="mt-2 text-[0.7rem] font-medium italic text-slate-500",
            ),
            rx.fragment(),
        ),
        rx.cond(
            item["submission_id"] > 0,
            _submission_block(item),
            rx.fragment(),
        ),
        rx.cond(item["is_graded"], _grade_block(item), rx.fragment()),
        rx.el.div(
            rx.cond(
                item["can_submit"],
                rx.cond(
                    TraineeAssignmentState.open_assignment_id == item["id"],
                    ghost_button(
                        "Close submission form",
                        on_click=lambda: TraineeAssignmentState.toggle_form(
                            item["id"]
                        ),
                    ),
                    teal_button(
                        rx.cond(
                            item["submission_id"] > 0,
                            "Update submission",
                            "Submit work",
                        ),
                        on_click=lambda: TraineeAssignmentState.toggle_form(
                            item["id"]
                        ),
                    ),
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
        rx.cond(
            (TraineeAssignmentState.open_assignment_id == item["id"])
            & item["can_submit"],
            _form(item),
            rx.fragment(),
        ),
        class_name="cc-card cc-hover flex h-full w-full min-w-0 flex-col p-4",
    )


def trainee_assignments_page() -> rx.Component:
    return trainee_page(
        "Assignments",
        "Course assignments",
        "Practical assignments set by your trainers, with deadline timelines, submission history, marks and written feedback.",
        TraineeAssignmentState.error_message,
        TraineeAssignmentState.success_message,
        _metrics(),
        _grading_band(),
        panel(
            "Assignment queue",
            "Filter by pending, submitted, graded or overdue work. Only assignments for courses you are enrolled in appear here.",
            rx.el.div(
                rx.foreach(TraineeAssignmentState.bucket_options, _filter_chip),
                class_name="flex w-full flex-wrap items-center gap-2",
            ),
            rx.cond(
                TraineeAssignmentState.is_loading,
                loading_rows(3),
                rx.cond(
                    TraineeAssignmentState.has_assignments,
                    rx.cond(
                        TraineeAssignmentState.has_matches,
                        rx.el.div(
                            rx.foreach(
                                TraineeAssignmentState.filtered_assignments,
                                _card,
                            ),
                            class_name="grid w-full min-w-0 grid-cols-1 gap-4 xl:grid-cols-2",
                        ),
                        empty_block(
                            "Nothing in this view",
                            "Switch the filter to see assignments in another state.",
                            "filter",
                        ),
                    ),
                    empty_block(
                        "No assignments yet",
                        "Once your trainers publish assignments for your enrolled courses they will appear here with deadlines and marks.",
                        "clipboard-list",
                    ),
                ),
            ),
            icon="clipboard-list",
        ),
    )

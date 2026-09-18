"""Trainer dashboard: portfolio summary and cohort snapshot."""

from __future__ import annotations

import reflex as rx

from app.components.trainee_ui import (
    chip,
    empty_block,
    loading_rows,
    metric_tile,
    panel,
    progress_bar,
)
from app.components.trainer_shell import trainer_page
from app.states.trainer_state import TrainerState


def _course_card(course) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    course["code"],
                    class_name="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-teal-700",
                ),
                rx.el.h3(
                    course["title"],
                    class_name="mt-1 text-sm font-semibold text-[#0A1B33]",
                ),
                class_name="min-w-0",
            ),
            chip(course["role"], "amber"),
            class_name="flex items-start justify-between gap-3",
        ),
        rx.el.div(
            rx.el.span(
                f"{course['cohort']} enrolled",
                class_name="text-xs font-medium text-slate-600",
            ),
            rx.el.span(
                f"{course['completed']} completed",
                class_name="text-xs font-medium text-slate-600",
            ),
            rx.el.span(
                f"{course['completion']}%",
                class_name="text-xs font-semibold text-teal-700",
            ),
            class_name="mt-3 flex items-center justify-between gap-2",
        ),
        rx.el.div(progress_bar(course["completion"]), class_name="mt-2"),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-[#FBFAF7] p-4",
    )


def _quick_link(
    label: str, description: str, href: str, icon: str
) -> rx.Component:
    return rx.el.a(
        rx.el.div(
            rx.icon(icon, class_name="h-4 w-4 text-teal-700"),
            class_name="flex size-9 shrink-0 items-center justify-center rounded-lg border border-teal-200 bg-teal-50",
        ),
        rx.el.div(
            rx.el.p(label, class_name="text-sm font-semibold text-[#0A1B33]"),
            rx.el.p(
                description,
                class_name="text-xs font-medium text-slate-500",
            ),
            class_name="min-w-0",
        ),
        rx.icon("arrow-right", class_name="ml-auto h-4 w-4 text-slate-400"),
        href=href,
        class_name="flex w-full min-w-0 items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 transition-colors hover:border-teal-300 hover:bg-teal-50/40",
    )


def trainer_dashboard_page() -> rx.Component:
    return trainer_page(
        "Dashboard",
        "Training command centre",
        "Your assigned cohorts, published material, live assessments and the trainees who need attention today.",
        TrainerState.error_message,
        TrainerState.success_message,
        rx.el.div(
            metric_tile(
                "Assigned courses",
                TrainerState.metrics["courses"].to_string(),
                "presentation",
                "Active teaching allocations",
            ),
            metric_tile(
                "Trainees",
                TrainerState.metrics["trainees"].to_string(),
                "users",
                "Across all your cohorts",
            ),
            metric_tile(
                "Completions",
                TrainerState.metrics["completed"].to_string(),
                "badge-check",
                "Finished the programme",
            ),
            metric_tile(
                "Needs attention",
                TrainerState.metrics["at_risk"].to_string(),
                "triangle-alert",
                "At risk or idle trainees",
            ),
            class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
        ),
        rx.el.div(
            metric_tile(
                "Resources",
                TrainerState.metrics["resources"].to_string(),
                "library",
                "Library items on your courses",
            ),
            metric_tile(
                "Assessments",
                TrainerState.metrics["assessments"].to_string(),
                "list-checks",
                f"{TrainerState.metrics['open_assessments']} currently open",
            ),
            metric_tile(
                "Avg cohort progress",
                f"{TrainerState.average_score:.1f}%",
                "activity",
                "Mean enrolment progress",
            ),
            metric_tile(
                "Teachable skills",
                TrainerState.teachable_count.to_string(),
                "target",
                f"Profile {TrainerState.profile_completion}% complete",
            ),
            class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
        ),
        rx.el.div(
            panel(
                "Assigned cohorts",
                "Completion is measured as finished enrolments over total enrolments.",
                rx.cond(
                    TrainerState.is_loading,
                    loading_rows(3),
                    rx.cond(
                        TrainerState.dashboard_courses.length() > 0,
                        rx.el.div(
                            rx.foreach(
                                TrainerState.dashboard_courses, _course_card
                            ),
                            class_name="grid w-full grid-cols-1 gap-4 md:grid-cols-2",
                        ),
                        empty_block(
                            "No courses assigned yet",
                            "An administrator assigns courses using the competency match. Keep your teachable skills current.",
                            "presentation",
                        ),
                    ),
                ),
                icon="presentation",
            ),
            panel(
                "Operational shortcuts",
                "Jump straight to the task that needs you.",
                rx.el.div(
                    _quick_link(
                        "Trainees",
                        "Search the roster and triage risk",
                        "/trainer/trainees",
                        "users",
                    ),
                    _quick_link(
                        "Upload content",
                        "Videos, PDFs, slides and notes",
                        "/trainer/upload",
                        "cloud-upload",
                    ),
                    _quick_link(
                        "Create assessment",
                        "Author MCQ questionnaires",
                        "/trainer/assessments/create",
                        "list-checks",
                    ),
                    _quick_link(
                        "Trainer library",
                        "Published module material",
                        "/trainer/library",
                        "library",
                    ),
                    _quick_link(
                        "Performance matrix",
                        "Completion and score analysis",
                        "/trainer/performance",
                        "chart-line",
                    ),
                    class_name="flex w-full flex-col gap-3",
                ),
                icon="compass",
            ),
            class_name="grid w-full grid-cols-1 gap-6 xl:grid-cols-[1.6fr_1fr]",
        ),
    )

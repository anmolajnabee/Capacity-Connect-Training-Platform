"""Trainer performance views: cohort status matrix and aggregate bars."""

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
from app.pages.trainer_courses import classification_chip
from app.states.trainer_course_state import TrainerCourseState


def _matrix_cell(row) -> rx.Component:
    return rx.el.div(
        rx.el.p(
            row["trainee"],
            class_name="truncate text-xs font-semibold text-[#0A1B33]",
        ),
        rx.el.p(
            row["course_code"],
            class_name="truncate text-[0.65rem] font-medium uppercase tracking-wider text-slate-500",
        ),
        rx.el.div(
            rx.el.span(
                f"{row['progress']}%",
                class_name="text-[0.7rem] font-semibold text-slate-700",
            ),
            rx.el.span(
                row["last_activity"],
                class_name="text-[0.65rem] font-medium text-slate-500",
            ),
            class_name="mt-1 flex items-center justify-between gap-2",
        ),
        rx.el.div(progress_bar(row["progress"]), class_name="mt-1"),
        rx.el.div(
            classification_chip(row["classification"]),
            class_name="mt-2",
        ),
        class_name=rx.match(
            row["classification"],
            (
                "high-performing",
                "w-full min-w-0 rounded-lg border border-green-200 bg-green-50 p-3",
            ),
            (
                "at-risk",
                "w-full min-w-0 rounded-lg border border-amber-300 bg-amber-50 p-3",
            ),
            (
                "inactive",
                "w-full min-w-0 rounded-lg border border-red-200 bg-red-50 p-3",
            ),
            (
                "completed",
                "w-full min-w-0 rounded-lg border border-teal-200 bg-teal-50 p-3",
            ),
            "w-full min-w-0 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
        ),
    )


def _course_row(row) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.p(
                row["code"],
                class_name="text-xs font-semibold text-teal-700",
            ),
            rx.el.p(
                row["title"],
                class_name="text-xs font-medium text-slate-700",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.span(
                row["cohort"].to_string(),
                class_name="text-xs font-semibold text-slate-700",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.span(
                    f"{row['completion']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["completion"]),
                class_name="flex w-32 flex-col gap-1",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.span(
                    f"{row['avg_progress']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["avg_progress"], "navy"),
                class_name="flex w-32 flex-col gap-1",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.span(
                    f"{row['avg_score']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["avg_score"], "amber"),
                class_name="flex w-32 flex-col gap-1",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.div(
                chip(f"{row['high']} high", "green"),
                chip(f"{row['at_risk']} risk", "amber"),
                chip(f"{row['inactive']} idle", "red"),
                chip(f"{row['incomplete']} open", "navy"),
                class_name="flex flex-wrap items-center gap-1.5",
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


def _legend() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(class_name="size-3 rounded-sm bg-green-300"),
            rx.el.span(
                "high-performing · ≥75% progress, ≥70% mean score",
                class_name="text-[0.7rem] font-medium text-slate-600",
            ),
            class_name="flex items-center gap-2",
        ),
        rx.el.div(
            rx.el.span(class_name="size-3 rounded-sm bg-amber-300"),
            rx.el.span(
                "at-risk · <40% progress, flagged status or <50% mean score",
                class_name="text-[0.7rem] font-medium text-slate-600",
            ),
            class_name="flex items-center gap-2",
        ),
        rx.el.div(
            rx.el.span(class_name="size-3 rounded-sm bg-red-300"),
            rx.el.span(
                "inactive · no activity for 21 days or more",
                class_name="text-[0.7rem] font-medium text-slate-600",
            ),
            class_name="flex items-center gap-2",
        ),
        rx.el.div(
            rx.el.span(class_name="size-3 rounded-sm bg-slate-300"),
            rx.el.span(
                "incomplete · progressing but not yet finished",
                class_name="text-[0.7rem] font-medium text-slate-600",
            ),
            class_name="flex items-center gap-2",
        ),
        class_name="grid w-full grid-cols-1 gap-2 md:grid-cols-2 xl:grid-cols-4",
    )


def trainer_performance_page() -> rx.Component:
    return trainer_page(
        "Performance",
        "Cohort performance map",
        "A weather-map style status matrix over every trainee you teach, with aggregate completion and score bars per course.",
        TrainerCourseState.error_message,
        TrainerCourseState.success_message,
        rx.el.div(
            metric_tile(
                "Trainees tracked",
                TrainerCourseState.totals["cohort"].to_string(),
                "users",
                "Across assigned cohorts",
            ),
            metric_tile(
                "High performing",
                TrainerCourseState.totals["high"].to_string(),
                "trending-up",
                "Strong progress and scores",
            ),
            metric_tile(
                "At risk",
                TrainerCourseState.totals["at_risk"].to_string(),
                "triangle-alert",
                "Low progress or weak scores",
            ),
            metric_tile(
                "Inactive",
                TrainerCourseState.totals["inactive"].to_string(),
                "moon",
                "Idle 21 days or more",
            ),
            class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
        ),
        panel(
            "Aggregate course performance",
            "Completion, mean progress and mean assessment score, computed from enrolment and result records.",
            rx.cond(
                TrainerCourseState.is_loading,
                loading_rows(3),
                rx.cond(
                    TrainerCourseState.performance.length() > 0,
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    _th("Course", "book-open"),
                                    _th("Cohort", "users"),
                                    _th("Completion", "badge-check"),
                                    _th("Mean progress", "activity"),
                                    _th("Mean score", "percent"),
                                    _th("Classification split", "flag"),
                                ),
                                class_name="bg-[#F1F5F9]",
                            ),
                            rx.el.tbody(
                                rx.foreach(
                                    TrainerCourseState.performance, _course_row
                                )
                            ),
                            class_name="w-full table-auto",
                        ),
                        class_name="w-full overflow-x-auto overflow-hidden rounded-lg border border-slate-200",
                    ),
                    empty_block(
                        "No cohort data yet",
                        "Performance appears once trainees enrol in the courses you teach.",
                        "chart-line",
                    ),
                ),
            ),
            icon="chart-line",
        ),
        panel(
            "Cohort status matrix",
            "Each tile is one trainee-course pairing, coloured by classification like a station status map.",
            _legend(),
            rx.cond(
                TrainerCourseState.roster.length() > 0,
                rx.el.div(
                    rx.foreach(TrainerCourseState.roster, _matrix_cell),
                    class_name="grid w-full grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
                ),
                empty_block(
                    "No trainees to plot",
                    "The status matrix fills in as trainees enrol and record activity.",
                    "grid-3x3",
                ),
            ),
            icon="grid-3x3",
        ),
    )

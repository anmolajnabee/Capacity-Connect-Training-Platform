"""Trainee dashboard: metrics, next actions, skill matrix and progress pathway."""

from __future__ import annotations

import reflex as rx

from app.components.trainee_shell import trainee_page
from app.components.trainee_ui import (
    chip,
    empty_block,
    loading_rows,
    metric_tile,
    panel,
    progress_bar,
    skill_meter,
    status_chip,
)
from app.states.trainee_state import NextAction, ProgressRow, TraineeState


def _metrics() -> rx.Component:
    return rx.el.div(
        metric_tile(
            "Enrolments",
            TraineeState.metrics["enrollments"].to_string(),
            "book-open",
            f"{TraineeState.metrics['active']} active · {TraineeState.metrics['completed']} completed",
        ),
        metric_tile(
            "Avg progress",
            f"{TraineeState.metrics['avg_progress']}%",
            "activity",
            f"{TraineeState.metrics['resources_done']} resources completed",
        ),
        metric_tile(
            "Assessments open",
            TraineeState.metrics["assessments_open"].to_string(),
            "clipboard-check",
            f"{TraineeState.metrics['results']} graded results",
        ),
        metric_tile(
            "Avg score",
            f"{TraineeState.metrics['avg_score']}%",
            "gauge",
            f"{TraineeState.metrics['certificates']} certificates issued",
        ),
        class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
    )


def _action_card(action: NextAction) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(action["icon"], class_name="h-4 w-4 text-teal-700"),
                class_name="flex size-9 shrink-0 items-center justify-center rounded-lg border border-teal-200 bg-teal-50",
            ),
            rx.el.div(
                rx.el.p(
                    action["title"],
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    action["detail"],
                    class_name="mt-1 text-xs font-medium leading-relaxed text-slate-500",
                ),
                class_name="min-w-0",
            ),
            class_name="flex items-start gap-3",
        ),
        rx.el.a(
            action["cta"],
            rx.icon("arrow-right", class_name="h-3.5 w-3.5"),
            href=action["href"],
            class_name="mt-3 flex w-fit items-center gap-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-[#0A1B33] transition-colors hover:border-teal-300 hover:bg-teal-50",
        ),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def _progress_row(row: ProgressRow) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                chip(row["code"], "navy"),
                rx.el.p(
                    row["title"],
                    class_name="truncate text-sm font-semibold text-[#0A1B33]",
                ),
                class_name="flex min-w-0 items-center gap-2",
            ),
            rx.el.div(
                rx.el.span(
                    f"{row['completed_resources']}/{row['total_resources']} resources",
                    class_name="text-[0.7rem] font-medium text-slate-500",
                ),
                status_chip(row["status"], row["progress"] >= 100),
                class_name="flex shrink-0 items-center gap-2",
            ),
            class_name="flex flex-wrap items-center justify-between gap-2",
        ),
        rx.el.div(
            progress_bar(row["progress"]),
            rx.el.span(
                f"{row['progress']}%",
                class_name="w-10 shrink-0 text-right text-xs font-semibold text-teal-700",
            ),
            class_name="mt-2 flex items-center gap-3",
        ),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-white p-3",
    )


def _matrix_panel() -> rx.Component:
    return panel(
        "Competency matrix",
        "Skill meters drive course recommendations, trainer matching and certification.",
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Matrix mean",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.p(
                    f"{TraineeState.average_skill_score}%",
                    class_name="text-xl font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Strongest",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.p(
                    TraineeState.strongest_skill,
                    class_name="truncate text-sm font-semibold text-teal-700",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Priority gap",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.p(
                    TraineeState.weakest_skill,
                    class_name="truncate text-sm font-semibold text-amber-700",
                ),
            ),
            class_name="grid w-full grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3 sm:grid-cols-3",
        ),
        rx.cond(
            TraineeState.has_skills,
            rx.el.div(
                rx.foreach(TraineeState.skills, skill_meter),
                class_name="grid w-full grid-cols-1 gap-3 md:grid-cols-2",
            ),
            empty_block(
                "No skills recorded yet",
                "Add skills with proficiency scores on the Profile tab to build your matrix.",
                "grid-3x3",
            ),
        ),
        icon="grid-3x3",
    )


def trainee_dashboard_page() -> rx.Component:
    return trainee_page(
        "Dashboard",
        "Learning command centre",
        "Live view of your enrolments, competency matrix, open assessments and certification pipeline.",
        TraineeState.error_message,
        TraineeState.success_message,
        rx.cond(
            TraineeState.is_loading,
            rx.el.div(
                rx.el.div(
                    rx.foreach(
                        [0, 1, 2, 3],
                        lambda _slot: rx.el.div(
                            class_name="h-24 w-full animate-pulse rounded-xl border border-slate-200 bg-white"
                        ),
                    ),
                    class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
                ),
                loading_rows(4),
                class_name="flex w-full flex-col gap-6",
            ),
            rx.el.div(
                _metrics(),
                rx.el.div(
                    _matrix_panel(),
                    rx.el.div(
                        panel(
                            "Next actions",
                            "Prioritised steps generated from your live records.",
                            rx.cond(
                                TraineeState.next_actions.length() > 0,
                                rx.el.div(
                                    rx.foreach(
                                        TraineeState.next_actions, _action_card
                                    ),
                                    class_name="flex w-full flex-col gap-3",
                                ),
                                empty_block(
                                    "You are all caught up",
                                    "No outstanding profile, learning or assessment actions.",
                                    "circle-check",
                                ),
                            ),
                            icon="list-checks",
                        ),
                        panel(
                            "Progress pathway",
                            "Resource completion recalculates enrolment progress automatically.",
                            rx.cond(
                                TraineeState.progress_rows.length() > 0,
                                rx.el.div(
                                    rx.foreach(
                                        TraineeState.progress_rows,
                                        _progress_row,
                                    ),
                                    class_name="flex w-full flex-col gap-3",
                                ),
                                empty_block(
                                    "No enrolments yet",
                                    "Discover published courses and enrol to start your pathway.",
                                    "compass",
                                ),
                            ),
                            icon="git-branch",
                        ),
                        class_name="flex w-full min-w-0 flex-col gap-6",
                    ),
                    class_name="grid w-full min-w-0 grid-cols-1 gap-6 xl:grid-cols-2",
                ),
                class_name="flex w-full min-w-0 flex-col gap-6",
            ),
        ),
    )

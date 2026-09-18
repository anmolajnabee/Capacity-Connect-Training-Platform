"""Assigned courses and trainee oversight roster."""

from __future__ import annotations

import reflex as rx

from app.components.trainee_ui import (
    chip,
    empty_block,
    ghost_button,
    loading_rows,
    panel,
    progress_bar,
)
from app.components.trainer_shell import trainer_page
from app.states.trainer_course_state import TrainerCourseState


def classification_chip(value: rx.Var) -> rx.Component:
    return rx.match(
        value,
        ("high-performing", chip("high-performing", "green")),
        ("at-risk", chip("at-risk", "amber")),
        ("inactive", chip("inactive", "red")),
        ("completed", chip("completed", "teal")),
        chip("incomplete", "navy"),
    )


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
                    class_name="mt-1 text-base font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    course["window"],
                    class_name="mt-1 text-xs font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                chip(course["role"], "amber"),
                chip(course["status"], "navy"),
                class_name="flex shrink-0 flex-col items-end gap-2",
            ),
            class_name="flex items-start justify-between gap-3",
        ),
        rx.el.div(
            chip(course["category"], "teal"),
            chip(course["level"], "navy"),
            chip(course["mode"], "navy"),
            chip(f"match {course['match_score']:.0f}%", "teal"),
            class_name="mt-3 flex flex-wrap items-center gap-2",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    course["cohort"].to_string(),
                    class_name="text-lg font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    "Cohort",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                rx.el.p(
                    course["active"].to_string(),
                    class_name="text-lg font-semibold text-teal-700",
                ),
                rx.el.p(
                    "Active",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                rx.el.p(
                    course["completed"].to_string(),
                    class_name="text-lg font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    "Completed",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                rx.el.p(
                    course["at_risk"].to_string(),
                    class_name="text-lg font-semibold text-amber-600",
                ),
                rx.el.p(
                    "Needs help",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                class_name="min-w-0",
            ),
            class_name="mt-4 grid w-full grid-cols-2 gap-3 sm:grid-cols-4",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Cohort completion",
                    class_name="text-xs font-medium text-slate-600",
                ),
                rx.el.span(
                    f"{course['completion']}%",
                    class_name="text-xs font-semibold text-teal-700",
                ),
                class_name="flex items-center justify-between gap-2",
            ),
            progress_bar(course["completion"]),
            rx.el.p(
                f"Average progress {course['avg_progress']:.1f}% · {course['resources']} resources published",
                class_name="mt-1 text-[0.7rem] font-medium text-slate-500",
            ),
            class_name="mt-4 flex w-full flex-col gap-1",
        ),
        class_name="w-full min-w-0 rounded-xl border border-slate-200 bg-white p-4",
    )


def _roster_row(row) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.div(
                rx.el.p(
                    row["trainee"],
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    row["email"],
                    class_name="text-xs font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.p(
                row["course_code"],
                class_name="text-xs font-semibold text-teal-700",
            ),
            rx.el.p(
                row["course"],
                class_name="text-xs font-medium text-slate-600",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.div(
                rx.el.span(
                    f"{row['progress']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["progress"]),
                class_name="flex w-32 flex-col gap-1",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.span(
                f"{row['avg_score']:.0f}%",
                class_name="text-xs font-semibold text-slate-700",
            ),
            rx.el.p(
                f"{row['attempts']} attempts",
                class_name="text-[0.7rem] font-medium text-slate-500",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.span(
                row["last_activity"],
                class_name="text-xs font-medium text-slate-600",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            classification_chip(row["classification"]),
            class_name="px-3 py-2",
        ),
        class_name="border-b border-slate-100 odd:bg-white even:bg-[#FBFAF7] hover:bg-teal-50/50",
    )


def _header_cell(label: str, icon: str) -> rx.Component:
    return rx.el.th(
        rx.el.div(
            rx.icon(icon, class_name="h-3.5 w-3.5 text-slate-400"),
            rx.el.span(label),
            class_name="flex items-center gap-1.5",
        ),
        class_name="px-3 py-2 text-left text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
    )


def _filters() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(
                "search",
                class_name="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
            ),
            rx.el.input(
                placeholder="Search trainee, email or course code",
                default_value=TrainerCourseState.search_query,
                on_change=TrainerCourseState.set_search_query.debounce(400),
                class_name="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm font-medium text-slate-900 outline-hidden focus:border-teal-500 focus:ring-2 focus:ring-teal-500/30",
            ),
            class_name="relative w-full min-w-0 sm:max-w-sm",
        ),
        rx.el.div(
            rx.el.select(
                rx.foreach(
                    TrainerCourseState.status_options,
                    lambda option: rx.el.option(option, value=option),
                ),
                value=TrainerCourseState.status_filter,
                on_change=TrainerCourseState.set_status_filter,
                class_name="w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2 pr-9 text-sm font-medium text-slate-900 outline-hidden focus:border-teal-500",
            ),
            rx.icon(
                "chevron-down",
                class_name="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
            ),
            class_name="relative w-full min-w-0 sm:w-48",
        ),
        rx.el.div(
            rx.el.select(
                rx.foreach(
                    TrainerCourseState.course_names,
                    lambda option: rx.el.option(option, value=option),
                ),
                value=TrainerCourseState.course_filter,
                on_change=TrainerCourseState.set_course_filter,
                class_name="w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2 pr-9 text-sm font-medium text-slate-900 outline-hidden focus:border-teal-500",
            ),
            rx.icon(
                "chevron-down",
                class_name="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
            ),
            class_name="relative w-full min-w-0 sm:w-64",
        ),
        ghost_button("Reset", on_click=TrainerCourseState.clear_filters),
        class_name="flex w-full flex-col gap-3 sm:flex-row sm:items-center",
    )


def _course_grid() -> rx.Component:
    return rx.cond(
        TrainerCourseState.is_loading,
        loading_rows(4),
        rx.cond(
            TrainerCourseState.courses.length() > 0,
            rx.el.div(
                rx.foreach(TrainerCourseState.courses, _course_card),
                class_name="grid w-full grid-cols-1 gap-5 xl:grid-cols-2",
            ),
            empty_block(
                "No assigned courses",
                "Once an administrator assigns you to a course, its cohort will appear here.",
                "presentation",
            ),
        ),
    )


def _roster_panel() -> rx.Component:
    return panel(
        "Trainee roster",
        "Classification thresholds: inactive ≥ 21 idle days · at-risk < 40% progress, flagged status or mean score < 50% · high-performing ≥ 75% progress with mean score ≥ 70%.",
        _filters(),
        rx.cond(
            TrainerCourseState.filtered_roster.length() > 0,
            rx.el.div(
                rx.el.table(
                    rx.el.thead(
                        rx.el.tr(
                            _header_cell("Trainee", "user"),
                            _header_cell("Course", "book-open"),
                            _header_cell("Progress", "activity"),
                            _header_cell("Mean score", "percent"),
                            _header_cell("Last activity", "clock"),
                            _header_cell("Classification", "flag"),
                        ),
                        class_name="bg-[#F1F5F9]",
                    ),
                    rx.el.tbody(
                        rx.foreach(
                            TrainerCourseState.filtered_roster, _roster_row
                        )
                    ),
                    class_name="w-full table-auto",
                ),
                class_name="w-full overflow-x-auto overflow-hidden rounded-lg border border-slate-200",
            ),
            empty_block(
                "No trainees match these filters",
                "Adjust the search text, status or course filter to widen the roster.",
                "users",
            ),
        ),
        icon="users",
    )


def trainer_courses_page() -> rx.Component:
    return trainer_page(
        "My Courses",
        "My courses",
        "Cohort load, completion and content coverage for every course you are assigned to deliver.",
        TrainerCourseState.error_message,
        TrainerCourseState.success_message,
        _course_grid(),
        rx.el.div(
            rx.el.a(
                rx.icon("users", class_name="h-4 w-4"),
                rx.el.span("Open the full trainee roster"),
                href="/trainer/trainees",
                class_name="cc-focus-amber flex w-fit items-center gap-2 rounded-[0.875rem] border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-800 outline-hidden transition-all duration-200 hover:bg-amber-100",
            ),
            class_name="flex w-full",
        ),
    )


def trainer_trainees_page() -> rx.Component:
    return trainer_page(
        "Trainees",
        "Trainee oversight",
        "A searchable roster of every trainee on your courses, classified by progress, activity and assessment results.",
        TrainerCourseState.error_message,
        TrainerCourseState.success_message,
        _roster_panel(),
    )

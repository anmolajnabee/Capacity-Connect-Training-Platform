"""Trainee course discovery and enrolment."""

from __future__ import annotations

import reflex as rx

from app.components.trainee_shell import trainee_page
from app.components.trainee_ui import (
    chip,
    empty_block,
    loading_rows,
    panel,
)
from app.states.trainee_learning_state import (
    DiscoverCourse,
    TraineeLearningState,
)


def _filters() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(
                "search",
                class_name="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
            ),
            rx.el.input(
                placeholder="Search by title, code, trainer or competency",
                default_value=TraineeLearningState.search_query,
                on_change=TraineeLearningState.set_search_query.debounce(400),
                class_name="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm font-medium text-slate-900 outline-hidden focus:border-teal-500 focus:ring-2 focus:ring-teal-500/30",
            ),
            class_name="relative w-full min-w-0 flex-1",
        ),
        rx.el.div(
            rx.el.select(
                rx.foreach(
                    TraineeLearningState.categories,
                    lambda item: rx.el.option(item, value=item),
                ),
                value=TraineeLearningState.category_filter,
                on_change=TraineeLearningState.set_category_filter,
                class_name="w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2 pr-9 text-sm font-medium text-slate-900 outline-hidden focus:border-teal-500",
            ),
            rx.icon(
                "chevron-down",
                class_name="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
            ),
            class_name="relative w-full sm:w-48",
        ),
        rx.el.div(
            rx.el.select(
                rx.foreach(
                    TraineeLearningState.levels,
                    lambda item: rx.el.option(item, value=item),
                ),
                value=TraineeLearningState.level_filter,
                on_change=TraineeLearningState.set_level_filter,
                class_name="w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2 pr-9 text-sm font-medium text-slate-900 outline-hidden focus:border-teal-500",
            ),
            rx.icon(
                "chevron-down",
                class_name="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
            ),
            class_name="relative w-full sm:w-44",
        ),
        rx.el.button(
            rx.icon("filter", class_name="h-4 w-4"),
            "Open for enrolment",
            on_click=TraineeLearningState.toggle_only_open,
            class_name=rx.cond(
                TraineeLearningState.only_open,
                "flex w-full items-center justify-center gap-2 rounded-lg border border-teal-500 bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-800 sm:w-auto",
                "flex w-full items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 sm:w-auto",
            ),
        ),
        rx.el.button(
            rx.icon("rotate-ccw", class_name="h-4 w-4"),
            "Reset",
            on_click=TraineeLearningState.clear_filters,
            class_name="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 sm:w-auto",
        ),
        class_name="flex w-full min-w-0 flex-col gap-3 sm:flex-row sm:items-center",
    )


def _course_card(course: DiscoverCourse) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            chip(course["code"], "navy"),
            chip(course["category"], "amber"),
            chip(course["level"]),
            class_name="flex flex-wrap items-center gap-2",
        ),
        rx.el.h3(
            course["title"],
            class_name="mt-3 text-base font-semibold leading-snug text-[#0A1B33]",
        ),
        rx.el.p(
            course["summary"],
            class_name="mt-1 line-clamp-3 text-xs font-medium leading-relaxed text-slate-600",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Trainer",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    course["trainer_name"],
                    class_name="block truncate text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Starts",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    course["start_date"],
                    class_name="block text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Hours",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    f"{course['duration_hours']:.0f}",
                    class_name="block text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Seats left",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    course["seats_left"].to_string(),
                    class_name="block text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Resources",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    course["resource_count"].to_string(),
                    class_name="block text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Closes",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    course["deadline"],
                    class_name="block text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            class_name="mt-3 grid w-full grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3 sm:grid-cols-3",
        ),
        rx.cond(
            course["skills"].length() > 0,
            rx.el.div(
                rx.foreach(course["skills"], lambda name: chip(name)),
                class_name="mt-3 flex flex-wrap gap-2",
            ),
            rx.fragment(),
        ),
        rx.el.div(
            rx.cond(
                course["is_enrolled"],
                rx.el.div(
                    chip("Enrolled", "green"),
                    rx.el.a(
                        "Open modules",
                        rx.icon("arrow-right", class_name="h-3.5 w-3.5"),
                        href="/trainee/learning",
                        class_name="flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-[#0A1B33] hover:bg-slate-100",
                    ),
                    class_name="flex flex-wrap items-center gap-2",
                ),
                rx.cond(
                    course["is_open"],
                    rx.el.button(
                        rx.icon("user-plus", class_name="h-4 w-4"),
                        "Enrol now",
                        on_click=lambda: TraineeLearningState.enroll(
                            course["id"]
                        ),
                        class_name="flex items-center gap-2 rounded-lg bg-teal-600 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-teal-500",
                    ),
                    rx.el.div(
                        rx.icon(
                            "lock", class_name="h-3.5 w-3.5 text-amber-700"
                        ),
                        rx.el.span(
                            course["closed_reason"],
                            class_name="text-xs font-semibold text-amber-800",
                        ),
                        class_name="flex w-full items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2",
                    ),
                ),
            ),
            class_name="mt-4 flex w-full items-center justify-between gap-3",
        ),
        class_name="flex h-full w-full min-w-0 flex-col rounded-xl border border-slate-200 bg-white p-4 transition-colors hover:border-teal-300",
    )


def trainee_courses_page() -> rx.Component:
    return trainee_page(
        "Courses",
        "Course discovery",
        "Search the published catalogue, filter by category or level and enrol with live seat and deadline checks.",
        TraineeLearningState.error_message,
        TraineeLearningState.success_message,
        panel(
            "Filters",
            TraineeLearningState.discovery_count_label,
            _filters(),
            icon="sliders-horizontal",
        ),
        rx.cond(
            TraineeLearningState.is_loading,
            loading_rows(4),
            rx.cond(
                TraineeLearningState.filtered_courses.length() > 0,
                rx.el.div(
                    rx.foreach(
                        TraineeLearningState.filtered_courses, _course_card
                    ),
                    class_name="grid w-full min-w-0 grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3",
                ),
                empty_block(
                    "No courses match these filters",
                    "Reset the filters or widen your search to see the full published catalogue.",
                    "compass",
                ),
            ),
        ),
    )

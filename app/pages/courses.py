"""Public course catalogue with search and category filtering."""

import reflex as rx

from app.components.cards import (
    course_card,
    empty_state,
    error_banner,
    loading_grid,
)
from app.components.layout import page_shell
from app.states.public_state import PublicState


def _category_button(category: str) -> rx.Component:
    return rx.el.button(
        category,
        on_click=lambda: PublicState.set_category_filter(category),
        class_name=rx.cond(
            PublicState.category_filter == category,
            "w-fit rounded-full border border-teal-600 bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white",
            "w-fit rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-400",
        ),
    )


def _controls() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(
                "search",
                class_name="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
            ),
            rx.el.input(
                placeholder="Search by course, code, trainer or skill",
                default_value=PublicState.search_query,
                on_change=PublicState.set_search_query.debounce(400),
                class_name="w-full rounded-lg border border-slate-300 bg-white py-2.5 pl-9 pr-3 text-sm font-medium text-slate-900 placeholder:text-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-500 outline-hidden",
            ),
            class_name="relative w-full sm:max-w-md",
        ),
        rx.el.div(
            rx.foreach(PublicState.categories, _category_button),
            class_name="flex flex-wrap gap-2",
        ),
        class_name="flex w-full flex-col gap-4 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between",
    )


def courses_page() -> rx.Component:
    return page_shell(
        rx.el.section(
            rx.el.div(
                rx.el.span(
                    "Course catalogue",
                    class_name="w-fit rounded-full border border-teal-400/40 bg-teal-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-teal-200",
                ),
                rx.el.h1(
                    "Programmes mapped to required competencies",
                    class_name="mt-4 text-3xl font-semibold leading-tight text-white sm:text-4xl",
                ),
                rx.el.p(
                    "Filter the catalogue by competency area, then register to "
                    "nominate yourself for enrolment.",
                    class_name="mt-3 max-w-2xl text-sm font-medium leading-relaxed text-slate-300",
                ),
                class_name="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6",
            ),
            class_name="w-full bg-[#0A1B33]",
        ),
        rx.el.section(
            rx.el.div(
                _controls(),
                error_banner(),
                rx.el.div(
                    rx.el.p(
                        f"{PublicState.filtered_courses.length()} of {PublicState.courses.length()} published courses",
                        class_name="text-sm font-medium text-slate-600",
                    ),
                    class_name="flex w-full items-center justify-between",
                ),
                rx.cond(
                    PublicState.is_loading,
                    loading_grid(6),
                    rx.cond(
                        PublicState.filtered_courses.length() > 0,
                        rx.el.div(
                            rx.foreach(
                                PublicState.filtered_courses,
                                lambda course: course_card(
                                    course, key=course["code"]
                                ),
                            ),
                            class_name="grid w-full grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3",
                        ),
                        empty_state(
                            "No courses match this filter",
                            "Clear the search text or pick another competency area.",
                            "search-x",
                        ),
                    ),
                ),
                class_name="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-10 sm:px-6",
            ),
            class_name="w-full",
        ),
    )

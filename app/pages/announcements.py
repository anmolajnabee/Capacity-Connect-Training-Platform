"""Public announcements notice board."""

import reflex as rx

from app.components.cards import (
    announcement_card,
    empty_state,
    error_banner,
    loading_grid,
)
from app.components.layout import page_shell
from app.states.public_state import PublicState

AUDIENCES: list[tuple[str, str]] = [
    ("all", "All notices"),
    ("trainees", "For trainees"),
    ("trainers", "For trainers"),
    ("admins", "For administrators"),
]


def _audience_button(item: tuple[str, str]) -> rx.Component:
    return rx.el.button(
        item[1],
        on_click=lambda: PublicState.set_audience_filter(item[0]),
        class_name=rx.cond(
            PublicState.audience_filter == item[0],
            "w-fit rounded-full border border-teal-600 bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white",
            "w-fit rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-teal-400",
        ),
    )


def announcements_page() -> rx.Component:
    return page_shell(
        rx.el.section(
            rx.el.div(
                rx.el.span(
                    "Notice board",
                    class_name="w-fit rounded-full border border-teal-400/40 bg-teal-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-teal-200",
                ),
                rx.el.h1(
                    "Institutional announcements",
                    class_name="mt-4 text-3xl font-semibold leading-tight text-white sm:text-4xl",
                ),
                rx.el.p(
                    "Nomination windows, competency refresh drives, venue changes "
                    "and certification notices published by the secretariat.",
                    class_name="mt-3 max-w-2xl text-sm font-medium leading-relaxed text-slate-300",
                ),
                class_name="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6",
            ),
            class_name="w-full bg-[#0A1B33]",
        ),
        rx.el.section(
            rx.el.div(
                rx.el.div(
                    rx.foreach(AUDIENCES, _audience_button),
                    class_name="flex w-full flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-4",
                ),
                error_banner(),
                rx.cond(
                    PublicState.is_loading,
                    loading_grid(4),
                    rx.cond(
                        PublicState.filtered_announcements.length() > 0,
                        rx.el.div(
                            rx.foreach(
                                PublicState.filtered_announcements,
                                lambda item: announcement_card(
                                    item, key=item["id"].to_string()
                                ),
                            ),
                            class_name="grid w-full grid-cols-1 gap-5 lg:grid-cols-2",
                        ),
                        empty_state(
                            "No announcements for this audience",
                            "Try another audience filter or check back later.",
                            "megaphone",
                        ),
                    ),
                ),
                class_name="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-10 sm:px-6",
            ),
            class_name="w-full",
        ),
    )

"""Public trainer directory."""

import reflex as rx

from app.components.cards import (
    empty_state,
    error_banner,
    loading_grid,
    trainer_card,
)
from app.components.layout import page_shell
from app.states.public_state import PublicState


def trainers_page() -> rx.Component:
    return page_shell(
        rx.el.section(
            rx.el.div(
                rx.el.span(
                    "Faculty directory",
                    class_name="w-fit rounded-full border border-teal-400/40 bg-teal-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-teal-200",
                ),
                rx.el.h1(
                    "Approved trainers and their teachable skills",
                    class_name="mt-4 text-3xl font-semibold leading-tight text-white sm:text-4xl",
                ),
                rx.el.p(
                    "Only administrator-approved trainers appear in the public "
                    "directory. Teachable skills drive the competency match used "
                    "when courses are assigned.",
                    class_name="mt-3 max-w-2xl text-sm font-medium leading-relaxed text-slate-300",
                ),
                class_name="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6",
            ),
            class_name="w-full bg-[#0A1B33]",
        ),
        rx.el.section(
            rx.el.div(
                error_banner(),
                rx.cond(
                    PublicState.is_loading,
                    loading_grid(6),
                    rx.cond(
                        PublicState.trainers.length() > 0,
                        rx.el.div(
                            rx.foreach(
                                PublicState.trainers,
                                lambda trainer: trainer_card(
                                    trainer, key=trainer["id"].to_string()
                                ),
                            ),
                            class_name="grid w-full grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3",
                        ),
                        empty_state(
                            "No approved trainers yet",
                            "Trainer profiles are listed as soon as an administrator approves the access request.",
                            "user-check",
                        ),
                    ),
                ),
                class_name="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-10 sm:px-6",
            ),
            class_name="w-full",
        ),
    )

"""Reusable content cards for public pages."""

import reflex as rx

from app.states.public_state import (
    AnnouncementItem,
    CourseCard,
    PublicState,
    TrainerCard,
)


def _chip(text: rx.Var | str) -> rx.Component:
    return rx.el.span(
        text,
        class_name="w-fit rounded-full border border-teal-200 bg-teal-50 px-2 py-0.5 text-[0.7rem] font-semibold text-teal-800",
    )


def stat_tile(label: str, value: rx.Var, icon: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, class_name="h-4 w-4 text-teal-700"),
            rx.el.span(
                label,
                class_name="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500",
            ),
            class_name="flex items-center gap-2",
        ),
        rx.el.p(
            value.to_string(),
            class_name="mt-2 text-2xl font-semibold tracking-tight text-[#0A1B33]",
        ),
        class_name="cc-card cc-hover w-full p-4",
    )


def course_card(course: CourseCard, **props) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.el.span(
                course["code"],
                class_name="w-fit rounded-md bg-[#0A1B33] px-2 py-0.5 text-[0.7rem] font-semibold tracking-wider text-teal-200",
            ),
            rx.el.span(
                course["category"],
                class_name="w-fit rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[0.7rem] font-semibold text-amber-700",
            ),
            class_name="flex flex-wrap items-center gap-2",
        ),
        rx.el.h3(
            course["title"],
            class_name="mt-3 text-lg font-semibold leading-snug text-[#0A1B33]",
        ),
        rx.el.p(
            course["summary"],
            class_name="mt-2 line-clamp-3 text-sm font-medium leading-relaxed text-slate-600",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("user-check", class_name="h-4 w-4 text-teal-700"),
                rx.el.span(
                    course["trainer_name"],
                    class_name="truncate text-sm font-medium text-slate-700",
                ),
                class_name="flex min-w-0 items-center gap-2",
            ),
            rx.el.div(
                rx.icon("calendar", class_name="h-4 w-4 text-teal-700"),
                rx.el.span(
                    course["start_date"],
                    class_name="text-sm font-medium text-slate-700",
                ),
                class_name="flex items-center gap-2",
            ),
            class_name="mt-4 flex flex-col gap-2",
        ),
        rx.el.div(
            rx.foreach(course["skills"], lambda skill: _chip(skill)),
            class_name="mt-4 flex flex-wrap gap-2",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Level",
                    class_name="block text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    course["level"],
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Hours",
                    class_name="block text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    f"{course['duration_hours']:.0f}",
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Resources",
                    class_name="block text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    course["resource_count"].to_string(),
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Seats left",
                    class_name="block text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    course["seats_left"].to_string(),
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
            ),
            class_name="cc-inset mt-4 grid grid-cols-2 gap-3 p-3 sm:grid-cols-4",
        ),
        rx.el.div(
            rx.el.span(
                f"Enrolment closes {course['deadline']}",
                class_name="text-xs font-medium text-slate-500",
            ),
            rx.el.a(
                "Register to enrol",
                rx.icon("arrow-right", class_name="ml-1 h-4 w-4"),
                href="/signup",
                class_name="cc-focus flex items-center rounded-[0.875rem] bg-teal-600 px-3 py-2 text-sm font-semibold text-white outline-hidden transition-all duration-200 hover:bg-teal-500 hover:shadow-sm",
            ),
            class_name="mt-4 flex flex-wrap items-center justify-between gap-3",
        ),
        class_name="cc-card cc-hover flex h-full w-full min-w-0 flex-col p-5",
        **props,
    )


def trainer_card(trainer: TrainerCard, **props) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.image(
                src=f"https://api.dicebear.com/9.x/notionists/svg?seed={trainer['avatar_seed']}",
                class_name="size-12 shrink-0 rounded-full bg-slate-100",
            ),
            rx.el.div(
                rx.el.h3(
                    trainer["name"],
                    class_name="truncate text-base font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    trainer["designation"],
                    class_name="truncate text-sm font-medium text-slate-600",
                ),
                class_name="min-w-0",
            ),
            rx.cond(
                trainer["is_available"],
                rx.el.span(
                    "Available",
                    class_name="w-fit rounded-full bg-green-100 px-2 py-0.5 text-[0.7rem] font-semibold text-green-700",
                ),
                rx.el.span(
                    "Engaged",
                    class_name="w-fit rounded-full bg-amber-100 px-2 py-0.5 text-[0.7rem] font-semibold text-amber-700",
                ),
            ),
            class_name="flex items-start justify-between gap-3",
        ),
        rx.el.p(
            trainer["specialization"],
            class_name="mt-3 line-clamp-2 text-sm font-medium leading-relaxed text-slate-600",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("building-2", class_name="h-4 w-4 text-teal-700"),
                rx.el.span(
                    trainer["organization"],
                    class_name="truncate text-sm font-medium text-slate-700",
                ),
                class_name="flex min-w-0 items-center gap-2",
            ),
            rx.el.div(
                rx.icon("star", class_name="h-4 w-4 text-amber-500"),
                rx.el.span(
                    f"{trainer['rating']:.1f} · {trainer['rating_count']} reviews",
                    class_name="text-sm font-medium text-slate-700",
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                rx.icon("hourglass", class_name="h-4 w-4 text-teal-700"),
                rx.el.span(
                    f"{trainer['years']:.1f} years of training experience",
                    class_name="text-sm font-medium text-slate-700",
                ),
                class_name="flex items-center gap-2",
            ),
            class_name="mt-3 flex flex-col gap-2",
        ),
        rx.el.div(
            rx.el.span(
                "Teachable skills",
                class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
            ),
            rx.cond(
                trainer["skills"].length() > 0,
                rx.el.div(
                    rx.foreach(trainer["skills"], lambda skill: _chip(skill)),
                    class_name="mt-2 flex flex-wrap gap-2",
                ),
                rx.el.p(
                    "No teachable skills declared yet.",
                    class_name="mt-2 text-xs font-medium text-slate-500",
                ),
            ),
            class_name="mt-4",
        ),
        rx.el.div(
            rx.el.span(
                "Assigned courses",
                class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
            ),
            rx.cond(
                trainer["courses"].length() > 0,
                rx.el.div(
                    rx.foreach(
                        trainer["courses"],
                        lambda title: rx.el.p(
                            title,
                            class_name="truncate text-sm font-medium text-slate-700",
                        ),
                    ),
                    class_name="mt-2 flex flex-col gap-1",
                ),
                rx.el.p(
                    "Awaiting course assignment.",
                    class_name="mt-2 text-xs font-medium text-slate-500",
                ),
            ),
            class_name="cc-inset mt-4 p-3",
        ),
        class_name="cc-card cc-hover flex h-full w-full min-w-0 flex-col p-5",
        **props,
    )


def announcement_card(item: AnnouncementItem, **props) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.el.div(
                rx.cond(
                    item["is_pinned"],
                    rx.el.span(
                        "Pinned",
                        class_name="w-fit rounded-full bg-amber-100 px-2 py-0.5 text-[0.7rem] font-semibold text-amber-700",
                    ),
                ),
                rx.el.span(
                    item["audience"],
                    class_name="w-fit rounded-full border border-slate-300 bg-slate-50 px-2 py-0.5 text-[0.7rem] font-semibold capitalize text-slate-600",
                ),
                class_name="flex flex-wrap items-center gap-2",
            ),
            rx.el.span(
                item["published"],
                class_name="text-xs font-medium text-slate-500",
            ),
            class_name="flex flex-wrap items-center justify-between gap-2",
        ),
        rx.el.h3(
            item["title"],
            class_name="mt-3 text-base font-semibold leading-snug text-[#0A1B33]",
        ),
        rx.el.p(
            item["body"],
            class_name="mt-2 text-sm font-medium leading-relaxed text-slate-600",
        ),
        rx.el.div(
            rx.icon("user", class_name="h-4 w-4 text-teal-700"),
            rx.el.span(
                item["author"],
                class_name="text-xs font-medium text-slate-600",
            ),
            rx.cond(
                item["course"] != "",
                rx.el.span(
                    item["course"],
                    class_name="w-fit rounded-full border border-teal-200 bg-teal-50 px-2 py-0.5 text-[0.7rem] font-semibold text-teal-800",
                ),
            ),
            class_name="mt-4 flex flex-wrap items-center gap-2",
        ),
        class_name="cc-card w-full min-w-0 p-5",
        **props,
    )


def loading_grid(count: int = 3) -> rx.Component:
    return rx.el.div(
        rx.foreach(
            list(range(count)),
            lambda _slot: rx.el.div(
                class_name="cc-skeleton h-60 w-full rounded-[1rem] border border-slate-200"
            ),
        ),
        class_name="grid w-full grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3",
    )


def empty_state(title: str, description: str, icon: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, class_name="h-6 w-6 text-teal-700"),
            class_name="flex size-12 items-center justify-center rounded-full border border-teal-200 bg-teal-50",
        ),
        rx.el.h3(
            title,
            class_name="mt-4 text-base font-semibold text-[#0A1B33]",
        ),
        rx.el.p(
            description,
            class_name="mt-1 max-w-md text-sm font-medium text-slate-600",
        ),
        class_name="cc-fade flex w-full flex-col items-center justify-center rounded-[1rem] border border-dashed border-slate-300 bg-white px-6 py-14 text-center",
    )


def error_banner() -> rx.Component:
    return rx.cond(
        PublicState.load_error != "",
        rx.el.div(
            rx.icon("triangle-alert", class_name="h-4 w-4 text-red-500"),
            rx.el.p(
                PublicState.load_error,
                class_name="text-sm font-medium text-red-700",
            ),
            rx.el.button(
                "Retry",
                on_click=PublicState.load_public_content,
                class_name="cc-focus ml-auto w-fit rounded-[0.875rem] border border-red-300 px-3 py-1 text-sm font-semibold text-red-700 outline-hidden transition-colors duration-200 hover:bg-red-200",
            ),
            class_name="cc-fade flex w-full items-center gap-2 rounded-[0.875rem] border border-red-200 bg-red-100 px-4 py-3",
        ),
    )

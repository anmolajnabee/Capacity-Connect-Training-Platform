"""Public home page — command centre overview."""

import reflex as rx

from app.components.cards import (
    announcement_card,
    course_card,
    empty_state,
    error_banner,
    loading_grid,
    stat_tile,
    trainer_card,
)
from app.components.layout import page_shell, section_heading
from app.components.pathway import pathway_panel
from app.components.trainee_ui import chip
from app.components.workflow_map import workflow_map
from app.states.public_state import PublicState


def _workflow_section() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            section_heading(
                "Why one registry",
                "Fragmented process → connected workflow",
                "The problems capacity building runs into, and the part of this registry that now carries each one. Figures read live from the registry.",
            ),
            workflow_map(
                rx.el.div(
                    chip(
                        f"{PublicState.stats['courses']} published courses",
                        "teal",
                    ),
                    chip(
                        f"{PublicState.stats['trainers']} approved trainers",
                        "navy",
                    ),
                    chip(
                        f"{PublicState.stats['trainees']} trainees",
                        "teal",
                    ),
                    chip(
                        f"{PublicState.stats['enrollments']} active enrolments",
                        "navy",
                    ),
                    chip(
                        f"{PublicState.stats['resources']} learning resources",
                        "teal",
                    ),
                    chip(
                        f"{PublicState.stats['assessments']} assessments",
                        "navy",
                    ),
                    chip(
                        f"{PublicState.stats['skills']} skills tracked",
                        "amber",
                    ),
                    chip(
                        f"{PublicState.stats['certificates']} certificates issued",
                        "green",
                    ),
                    class_name="flex w-full flex-wrap items-center gap-2",
                )
            ),
            class_name="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-12 sm:px-6",
        ),
        class_name="w-full border-y border-slate-200 bg-[#FBFAF7]",
    )


def _console_header() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Capacity building console",
                    class_name="w-fit rounded-full border border-teal-400/40 bg-teal-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-teal-200",
                ),
                rx.el.h1(
                    "Competency, charted end to end.",
                    class_name="mt-4 text-3xl font-semibold leading-tight text-white sm:text-4xl",
                ),
                rx.el.p(
                    "CAPACITY CONNECT reads the institution like a chart: skills "
                    "on one axis, training capacity on the other. Courses, "
                    "trainers, resources, assessments and certificates are held "
                    "in one registry so every capability claim is traceable.",
                    class_name="mt-3 max-w-2xl text-sm font-medium leading-relaxed text-slate-300",
                ),
                rx.el.div(
                    rx.el.a(
                        "Browse the course catalogue",
                        rx.icon("arrow-right", class_name="ml-2 h-4 w-4"),
                        href="/courses",
                        class_name="flex w-fit items-center rounded-lg bg-teal-500 px-4 py-2.5 text-sm font-semibold text-slate-900 transition-colors hover:bg-teal-400",
                    ),
                    rx.el.a(
                        "Request access",
                        href="/signup",
                        class_name="flex w-fit items-center rounded-lg border border-white/20 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-white/10",
                    ),
                    class_name="mt-6 flex flex-wrap gap-3",
                ),
                class_name="min-w-0 flex-1",
            ),
            rx.el.div(
                rx.el.span(
                    "Registry readings",
                    class_name="text-xs font-semibold uppercase tracking-[0.2em] text-teal-300",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.el.span(
                            "Published courses",
                            class_name="text-xs font-medium text-slate-400",
                        ),
                        rx.el.span(
                            PublicState.stats["courses"].to_string(),
                            class_name="text-2xl font-semibold text-white",
                        ),
                        class_name="flex flex-col",
                    ),
                    rx.el.div(
                        rx.el.span(
                            "Approved trainers",
                            class_name="text-xs font-medium text-slate-400",
                        ),
                        rx.el.span(
                            PublicState.stats["trainers"].to_string(),
                            class_name="text-2xl font-semibold text-white",
                        ),
                        class_name="flex flex-col",
                    ),
                    rx.el.div(
                        rx.el.span(
                            "Active enrolments",
                            class_name="text-xs font-medium text-slate-400",
                        ),
                        rx.el.span(
                            PublicState.stats["enrollments"].to_string(),
                            class_name="text-2xl font-semibold text-white",
                        ),
                        class_name="flex flex-col",
                    ),
                    rx.el.div(
                        rx.el.span(
                            "Certificates issued",
                            class_name="text-xs font-medium text-slate-400",
                        ),
                        rx.el.span(
                            PublicState.stats["certificates"].to_string(),
                            class_name="text-2xl font-semibold text-amber-300",
                        ),
                        class_name="flex flex-col",
                    ),
                    class_name="mt-4 grid grid-cols-2 gap-4",
                ),
                rx.el.p(
                    "Figures read live from the training registry.",
                    class_name="mt-4 text-xs font-medium text-slate-500",
                ),
                class_name="w-full rounded-xl border border-white/10 bg-white/[0.04] p-5 lg:max-w-sm",
            ),
            class_name="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-14 sm:px-6 lg:flex-row lg:items-start",
        ),
        class_name="w-full bg-[#0A1B33]",
    )


def _stat_band() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            stat_tile("Trainees", PublicState.stats["trainees"], "users"),
            stat_tile("Resources", PublicState.stats["resources"], "library"),
            stat_tile(
                "Assessments",
                PublicState.stats["assessments"],
                "clipboard-check",
            ),
            stat_tile(
                "Skills tracked", PublicState.stats["skills"], "grid-3x3"
            ),
            class_name="mx-auto grid w-full max-w-7xl grid-cols-2 gap-4 px-4 py-8 sm:px-6 md:grid-cols-4",
        ),
        class_name="w-full",
    )


def _featured_courses() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                section_heading(
                    "Catalogue",
                    "Courses now open for nomination",
                    "Each programme declares the competencies it closes, the matched faculty and the assessment that certifies it.",
                ),
                rx.el.a(
                    "All courses",
                    rx.icon("arrow-right", class_name="ml-1 h-4 w-4"),
                    href="/courses",
                    class_name="flex h-fit w-fit items-center rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-[#0A1B33] hover:bg-white",
                ),
                class_name="flex flex-wrap items-start justify-between gap-4",
            ),
            error_banner(),
            rx.cond(
                PublicState.is_loading,
                loading_grid(3),
                rx.cond(
                    PublicState.featured_courses.length() > 0,
                    rx.el.div(
                        rx.foreach(
                            PublicState.featured_courses,
                            lambda course: course_card(
                                course, key=course["code"]
                            ),
                        ),
                        class_name="grid w-full grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3",
                    ),
                    empty_state(
                        "No published courses yet",
                        "Programmes appear here as soon as the secretariat publishes them.",
                        "book-open",
                    ),
                ),
            ),
            class_name="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-12 sm:px-6",
        ),
        class_name="w-full",
    )


def _featured_trainers() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                section_heading(
                    "Faculty",
                    "Trainers matched by competency",
                    "Trainer expertise is scored against each course's required skills, so assignments are explainable.",
                ),
                rx.el.a(
                    "All trainers",
                    rx.icon("arrow-right", class_name="ml-1 h-4 w-4"),
                    href="/trainers",
                    class_name="flex h-fit w-fit items-center rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-[#0A1B33] hover:bg-white",
                ),
                class_name="flex flex-wrap items-start justify-between gap-4",
            ),
            rx.cond(
                PublicState.is_loading,
                loading_grid(3),
                rx.cond(
                    PublicState.featured_trainers.length() > 0,
                    rx.el.div(
                        rx.foreach(
                            PublicState.featured_trainers,
                            lambda trainer: trainer_card(
                                trainer, key=trainer["id"].to_string()
                            ),
                        ),
                        class_name="grid w-full grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3",
                    ),
                    empty_state(
                        "No approved trainers yet",
                        "Trainer profiles appear once an administrator approves their access request.",
                        "user-check",
                    ),
                ),
            ),
            class_name="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 pb-12 sm:px-6",
        ),
        class_name="w-full",
    )


def _latest_notices() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                section_heading(
                    "Notice board",
                    "Latest announcements",
                    "Nomination windows, competency refresh drives and certification notices.",
                ),
                rx.el.a(
                    "All announcements",
                    rx.icon("arrow-right", class_name="ml-1 h-4 w-4"),
                    href="/announcements",
                    class_name="flex h-fit w-fit items-center rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-[#0A1B33] hover:bg-white",
                ),
                class_name="flex flex-wrap items-start justify-between gap-4",
            ),
            rx.cond(
                PublicState.is_loading,
                loading_grid(3),
                rx.cond(
                    PublicState.latest_announcements.length() > 0,
                    rx.el.div(
                        rx.foreach(
                            PublicState.latest_announcements,
                            lambda item: announcement_card(
                                item, key=item["id"].to_string()
                            ),
                        ),
                        class_name="grid w-full grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3",
                    ),
                    empty_state(
                        "No announcements published",
                        "Institutional notices will be listed here.",
                        "megaphone",
                    ),
                ),
            ),
            class_name="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 pb-16 sm:px-6",
        ),
        class_name="w-full",
    )


def home_page() -> rx.Component:
    return page_shell(
        _console_header(),
        pathway_panel(),
        _workflow_section(),
        _stat_band(),
        _featured_courses(),
        _featured_trainers(),
        _latest_notices(),
    )

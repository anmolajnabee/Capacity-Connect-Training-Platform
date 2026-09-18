"""Public About page."""

import reflex as rx

from app.components.cards import stat_tile
from app.components.layout import page_shell, section_heading
from app.components.pathway import pathway_panel
from app.states.public_state import PublicState

PRINCIPLES: list[tuple[str, str, str]] = [
    (
        "target",
        "Competency first",
        "Every course declares the skills it closes and the minimum proficiency it expects, so training is planned against measured gaps rather than attendance targets.",
    ),
    (
        "user-check",
        "Explainable trainer matching",
        "Trainer expertise is scored against required skills with transparent match scores and matched-skill details, keeping assignments auditable.",
    ),
    (
        "layers",
        "One chain of custody",
        "Course, trainer, resources, assessment and certificate stay linked, so a certification always resolves back to the material and the score behind it.",
    ),
    (
        "shield-check",
        "Controlled access",
        "Trainee accounts activate immediately; trainer and administrator requests wait for explicit approval before any workspace opens.",
    ),
]

ROLES: list[tuple[str, str, str]] = [
    (
        "graduation-cap",
        "Trainee",
        "Maintain a professional profile and skill meters, enrol in courses, work through structured resources, take timed assessments, collect certificates and submit post-course feedback.",
    ),
    (
        "presentation",
        "Trainer",
        "Publish expertise, oversee assigned courses and trainees, curate the resource library, author MCQ questionnaires with deadlines, and monitor participation and performance.",
    ),
    (
        "shield",
        "Administrator",
        "Approve access requests and roles, oversee courses, trainers, assessments and certification, publish announcements and run competency mapping across the institution.",
    ),
]


def _principle(item: tuple[str, str, str]) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(item[0], class_name="h-5 w-5 text-teal-700"),
            class_name="flex size-10 items-center justify-center rounded-lg border border-teal-200 bg-teal-50",
        ),
        rx.el.h3(
            item[1],
            class_name="mt-4 text-base font-semibold text-[#0A1B33]",
        ),
        rx.el.p(
            item[2],
            class_name="mt-2 text-sm font-medium leading-relaxed text-slate-600",
        ),
        class_name="w-full min-w-0 rounded-xl border border-slate-200 bg-white p-5",
    )


def _role(item: tuple[str, str, str]) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(item[0], class_name="h-4 w-4 text-teal-300"),
            rx.el.h3(
                item[1],
                class_name="text-sm font-semibold uppercase tracking-[0.16em] text-white",
            ),
            class_name="flex items-center gap-2",
        ),
        rx.el.p(
            item[2],
            class_name="mt-3 text-sm font-medium leading-relaxed text-slate-300",
        ),
        class_name="w-full min-w-0 rounded-xl border border-white/10 bg-white/[0.04] p-5",
    )


def about_page() -> rx.Component:
    return page_shell(
        rx.el.section(
            rx.el.div(
                rx.el.span(
                    "About the programme",
                    class_name="w-fit rounded-full border border-teal-400/40 bg-teal-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-teal-200",
                ),
                rx.el.h1(
                    "A learning command centre for institutional capacity.",
                    class_name="mt-4 max-w-3xl text-3xl font-semibold leading-tight text-white sm:text-4xl",
                ),
                rx.el.p(
                    "CAPACITY CONNECT was built for training institutions that must "
                    "answer a hard question: which of our people can do which job, "
                    "to what standard, and what training closes the difference. The "
                    "platform keeps skills, courses, faculty, assessments and "
                    "certification in a single normalized registry.",
                    class_name="mt-4 max-w-3xl text-sm font-medium leading-relaxed text-slate-300",
                ),
                class_name="mx-auto w-full max-w-7xl px-4 py-14 sm:px-6",
            ),
            class_name="w-full bg-[#0A1B33]",
        ),
        rx.el.section(
            rx.el.div(
                stat_tile(
                    "Published courses",
                    PublicState.stats["courses"],
                    "book-open",
                ),
                stat_tile(
                    "Approved trainers",
                    PublicState.stats["trainers"],
                    "user-check",
                ),
                stat_tile(
                    "Registered trainees",
                    PublicState.stats["trainees"],
                    "users",
                ),
                stat_tile(
                    "Skills tracked", PublicState.stats["skills"], "grid-3x3"
                ),
                class_name="mx-auto grid w-full max-w-7xl grid-cols-2 gap-4 px-4 py-8 sm:px-6 md:grid-cols-4",
            ),
            class_name="w-full",
        ),
        rx.el.section(
            rx.el.div(
                section_heading(
                    "Operating principles",
                    "How the registry is designed",
                    "Four commitments shape every screen in the platform.",
                ),
                rx.el.div(
                    rx.foreach(PRINCIPLES, _principle),
                    class_name="grid w-full grid-cols-1 gap-5 md:grid-cols-2",
                ),
                class_name="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 pb-12 sm:px-6",
            ),
            class_name="w-full",
        ),
        pathway_panel(),
        rx.el.section(
            rx.el.div(
                section_heading(
                    "Workspaces",
                    "Three roles, one registry",
                    "Access is granted per role, and every workspace reads from the same records.",
                    dark=True,
                ),
                rx.el.div(
                    rx.foreach(ROLES, _role),
                    class_name="grid w-full grid-cols-1 gap-5 lg:grid-cols-3",
                ),
                class_name="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-14 sm:px-6",
            ),
            class_name="w-full bg-[#08172B]",
        ),
    )

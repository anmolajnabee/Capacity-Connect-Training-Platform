"""Trainee workspace shell: command-centre header band and workspace nav."""

from __future__ import annotations

import reflex as rx

from app.components.layout import alert_banner, page_shell
from app.states.auth_state import AuthState
from app.components.capacity_ai import capacity_ai_panel
from app.components.workspace_navigation import (
    navigation_group,
    navigation_label,
)

TRAINEE_NAV: list[tuple[str, str, str]] = [
    ("Dashboard", "/trainee", "layout-dashboard"),
    ("Training Catalogue", "/trainee/courses", "compass"),
    ("My Learning", "/trainee/learning", "graduation-cap"),
    ("Learning Resources", "/trainee/resources", "library"),
    ("Competencies", "/trainee/competencies", "radar"),
    ("Practice", "/trainee/practice", "pencil-line"),
    ("Assessments", "/trainee/assessments", "clipboard-check"),
    ("Assignments", "/trainee/assignments", "clipboard-list"),
    ("Competency Passport", "/trainee/passport", "book-user"),
    ("Certificates", "/trainee/certificates", "award"),
    ("Results", "/trainee/results", "chart-line"),
    ("Feedback", "/trainee/feedback", "message-square"),
    ("Learning Paths", "/trainee/paths", "route"),
    ("Notifications", "/trainee/notifications", "bell"),
    ("My Profile", "/trainee/profile", "user-pen"),
    ("Settings", "/account", "settings"),
]


def _nav_item(item: rx.Var, active: str) -> rx.Component:
    return rx.el.a(
        rx.icon(item[2], class_name="h-4 w-4 shrink-0"),
        navigation_label(item[0]),
        href=item[1],
        aria_current=rx.cond(
            (item[0] == active)
            | ((item[0] == "Training Catalogue") & (active == "Courses")),
            "page",
            "false",
        ),
        class_name=rx.cond(
            (item[0] == active)
            | ((item[0] == "Training Catalogue") & (active == "Courses")),
            "cc-focus flex shrink-0 items-center gap-2 rounded-[0.875rem] border border-teal-300/60 bg-teal-400/20 px-3 py-2 text-sm font-semibold text-teal-50 outline-hidden",
            "cc-focus flex shrink-0 items-center gap-2 rounded-[0.875rem] border border-transparent px-3 py-2 text-sm font-medium text-slate-300 outline-hidden transition-all duration-200 hover:border-white/15 hover:bg-white/10 hover:text-white",
        ),
    )


def _grid_lines() -> rx.Component:
    return rx.el.div(
        class_name="cc-grid-motif pointer-events-none absolute inset-0 opacity-[0.16]"
    )


def trainee_header(active: str, title: str, description: str) -> rx.Component:
    return rx.el.section(
        _grid_lines(),
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.span(
                        "Trainee workspace",
                        class_name="w-fit rounded-full border border-teal-400/40 bg-teal-400/10 px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-[0.2em] text-teal-200",
                    ),
                    rx.el.h1(
                        title,
                        class_name="mt-3 text-2xl font-semibold tracking-tight text-white sm:text-3xl",
                    ),
                    rx.el.p(
                        description,
                        class_name="mt-1 max-w-2xl text-sm font-medium leading-relaxed text-slate-300",
                    ),
                    class_name="min-w-0",
                ),
                rx.el.div(
                    rx.image(
                        src=f"https://api.dicebear.com/9.x/notionists/svg?seed={AuthState.avatar_seed}",
                        class_name="size-11 shrink-0 rounded-full bg-white/10",
                    ),
                    rx.el.div(
                        rx.el.p(
                            AuthState.full_name,
                            class_name="truncate text-sm font-semibold text-white",
                        ),
                        rx.el.p(
                            AuthState.profile_headline,
                            class_name="truncate text-xs font-medium text-slate-400",
                        ),
                        rx.el.p(
                            f"Last session · {AuthState.last_login_display}",
                            class_name="truncate text-[0.7rem] font-medium text-teal-300",
                        ),
                        class_name="min-w-0",
                    ),
                    class_name="flex w-full min-w-0 items-center gap-3 rounded-[0.875rem] border border-white/10 bg-white/[0.05] p-3 lg:w-auto lg:min-w-[16rem]",
                ),
                class_name="cc-rise flex w-full flex-col items-start justify-between gap-5 lg:flex-row lg:items-center",
            ),
            rx.el.nav(
                navigation_group(
                    "Overview",
                    rx.foreach(
                        TRAINEE_NAV[:1], lambda item: _nav_item(item, active)
                    ),
                ),
                navigation_group(
                    "Learn",
                    rx.foreach(
                        TRAINEE_NAV[1:4], lambda item: _nav_item(item, active)
                    ),
                ),
                navigation_group(
                    "Develop",
                    rx.foreach(
                        TRAINEE_NAV[4:8], lambda item: _nav_item(item, active)
                    ),
                ),
                navigation_group(
                    "Progress",
                    rx.foreach(
                        TRAINEE_NAV[8:13], lambda item: _nav_item(item, active)
                    ),
                ),
                navigation_group(
                    "Account",
                    rx.foreach(
                        TRAINEE_NAV[13:], lambda item: _nav_item(item, active)
                    ),
                ),
                aria_label="Trainee workspace navigation",
                class_name="cc-rise cc-rise-delay-1 mt-6 flex w-full flex-wrap items-start gap-x-6 gap-y-4 pb-1",
            ),
            class_name="relative mx-auto w-full max-w-7xl px-4 py-8 sm:px-6",
        ),
        class_name="relative w-full overflow-hidden border-b border-teal-400/20 bg-[#0A1B33]",
    )


def trainee_page(
    active: str,
    title: str,
    description: str,
    error_message: rx.Var,
    success_message: rx.Var,
    *children: rx.Component,
) -> rx.Component:
    return page_shell(
        trainee_header(active, title, description),
        rx.el.section(
            rx.el.div(
                alert_banner(error_message, success_message),
                capacity_ai_panel(),
                *children,
                class_name="cc-rise cc-rise-delay-2 mx-auto flex w-full max-w-7xl min-w-0 flex-col gap-6 px-4 py-8 sm:px-6",
            ),
            class_name="w-full",
        ),
    )

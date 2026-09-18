"""Admin control-centre shell: command band, station grid and workspace nav."""

from __future__ import annotations

import reflex as rx

from app.components.layout import alert_banner, page_shell
from app.states.auth_state import AuthState
from app.components.workspace_navigation import (
    navigation_group,
    navigation_label,
)

ADMIN_NAV: list[tuple[str, str, str]] = [
    ("Dashboard", "/admin", "gauge"),
    ("Users", "/admin/users", "users"),
    ("Approvals", "/admin/approvals", "shield-check"),
    ("Role Management", "/admin/roles", "user-cog"),
    ("Courses", "/admin/courses", "book-open"),
    ("Learning Content", "/admin/learning-content", "library"),
    ("Assessments", "/admin/assessments", "list-checks"),
    ("Competencies", "/admin/competencies", "radar"),
    ("Trainers", "/admin/trainers", "user-pen"),
    ("Trainer Fit", "/admin/trainer-fit", "scan-line"),
    ("Team Coverage", "/admin/team-matches", "network"),
    ("Requirements", "/admin/requirements", "list-checks"),
    ("Participation", "/admin/participation", "contact"),
    ("Effectiveness", "/admin/effectiveness", "trending-up"),
    ("Certifications", "/admin/certifications", "award"),
    ("Analytics", "/admin/analytics", "chart-line"),
    ("Announcements", "/admin/announcements", "megaphone"),
    ("Achievements", "/admin/achievements", "medal"),
    ("Notifications", "/admin/notifications", "bell"),
    ("Reports", "/admin/reports", "file-down"),
    ("Settings", "/admin/settings", "settings"),
    ("Trainees", "/admin/trainees", "users"),
]


def _nav_item(item: rx.Var, active: str) -> rx.Component:
    return rx.el.a(
        rx.icon(item[2], class_name="h-4 w-4 shrink-0"),
        navigation_label(item[0]),
        href=item[1],
        aria_current=rx.cond(item[0] == active, "page", "false"),
        class_name=rx.cond(
            item[0] == active,
            "cc-focus-sky flex shrink-0 items-center gap-2 rounded-[0.875rem] border border-sky-300/70 bg-sky-400/20 px-3 py-2 text-sm font-semibold text-sky-50 outline-hidden",
            "cc-focus-sky flex shrink-0 items-center gap-2 rounded-[0.875rem] border border-transparent px-3 py-2 text-sm font-medium text-slate-300 outline-hidden transition-all duration-200 hover:border-white/15 hover:bg-white/10 hover:text-white",
        ),
    )


def _isobars() -> rx.Component:
    return rx.el.div(
        class_name="cc-isobar-motif pointer-events-none absolute inset-0 opacity-[0.18]"
    )


def admin_header(active: str, title: str, description: str) -> rx.Component:
    return rx.el.section(
        _isobars(),
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.span(
                        "Admin control centre",
                        class_name="w-fit rounded-full border border-sky-300/40 bg-sky-400/10 px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-[0.2em] text-sky-200",
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
                            class_name="truncate text-[0.7rem] font-medium text-sky-300",
                        ),
                        class_name="min-w-0",
                    ),
                    class_name="flex w-full min-w-0 items-center gap-3 rounded-[0.875rem] border border-white/10 bg-white/[0.05] p-3 lg:w-auto lg:min-w-[16rem]",
                ),
                class_name="cc-rise flex w-full flex-col items-start justify-between gap-5 lg:flex-row lg:items-center",
            ),
            rx.el.nav(
                navigation_group(
                    "People & access",
                    rx.foreach(
                        ADMIN_NAV[:4], lambda item: _nav_item(item, active)
                    ),
                ),
                navigation_group(
                    "Training",
                    rx.foreach(
                        ADMIN_NAV[4:7], lambda item: _nav_item(item, active)
                    ),
                ),
                navigation_group(
                    "Capacity planning",
                    rx.foreach(
                        ADMIN_NAV[7:12], lambda item: _nav_item(item, active)
                    ),
                ),
                navigation_group(
                    "Evidence & outcomes",
                    rx.foreach(
                        ADMIN_NAV[12:16], lambda item: _nav_item(item, active)
                    ),
                ),
                navigation_group(
                    "Operations",
                    rx.foreach(
                        ADMIN_NAV[16:], lambda item: _nav_item(item, active)
                    ),
                ),
                aria_label="Administrator control centre navigation",
                class_name="cc-rise cc-rise-delay-1 mt-6 flex w-full flex-wrap items-start gap-x-6 gap-y-4 pb-1",
            ),
            class_name="relative mx-auto w-full max-w-7xl px-4 py-8 sm:px-6",
        ),
        class_name="relative w-full overflow-hidden border-b border-sky-300/20 bg-[#0A1B33]",
    )


def admin_page(
    active: str,
    title: str,
    description: str,
    error_message: rx.Var,
    success_message: rx.Var,
    *children: rx.Component,
) -> rx.Component:
    return page_shell(
        admin_header(active, title, description),
        rx.el.section(
            rx.el.div(
                alert_banner(error_message, success_message),
                *children,
                class_name="cc-rise cc-rise-delay-2 mx-auto flex w-full min-w-0 max-w-7xl flex-col gap-6 px-4 py-8 sm:px-6",
            ),
            class_name="w-full",
        ),
    )


def table_head(*cells: rx.Component) -> rx.Component:
    return rx.el.thead(
        rx.el.tr(*cells),
        class_name="bg-[#F1F5F9]",
    )


def th(label: str, icon: str) -> rx.Component:
    return rx.el.th(
        rx.el.div(
            rx.icon(icon, class_name="h-3.5 w-3.5 text-slate-400"),
            rx.el.span(label),
            class_name="flex items-center gap-1.5",
        ),
        class_name="whitespace-nowrap px-3 py-2 text-left text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
    )


def data_table(head: rx.Component, body: rx.Component) -> rx.Component:
    return rx.el.div(
        rx.el.table(
            head,
            body,
            class_name="w-full table-auto",
        ),
        class_name="w-full overflow-x-auto overflow-hidden rounded-[0.875rem] border border-slate-200 bg-white shadow-xs",
    )


def row_class() -> str:
    return "cc-table-row border-b border-slate-100 odd:bg-white even:bg-[#FBFAF7] hover:bg-sky-50/60"


def cell(*children: rx.Component) -> rx.Component:
    return rx.el.td(*children, class_name="px-3 py-2 align-top")


def status_pill(text: rx.Var | str) -> rx.Component:
    return rx.el.span(
        text,
        class_name=rx.match(
            text,
            (
                "approved",
                "w-fit rounded-full border border-green-200 bg-green-100 px-2 py-0.5 text-[0.7rem] font-semibold text-green-700",
            ),
            (
                "pending",
                "w-fit rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[0.7rem] font-semibold text-amber-800",
            ),
            (
                "rejected",
                "w-fit rounded-full border border-red-200 bg-red-100 px-2 py-0.5 text-[0.7rem] font-semibold text-red-700",
            ),
            (
                "suspended",
                "w-fit rounded-full border border-red-200 bg-red-100 px-2 py-0.5 text-[0.7rem] font-semibold text-red-700",
            ),
            (
                "published",
                "w-fit rounded-full border border-teal-200 bg-teal-50 px-2 py-0.5 text-[0.7rem] font-semibold text-teal-800",
            ),
            (
                "open",
                "w-fit rounded-full border border-teal-200 bg-teal-50 px-2 py-0.5 text-[0.7rem] font-semibold text-teal-800",
            ),
            (
                "draft",
                "w-fit rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 text-[0.7rem] font-semibold text-slate-700",
            ),
            "w-fit rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 text-[0.7rem] font-semibold text-slate-700",
        ),
    )


def filter_input(
    placeholder: str,
    default_value: rx.Var | str,
    on_change,
    icon: str = "search",
) -> rx.Component:
    return rx.el.div(
        rx.icon(
            icon,
            class_name="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
        ),
        rx.el.input(
            placeholder=placeholder,
            default_value=default_value,
            on_change=on_change,
            class_name="cc-focus w-full rounded-[0.875rem] border border-slate-300 bg-white py-2 pl-9 pr-3 text-sm font-medium text-slate-900 outline-hidden transition-colors duration-200 focus:border-sky-500",
        ),
        class_name="relative w-full min-w-0",
    )


def filter_select(
    options: rx.Var | list[str], value: rx.Var | str, on_change
) -> rx.Component:
    return rx.el.div(
        rx.el.select(
            rx.foreach(
                options, lambda option: rx.el.option(option, value=option)
            ),
            value=value,
            on_change=on_change,
            class_name="cc-focus w-full appearance-none rounded-[0.875rem] border border-slate-300 bg-white px-3 py-2 pr-9 text-sm font-medium text-slate-900 outline-hidden transition-colors duration-200 focus:border-sky-500",
        ),
        rx.icon(
            "chevron-down",
            class_name="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
        ),
        class_name="relative w-full min-w-0 sm:w-48",
    )

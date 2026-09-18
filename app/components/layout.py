"""Shared institutional shell: top navigation, footer and page wrapper."""

import reflex as rx

from app.states.auth_state import AuthState

NAV_LINKS: list[tuple[str, str]] = [
    ("Home", "/"),
    ("About", "/about"),
    ("Courses", "/courses"),
    ("Trainers", "/trainers"),
    ("Announcements", "/announcements"),
]


def _nav_link(label: str, href: str) -> rx.Component:
    return rx.el.a(
        label,
        href=href,
        class_name="cc-focus shrink-0 rounded-[0.875rem] px-3 py-2 text-sm font-medium text-slate-200 outline-hidden transition-all duration-200 hover:bg-white/10 hover:text-white",
    )


def brand() -> rx.Component:
    return rx.el.a(
        rx.el.div(
            rx.icon("radar", class_name="h-5 w-5 text-teal-300"),
            class_name="flex size-9 items-center justify-center rounded-md border border-teal-400/40 bg-teal-400/10",
        ),
        rx.el.div(
            rx.el.span(
                "CAPACITY CONNECT",
                class_name="block text-sm font-semibold tracking-[0.18em] text-white",
            ),
            rx.el.span(
                "Institutional capacity building registry",
                class_name="hidden text-xs font-medium text-slate-400 sm:block",
            ),
        ),
        href="/",
        class_name="flex items-center gap-3",
    )


def _session_actions() -> rx.Component:
    return rx.cond(
        AuthState.is_authenticated,
        rx.el.div(
            rx.el.a(
                rx.el.div(
                    AuthState.initials,
                    class_name="flex size-8 shrink-0 items-center justify-center rounded-full bg-teal-400/20 text-xs font-semibold text-teal-200",
                ),
                rx.el.div(
                    rx.el.span(
                        AuthState.full_name,
                        class_name="block max-w-[9rem] truncate text-sm font-medium text-white",
                    ),
                    rx.el.span(
                        AuthState.role_label,
                        class_name="block text-xs font-medium uppercase tracking-wide text-teal-300",
                    ),
                    class_name="hidden sm:block",
                ),
                href="/account",
                class_name="cc-focus flex items-center gap-2 rounded-[0.875rem] px-2 py-1 outline-hidden transition-colors duration-200 hover:bg-white/10",
            ),
            rx.el.a(
                "Workspace",
                href=AuthState.workspace_href,
                class_name="cc-focus hidden rounded-[0.875rem] bg-teal-500 px-3 py-2 text-sm font-semibold text-slate-900 outline-hidden transition-all duration-200 hover:bg-teal-400 md:block",
            ),
            rx.el.button(
                rx.icon("log-out", class_name="h-4 w-4"),
                on_click=AuthState.logout,
                title="Sign out",
                class_name="cc-focus flex size-9 items-center justify-center rounded-[0.875rem] border border-white/15 text-slate-200 outline-hidden transition-colors duration-200 hover:bg-white/10",
            ),
            class_name="flex items-center gap-2",
        ),
        rx.el.div(
            rx.el.a(
                rx.icon("log-in", class_name="h-4 w-4"),
                rx.el.span("Login"),
                href="/login",
                class_name="cc-focus flex items-center gap-1.5 rounded-[0.875rem] border border-white/20 px-3 py-2 text-sm font-semibold text-slate-100 outline-hidden transition-all duration-200 hover:border-white/40 hover:bg-white/10",
            ),
            rx.el.a(
                rx.icon("user-plus", class_name="h-4 w-4"),
                rx.el.span("Signup"),
                href="/signup",
                class_name="cc-focus flex items-center gap-1.5 rounded-[0.875rem] bg-teal-500 px-3 py-2 text-sm font-semibold text-slate-900 outline-hidden transition-all duration-200 hover:bg-teal-400",
            ),
            class_name="flex items-center gap-2",
        ),
    )


def navbar() -> rx.Component:
    return rx.el.header(
        rx.el.div(
            brand(),
            rx.el.nav(
                rx.foreach(
                    NAV_LINKS,
                    lambda item: _nav_link(item[0], item[1]),
                ),
                class_name="hidden items-center gap-1 lg:flex",
            ),
            _session_actions(),
            class_name="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6",
        ),
        rx.el.nav(
            rx.foreach(NAV_LINKS, lambda item: _nav_link(item[0], item[1])),
            class_name="cc-worknav flex items-center gap-1 overflow-x-auto border-t border-white/10 px-4 py-2 lg:hidden",
        ),
        class_name="sticky top-0 z-40 border-b border-white/10 bg-[#0A1B33]/95 shadow-[0_1px_0_rgba(255,255,255,0.06)] backdrop-blur",
    )


def footer() -> rx.Component:
    return rx.el.footer(
        rx.el.div(
            rx.el.div(
                brand(),
                rx.el.p(
                    "A competency-first training registry connecting courses, "
                    "trainers, resources, assessments and certification for "
                    "institutional capacity building.",
                    class_name="mt-3 max-w-md text-sm font-medium leading-relaxed text-slate-400",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Navigate",
                    class_name="text-xs font-semibold uppercase tracking-[0.2em] text-teal-300",
                ),
                rx.el.div(
                    rx.foreach(
                        NAV_LINKS,
                        lambda item: rx.el.a(
                            item[0],
                            href=item[1],
                            class_name="text-sm font-medium text-slate-300 hover:text-white",
                        ),
                    ),
                    class_name="mt-3 flex flex-col gap-2",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Access",
                    class_name="text-xs font-semibold uppercase tracking-[0.2em] text-teal-300",
                ),
                rx.el.div(
                    rx.el.a(
                        "Login",
                        href="/login",
                        class_name="text-sm font-medium text-slate-300 hover:text-white",
                    ),
                    rx.el.a(
                        "Signup",
                        href="/signup",
                        class_name="text-sm font-medium text-slate-300 hover:text-white",
                    ),
                    rx.el.a(
                        "Forgot password",
                        href="/forgot-password",
                        class_name="text-sm font-medium text-slate-300 hover:text-white",
                    ),
                    rx.el.a(
                        "Account",
                        href="/account",
                        class_name="text-sm font-medium text-slate-300 hover:text-white",
                    ),
                    class_name="mt-3 flex flex-col gap-2",
                ),
            ),
            class_name="mx-auto grid w-full max-w-7xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-3",
        ),
        rx.el.div(
            rx.el.p(
                "© CAPACITY CONNECT — development environment with seeded demo records.",
                class_name="text-xs font-medium text-slate-500",
            ),
            class_name="mx-auto w-full max-w-7xl border-t border-white/10 px-4 py-4 sm:px-6",
        ),
        class_name="bg-[#08172B]",
    )


def page_shell(*children: rx.Component) -> rx.Component:
    return rx.el.div(
        navbar(),
        rx.el.main(
            *children,
            class_name="w-full min-w-0 flex-1",
        ),
        footer(),
        class_name="flex min-h-screen w-full flex-col bg-[#F6F4EF] font-['Inter'] text-slate-900",
    )


def section_heading(
    eyebrow: str, title: str, description: str, *, dark: bool = False
) -> rx.Component:
    return rx.el.div(
        rx.el.span(
            eyebrow,
            class_name=(
                "text-xs font-semibold uppercase tracking-[0.22em] text-teal-300"
                if dark
                else "text-xs font-semibold uppercase tracking-[0.22em] text-teal-700"
            ),
        ),
        rx.el.h2(
            title,
            class_name=(
                "mt-2 text-2xl font-semibold text-white sm:text-3xl"
                if dark
                else "mt-2 text-2xl font-semibold text-[#0A1B33] sm:text-3xl"
            ),
        ),
        rx.el.p(
            description,
            class_name=(
                "mt-2 max-w-2xl text-sm font-medium leading-relaxed text-slate-300"
                if dark
                else "mt-2 max-w-2xl text-sm font-medium leading-relaxed text-slate-600"
            ),
        ),
        class_name="w-full",
    )


def alert_banner(
    error_message: rx.Var, success_message: rx.Var
) -> rx.Component:
    return rx.el.div(
        rx.cond(
            error_message != "",
            rx.el.div(
                rx.icon(
                    "triangle-alert", class_name="h-4 w-4 shrink-0 text-red-500"
                ),
                rx.el.p(
                    error_message,
                    class_name="text-sm font-medium text-red-700",
                ),
                class_name="cc-fade flex items-start gap-2 rounded-[0.875rem] border border-red-200 bg-red-100 px-3 py-2 shadow-xs",
            ),
        ),
        rx.cond(
            success_message != "",
            rx.el.div(
                rx.icon(
                    "circle-check", class_name="h-4 w-4 shrink-0 text-green-600"
                ),
                rx.el.p(
                    success_message,
                    class_name="text-sm font-medium text-green-700",
                ),
                class_name="cc-fade flex items-start gap-2 rounded-[0.875rem] border border-green-200 bg-green-100 px-3 py-2 shadow-xs",
            ),
        ),
        class_name="flex w-full flex-col gap-2",
    )

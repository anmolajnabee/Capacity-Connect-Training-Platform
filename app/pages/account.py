"""Authenticated account management page."""

import reflex as rx

from app.components.auth_forms import (
    demo_credentials_panel,
    submit_button,
    text_field,
)
from app.components.layout import alert_banner, page_shell
from app.states.auth_state import AuthState


def _status_badge() -> rx.Component:
    return rx.match(
        AuthState.approval_status,
        (
            "approved",
            rx.el.span(
                "Approved",
                class_name="w-fit rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-700",
            ),
        ),
        (
            "pending",
            rx.el.span(
                "Awaiting approval",
                class_name="w-fit rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700",
            ),
        ),
        (
            "rejected",
            rx.el.span(
                "Declined",
                class_name="w-fit rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700",
            ),
        ),
        rx.el.span(
            "Suspended",
            class_name="w-fit rounded-full bg-slate-200 px-2 py-0.5 text-xs font-semibold text-slate-700",
        ),
    )


def _identity_panel() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.image(
                src=f"https://api.dicebear.com/9.x/notionists/svg?seed={AuthState.avatar_seed}",
                class_name="size-14 shrink-0 rounded-full bg-slate-100",
            ),
            rx.el.div(
                rx.el.h1(
                    AuthState.full_name,
                    class_name="truncate text-xl font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    AuthState.email,
                    class_name="truncate text-sm font-medium text-slate-600",
                ),
                rx.cond(
                    AuthState.profile_headline != "",
                    rx.el.p(
                        AuthState.profile_headline,
                        class_name="truncate text-xs font-medium text-slate-500",
                    ),
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                rx.el.span(
                    AuthState.role_label,
                    class_name="w-fit rounded-full bg-[#0A1B33] px-2 py-0.5 text-xs font-semibold text-teal-200",
                ),
                _status_badge(),
                class_name="flex shrink-0 flex-col items-end gap-2",
            ),
            class_name="flex items-start justify-between gap-4",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Last sign in",
                    class_name="block text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    AuthState.last_login_display,
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Phone",
                    class_name="block text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    rx.cond(AuthState.phone != "", AuthState.phone, "Not set"),
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Workspace",
                    class_name="block text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    AuthState.workspace_href,
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
            ),
            class_name="mt-5 grid grid-cols-1 gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4 sm:grid-cols-3",
        ),
        rx.cond(
            AuthState.is_approved,
            rx.el.a(
                "Open my workspace",
                rx.icon("arrow-right", class_name="ml-2 h-4 w-4"),
                href=AuthState.workspace_href,
                class_name="mt-5 flex w-fit items-center rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-teal-500",
            ),
            rx.el.div(
                rx.icon("hourglass", class_name="h-4 w-4 text-amber-600"),
                rx.el.p(
                    "Your access request is queued. An administrator must approve "
                    "it before the role workspace unlocks.",
                    class_name="text-sm font-medium text-amber-800",
                ),
                class_name="mt-5 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2",
            ),
        ),
        class_name="w-full rounded-2xl border border-slate-200 bg-white p-6",
    )


def _details_form() -> rx.Component:
    return rx.el.div(
        rx.el.h2(
            "Account details",
            class_name="text-base font-semibold text-[#0A1B33]",
        ),
        rx.el.p(
            "Keep your contact record current so course coordinators can reach you.",
            class_name="mt-1 text-sm font-medium text-slate-600",
        ),
        rx.el.form(
            rx.el.div(
                text_field(
                    "Full name",
                    "full_name",
                    "Your full name",
                    "text",
                    AuthState.full_name,
                ),
                text_field(
                    "Phone",
                    "phone",
                    "+91 98450 00000",
                    "tel",
                    AuthState.phone,
                    False,
                ),
                submit_button("Save details", "Saving…"),
                class_name="mt-4 flex w-full flex-col gap-4",
            ),
            on_submit=AuthState.update_account,
        ),
        class_name="w-full rounded-2xl border border-slate-200 bg-white p-6",
    )


def _password_form() -> rx.Component:
    return rx.el.div(
        rx.el.h2(
            "Change password",
            class_name="text-base font-semibold text-[#0A1B33]",
        ),
        rx.el.p(
            "Your current password is verified in constant time before any change is applied.",
            class_name="mt-1 text-sm font-medium text-slate-600",
        ),
        rx.el.form(
            rx.el.div(
                text_field(
                    "Current password",
                    "current_password",
                    "Current password",
                    "password",
                ),
                text_field(
                    "New password",
                    "password",
                    "At least 8 characters",
                    "password",
                ),
                text_field(
                    "Confirm new password",
                    "confirm_password",
                    "Repeat the new password",
                    "password",
                ),
                submit_button("Change password", "Updating…"),
                class_name="mt-4 flex w-full flex-col gap-4",
            ),
            on_submit=AuthState.change_password,
        ),
        class_name="w-full rounded-2xl border border-slate-200 bg-white p-6",
    )


def account_page() -> rx.Component:
    return page_shell(
        rx.el.section(
            rx.el.div(
                rx.el.span(
                    "Account",
                    class_name="w-fit rounded-full border border-teal-400/40 bg-teal-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-teal-200",
                ),
                rx.el.h1(
                    "Your access record",
                    class_name="mt-4 text-3xl font-semibold text-white sm:text-4xl",
                ),
                rx.el.p(
                    "Role, approval status, contact details and credentials in one place.",
                    class_name="mt-2 text-sm font-medium text-slate-300",
                ),
                class_name="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6",
            ),
            class_name="w-full bg-[#0A1B33]",
        ),
        rx.el.section(
            rx.el.div(
                alert_banner(
                    AuthState.error_message, AuthState.success_message
                ),
                rx.cond(
                    AuthState.is_authenticated,
                    rx.el.div(
                        rx.el.div(
                            _identity_panel(),
                            rx.el.div(
                                _details_form(),
                                _password_form(),
                                class_name="grid w-full grid-cols-1 gap-6 lg:grid-cols-2",
                            ),
                            class_name="flex w-full min-w-0 flex-1 flex-col gap-6",
                        ),
                        rx.el.div(
                            demo_credentials_panel(),
                            rx.el.button(
                                rx.icon("log-out", class_name="mr-2 h-4 w-4"),
                                "Sign out of this session",
                                on_click=AuthState.logout,
                                class_name="flex w-full items-center justify-center rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50",
                            ),
                            class_name="flex w-full min-w-0 flex-col gap-5 lg:max-w-sm",
                        ),
                        class_name="flex w-full flex-col gap-6 lg:flex-row lg:items-start",
                    ),
                    rx.el.div(
                        rx.el.div(
                            class_name="h-40 w-full animate-pulse rounded-2xl border border-slate-200 bg-white"
                        ),
                        rx.el.p(
                            "Verifying your session…",
                            class_name="text-sm font-medium text-slate-600",
                        ),
                        class_name="flex w-full flex-col gap-3",
                    ),
                ),
                class_name="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-10 sm:px-6",
            ),
            class_name="w-full",
        ),
    )

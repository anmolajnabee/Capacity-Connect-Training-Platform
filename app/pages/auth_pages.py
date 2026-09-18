"""Login, signup, forgot-password and reset-password routes."""

import reflex as rx

from app.components.auth_forms import (
    auth_card,
    field_label,
    submit_button,
    text_field,
    INPUT_CLASS,
)
from app.components.auth_portal import (
    portal_context_panel,
    portal_hero,
    portal_login_card,
)
from app.components.layout import page_shell
from app.states.auth_state import AuthState


def _auth_layout(main: rx.Component, aside: rx.Component) -> rx.Component:
    return page_shell(
        rx.el.section(
            rx.el.div(
                rx.el.div(main, class_name="w-full min-w-0 flex-1"),
                rx.el.div(
                    aside,
                    class_name="w-full min-w-0 lg:max-w-sm",
                ),
                class_name="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-12 sm:px-6 lg:flex-row lg:items-start",
            ),
            class_name="cc-auth-surface w-full",
        )
    )


def _access_note(title: str, body: str, icon: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, class_name="h-4 w-4 text-teal-300"),
            rx.el.h3(
                title,
                class_name="text-sm font-semibold uppercase tracking-[0.16em] text-white",
            ),
            class_name="flex items-center gap-2",
        ),
        rx.el.p(
            body,
            class_name="mt-2 text-xs font-medium leading-relaxed text-slate-400",
        ),
        class_name="w-full rounded-xl border border-white/10 bg-[#0A1B33] p-5",
    )


# ------------------------------------------------------------------- login
def login_page() -> rx.Component:
    return page_shell(
        rx.el.section(
            rx.el.div(
                rx.el.div(
                    portal_hero(),
                    rx.el.div(portal_context_panel(), class_name="mt-8 w-full"),
                    class_name="w-full min-w-0 flex-1",
                ),
                rx.el.div(
                    portal_login_card(),
                    _access_note(
                        "Approval gate",
                        "Trainer and administrator accounts stay pending until an administrator approves them. Pending users can sign in but only reach their account page.",
                        "shield-check",
                    ),
                    class_name="flex w-full min-w-0 flex-col gap-5 lg:max-w-md",
                ),
                class_name="mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 py-12 sm:px-6 lg:flex-row lg:items-start lg:py-16",
            ),
            class_name="cc-auth-surface w-full bg-[#0A1B33]",
        )
    )


# ------------------------------------------------------------------ signup
def _role_select() -> rx.Component:
    return rx.el.div(
        field_label("Requested role"),
        rx.el.div(
            rx.el.select(
                rx.el.option("Trainee — immediate access", value="trainee"),
                rx.el.option("Trainer — requires approval", value="trainer"),
                rx.el.option(
                    "Administrator — requires approval", value="admin"
                ),
                name="role",
                default_value="trainee",
                class_name=f"{INPUT_CLASS} appearance-none pr-9",
            ),
            rx.icon(
                "chevron-down",
                class_name="pointer-events-none absolute right-3 top-1/2 h-4 w-4 translate-y-[-25%] text-slate-400",
            ),
            class_name="relative w-full",
        ),
        class_name="w-full",
    )


def signup_page() -> rx.Component:
    return _auth_layout(
        auth_card(
            "Request access",
            "Create your CAPACITY CONNECT account",
            "Trainee accounts activate immediately. Trainer and administrator requests are queued for administrator approval.",
            rx.el.form(
                rx.el.div(
                    text_field("Full name", "full_name", "Rahul Deshmukh"),
                    text_field(
                        "Email", "email", "you@institution.gov", "email"
                    ),
                    text_field(
                        "Phone (optional)",
                        "phone",
                        "+91 98450 00000",
                        "tel",
                        "",
                        False,
                    ),
                    _role_select(),
                    text_field(
                        "Password",
                        "password",
                        "At least 8 characters",
                        "password",
                    ),
                    text_field(
                        "Confirm password",
                        "confirm_password",
                        "Repeat your password",
                        "password",
                    ),
                    rx.el.p(
                        "Use at least 8 characters with upper and lower case letters and a number.",
                        class_name="text-xs font-medium text-slate-500",
                    ),
                    submit_button("Create account", "Creating account…"),
                    class_name="flex w-full flex-col gap-4",
                ),
                on_submit=AuthState.handle_signup,
            ),
            rx.el.div(
                rx.el.span(
                    "Already registered?",
                    class_name="text-sm font-medium text-slate-600",
                ),
                rx.el.a(
                    "Sign in instead",
                    href="/login",
                    class_name="text-sm font-semibold text-teal-700 hover:text-teal-600",
                ),
                class_name="flex flex-wrap items-center gap-2",
            ),
        ),
        rx.el.div(
            _access_note(
                "What happens next",
                "Trainees land straight in the trainee workspace. Trainer and administrator requests create an approval record that an administrator must decide before the workspace unlocks.",
                "route",
            ),
            class_name="flex w-full flex-col gap-5",
        ),
    )


# --------------------------------------------------------- forgot password
def forgot_password_page() -> rx.Component:
    return _auth_layout(
        auth_card(
            "Password recovery",
            "Request a password reset",
            "We generate a single-use, hashed reset token that expires in two hours.",
            rx.el.div(
                rx.el.form(
                    rx.el.div(
                        text_field(
                            "Registered email",
                            "email",
                            "you@institution.gov",
                            "email",
                        ),
                        submit_button(
                            "Generate reset link", "Generating link…"
                        ),
                        class_name="flex w-full flex-col gap-4",
                    ),
                    on_submit=AuthState.request_password_reset,
                ),
                rx.cond(
                    AuthState.reset_link != "",
                    rx.el.div(
                        rx.el.span(
                            "Development reset link",
                            class_name="text-xs font-semibold uppercase tracking-wider text-slate-500",
                        ),
                        rx.el.a(
                            AuthState.reset_link,
                            href=AuthState.reset_link,
                            class_name="mt-1 block break-all font-mono text-xs font-medium text-teal-700 hover:underline",
                        ),
                        class_name="mt-4 w-full rounded-lg border border-teal-200 bg-teal-50 p-4",
                    ),
                ),
                class_name="w-full",
            ),
            rx.el.a(
                "Back to sign in",
                href="/login",
                class_name="text-sm font-semibold text-teal-700 hover:text-teal-600",
            ),
        ),
        _access_note(
            "How reset tokens are stored",
            "Only a SHA-256 hash of the token is persisted, with an expiry timestamp and a used-at marker so a link can never be replayed.",
            "lock",
        ),
    )


# ---------------------------------------------------------- reset password
def reset_password_page() -> rx.Component:
    return _auth_layout(
        auth_card(
            "Password recovery",
            "Choose a new password",
            "Your reset token is verified against its stored hash before the password is replaced.",
            rx.el.form(
                rx.el.div(
                    rx.el.div(
                        field_label("Reset token"),
                        rx.el.input(
                            name="token",
                            type="text",
                            placeholder="Paste your reset token",
                            default_value=AuthState.reset_token_input,
                            key=AuthState.reset_token_input,
                            required=True,
                            class_name=INPUT_CLASS,
                        ),
                        class_name="w-full",
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
                    submit_button("Update password", "Updating password…"),
                    class_name="flex w-full flex-col gap-4",
                ),
                on_submit=AuthState.confirm_password_reset,
            ),
            rx.el.div(
                rx.el.a(
                    "Request a new link",
                    href="/forgot-password",
                    class_name="text-sm font-semibold text-slate-600 hover:text-[#0A1B33]",
                ),
                rx.el.a(
                    "Back to sign in",
                    href="/login",
                    class_name="text-sm font-semibold text-teal-700 hover:text-teal-600",
                ),
                class_name="flex flex-wrap items-center justify-between gap-3",
            ),
        ),
        _access_note(
            "Single use only",
            "Once a reset token is used it is marked spent immediately, and expired tokens are refused.",
            "timer",
        ),
    )

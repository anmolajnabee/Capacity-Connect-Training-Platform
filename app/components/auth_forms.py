"""Shared building blocks for the authentication routes."""

import reflex as rx

from app.components.layout import alert_banner
from app.states.auth_state import AuthState, DemoAccount


def field_label(text: str) -> rx.Component:
    return rx.el.label(
        text,
        class_name="block text-xs font-semibold uppercase tracking-wider text-slate-600",
    )


INPUT_CLASS = (
    "mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm "
    "font-medium text-slate-900 placeholder:text-slate-400 focus:border-teal-500 "
    "focus:ring-2 focus:ring-teal-500 outline-hidden"
)


def text_field(
    label: str,
    name: str,
    placeholder: str,
    input_type: str = "text",
    default_value: rx.Var | str = "",
    required: bool = True,
) -> rx.Component:
    return rx.el.div(
        field_label(label),
        rx.el.input(
            name=name,
            type=input_type,
            placeholder=placeholder,
            default_value=default_value,
            key=default_value,
            required=required,
            class_name=INPUT_CLASS,
        ),
        class_name="w-full",
    )


def submit_button(idle: str, busy: str) -> rx.Component:
    return rx.el.button(
        rx.cond(AuthState.is_loading, busy, idle),
        type="submit",
        disabled=AuthState.is_loading,
        class_name=(
            "flex w-full items-center justify-center rounded-lg bg-[#0A1B33] px-4 py-2.5 "
            "text-sm font-semibold text-white transition-colors hover:bg-[#122c50] "
            "disabled:cursor-not-allowed disabled:opacity-60"
        ),
    )


def auth_messages() -> rx.Component:
    return alert_banner(AuthState.error_message, AuthState.success_message)


def _demo_row(account: DemoAccount, **props) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                account["role"],
                class_name="w-fit rounded-full bg-teal-500/20 px-2 py-0.5 text-[0.7rem] font-semibold text-teal-200",
            ),
            rx.el.p(
                account["note"],
                class_name="mt-1 text-xs font-medium text-slate-400",
            ),
            rx.el.p(
                account["email"],
                class_name="mt-1 font-mono text-xs font-medium text-slate-200",
            ),
            rx.el.p(
                account["password"],
                class_name="font-mono text-xs font-medium text-slate-200",
            ),
            class_name="min-w-0",
        ),
        rx.el.button(
            "Use",
            on_click=lambda: AuthState.use_demo_account(
                account["email"], account["password"]
            ),
            class_name="h-fit w-fit shrink-0 rounded-md border border-teal-400/50 px-3 py-1 text-xs font-semibold text-teal-200 transition-colors hover:bg-teal-400/10",
        ),
        class_name="flex items-start justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.04] p-3",
        **props,
    )


def demo_credentials_panel() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("key-round", class_name="h-4 w-4 text-amber-300"),
            rx.el.h3(
                "Demo credentials",
                class_name="text-sm font-semibold uppercase tracking-[0.16em] text-white",
            ),
            class_name="flex items-center gap-2",
        ),
        rx.el.p(
            "This development environment ships one seeded account per role. "
            "Select one to fill the sign-in form.",
            class_name="mt-2 text-xs font-medium leading-relaxed text-slate-400",
        ),
        rx.el.div(
            rx.foreach(
                AuthState.demo_accounts,
                lambda account: _demo_row(account, key=account["email"]),
            ),
            class_name="mt-4 flex flex-col gap-2",
        ),
        class_name="w-full rounded-xl border border-white/10 bg-[#0A1B33] p-5",
    )


def auth_card(
    eyebrow: str,
    title: str,
    description: str,
    body: rx.Component,
    footer: rx.Component,
) -> rx.Component:
    return rx.el.div(
        rx.el.span(
            eyebrow,
            class_name="text-xs font-semibold uppercase tracking-[0.22em] text-teal-700",
        ),
        rx.el.h1(
            title,
            class_name="mt-2 text-2xl font-semibold text-[#0A1B33]",
        ),
        rx.el.p(
            description,
            class_name="mt-2 text-sm font-medium leading-relaxed text-slate-600",
        ),
        rx.el.div(auth_messages(), class_name="mt-5"),
        rx.el.div(body, class_name="mt-5"),
        rx.el.div(footer, class_name="mt-5"),
        class_name="w-full rounded-2xl border border-slate-200 bg-white p-6 sm:p-8",
    )

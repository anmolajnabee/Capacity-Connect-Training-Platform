"""Role-aware sign-in portal: role selector, pathway and premium form."""

import reflex as rx

from app.components.auth_forms import auth_messages, field_label
from app.states.auth_state import AuthState, PortalOption

_CARD_BASE = (
    "cc-lift group flex w-full min-w-0 flex-col gap-2 rounded-2xl border p-4 text-left "
    "outline-hidden focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0A1B33]"
)

_ACTIVE_BY_ROLE = {
    "trainee": (
        f"{_CARD_BASE} border-teal-400/70 bg-teal-400/12 focus-visible:ring-teal-300"
    ),
    "trainer": (
        f"{_CARD_BASE} border-amber-400/70 bg-amber-400/12 focus-visible:ring-amber-300"
    ),
    "admin": (
        f"{_CARD_BASE} border-sky-400/70 bg-sky-400/12 focus-visible:ring-sky-300"
    ),
}
_IDLE = (
    f"{_CARD_BASE} border-white/10 bg-white/[0.03] hover:border-white/25 "
    "hover:bg-white/[0.07] focus-visible:ring-white/50"
)

_ICON_ACTIVE = {
    "trainee": "flex size-10 items-center justify-center rounded-xl border border-teal-400/50 bg-teal-400/15 text-teal-200",
    "trainer": "flex size-10 items-center justify-center rounded-xl border border-amber-400/50 bg-amber-400/15 text-amber-200",
    "admin": "flex size-10 items-center justify-center rounded-xl border border-sky-400/50 bg-sky-400/15 text-sky-200",
}
_ICON_IDLE = "flex size-10 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-300"


_EYEBROW_BY_ROLE = rx.match(
    AuthState.selected_portal,
    (
        "trainer",
        "text-xs font-semibold uppercase tracking-[0.22em] text-amber-600",
    ),
    (
        "admin",
        "text-xs font-semibold uppercase tracking-[0.22em] text-sky-600",
    ),
    "text-xs font-semibold uppercase tracking-[0.22em] text-teal-700",
)


def _role_card(option: PortalOption, **props) -> rx.Component:
    is_active = AuthState.selected_portal == option["role"]
    return rx.el.button(
        rx.el.div(
            rx.el.div(
                rx.icon(option["icon"], class_name="h-5 w-5"),
                class_name=rx.cond(
                    is_active,
                    rx.match(
                        option["role"],
                        ("trainer", _ICON_ACTIVE["trainer"]),
                        ("admin", _ICON_ACTIVE["admin"]),
                        _ICON_ACTIVE["trainee"],
                    ),
                    _ICON_IDLE,
                ),
            ),
            rx.cond(
                is_active,
                rx.el.span(
                    rx.el.span(
                        class_name=rx.match(
                            option["role"],
                            (
                                "trainer",
                                "cc-pulse-dot block size-2 rounded-full bg-amber-300",
                            ),
                            (
                                "admin",
                                "cc-pulse-dot block size-2 rounded-full bg-sky-300",
                            ),
                            "cc-pulse-dot block size-2 rounded-full bg-teal-300",
                        )
                    ),
                    class_name="flex size-5 items-center justify-center",
                ),
                rx.el.span(class_name="size-5"),
            ),
            class_name="flex w-full items-start justify-between gap-2",
        ),
        rx.el.span(
            option["label"],
            class_name="text-sm font-semibold text-white",
        ),
        rx.el.span(
            option["tagline"],
            class_name="text-xs font-medium text-slate-400",
        ),
        type="button",
        aria_pressed=is_active.to_string(),
        title=f"Sign in as {option['label']}",
        on_click=lambda: AuthState.select_portal(option["role"]),
        class_name=rx.cond(
            is_active,
            rx.match(
                option["role"],
                ("trainer", _ACTIVE_BY_ROLE["trainer"]),
                ("admin", _ACTIVE_BY_ROLE["admin"]),
                _ACTIVE_BY_ROLE["trainee"],
            ),
            _IDLE,
        ),
        **props,
    )


def role_selector() -> rx.Component:
    return rx.el.div(
        rx.el.span(
            "Select your portal",
            class_name="text-xs font-semibold uppercase tracking-[0.22em] text-teal-300",
        ),
        rx.el.div(
            rx.foreach(
                AuthState.portal_options,
                lambda option: _role_card(option, key=option["role"]),
            ),
            role="group",
            aria_label="Sign-in portal",
            class_name="mt-3 grid w-full grid-cols-1 gap-3 sm:grid-cols-3",
        ),
        class_name="w-full",
    )


def _pathway_step(label: str, index: int) -> rx.Component:
    return rx.el.div(
        rx.el.span(
            (index + 1).to_string(),
            class_name=rx.match(
                AuthState.selected_portal,
                (
                    "trainer",
                    "flex size-6 shrink-0 items-center justify-center rounded-full border border-amber-300/50 bg-amber-400/15 text-[0.7rem] font-semibold text-amber-200",
                ),
                (
                    "admin",
                    "flex size-6 shrink-0 items-center justify-center rounded-full border border-sky-300/50 bg-sky-400/15 text-[0.7rem] font-semibold text-sky-200",
                ),
                "flex size-6 shrink-0 items-center justify-center rounded-full border border-teal-300/50 bg-teal-400/15 text-[0.7rem] font-semibold text-teal-200",
            ),
        ),
        rx.el.span(
            label,
            class_name="text-xs font-semibold text-slate-200",
        ),
        class_name="flex min-w-0 items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5",
    )


def portal_pathway() -> rx.Component:
    return rx.el.div(
        rx.el.span(
            "Role → workspace pathway",
            class_name="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400",
        ),
        rx.el.div(
            rx.foreach(
                AuthState.active_portal["pathway"],
                lambda step, index: _pathway_step(step, index),
            ),
            class_name="mt-3 flex flex-wrap items-center gap-2",
        ),
        class_name="w-full",
    )


def _bullet(text: str, icon: str, tone: str) -> rx.Component:
    return rx.el.li(
        rx.icon(icon, class_name=f"mt-0.5 h-4 w-4 shrink-0 {tone}"),
        rx.el.span(
            text,
            class_name="text-xs font-medium leading-relaxed text-slate-300",
        ),
        class_name="flex items-start gap-2",
    )


def portal_context_panel() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(
                    AuthState.active_portal["icon"],
                    class_name=rx.match(
                        AuthState.selected_portal,
                        ("trainer", "h-5 w-5 text-amber-300"),
                        ("admin", "h-5 w-5 text-sky-300"),
                        "h-5 w-5 text-teal-300",
                    ),
                ),
                class_name="flex size-11 items-center justify-center rounded-xl border border-white/10 bg-white/5",
            ),
            rx.el.div(
                rx.el.h2(
                    AuthState.active_portal["heading"],
                    class_name="text-lg font-semibold text-white",
                ),
                rx.el.p(
                    AuthState.active_portal["description"],
                    class_name="mt-1 text-sm font-medium leading-relaxed text-slate-300",
                ),
                class_name="min-w-0",
            ),
            class_name="flex items-start gap-3",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Access expectations",
                    class_name="text-xs font-semibold uppercase tracking-[0.16em] text-white",
                ),
                rx.el.ul(
                    rx.foreach(
                        AuthState.active_portal["expectations"],
                        lambda item: _bullet(
                            item, "circle-check", "text-teal-300"
                        ),
                    ),
                    class_name="mt-3 flex flex-col gap-2",
                ),
                class_name="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/[0.03] p-4",
            ),
            rx.el.div(
                rx.el.span(
                    "Workspace preview",
                    class_name="text-xs font-semibold uppercase tracking-[0.16em] text-white",
                ),
                rx.el.ul(
                    rx.foreach(
                        AuthState.active_portal["workspace"],
                        lambda item: _bullet(
                            item, "layout-dashboard", "text-amber-300"
                        ),
                    ),
                    class_name="mt-3 flex flex-col gap-2",
                ),
                class_name="min-w-0 flex-1 rounded-xl border border-white/10 bg-white/[0.03] p-4",
            ),
            class_name="mt-5 flex flex-col gap-4 md:flex-row",
        ),
        rx.el.div(portal_pathway(), class_name="mt-5"),
        class_name="cc-rise cc-rise-delay-1 w-full rounded-2xl border border-white/10 bg-white/[0.03] p-5 backdrop-blur",
    )


def portal_hero() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("radar", class_name="h-4 w-4 text-teal-300"),
            rx.el.span(
                "Institutional access control",
                class_name="text-xs font-semibold uppercase tracking-[0.22em] text-teal-300",
            ),
            class_name="flex w-fit items-center gap-2 rounded-full border border-teal-400/30 bg-teal-400/10 px-3 py-1",
        ),
        rx.el.h1(
            "Three portals. One competency registry.",
            class_name="mt-4 text-2xl font-semibold leading-tight text-white sm:text-3xl",
        ),
        rx.el.p(
            "Choose the portal that matches your registered role. Credentials "
            "are verified against the institutional account directory and a "
            "session is created only when the role matches.",
            class_name="mt-2 max-w-xl text-sm font-medium leading-relaxed text-slate-300",
        ),
        rx.el.div(role_selector(), class_name="mt-6"),
        class_name="cc-rise w-full",
    )


# --------------------------------------------------------------- form pieces
_FIELD_CLASS = (
    "w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-3 text-sm "
    "font-medium text-slate-900 placeholder:text-slate-400 outline-hidden transition-colors "
    "focus:border-[#0A1B33] focus:ring-2 focus:ring-[#0A1B33]/25"
)


def _icon_field(
    label: str,
    name: str,
    placeholder: str,
    icon: str,
    input_type: rx.Var | str,
    default_value: rx.Var | str,
    trailing: rx.Component | None = None,
) -> rx.Component:
    field_class = rx.cond(
        trailing == None, _FIELD_CLASS, f"{_FIELD_CLASS} pr-11"
    )
    return rx.el.div(
        field_label(label),
        rx.el.div(
            rx.icon(
                icon,
                class_name="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
            ),
            rx.el.input(
                name=name,
                type=input_type,
                placeholder=placeholder,
                default_value=default_value,
                key=default_value,
                required=True,
                auto_complete=(
                    rx.cond(name == "email", "email", "current-password")
                ),
                class_name=field_class,
            ),
            rx.cond(trailing != None, trailing, rx.fragment()),
            class_name="relative mt-1 w-full",
        ),
        class_name="w-full",
    )


def _password_toggle() -> rx.Component:
    return rx.el.button(
        rx.cond(
            AuthState.show_password,
            rx.icon("eye-off", class_name="h-4 w-4"),
            rx.icon("eye", class_name="h-4 w-4"),
        ),
        type="button",
        title=rx.cond(
            AuthState.show_password, "Hide password", "Show password"
        ),
        aria_label=rx.cond(
            AuthState.show_password, "Hide password", "Show password"
        ),
        on_click=AuthState.toggle_password_visibility,
        class_name=(
            "absolute right-2 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center "
            "rounded-lg text-slate-500 outline-hidden transition-colors hover:bg-slate-100 "
            "hover:text-[#0A1B33] focus-visible:ring-2 focus-visible:ring-[#0A1B33]/40"
        ),
    )


def _submit_row() -> rx.Component:
    return rx.el.button(
        rx.cond(
            AuthState.is_loading,
            rx.el.div(
                rx.el.span(
                    class_name="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
                ),
                rx.el.span("Verifying credentials…"),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                rx.icon("log-in", class_name="h-4 w-4"),
                rx.el.span(
                    f"Sign in to {AuthState.active_portal['label']} portal"
                ),
                class_name="flex items-center gap-2",
            ),
        ),
        type="submit",
        disabled=AuthState.is_loading,
        class_name=rx.match(
            AuthState.selected_portal,
            (
                "trainer",
                "cc-lift flex w-full items-center justify-center rounded-xl bg-[#0A1B33] px-4 py-3 text-sm font-semibold text-white outline-hidden hover:bg-[#122c50] focus-visible:ring-2 focus-visible:ring-amber-400 disabled:cursor-not-allowed disabled:opacity-60",
            ),
            (
                "admin",
                "cc-lift flex w-full items-center justify-center rounded-xl bg-[#0A1B33] px-4 py-3 text-sm font-semibold text-white outline-hidden hover:bg-[#122c50] focus-visible:ring-2 focus-visible:ring-sky-400 disabled:cursor-not-allowed disabled:opacity-60",
            ),
            "cc-lift flex w-full items-center justify-center rounded-xl bg-[#0A1B33] px-4 py-3 text-sm font-semibold text-white outline-hidden hover:bg-[#122c50] focus-visible:ring-2 focus-visible:ring-teal-400 disabled:cursor-not-allowed disabled:opacity-60",
        ),
    )


def _trust_cue(icon: str, text: str) -> rx.Component:
    return rx.el.div(
        rx.icon(icon, class_name="h-3.5 w-3.5 shrink-0 text-teal-700"),
        rx.el.span(text, class_name="text-xs font-medium text-slate-600"),
        class_name="flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1",
    )


def portal_login_card() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    f"{AuthState.active_portal['label']} sign in",
                    class_name=_EYEBROW_BY_ROLE,
                ),
                rx.el.h2(
                    "Verify your credentials",
                    class_name="mt-1 text-xl font-semibold text-[#0A1B33]",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                rx.icon("lock", class_name="h-4 w-4 text-slate-500"),
                class_name="flex size-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-[#F6F4EF]",
            ),
            class_name="flex items-start justify-between gap-3",
        ),
        rx.el.div(auth_messages(), class_name="mt-4"),
        rx.el.form(
            rx.el.div(
                rx.el.input(
                    type="hidden",
                    name="expected_role",
                    default_value=AuthState.selected_portal,
                    key=AuthState.selected_portal,
                ),
                _icon_field(
                    "Official email",
                    "email",
                    "you@institution.gov",
                    "mail",
                    "email",
                    AuthState.login_email_prefill,
                ),
                _icon_field(
                    "Password",
                    "password",
                    "Your password",
                    "key-round",
                    AuthState.password_input_type,
                    AuthState.login_password_prefill,
                    _password_toggle(),
                ),
                _submit_row(),
                class_name="flex w-full flex-col gap-4",
            ),
            on_submit=AuthState.handle_login,
        ),
        rx.el.button(
            rx.icon("wand-sparkles", class_name="h-4 w-4"),
            rx.el.span(
                f"Fill seeded {AuthState.active_portal['label']} demo credentials"
            ),
            type="button",
            on_click=AuthState.fill_portal_demo,
            class_name=(
                "mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-dashed "
                "border-slate-300 bg-[#FBFAF6] px-4 py-2.5 text-xs font-semibold text-slate-700 "
                "outline-hidden transition-colors hover:border-slate-400 hover:text-[#0A1B33] "
                "focus-visible:ring-2 focus-visible:ring-[#0A1B33]/30"
            ),
        ),
        rx.el.div(
            rx.el.a(
                "Forgot your password?",
                href="/forgot-password",
                class_name="rounded-md text-sm font-semibold text-teal-700 outline-hidden hover:text-teal-600 focus-visible:ring-2 focus-visible:ring-teal-500",
            ),
            rx.el.a(
                "Request an account",
                href="/signup",
                class_name="rounded-md text-sm font-semibold text-slate-600 outline-hidden hover:text-[#0A1B33] focus-visible:ring-2 focus-visible:ring-slate-400",
            ),
            class_name="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4",
        ),
        rx.el.div(
            _trust_cue("shield-check", "PBKDF2-HMAC-SHA256"),
            _trust_cue("fingerprint", "Signed session cookie"),
            _trust_cue("scan-eye", "Role-matched access"),
            class_name="mt-4 flex flex-wrap gap-2",
        ),
        class_name="cc-rise cc-rise-delay-2 w-full rounded-2xl border border-slate-200 bg-[#FBFAF6] p-6 sm:p-7",
    )

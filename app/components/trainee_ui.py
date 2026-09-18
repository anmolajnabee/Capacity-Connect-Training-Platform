"""Compact, data-dense building blocks for the trainee workspace."""

from __future__ import annotations

import reflex as rx


def chip(text: rx.Var | str, tone: str = "teal") -> rx.Component:
    tones = {
        "teal": "border-teal-200 bg-teal-50 text-teal-800",
        "navy": "border-slate-300 bg-slate-100 text-slate-700",
        "amber": "border-amber-300 bg-amber-50 text-amber-800",
        "green": "border-green-200 bg-green-100 text-green-700",
        "red": "border-red-200 bg-red-100 text-red-700",
    }
    return rx.el.span(
        text,
        class_name=f"w-fit rounded-full border px-2 py-0.5 text-[0.7rem] font-semibold {tones.get(tone, tones['teal'])}",
    )


def status_chip(text: rx.Var | str, is_good: rx.Var | bool) -> rx.Component:
    """Chip whose tone depends on a runtime condition."""
    return rx.cond(
        text,
        rx.cond(is_good, chip(text, "green"), chip(text, "amber")),
        rx.fragment(),
    )


def panel(
    title: str, description: str, *children: rx.Component, icon: str = "layers"
) -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.icon(icon, class_name="h-4 w-4 text-teal-700"),
                class_name="flex size-9 shrink-0 items-center justify-center rounded-lg border border-teal-200 bg-teal-50",
            ),
            rx.el.div(
                rx.el.h2(
                    title,
                    class_name="text-base font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    description,
                    class_name="mt-0.5 text-xs font-medium leading-relaxed text-slate-500",
                ),
                class_name="min-w-0",
            ),
            class_name="cc-panel-head flex items-start gap-3 border-b border-slate-200 px-4 py-3.5",
        ),
        rx.el.div(
            *children,
            class_name="flex w-full min-w-0 flex-col gap-4 px-4 py-4",
        ),
        class_name="cc-panel w-full min-w-0",
    )


def metric_tile(
    label: str, value: rx.Var | str, icon: str, hint: rx.Var | str = ""
) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                label,
                class_name="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-slate-500",
            ),
            rx.icon(icon, class_name="h-4 w-4 text-teal-700"),
            class_name="flex items-start justify-between gap-2",
        ),
        rx.el.p(
            value,
            class_name="mt-2 text-2xl font-semibold leading-none tracking-tight text-[#0A1B33]",
        ),
        rx.el.p(
            hint,
            class_name="mt-1 truncate text-[0.7rem] font-medium text-slate-500",
        ),
        class_name="cc-card cc-hover w-full min-w-0 p-4",
    )


def progress_bar(percent: rx.Var | int, tone: str = "teal") -> rx.Component:
    bar = {
        "teal": "bg-teal-600",
        "amber": "bg-amber-500",
        "navy": "bg-[#0A1B33]",
        "sky": "bg-sky-600",
    }.get(tone, "bg-teal-600")
    return rx.el.div(
        rx.el.div(
            class_name=f"cc-bar-fill {bar}",
            style={"width": f"{percent}%"},
        ),
        class_name="cc-bar h-2 w-full",
    )


def skill_meter(skill) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    skill["name"],
                    class_name="truncate text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    skill["category"],
                    class_name="truncate text-[0.7rem] font-medium uppercase tracking-wider text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                rx.el.span(
                    f"{skill['score']}%",
                    class_name="text-sm font-semibold text-teal-700",
                ),
                chip(skill["level"], "navy"),
                class_name="flex shrink-0 items-center gap-2",
            ),
            class_name="flex items-start justify-between gap-3",
        ),
        rx.el.div(
            progress_bar(skill["score"]),
            class_name="mt-2",
        ),
        rx.el.div(
            rx.el.span(
                f"{skill['years']:.1f} yrs practice",
                class_name="text-[0.7rem] font-medium text-slate-500",
            ),
            class_name="mt-2 flex items-center justify-between gap-2",
        ),
        class_name="cc-inset w-full min-w-0 p-3",
    )


def field(
    label: str,
    name: str,
    default_value: rx.Var | str = "",
    placeholder: str = "",
    input_type: str = "text",
    required: bool = False,
    step: str = "",
) -> rx.Component:
    props = {}
    if step:
        props["step"] = step
    return rx.el.label(
        rx.el.span(
            label,
            class_name="block text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
        ),
        rx.el.input(
            name=name,
            type=input_type,
            placeholder=placeholder,
            default_value=default_value,
            required=required,
            class_name="cc-focus mt-1 w-full rounded-[0.875rem] border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-900 outline-hidden transition-colors duration-200 focus:border-teal-600",
            **props,
        ),
        class_name="flex w-full min-w-0 flex-col",
    )


def textarea_field(
    label: str,
    name: str,
    default_value: rx.Var | str = "",
    placeholder: str = "",
    rows: str = "3",
) -> rx.Component:
    return rx.el.label(
        rx.el.span(
            label,
            class_name="block text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
        ),
        rx.el.textarea(
            name=name,
            rows=rows,
            placeholder=placeholder,
            default_value=default_value,
            class_name="cc-focus mt-1 w-full rounded-[0.875rem] border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-900 outline-hidden transition-colors duration-200 focus:border-teal-600",
        ),
        class_name="flex w-full min-w-0 flex-col",
    )


def select_field(
    label: str,
    name: str,
    options: rx.Component,
    default_value: rx.Var | str = "",
) -> rx.Component:
    return rx.el.label(
        rx.el.span(
            label,
            class_name="block text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
        ),
        rx.el.div(
            rx.el.select(
                options,
                name=name,
                default_value=default_value,
                class_name="cc-focus w-full appearance-none rounded-[0.875rem] border border-slate-300 bg-white px-3 py-2 pr-9 text-sm font-medium text-slate-900 outline-hidden transition-colors duration-200 focus:border-teal-600",
            ),
            rx.icon(
                "chevron-down",
                class_name="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400",
            ),
            class_name="relative mt-1 w-full",
        ),
        class_name="flex w-full min-w-0 flex-col",
    )


def primary_button(label: str, **props) -> rx.Component:
    return rx.el.button(
        label,
        class_name="cc-focus-navy cc-press flex w-fit items-center justify-center gap-2 rounded-[0.875rem] bg-[#0A1B33] px-4 py-2 text-sm font-semibold text-white shadow-xs outline-hidden transition-all duration-200 hover:bg-[#12304f] hover:shadow-sm disabled:opacity-50",
        **props,
    )


def teal_button(label: str, **props) -> rx.Component:
    return rx.el.button(
        label,
        class_name="cc-focus cc-press flex w-fit items-center justify-center gap-2 rounded-[0.875rem] bg-teal-600 px-4 py-2 text-sm font-semibold text-white shadow-xs outline-hidden transition-all duration-200 hover:bg-teal-500 hover:shadow-sm disabled:opacity-50",
        **props,
    )


def ghost_button(label: str, **props) -> rx.Component:
    return rx.el.button(
        label,
        class_name="cc-focus cc-press flex w-fit items-center justify-center gap-2 rounded-[0.875rem] border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 outline-hidden transition-all duration-200 hover:border-slate-400 hover:bg-slate-50",
        **props,
    )


def empty_block(
    title: str, description: str, icon: str = "inbox"
) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, class_name="h-5 w-5 text-teal-700"),
            class_name="flex size-11 items-center justify-center rounded-full border border-teal-200 bg-teal-50",
        ),
        rx.el.p(
            title,
            class_name="mt-3 text-sm font-semibold text-[#0A1B33]",
        ),
        rx.el.p(
            description,
            class_name="mt-1 max-w-sm text-xs font-medium leading-relaxed text-slate-500",
        ),
        class_name="cc-fade flex w-full flex-col items-center justify-center rounded-[0.875rem] border border-dashed border-slate-300 bg-[#FBFAF7] px-5 py-10 text-center",
    )


def loading_rows(count: int = 3) -> rx.Component:
    return rx.el.div(
        rx.foreach(
            list(range(count)),
            lambda _slot: rx.el.div(
                class_name="cc-skeleton h-16 w-full rounded-[0.875rem] border border-slate-200"
            ),
        ),
        class_name="flex w-full flex-col gap-3",
    )

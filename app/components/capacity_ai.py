import reflex as rx
from app.states.capacity_ai_state import CapacityAIState as A


def capacity_ai_panel() -> rx.Component:
    return rx.el.aside(
        rx.el.button(
            rx.icon("radar", class_name="h-4 w-4"),
            "CAPACITY AI · learning support",
            on_click=A.toggle,
            aria_expanded=A.opened,
            class_name="cc-focus flex w-fit items-center gap-2 rounded-lg border border-teal-300 bg-[#0A1B33] px-4 py-3 text-sm font-semibold text-teal-100",
        ),
        rx.cond(
            A.opened,
            rx.el.div(
                rx.el.div(
                    rx.el.h2(
                        "Contextual learning support",
                        class_name="text-xl font-semibold text-[#0A1B33]",
                    ),
                    rx.el.p(
                        "Advisory only · approved course material · no official assessment answers or proficiency writes. Select the course you are currently studying.",
                        class_name="mt-1 text-sm text-slate-600",
                    ),
                ),
                rx.el.form(
                    rx.el.label(
                        "Enrolled course",
                        rx.el.div(
                            rx.el.select(
                                rx.el.option("Select course context", value=""),
                                rx.foreach(
                                    A.courses,
                                    lambda c: rx.el.option(
                                        c["title"], value=c["id"]
                                    ),
                                ),
                                name="course",
                                required=True,
                                class_name="cc-focus w-full appearance-none rounded-lg border border-slate-300 bg-white p-3 pr-9 text-sm text-slate-900",
                            ),
                            rx.icon(
                                "chevron-down",
                                class_name="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-500",
                            ),
                            class_name="relative",
                        ),
                        class_name="text-xs font-semibold text-slate-700",
                    ),
                    rx.el.label(
                        "Learning action",
                        rx.el.div(
                            rx.el.select(
                                rx.foreach(
                                    [
                                        "Explain Concept",
                                        "Summarize Resource",
                                        "Explain Mistake",
                                        "Generate Practice Questions",
                                        "Recommend Resource",
                                        "Suggest Next Learning Step",
                                    ],
                                    lambda label: rx.el.option(
                                        label, value=label
                                    ),
                                ),
                                name="action",
                                class_name="cc-focus w-full appearance-none rounded-lg border border-slate-300 bg-white p-3 pr-9 text-sm text-slate-900",
                            ),
                            rx.icon(
                                "chevron-down",
                                class_name="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-500",
                            ),
                            class_name="relative",
                        ),
                        class_name="text-xs font-semibold text-slate-700",
                    ),
                    rx.el.button(
                        rx.cond(
                            A.busy,
                            "Reviewing authorized context…",
                            "Run learning action",
                        ),
                        type="submit",
                        disabled=A.busy | (A.courses.length() == 0),
                        class_name="cc-focus rounded-lg bg-teal-700 px-4 py-3 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-40",
                    ),
                    on_submit=A.request,
                    class_name="grid gap-3 md:grid-cols-3",
                ),
                rx.cond(
                    A.error != "",
                    rx.el.p(
                        A.error, role="alert", class_name="text-sm text-red-700"
                    ),
                ),
                rx.cond(
                    A.busy,
                    rx.el.div(
                        "Preparing grounded guidance…",
                        role="status",
                        class_name="animate-pulse rounded-lg bg-teal-50 p-5 text-sm text-teal-900",
                    ),
                ),
                rx.cond(
                    A.response != "",
                    rx.el.div(
                        rx.el.span(
                            A.model_label,
                            class_name="w-fit rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900",
                        ),
                        rx.el.p(
                            A.response,
                            class_name="whitespace-pre-wrap text-sm leading-relaxed text-slate-800",
                        ),
                        rx.el.h3(
                            "Source register",
                            class_name="font-semibold text-[#0A1B33]",
                        ),
                        rx.cond(
                            A.sources.length() == 0,
                            rx.el.p(
                                "No approved resource excerpts were available. This is not a sourced concept explanation.",
                                class_name="text-sm text-slate-600",
                            ),
                        ),
                        rx.foreach(
                            A.sources,
                            lambda source: rx.el.article(
                                rx.el.h4(
                                    source["title"],
                                    class_name="text-sm font-semibold text-teal-900",
                                ),
                                rx.el.p(
                                    f"{source['course']} → {source['module']}",
                                    class_name="text-xs text-slate-600",
                                ),
                                rx.el.p(
                                    source["excerpt"],
                                    class_name="text-sm text-slate-700",
                                ),
                                class_name="rounded-lg border border-teal-100 bg-white p-3",
                            ),
                        ),
                        class_name="flex flex-col gap-3",
                    ),
                ),
                class_name="mt-3 flex flex-col gap-5 rounded-xl border border-teal-200 bg-[#FBFAF7] p-5",
            ),
        ),
        class_name="w-full",
    )

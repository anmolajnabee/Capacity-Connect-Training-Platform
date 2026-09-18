"""Signature skills-to-training pathway visualization."""

import reflex as rx

LOOP_STAGES: list[dict[str, str]] = [
    {
        "step": "01",
        "stage": "Organizational need",
        "headline": "Define operational demand",
        "detail": "Organization, department and role requirements establish the target capability.",
        "icon": "building-2",
        "metric": "Required capability",
    },
    {
        "step": "02",
        "stage": "Competency gap",
        "headline": "Compare target with evidence",
        "detail": "Required level minus verified demonstrated level. An unknown baseline remains unmeasured.",
        "icon": "radar",
        "metric": "Verified baseline",
    },
    {
        "step": "03",
        "stage": "Trainer fit",
        "headline": "Explain the staffing decision",
        "detail": "Read competency coverage, eligibility, availability and capacity before assigning faculty.",
        "icon": "scan-line",
        "metric": "Trainer Fit Score",
    },
    {
        "step": "04",
        "stage": "Training",
        "headline": "Deliver structured learning",
        "detail": "Programs, courses, modules and resources connect learning activity to the identified gap.",
        "icon": "presentation",
        "metric": "Learning pathway",
    },
    {
        "step": "05",
        "stage": "Evidence",
        "headline": "Measure, verify and retain",
        "detail": "Official results and verified evaluations provide an auditable evidence trail. Practice stays separate.",
        "icon": "clipboard-check",
        "metric": "Verification trail",
    },
    {
        "step": "06",
        "stage": "Improvement",
        "headline": "Compare verified observations",
        "detail": "Observed Competency Improvement compares measured pre/post levels without inferring missing values.",
        "icon": "trending-up",
        "metric": "Observed change",
    },
    {
        "step": "07",
        "stage": "Effectiveness",
        "headline": "Read outcomes in context",
        "detail": "Participation, completion, official performance and feedback inform an observational review, not a causal claim.",
        "icon": "chart-no-axes-combined",
        "metric": "Evidence-led review",
    },
    {
        "step": "08",
        "stage": "Organizational capacity",
        "headline": "Reassess operational readiness",
        "detail": "Review remaining demand, revisit targets and feed the next organizational need back into the loop.",
        "icon": "refresh-cw",
        "metric": "Feedback to need",
    },
]


def _stage_card(stage: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                stage["step"],
                class_name="text-[0.65rem] font-semibold tracking-[0.2em] text-teal-300",
            ),
            rx.icon(
                stage["icon"],
                class_name="h-4 w-4 text-teal-300",
            ),
            class_name="flex items-center justify-between",
        ),
        rx.el.h3(
            stage["stage"],
            class_name="mt-3 text-sm font-semibold uppercase tracking-[0.14em] text-white",
        ),
        rx.el.p(
            stage["headline"],
            class_name="mt-2 line-clamp-2 text-sm font-semibold leading-snug text-slate-100",
        ),
        rx.el.p(
            stage["detail"],
            class_name="mt-2 text-xs font-medium leading-relaxed text-slate-400",
        ),
        rx.el.div(
            rx.el.span(
                stage["metric"],
                class_name="rounded-full border border-amber-400/40 bg-amber-400/10 px-2 py-0.5 text-[0.7rem] font-semibold text-amber-200",
            ),
            class_name="mt-4 flex w-fit",
        ),
        class_name="relative flex h-full min-w-0 flex-col rounded-xl border border-white/10 bg-white/[0.04] p-4 transition-colors hover:border-teal-300/40 hover:bg-white/[0.07]",
    )


def _grid_lines() -> rx.Component:
    return rx.el.div(
        class_name=(
            "pointer-events-none absolute inset-0 opacity-[0.18] "
            "[background-image:linear-gradient(to_right,rgba(148,163,184,0.35)_1px,transparent_1px),"
            "linear-gradient(to_bottom,rgba(148,163,184,0.35)_1px,transparent_1px)] "
            "[background-size:44px_44px]"
        )
    )


def pathway_panel() -> rx.Component:
    return rx.el.section(
        _grid_lines(),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "SIH26075 · capacity feedback loop",
                    class_name="text-xs font-semibold uppercase tracking-[0.22em] text-teal-300",
                ),
                rx.el.h2(
                    "From operational need to evidenced capacity",
                    class_name="mt-2 text-2xl font-semibold text-white sm:text-3xl",
                ),
                rx.el.p(
                    "Organizational need → competency gap → trainer fit → training → evidence → improvement → effectiveness → organizational capacity. The loop is a decision process, not a promise that attendance produces mastery.",
                    class_name="mt-2 max-w-3xl text-sm font-medium leading-relaxed text-slate-300",
                ),
                class_name="w-full",
            ),
            rx.cond(
                True,
                rx.el.div(
                    rx.el.div(
                        class_name="absolute left-0 right-0 top-1/2 hidden h-px bg-gradient-to-r from-teal-400/10 via-teal-400/60 to-amber-300/40 xl:block",
                    ),
                    rx.el.div(
                        rx.foreach(
                            LOOP_STAGES,
                            lambda stage: _stage_card(stage),
                        ),
                        class_name="relative grid w-full grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4",
                    ),
                    class_name="relative mt-8 w-full",
                ),
                rx.el.div(
                    rx.foreach(
                        [0, 1, 2, 3, 4],
                        lambda _slot: rx.el.div(
                            class_name="h-44 animate-pulse rounded-xl border border-white/10 bg-white/[0.05]"
                        ),
                    ),
                    class_name="mt-8 grid w-full grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4",
                ),
            ),
            rx.el.div(
                rx.el.div(
                    rx.icon("git-branch", class_name="h-4 w-4 text-teal-300"),
                    rx.el.p(
                        "Organizational capacity → organizational need. Verified evidence informs the next decision; course completion alone never establishes competency mastery.",
                        class_name="text-xs font-medium text-slate-300",
                    ),
                    class_name="flex items-center gap-2",
                ),
                class_name="mt-6 w-full rounded-lg border border-white/10 bg-white/[0.03] px-4 py-3",
            ),
            class_name="relative mx-auto w-full max-w-7xl px-4 py-14 sm:px-6",
        ),
        class_name="relative w-full overflow-hidden bg-[#0A1B33]",
    )

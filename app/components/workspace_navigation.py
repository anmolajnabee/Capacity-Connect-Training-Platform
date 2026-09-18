import reflex as rx


def navigation_group(label: str, links: rx.Component) -> rx.Component:
    return rx.el.div(
        rx.el.p(
            label,
            class_name="mb-2 text-[0.65rem] font-semibold uppercase tracking-[0.18em] text-slate-400",
        ),
        rx.el.div(links, class_name="flex flex-wrap gap-1"),
        class_name="flex min-w-0 flex-col border-l border-white/15 pl-3",
    )


def navigation_label(label: rx.Var) -> rx.Component:
    return rx.el.span(
        rx.match(
            label,
            ("Dashboard", "Overview"),
            ("Courses", "Training"),
            ("Learning Resources", "Resources"),
            ("My Courses", "Assigned Courses"),
            ("Trainer Library", "Resource Library"),
            ("Create Assessment", "Questionnaires"),
            ("Certifications", "Certificates"),
            ("My Profile", "Profile"),
            label,
        ),
        class_name="whitespace-nowrap",
    )

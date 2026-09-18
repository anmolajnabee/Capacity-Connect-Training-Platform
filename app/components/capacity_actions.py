import reflex as rx
from app.states.capacity_operations_state import CapacityOperationsState as O
from app.states.practice_state import PracticeState as P

BUTTON = "cc-focus rounded-lg border border-teal-700 bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-40"
INPUT = "cc-focus w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"


def field(name: str, label: str, kind: str = "text") -> rx.Component:
    return rx.el.label(
        rx.el.span(label, class_name="text-xs font-semibold text-slate-700"),
        rx.el.input(name=name, type=kind, required=True, class_name=INPUT),
        class_name="flex min-w-0 flex-col gap-1",
    )


def choices(name: str, label: str, items: list[str]) -> rx.Component:
    return rx.el.label(
        rx.el.span(label, class_name="text-xs font-semibold text-slate-700"),
        rx.el.div(
            rx.el.select(
                rx.foreach(items, lambda item: rx.el.option(item, value=item)),
                name=name,
                class_name="cc-focus w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2 pr-9 text-sm text-slate-900",
            ),
            rx.icon(
                "chevron-down",
                class_name="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-500",
            ),
            class_name="relative",
        ),
        class_name="flex flex-col gap-1",
    )


def catalog(name: str, label: str, kind: str) -> rx.Component:
    return rx.el.label(
        rx.el.span(label, class_name="text-xs font-semibold text-slate-700"),
        rx.el.div(
            rx.el.select(
                rx.el.option("Select a record", value=""),
                rx.foreach(
                    O.options,
                    lambda item: rx.cond(
                        (item["kind"] == kind) | (kind == "all"),
                        rx.el.option(
                            f"{item['kind']} #{item['id']} · {item['label']}",
                            value=item["id"],
                        ),
                    ),
                ),
                name=name,
                required=True,
                class_name="cc-focus w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2 pr-9 text-sm text-slate-900",
            ),
            rx.icon(
                "chevron-down",
                class_name="pointer-events-none absolute right-3 top-3 h-4 w-4 text-slate-500",
            ),
            class_name="relative",
        ),
        class_name="flex min-w-0 flex-col gap-1",
    )


def form(action: str, title: str, *children: rx.Component) -> rx.Component:
    return rx.el.form(
        rx.el.h3(
            title,
            class_name="col-span-full text-lg font-semibold text-[#0A1B33]",
        ),
        rx.el.input(type="hidden", name="action", value=action),
        *children,
        rx.el.button(
            rx.cond(O.busy, "Saving…", "Save / execute"),
            type="submit",
            disabled=O.busy,
            class_name=BUTTON,
        ),
        on_submit=O.act,
        class_name="grid w-full gap-4 rounded-xl border border-teal-200 bg-[#FBFAF7] p-5 md:grid-cols-2",
    )


def practice_panel() -> rx.Component:
    return rx.el.section(
        rx.el.h2(
            "Practice only · weak competency review",
            class_name="text-xl font-semibold text-[#0A1B33]",
        ),
        rx.el.p(
            "Published formative questions only. Your answers are scored on the server and never update official results or competency levels.",
            class_name="text-sm text-slate-600",
        ),
        rx.el.button(
            "Start / resume practice",
            on_click=P.start,
            disabled=P.busy,
            class_name=BUTTON,
        ),
        rx.el.p(
            P.message,
            role="status",
            class_name="whitespace-pre-wrap text-sm text-teal-900",
        ),
        rx.cond(
            P.items.length() > 0,
            rx.el.form(
                rx.foreach(
                    P.items,
                    lambda item: rx.el.fieldset(
                        rx.el.legend(
                            item["prompt"],
                            class_name="font-semibold text-slate-900",
                        ),
                        rx.foreach(
                            item["options"],
                            lambda option: rx.el.label(
                                rx.el.input(
                                    type="radio",
                                    name=item["id"],
                                    value=option["id"],
                                    default_checked=item["selected"]
                                    == option["id"],
                                    disabled=P.status == "graded",
                                    required=True,
                                    class_name="accent-teal-700",
                                ),
                                option["text"],
                                class_name="flex items-start gap-2 rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700",
                            ),
                        ),
                        rx.el.p(
                            item["feedback"], class_name="text-sm text-teal-800"
                        ),
                        key=f"{P.attempt_id}-{item['id']}-{P.status}",
                        class_name="flex flex-col gap-3 rounded-lg border border-slate-200 p-4",
                    ),
                ),
                rx.cond(
                    P.status == "in_progress",
                    rx.el.button(
                        "Submit formative answers",
                        type="submit",
                        disabled=P.busy,
                        class_name=BUTTON,
                    ),
                ),
                on_submit=P.save,
                class_name="flex flex-col gap-4",
            ),
        ),
        class_name="flex flex-col gap-4 rounded-xl border border-amber-200 bg-amber-50/40 p-5",
    )


def notification_panel() -> rx.Component:
    return rx.el.div(
        rx.el.button(
            "Mark all loaded notifications read",
            on_click=lambda: O.mark_read(0),
            disabled=O.busy,
            class_name=BUTTON,
        ),
        rx.cond(
            O.notices.length() == 0,
            rx.el.p(
                "No notifications currently addressed to you.",
                class_name="text-sm text-slate-600",
            ),
        ),
        rx.foreach(
            O.notices,
            lambda n: rx.el.article(
                rx.el.div(
                    rx.el.h3(
                        n["title"], class_name="font-semibold text-slate-900"
                    ),
                    rx.el.span(
                        n["status"],
                        class_name="w-fit rounded-full bg-teal-50 px-2 py-1 text-xs text-teal-800",
                    ),
                    class_name="flex justify-between gap-3",
                ),
                rx.el.p(
                    n["body"],
                    class_name="whitespace-pre-wrap text-sm text-slate-700",
                ),
                rx.el.button(
                    "Mark read",
                    on_click=lambda: O.mark_read(n["id"].to(int)),
                    disabled=(n["status"] == "read") | O.busy,
                    class_name=BUTTON,
                ),
                class_name="flex flex-col items-start gap-3 rounded-xl border border-slate-200 bg-white p-5",
            ),
        ),
        class_name="flex flex-col items-start gap-4",
    )


def path_panel() -> rx.Component:
    return rx.el.ol(
        rx.cond(
            O.steps.length() == 0,
            rx.el.p(
                "Open Competencies, inspect a gap and generate a mapped pathway.",
                class_name="text-sm text-slate-600",
            ),
        ),
        rx.foreach(
            O.steps,
            lambda s: rx.el.li(
                rx.el.span(
                    f"Step {s['position']} · {s['kind']} · {s['status']}",
                    class_name="text-xs font-semibold uppercase text-teal-800",
                ),
                rx.el.h3(s["title"], class_name="font-semibold text-slate-900"),
                rx.el.p(
                    "Complete the linked activity first. Earlier steps and completion records are checked before saving.",
                    class_name="text-sm text-slate-600",
                ),
                rx.el.div(
                    rx.el.a(
                        "Open My Learning",
                        href="/trainee/learning",
                        class_name=BUTTON,
                    ),
                    rx.el.button(
                        "Confirm eligible completion",
                        on_click=lambda: O.finish_step(s["id"].to(int)),
                        disabled=(s["status"] == "completed") | O.busy,
                        class_name=BUTTON,
                    ),
                    class_name="flex flex-wrap gap-2",
                ),
                class_name="flex flex-col gap-3 border-l-2 border-teal-500 bg-white p-5",
            ),
        ),
        class_name="flex flex-col gap-4",
    )


def fit_panel(team: bool = False) -> rx.Component:
    return rx.el.div(
        form(
            rx.cond(team, "team", "fit"),
            "Recalculate from current evidence",
            catalog("course", "Course", "course"),
            field("start", "Window start", "date"),
            field("end", "Window end", "date"),
            choices(
                "qualification",
                "Require verified qualification",
                ["false", "true"],
            ),
        ),
        rx.el.p(
            "Score = coverage × 40% + domain × 25% + experience × 15% + qualification × 10% + observed effectiveness × 10%. Availability and capacity are eligibility gates, not substituted factors.",
            class_name="rounded-lg bg-teal-50 p-4 text-sm text-teal-900",
        ),
        rx.foreach(
            O.fits,
            lambda f: rx.el.article(
                rx.el.h3(
                    f"{f['trainer']} · {f['score']} / 100",
                    class_name="text-lg font-semibold text-slate-900",
                ),
                rx.el.p(
                    f"{f['course']} · {f['status']}",
                    class_name="text-sm text-teal-800",
                ),
                rx.el.progress(
                    value=f["score"].to(float),
                    max=100,
                    class_name="h-2 w-full accent-teal-700",
                ),
                rx.el.details(
                    rx.el.summary(
                        "Five-factor arithmetic, covered competencies and eligibility failures",
                        class_name="cc-focus cursor-pointer text-sm font-semibold text-teal-800",
                    ),
                    rx.el.pre(
                        f["detail"],
                        class_name="overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-xs text-slate-700",
                    ),
                ),
                rx.el.button(
                    "Revalidate & assign individual",
                    on_click=lambda: O.assign_fit(f["id"].to(int)),
                    disabled=(f["status"] != "eligible") | O.busy,
                    class_name=BUTTON,
                ),
                class_name="flex flex-col items-start gap-3 rounded-xl border border-slate-200 bg-white p-5",
            ),
        ),
        class_name="flex flex-col gap-4",
    )


def authoring_panel() -> rx.Component:
    return rx.el.div(
        form(
            "training",
            "Create Training · draft delivery hierarchy",
            field("code", "Unique course code"),
            field("title", "Course / program title"),
            field("description", "Course summary"),
            field("module", "First module title"),
            field("lesson", "First lesson title"),
            field("content", "Lesson content"),
        ),
        form(
            "lesson",
            "Add structured learning content",
            catalog("course", "Authorized course", "course"),
            field("module", "New module title"),
            field("title", "Lesson title"),
            field("description", "Lesson content"),
        ),
        rx.el.details(
            rx.el.summary(
                "CAPACITY AI practice drafts · trainer review",
                class_name="cc-focus cursor-pointer font-semibold text-teal-900",
            ),
            rx.foreach(
                O.drafts,
                lambda d: rx.el.article(
                    rx.el.p(
                        f"Draft #{d['id']} · course #{d['course']}",
                        class_name="text-xs text-teal-800",
                    ),
                    rx.el.p(
                        d["prompt"],
                        class_name="whitespace-pre-wrap text-sm text-slate-700",
                    ),
                    class_name="my-3 rounded-lg border border-slate-200 bg-white p-4",
                ),
            ),
            form(
                "review_practice",
                "Review and publish formative question",
                field("id", "Draft question ID", "number"),
                catalog("course", "Authorized course", "course"),
                field("title", "Reviewed question prompt"),
                field("description", "Reviewed explanation"),
                field("correct", "Correct option"),
                field("incorrect", "Distractor"),
            ),
        ),
        class_name="flex flex-col gap-5",
    )


def operations_panel(view: rx.Var) -> rx.Component:
    return rx.el.section(
        rx.cond(
            O.error != "",
            rx.el.p(
                O.error,
                role="alert",
                class_name="rounded-lg bg-red-50 p-3 text-sm text-red-800",
            ),
        ),
        rx.cond(
            O.success != "",
            rx.el.p(
                O.success,
                role="status",
                class_name="rounded-lg bg-green-50 p-3 text-sm text-green-800",
            ),
        ),
        rx.match(
            view,
            (
                "notifications",
                rx.el.div(
                    notification_panel(),
                    rx.cond(
                        O.role == "admin",
                        form(
                            "notice",
                            "Publish notification",
                            field("title", "Title"),
                            field("description", "Message"),
                            choices(
                                "audience",
                                "Audience",
                                ["all", "trainees", "trainers", "admins"],
                            ),
                        ),
                    ),
                    class_name="flex flex-col gap-5",
                ),
            ),
            ("paths", path_panel()),
            ("practice", practice_panel()),
            (
                "availability",
                form(
                    "availability",
                    "Save your availability and capacity (UTC)",
                    field("start", "Window starts", "datetime-local"),
                    field("end", "Window ends", "datetime-local"),
                    choices(
                        "status",
                        "Availability",
                        ["available", "tentative", "unavailable"],
                    ),
                    field("hours", "Maximum training hours", "number"),
                    field("slots", "Maximum concurrent courses", "number"),
                    field("participants", "Maximum participants", "number"),
                    field("description", "Operational notes"),
                ),
            ),
            ("programs", authoring_panel()),
            ("learning-content", authoring_panel()),
            (
                "framework",
                form(
                    "framework",
                    "Create / update / deactivate framework record",
                    choices(
                        "kind",
                        "Record type",
                        [
                            "organization",
                            "department",
                            "subject",
                            "competency",
                            "role",
                        ],
                    ),
                    rx.el.label(
                        "Existing record ID (blank creates a new record)",
                        rx.el.input(name="id", type="number", class_name=INPUT),
                        class_name="text-xs text-slate-700",
                    ),
                    field("code", "Stable code"),
                    field("title", "Name / role title"),
                    field("description", "Description"),
                    rx.el.label(
                        "Parent ID: organization for department/role; subject for competency; blank otherwise",
                        rx.el.input(
                            name="parent", type="number", class_name=INPUT
                        ),
                        class_name="text-xs text-slate-700",
                    ),
                    choices("active", "Active", ["true", "false"]),
                    rx.el.details(
                        rx.el.summary(
                            "Parent / record directory",
                            class_name="text-sm font-semibold text-teal-800",
                        ),
                        rx.foreach(
                            O.options,
                            lambda item: rx.el.p(
                                f"{item['kind']} #{item['id']} · {item['label']}",
                                class_name="text-xs text-slate-700",
                            ),
                        ),
                    ),
                ),
            ),
            (
                "requirements",
                form(
                    "requirement",
                    "Save competency requirement",
                    choices(
                        "kind",
                        "Requirement type",
                        ["role", "outcome", "trainer", "prerequisite", "need"],
                    ),
                    catalog(
                        "owner",
                        "Owner (match type: role, course or organization)",
                        "all",
                    ),
                    catalog("competency", "Competency", "competency"),
                    choices(
                        "level", "Required level", ["1", "2", "3", "4", "5"]
                    ),
                    rx.el.label(
                        "Stable code (capacity needs only)",
                        rx.el.input(name="code", class_name=INPUT),
                        class_name="text-xs text-slate-700",
                    ),
                ),
            ),
            ("trainer-fit", fit_panel()),
            ("teams", fit_panel(True)),
            (
                "effectiveness",
                form(
                    "effectiveness",
                    "Refresh observed effectiveness snapshot",
                    catalog("course", "Course", "course"),
                ),
            ),
            (
                "achievements",
                form(
                    "achievement",
                    "Publish achievement criteria",
                    field("code", "Unique code"),
                    field("title", "Title"),
                    field("description", "Description"),
                    field("criteria", "Evidence-based award criteria"),
                ),
            ),
            rx.fragment(),
        ),
        class_name="flex flex-col gap-4",
    )

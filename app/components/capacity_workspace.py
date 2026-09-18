import reflex as rx
from app.components.admin_shell import admin_page
from app.components.trainee_shell import trainee_page
from app.components.trainer_shell import trainer_page
from app.components.layout import page_shell
from app.components.capacity_actions import operations_panel
from app.states.capacity_operations_state import CapacityOperationsState as O
from app.states.competency_workspace_state import CompetencyWorkspaceState as G
from app.states.registry_workspace_state import RegistryWorkspaceState as R
from app.states.competency_report_state import CompetencyReportState
from app.states.certificate_verification_state import (
    CertificateVerificationState as V,
)


BUTTON = "cc-focus inline-flex items-center justify-center gap-2 rounded-lg border border-teal-700 bg-teal-700 px-3 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-40 disabled:cursor-not-allowed"


def note(text: str) -> rx.Component:
    return rx.el.p(
        text,
        class_name="rounded-lg border border-teal-200 bg-teal-50 px-4 py-3 text-sm leading-relaxed text-teal-900",
    )


def registry_table() -> rx.Component:
    return rx.el.div(
        rx.cond(
            R.loading,
            rx.el.div(
                "Loading current records…",
                role="status",
                class_name="animate-pulse p-8 text-slate-600 bg-slate-50",
            ),
            rx.cond(
                R.rows.length() > 0,
                rx.el.div(
                    rx.el.table(
                        rx.el.thead(
                            rx.el.tr(
                                rx.foreach(
                                    R.headings,
                                    lambda h: rx.el.th(
                                        rx.el.div(
                                            rx.icon(
                                                "list",
                                                class_name="h-3 w-3 shrink-0",
                                            ),
                                            h,
                                            class_name="flex items-center gap-2",
                                        ),
                                        class_name="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold text-slate-600",
                                    ),
                                )
                            ),
                            class_name="bg-slate-100",
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                R.rows,
                                lambda row: rx.el.tr(
                                    rx.foreach(
                                        row,
                                        lambda cell: rx.el.td(
                                            cell,
                                            class_name="max-w-md min-w-32 whitespace-pre-wrap break-words px-4 py-3 align-top text-sm text-slate-700",
                                        ),
                                    ),
                                    class_name="border-t border-slate-200 odd:bg-white even:bg-[#FBFAF7] hover:bg-teal-50",
                                ),
                            )
                        ),
                        class_name="table-auto w-full",
                    ),
                    class_name="w-full overflow-x-auto",
                ),
                rx.el.div(
                    rx.icon("database", class_name="h-7 w-7 text-teal-700"),
                    rx.el.h3(
                        "No matching records",
                        class_name="text-lg font-semibold text-slate-900",
                    ),
                    rx.el.p(
                        "Nothing matches this scope yet. Missing measurements remain unmeasured; use the available controls to create or review records.",
                        class_name="max-w-xl text-sm text-slate-600",
                    ),
                    class_name="flex flex-col items-start gap-3 bg-white p-8",
                ),
            ),
        ),
        class_name="w-full overflow-hidden rounded-xl border border-slate-200 bg-white",
    )


def registry_body() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.button(
                rx.icon("refresh-cw", class_name="h-4 w-4"),
                "Refresh",
                on_click=R.load,
                class_name=BUTTON,
            ),
            rx.cond(
                R.role == "admin",
                rx.el.button(
                    rx.icon("download", class_name="h-4 w-4"),
                    "Export CSV",
                    on_click=R.export_csv,
                    class_name=BUTTON,
                ),
            ),
            class_name="flex flex-wrap gap-2",
        ),
        rx.match(
            R.view,
            (
                "effectiveness",
                note(
                    "Observed Competency Improvement uses the latest verified, chronological pre/post pair for each trainee and competency, averaged within each trainee before averaging across the cohort. These are observational differences, not causal effects. Official pass rate uses the latest submitted result per trainee and assessment; practice is excluded."
                ),
            ),
            (
                "trainer-fit",
                note(
                    "Recalculate before assigning. Five-factor evaluations use coverage 40%, domain 25%, experience 15%, qualification 10% and observed effectiveness 10%. For compatibility, the stored composite combines coverage/domain/qualification at weight 75%; the expanded explanation preserves all five scores. Availability and capacity are gates. Older policy records retain their original arithmetic."
                ),
            ),
            (
                "teams",
                note(
                    "Saved team proposals show exactly which member covers each competency, including uncovered requirements. Proposal status is not proof of a current assignment or current capacity."
                ),
            ),
            (
                "practice",
                note(
                    "Practice only: start weak-competency questions, submit answers and review explanations. Practice never changes official results or verified competency and never reveals official answer keys."
                ),
            ),
            (
                "paths",
                note(
                    "Follow your ordered learning pathway and confirm completion after the underlying learning activity is complete. Server-side checks enforce ownership and earlier steps. Completion does not verify proficiency."
                ),
            ),
            (
                "notifications",
                note(
                    "Notifications are scoped to your role, direct recipient, course membership or organization. Mark one or all loaded notices read; changes persist only to your own recipient receipts."
                ),
            ),
            note(
                "Live registry records • 50 rows per page • Missing measurements remain explicitly unmeasured. Existing authoring and approval workflows remain available through workspace navigation."
            ),
        ),
        operations_panel(R.view),
        rx.cond(
            (R.view != "notifications")
            & (R.view != "paths")
            & (R.view != "trainer-fit"),
            registry_table(),
        ),
        rx.el.div(
            rx.el.button(
                "Previous",
                on_click=R.previous_page,
                disabled=R.offset == 0,
                class_name=BUTTON,
            ),
            rx.el.span(
                f"Page {R.offset // 50 + 1}",
                class_name="text-sm text-slate-600",
            ),
            rx.el.button(
                "Next",
                on_click=R.next_page,
                disabled=~R.has_more,
                class_name=BUTTON,
            ),
            class_name="flex items-center gap-3",
        ),
        rx.foreach(
            R.actions,
            lambda action: rx.el.a(
                action["title"],
                rx.icon("arrow-up-right", class_name="h-4 w-4"),
                href=action["path"],
                class_name="cc-focus flex w-fit items-center gap-2 rounded-lg border border-teal-200 bg-white px-4 py-2 text-sm font-semibold text-teal-800",
            ),
        ),
        class_name="flex w-full min-w-0 flex-col gap-5",
    )


def registry_page(
    role: str, active: str, title: str, description: str
) -> rx.Component:
    return rx.match(
        role,
        (
            "admin",
            admin_page(
                active, title, description, R.error, "", registry_body()
            ),
        ),
        (
            "trainer",
            trainer_page(
                active, title, description, R.error, "", registry_body()
            ),
        ),
        trainee_page(active, title, description, R.error, "", registry_body()),
    )


def filter_field(label: str, name: str, value: rx.Var) -> rx.Component:
    return rx.el.label(
        rx.el.span(label, class_name="text-xs font-semibold text-slate-600"),
        rx.el.input(
            name=name,
            default_value=value,
            key=value,
            placeholder=f"Filter {label.lower()}",
            class_name="cc-focus mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900",
        ),
        class_name="min-w-0 flex-1",
    )


def gap_card(row: rx.Var) -> rx.Component:
    return rx.el.button(
        rx.el.div(
            rx.el.span(
                row["subject"],
                class_name="text-xs font-semibold uppercase tracking-wider text-teal-800",
            ),
            rx.el.span(
                row["severity"],
                class_name=rx.match(
                    row["severity"],
                    (
                        "High",
                        "w-fit rounded-full bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-900",
                    ),
                    (
                        "Unmeasured",
                        "w-fit rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600",
                    ),
                    "w-fit rounded-full bg-teal-50 px-2 py-1 text-xs font-semibold text-teal-800",
                ),
            ),
            class_name="flex flex-wrap items-center justify-between gap-2",
        ),
        rx.el.h3(
            row["name"],
            class_name="mt-2 text-base font-semibold text-[#0A1B33]",
        ),
        rx.cond(
            G.is_admin,
            rx.el.p(
                f"{row['organization']} → {row['department']} → {row['role']}",
                class_name="mt-1 text-xs text-slate-600",
            ),
        ),
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    "Verified current / average",
                    class_name="text-xs text-slate-500",
                ),
                rx.el.p(
                    row["current"],
                    class_name="text-xl font-semibold text-teal-800",
                ),
            ),
            rx.el.div(
                rx.el.p(
                    "Target (maximum)", class_name="text-xs text-slate-500"
                ),
                rx.el.p(
                    rx.cond(
                        row["target"] > 0, row["target"].to_string(), "Not set"
                    ),
                    class_name="text-xl font-semibold text-slate-900",
                ),
            ),
            rx.el.div(
                rx.el.p(
                    "Measured gap / average",
                    class_name="text-xs text-slate-500",
                ),
                rx.el.p(
                    row["gap"],
                    class_name="text-xl font-semibold text-amber-800",
                ),
            ),
            class_name="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3",
        ),
        rx.el.div(
            rx.foreach(
                [1, 2, 3, 4, 5],
                lambda level: rx.el.div(
                    rx.el.span(level, class_name="text-xs font-bold"),
                    class_name=rx.cond(
                        level <= row["target"],
                        "flex h-7 items-center justify-center rounded-sm border border-teal-300 bg-teal-50 text-teal-900",
                        "flex h-7 items-center justify-center rounded-sm border border-slate-200 bg-slate-50 text-slate-500",
                    ),
                ),
            ),
            class_name="mt-4 grid grid-cols-5 gap-1",
            aria_label="Target proficiency ladder; not a mastery indicator",
        ),
        rx.el.p(
            f"{row['verified']} measured · {row['unmeasured']} unmeasured · {row['affected']} below target",
            class_name="mt-3 text-xs text-slate-600",
        ),
        rx.el.span(
            "Inspect evidence and learning options →",
            class_name="mt-3 block text-sm font-semibold text-teal-800",
        ),
        on_click=lambda: G.inspect_gap(
            row["competency_id"],
            row["organization_id"],
            row["department_id"],
            row["role_id"],
        ),
        class_name="cc-focus w-full rounded-xl border border-slate-200 bg-white p-5 text-left transition-colors hover:border-teal-500",
    )


def gap_detail() -> rx.Component:
    return rx.cond(
        G.selected_name != "",
        rx.el.section(
            rx.el.h2(
                G.selected_name,
                class_name="text-xl font-semibold text-slate-900",
            ),
            rx.el.p(
                "Evidence trail • latest 50 records. Unmeasured trainees need assessment, not an assumed level zero.",
                class_name="text-sm text-slate-600",
            ),
            rx.el.div(
                rx.foreach(
                    G.learners,
                    lambda person: rx.el.div(
                        rx.el.h3(
                            person["name"],
                            class_name="font-semibold text-slate-900",
                        ),
                        rx.el.p(
                            f"Current {person['current']} · target {person['target']} · gap {person['gap']}",
                            class_name="text-sm text-teal-800",
                        ),
                        rx.el.p(
                            f"Last verified: {person['verified']}",
                            class_name="text-xs text-slate-600",
                        ),
                        class_name="rounded-lg border border-slate-200 bg-white p-3",
                    ),
                ),
                class_name="grid gap-3 md:grid-cols-2",
            ),
            rx.el.h3(
                "Verification timeline",
                class_name="text-lg font-semibold text-slate-900",
            ),
            rx.cond(
                G.evidence.length() > 0,
                rx.el.ol(
                    rx.foreach(
                        G.evidence,
                        lambda e: rx.el.li(
                            rx.el.div(
                                rx.icon(
                                    "git-commit-horizontal",
                                    class_name="h-5 w-5 text-teal-700",
                                ),
                                rx.el.h4(
                                    f"{e['type']} · {e['status']}",
                                    class_name="text-sm font-semibold text-slate-900",
                                ),
                                class_name="flex items-center gap-2",
                            ),
                            rx.el.p(
                                f"{e['name']} · level: {e['level']} · observed {e['observed']}",
                                class_name="text-xs text-slate-600",
                            ),
                            rx.el.p(
                                f"Verified: {e['verified']} · source: {e['reference']}",
                                class_name="text-xs text-slate-600",
                            ),
                            rx.el.p(
                                e["notes"], class_name="text-sm text-slate-700"
                            ),
                            class_name="ml-2 flex flex-col gap-1 border-l-2 border-teal-200 py-3 pl-4",
                        ),
                    ),
                    class_name="flex flex-col",
                ),
                note(
                    "No evidence is recorded for this competency in the selected scope. Course attendance or completion cannot substitute for a verified measurement."
                ),
            ),
            rx.cond(
                ~G.is_admin & ~G.is_trainer,
                rx.el.div(
                    rx.el.button(
                        "Generate / start owned gap pathway",
                        on_click=lambda: O.generate_learning(
                            G.selected_competency
                        ),
                        disabled=O.busy,
                        class_name=BUTTON,
                    ),
                    rx.el.p(
                        O.success,
                        role="status",
                        class_name="text-sm text-teal-800",
                    ),
                    rx.el.p(
                        O.error, role="alert", class_name="text-sm text-red-700"
                    ),
                    class_name="flex flex-col items-start gap-3",
                ),
            ),
            rx.el.h3(
                "Mapped learning opportunities",
                class_name="text-lg font-semibold text-slate-900",
            ),
            rx.cond(
                G.recommendations.length() > 0,
                rx.el.div(
                    rx.foreach(
                        G.recommendations,
                        lambda c: rx.el.div(
                            rx.el.h4(
                                f"{c['code']} · {c['title']}",
                                class_name="font-semibold text-slate-900",
                            ),
                            rx.el.p(
                                c["detail"], class_name="text-sm text-slate-600"
                            ),
                            class_name="rounded-lg border border-teal-200 bg-white p-3",
                        ),
                    ),
                    class_name="grid gap-3 md:grid-cols-2",
                ),
                note(
                    "No published course is mapped to this competency outcome yet. A curriculum owner must define an outcome mapping before a recommendation can be made."
                ),
            ),
            rx.cond(
                G.is_admin,
                rx.el.div(
                    rx.el.a(
                        "Find trainers",
                        href="/admin/trainer-fit",
                        class_name=BUTTON,
                    ),
                    rx.el.a(
                        "Create / assign training",
                        href="/admin/courses",
                        class_name=BUTTON,
                    ),
                    class_name="flex flex-wrap gap-3",
                ),
                rx.cond(
                    G.is_trainer,
                    rx.el.a(
                        "Create Training",
                        href="/trainer/create-training",
                        class_name=BUTTON,
                    ),
                    rx.el.div(
                        rx.el.a(
                            "Training catalogue",
                            href="/trainee/courses",
                            class_name=BUTTON,
                        ),
                        rx.el.a(
                            "Official assessments",
                            href="/trainee/assessments",
                            class_name=BUTTON,
                        ),
                        rx.el.a(
                            "Practice record",
                            href="/trainee/practice",
                            class_name=BUTTON,
                        ),
                        rx.el.a(
                            "Saved learning paths",
                            href="/trainee/paths",
                            class_name=BUTTON,
                        ),
                        class_name="flex flex-wrap gap-3",
                    ),
                ),
            ),
            class_name="flex flex-col gap-4 rounded-xl border border-teal-300 bg-[#FBFAF7] p-5",
        ),
    )


def competency_body() -> rx.Component:
    return rx.el.div(
        note(
            "Proficiency: 1 Awareness · 2 Basic (guided) · 3 Working (independent) · 4 Advanced · 5 Expert. Demonstrated levels require a verified snapshot tied to matching verified evidence. Practice and course completion alone never establish mastery. Numeric gaps exclude unmeasured baselines; affected trainees and unmeasured trainees are shown separately."
        ),
        rx.el.form(
            filter_field("Organization", "organization", G.organization),
            filter_field("Department", "department", G.department),
            filter_field("Role", "role", G.role_filter),
            filter_field("Subject", "subject", G.subject),
            filter_field("Competency", "search", G.search),
            rx.el.button("Apply filters", type="submit", class_name=BUTTON),
            on_submit=G.filter_rows,
            class_name="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-[#FBFAF7] p-4",
        ),
        rx.cond(
            G.loading,
            rx.el.div(
                "Loading verified evidence…",
                role="status",
                class_name="animate-pulse rounded-xl bg-slate-100 p-8 text-slate-600",
            ),
            rx.cond(
                G.rows.length() > 0,
                rx.el.div(
                    rx.foreach(G.rows, gap_card),
                    class_name="grid w-full gap-4 xl:grid-cols-2",
                ),
                note(
                    "No normalized competency records match these filters. Existing legacy skills remain preserved, but are not treated as verified competencies. No evidence or proficiency has been fabricated."
                ),
            ),
        ),
        rx.el.div(
            rx.el.button(
                "Previous",
                on_click=G.previous_page,
                disabled=G.offset == 0,
                class_name=BUTTON,
            ),
            rx.el.span(
                f"Page {G.offset // 50 + 1}",
                class_name="text-sm text-slate-600",
            ),
            rx.el.button(
                "Next",
                on_click=G.next_page,
                disabled=~G.has_more,
                class_name=BUTTON,
            ),
            class_name="flex items-center gap-3",
        ),
        gap_detail(),
        class_name="flex w-full min-w-0 flex-col gap-5",
    )


def competency_page(role: str, active: str, title: str) -> rx.Component:
    return rx.match(
        role,
        (
            "admin",
            admin_page(
                active,
                title,
                "Organization → Department → Role → Subject → Competency. Verified evidence, measured gaps and training demand.",
                G.error,
                "",
                competency_body(),
            ),
        ),
        (
            "trainer",
            trainer_page(
                active,
                title,
                "Verified expertise coverage and evidence for teaching. Pending legacy claims are not teachable verified coverage; course-specific eligibility also requires minimums, dates and capacity.",
                G.error,
                "",
                competency_body(),
            ),
        ),
        trainee_page(
            active,
            title,
            "Your current level, target, verification history and mapped learning opportunities.",
            G.error,
            "",
            competency_body(),
        ),
    )


def reports_page() -> rx.Component:
    return admin_page(
        "Reports",
        "Operational reports",
        "Download database-derived CSV reports. Exports are reauthorized and refreshed from the database, not copied from browser state.",
        rx.cond(R.error != "", R.error, CompetencyReportState.error),
        "",
        rx.el.div(
            rx.el.button(
                "Competency gaps CSV",
                on_click=CompetencyReportState.export_gaps,
                class_name=BUTTON,
            ),
            rx.foreach(
                [
                    ("participation", "Participation"),
                    ("trainer-fit", "Trainer Fit"),
                    ("effectiveness", "Effectiveness"),
                    ("certifications", "Certifications"),
                ],
                lambda item: rx.el.button(
                    item[1],
                    on_click=lambda: R.open_view(item[0]),
                    class_name=BUTTON,
                ),
            ),
            class_name="flex flex-wrap gap-2",
        ),
        rx.el.p(
            "Choose a report, review its live rows, then export CSV. Exports stop at 10,000 rows rather than silently truncating. Blank numeric fields mean unmeasured, not zero.",
            class_name="text-sm text-slate-600",
        ),
        registry_body(),
    )


def verification_page() -> rx.Component:
    return page_shell(
        rx.el.main(
            rx.el.div(
                rx.icon("badge-check", class_name="h-8 w-8 text-teal-700"),
                rx.el.h1(
                    "Certificate verification",
                    class_name="text-3xl font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    "Validate a CAPACITY CONNECT certificate against the current registry.",
                    class_name="text-sm text-slate-600",
                ),
                class_name="flex flex-col gap-3",
            ),
            rx.cond(V.error != "", note(V.error)),
            rx.cond(
                V.loading,
                rx.el.div(
                    "Checking certificate…",
                    role="status",
                    class_name="animate-pulse p-8 text-slate-600",
                ),
                rx.cond(
                    V.found,
                    rx.el.article(
                        rx.el.div(
                            rx.el.span(
                                rx.cond(V.revoked, "REVOKED", "VALID"),
                                class_name=rx.cond(
                                    V.revoked,
                                    "w-fit rounded-full bg-red-100 px-3 py-1 font-semibold text-red-800",
                                    "w-fit rounded-full bg-green-100 px-3 py-1 font-semibold text-green-800",
                                ),
                            ),
                            rx.el.h2(
                                V.number,
                                class_name="break-all font-mono text-xl font-semibold text-slate-900",
                            ),
                            class_name="flex flex-wrap items-center gap-4",
                        ),
                        rx.el.div(
                            rx.el.div(
                                rx.el.h3(
                                    V.trainee,
                                    class_name="text-2xl font-semibold text-slate-900",
                                ),
                                rx.el.p(
                                    V.training,
                                    class_name="mt-2 text-lg text-teal-800",
                                ),
                                rx.el.p(
                                    f"Issued {V.issued}",
                                    class_name="mt-3 text-sm text-slate-600",
                                ),
                                rx.el.p(
                                    f"Issuer: {V.issuer}",
                                    class_name="text-sm text-slate-600",
                                ),
                                class_name="flex-1",
                            ),
                            rx.cond(
                                V.qr != "",
                                rx.el.div(
                                    rx.el.img(
                                        src=V.qr,
                                        alt="QR code linking to this certificate verification page",
                                        class_name="h-40 w-40 bg-white",
                                    ),
                                    rx.el.a(
                                        "Open verification link",
                                        href=V.verification_url,
                                        class_name="cc-focus text-sm font-semibold text-teal-800 underline",
                                    ),
                                    class_name="flex flex-col items-center gap-2",
                                ),
                            ),
                            class_name="flex flex-col gap-5 sm:flex-row",
                        ),
                        rx.el.h3(
                            "Linked competency evidence",
                            class_name="text-lg font-semibold text-slate-900",
                        ),
                        rx.cond(
                            V.competencies.length() > 0,
                            rx.el.div(
                                rx.foreach(
                                    V.competencies,
                                    lambda c: rx.el.div(
                                        rx.el.h4(
                                            c["name"],
                                            class_name="font-semibold text-slate-900",
                                        ),
                                        rx.el.p(
                                            f"Certified level {c['level']} · evidence {c['status']}",
                                            class_name="text-sm text-teal-800",
                                        ),
                                        rx.el.p(
                                            f"Verified: {c['verified']}",
                                            class_name="text-xs text-slate-600",
                                        ),
                                        class_name="rounded-lg border border-slate-200 p-3",
                                    ),
                                ),
                                class_name="grid gap-3 sm:grid-cols-2",
                            ),
                            note(
                                "No normalized competency evidence is linked to this certificate. A valid course certificate alone is not a claim of competency mastery."
                            ),
                        ),
                        class_name="flex flex-col gap-6 rounded-xl border border-slate-200 bg-white p-6",
                    ),
                    note(
                        "No certificate matches this identifier. Check the complete certificate number with the issuer."
                    ),
                ),
            ),
            class_name="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-12",
        )
    )

"""Admin dashboard: organization-wide totals and the approval queue."""

from __future__ import annotations

import reflex as rx

from app.components.admin_shell import (
    admin_page,
    cell,
    data_table,
    row_class,
    table_head,
    th,
)
from app.components.trainee_ui import (
    chip,
    empty_block,
    loading_rows,
    metric_tile,
    panel,
    progress_bar,
)
from app.components.workflow_map import workflow_map
from app.states.admin_state import AdminState

QUICK_LINKS: list[tuple[str, str, str, str]] = [
    (
        "Users",
        "/admin/users",
        "users",
        "The full account directory with roles and audit history.",
    ),
    (
        "Approvals",
        "/admin/approvals",
        "shield-check",
        "Decide pending trainer and administrator access requests.",
    ),
    (
        "Role management",
        "/admin/roles",
        "user-cog",
        "Promote, demote and control account availability.",
    ),
    (
        "Courses",
        "/admin/courses",
        "book-open",
        "Course delivery, cohorts and trainer coverage.",
    ),
    (
        "Trainers",
        "/admin/trainers",
        "user-pen",
        "Expertise, availability and teaching load per trainer.",
    ),
    (
        "Assessments",
        "/admin/assessments",
        "list-checks",
        "Assessment outcomes and live enrolment participation.",
    ),
    (
        "Certifications",
        "/admin/certifications",
        "award",
        "Issued certificates, grades and verification codes.",
    ),
    (
        "Analytics",
        "/admin/analytics",
        "chart-line",
        "Participation, completion and assessment outcome series.",
    ),
    (
        "Announcements",
        "/admin/announcements",
        "megaphone",
        "Publish notices to audiences and course cohorts.",
    ),
    (
        "Competency mapping",
        "/admin/competency",
        "grid-3x3",
        "Rank trainers against each course's weighted skills.",
    ),
]


def _quick_link(item: tuple[str, str, str, str]) -> rx.Component:
    return rx.el.a(
        rx.el.div(
            rx.icon(item[2], class_name="h-4 w-4 text-sky-700"),
            class_name="flex size-9 items-center justify-center rounded-[0.875rem] border border-sky-200 bg-sky-50",
        ),
        rx.el.div(
            rx.el.p(
                item[0],
                class_name="text-sm font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                item[3],
                class_name="mt-0.5 text-xs font-medium leading-relaxed text-slate-500",
            ),
            class_name="min-w-0",
        ),
        rx.icon("arrow-right", class_name="ml-auto h-4 w-4 text-slate-400"),
        href=item[1],
        class_name="cc-card cc-hover cc-focus-sky flex w-full min-w-0 items-start gap-3 p-4 outline-hidden",
    )


def _pending_row(row) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.p(
                row["name"],
                class_name="text-xs font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                row["email"],
                class_name="text-[0.7rem] font-medium text-slate-500",
            ),
        ),
        cell(chip(row["requested_role"], "amber")),
        cell(chip(row["role"], "navy")),
        cell(
            rx.el.p(
                row["audit"],
                class_name="text-[0.7rem] font-medium text-slate-600",
            )
        ),
        cell(
            rx.el.a(
                "Review",
                rx.icon("arrow-right", class_name="h-3.5 w-3.5"),
                href="/admin/users",
                class_name="flex w-fit items-center gap-1 rounded-lg bg-[#0A1B33] px-2.5 py-1.5 text-[0.7rem] font-semibold text-white hover:bg-[#12304f]",
            )
        ),
        class_name=row_class(),
    )


def _bar_stat(label: str, value: rx.Var, tone: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                label,
                class_name="text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
            ),
            rx.el.span(
                f"{value:.1f}%",
                class_name="text-sm font-semibold text-[#0A1B33]",
            ),
            class_name="flex items-center justify-between gap-2",
        ),
        rx.el.div(progress_bar(value, tone), class_name="mt-2"),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def admin_dashboard_page() -> rx.Component:
    return admin_page(
        "Dashboard",
        "Institution-wide situation board",
        "Live counts across accounts, courses, delivery, assessment outcomes and certification, read straight from the registry.",
        AdminState.error_message,
        AdminState.success_message,
        rx.el.div(
            metric_tile(
                "Accounts",
                AdminState.totals["users"].to_string(),
                "users",
                "All registered users",
            ),
            metric_tile(
                "Pending approvals",
                AdminState.totals["pending"].to_string(),
                "shield-alert",
                "Awaiting an admin decision",
            ),
            metric_tile(
                "Published courses",
                AdminState.totals["published_courses"].to_string(),
                "book-open",
                f"{AdminState.totals['courses']} in the catalogue",
            ),
            metric_tile(
                "Enrolments",
                AdminState.totals["enrollments"].to_string(),
                "clipboard-list",
                f"{AdminState.totals['completions']} completed",
            ),
            metric_tile(
                "Assessments",
                AdminState.totals["assessments"].to_string(),
                "list-checks",
                f"{AdminState.totals['results']} graded results",
            ),
            metric_tile(
                "Certificates",
                AdminState.totals["certificates"].to_string(),
                "award",
                "Issued and not revoked",
            ),
            metric_tile(
                "Trainer assignments",
                AdminState.totals["assignments"].to_string(),
                "user-pen",
                f"{AdminState.totals['trainers']} trainers on record",
            ),
            metric_tile(
                "Resources",
                AdminState.totals["resources"].to_string(),
                "library",
                f"{AdminState.totals['announcements']} notices published",
            ),
            class_name="grid w-full grid-cols-2 gap-4 md:grid-cols-4",
        ),
        panel(
            "Delivery health",
            "Completion and assessment pass rates computed from enrolment and result records.",
            rx.el.div(
                _bar_stat(
                    "Completion rate", AdminState.completion_rate, "teal"
                ),
                _bar_stat("Assessment pass rate", AdminState.pass_rate, "navy"),
                _bar_stat(
                    "Draft course share",
                    AdminState.totals["draft_courses"]
                    * 100.0
                    / rx.cond(
                        AdminState.totals["courses"] > 0,
                        AdminState.totals["courses"],
                        1,
                    ),
                    "amber",
                ),
                class_name="grid w-full grid-cols-1 gap-3 md:grid-cols-3",
            ),
            rx.el.div(
                chip(
                    f"{AdminState.totals['trainees']} trainees",
                    "teal",
                ),
                chip(
                    f"{AdminState.totals['trainers']} trainers",
                    "navy",
                ),
                chip(f"{AdminState.totals['admins']} admins", "green"),
                chip(
                    f"{AdminState.totals['suspended']} suspended",
                    "red",
                ),
                chip(
                    f"{AdminState.totals['inactive']} deactivated",
                    "amber",
                ),
                class_name="flex w-full flex-wrap items-center gap-2",
            ),
            icon="activity",
        ),
        panel(
            "Approval queue",
            "Access requests awaiting a decision, with the requested and current role side by side.",
            rx.cond(
                AdminState.is_loading,
                loading_rows(3),
                rx.cond(
                    AdminState.pending_count > 0,
                    data_table(
                        table_head(
                            th("Account", "user"),
                            th("Requested role", "shield"),
                            th("Current role", "id-card"),
                            th("Audit status", "history"),
                            th("Action", "check"),
                        ),
                        rx.el.tbody(
                            rx.foreach(AdminState.pending_users, _pending_row)
                        ),
                    ),
                    empty_block(
                        "No pending requests",
                        "Every access request has been decided. New registrations will appear here.",
                        "shield-check",
                    ),
                ),
            ),
            icon="shield-check",
        ),
        panel(
            "Fragmented process → connected workflow",
            "Each operational problem this registry was built for, mapped to the feature that now carries it, with live figures from the registry.",
            workflow_map(
                rx.el.div(
                    chip(
                        f"{AdminState.totals['users']} accounts",
                        "navy",
                    ),
                    chip(
                        f"{AdminState.totals['courses']} courses ({AdminState.totals['published_courses']} published)",
                        "teal",
                    ),
                    chip(
                        f"{AdminState.totals['resources']} resources",
                        "navy",
                    ),
                    chip(
                        f"{AdminState.totals['enrollments']} enrolments · {AdminState.totals['completions']} completed",
                        "teal",
                    ),
                    chip(
                        f"{AdminState.totals['results']} graded results",
                        "navy",
                    ),
                    chip(
                        f"{AdminState.totals['certificates']} certificates",
                        "green",
                    ),
                    chip(
                        f"{AdminState.totals['assignments']} trainer assignments",
                        "amber",
                    ),
                    chip(
                        f"{AdminState.totals['announcements']} announcements",
                        "teal",
                    ),
                    class_name="flex w-full flex-wrap items-center gap-2",
                )
            ),
            icon="workflow",
        ),
        panel(
            "Control centre sections",
            "Every oversight surface in the administrator workspace.",
            rx.el.div(
                rx.foreach(QUICK_LINKS, _quick_link),
                class_name="grid w-full grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3",
            ),
            icon="layout-dashboard",
        ),
    )

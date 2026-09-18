"""Users & approvals: searchable directory, decisions, roles and account state."""

from __future__ import annotations

import reflex as rx

from app.components.admin_shell import (
    admin_page,
    cell,
    data_table,
    filter_input,
    filter_select,
    row_class,
    status_pill,
    table_head,
    th,
)
from app.components.trainee_ui import (
    chip,
    empty_block,
    ghost_button,
    loading_rows,
    metric_tile,
    panel,
    select_field,
    teal_button,
    textarea_field,
)
from app.states.admin_role_ops_state import AdminRoleOpsState
from app.states.admin_state import AdminState

# (role, risk, headline, can view, can create, can approve, data boundary,
#  approval requirement, icon)
PERMISSION_SCOPES: list[tuple[str, str, str, str, str, str, str, str, str]] = [
    (
        "Trainee",
        "Low risk",
        "Learns, is assessed and collects evidence.",
        "Published courses, own enrolments, own results, own certificates and announcements addressed to trainees.",
        "Enrolments, assessment attempts, assignment submissions, course feedback, own profile, skills and qualifications.",
        "Nothing. A trainee approves no record.",
        "Scoped to their own account. No other trainee's progress, marks or profile is readable.",
        "Self-registration is auto-approved so nomination is never blocked.",
        "graduation-cap",
    ),
    (
        "Trainer",
        "Elevated risk",
        "Delivers assigned courses and grades the cohort.",
        "Assigned courses, their cohort's progress, submissions, attempts and results, plus performance segments.",
        "Learning resources, MCQ assessments with deadlines and time limits, assignments, grades and feedback replies.",
        "Grades and submission outcomes for their own cohorts only.",
        "Limited to courses where a CourseTrainerAssignment exists. No registry-wide user or certificate access.",
        "Requires administrator approval before the trainer workspace unlocks.",
        "user-pen",
    ),
    (
        "Administrator",
        "High risk",
        "Owns the registry, access decisions and oversight.",
        "Every account, course, resource, assessment, assignment, certificate request and analytics series.",
        "Announcements, course lifecycle changes, trainer staffing, role changes and certification decisions.",
        "Access requests, role transitions, certificate issuance and course publication.",
        "No boundary — full registry read and write. Actions are written to the approval audit trail.",
        "Requires an existing administrator's approval; the last approved administrator cannot be demoted.",
        "shield-check",
    ),
]

ROLE_OPERATIONS_COPY: list[tuple[str, str]] = [
    (
        "Access was tracked in scattered spreadsheets",
        "Roles, approval state, activity and workload live on one account record, so who can see what is never guesswork.",
    ),
    (
        "Privilege changes had no paper trail",
        "Every escalation or demotion writes an ApprovalRequest with the deciding administrator, timestamp and written reason.",
    ),
    (
        "Demotions silently broke live delivery",
        "Each row states the impact first: assigned courses, cohort size, enrolments and completions that a change would affect.",
    ),
]


def _scope_card(item: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon(item[8], class_name="h-4 w-4 text-sky-700"),
                class_name="flex size-9 shrink-0 items-center justify-center rounded-[0.875rem] border border-sky-200 bg-sky-50",
            ),
            rx.el.div(
                rx.el.p(
                    item[0],
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    item[2],
                    class_name="text-[0.7rem] font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.span(
                item[1],
                class_name="ml-auto w-fit shrink-0 rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-slate-700",
            ),
            class_name="flex w-full items-start gap-3",
        ),
        rx.el.div(
            _scope_line("eye", "Can view", item[3]),
            _scope_line("plus", "Can create", item[4]),
            _scope_line("check-check", "Can approve", item[5]),
            _scope_line("lock", "Data boundary", item[6]),
            _scope_line("shield", "Approval requirement", item[7]),
            class_name="mt-3 flex w-full flex-col gap-2",
        ),
        class_name="cc-card cc-hover w-full min-w-0 p-4",
    )


def _scope_line(icon: str, label: str, value: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, class_name="h-3.5 w-3.5 text-teal-700"),
            rx.el.span(
                label,
                class_name="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-slate-500",
            ),
            class_name="flex items-center gap-1.5",
        ),
        rx.el.p(
            value,
            class_name="mt-1 text-[0.72rem] font-medium leading-relaxed text-slate-700",
        ),
        class_name="cc-inset w-full min-w-0 p-2.5",
    )


def _role_copy(item: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("unlink", class_name="h-3.5 w-3.5 text-amber-600"),
            rx.el.p(
                item[0],
                class_name="text-xs font-semibold text-[#0A1B33]",
            ),
            class_name="flex items-start gap-2",
        ),
        rx.el.p(
            item[1],
            class_name="mt-1.5 pl-5 text-xs font-medium leading-relaxed text-slate-600",
        ),
        class_name="cc-inset w-full min-w-0 p-3",
    )


def _role_counts() -> rx.Component:
    return rx.el.div(
        metric_tile(
            "Trainees",
            AdminRoleOpsState.counts["trainees"].to_string(),
            "graduation-cap",
            f"{AdminRoleOpsState.counts['trainees_without_enrollment']} without an active enrolment",
        ),
        metric_tile(
            "Trainers",
            AdminRoleOpsState.counts["trainers"].to_string(),
            "user-pen",
            f"{AdminRoleOpsState.counts['trainers_without_course']} with no assigned course",
        ),
        metric_tile(
            "Administrators",
            AdminRoleOpsState.counts["admins"].to_string(),
            "shield-check",
            "Full registry oversight",
        ),
        metric_tile(
            "Pending access",
            AdminRoleOpsState.counts["pending"].to_string(),
            "shield-alert",
            "Awaiting a decision",
        ),
        metric_tile(
            "Suspended",
            AdminRoleOpsState.counts["suspended"].to_string(),
            "ban",
            f"{AdminRoleOpsState.counts['inactive']} deactivated accounts",
        ),
        metric_tile(
            "Role decisions",
            AdminRoleOpsState.counts["role_decisions"].to_string(),
            "history",
            "Recorded in the audit trail",
        ),
        class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6",
    )


def _context_card(row: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    row["name"],
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    row["email"],
                    class_name="text-[0.7rem] font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                chip(row["role"], "teal"),
                status_pill(row["approval_status"]),
                rx.cond(row["is_self"], chip("you", "green"), rx.fragment()),
                class_name="flex flex-wrap items-center gap-1.5",
            ),
            class_name="flex w-full flex-wrap items-start justify-between gap-3",
        ),
        rx.el.p(
            row["context"],
            class_name="mt-2 text-xs font-medium text-slate-700",
        ),
        rx.el.div(
            rx.icon(
                "triangle-alert",
                class_name="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600",
            ),
            rx.el.p(
                row["impact"],
                class_name="text-[0.7rem] font-medium leading-relaxed text-amber-900",
            ),
            class_name="mt-2 flex w-full items-start gap-2 rounded-lg border border-amber-200 bg-amber-50/60 px-2.5 py-2",
        ),
        rx.el.p(
            row["guardrail"],
            class_name="mt-2 text-[0.65rem] font-medium text-slate-500",
        ),
        rx.el.form(
            select_field(
                "New role",
                "role",
                rx.foreach(
                    AdminRoleOpsState.role_choices,
                    lambda option: rx.el.option(option, value=option),
                ),
                default_value=row["role"],
            ),
            textarea_field(
                "Reason (required, 10+ characters)",
                "reason",
                placeholder="Why this escalation or demotion is authorised.",
                rows="2",
            ),
            teal_button(
                "Apply role change",
                type="submit",
                disabled=row["is_self"],
            ),
            on_submit=lambda form_data: AdminRoleOpsState.apply_role(
                row["id"], form_data
            ),
            reset_on_submit=True,
            class_name="mt-3 flex w-full flex-col gap-3 border-t border-slate-200 pt-3",
        ),
        class_name="cc-card w-full min-w-0 p-4",
    )


def _audit_entry(row: rx.Var) -> rx.Component:
    return rx.el.li(
        rx.el.div(
            rx.cond(
                row["pending"],
                rx.icon("clock", class_name="h-3.5 w-3.5 text-amber-600"),
                rx.icon("circle-check", class_name="h-3.5 w-3.5 text-teal-700"),
            ),
            class_name="absolute -left-[0.6rem] top-1 flex size-5 items-center justify-center rounded-full border border-slate-200 bg-white",
        ),
        rx.el.div(
            rx.el.p(
                row["name"],
                class_name="text-xs font-semibold text-[#0A1B33]",
            ),
            rx.el.div(
                chip(row["requested_role"], "navy"),
                status_pill(row["status"]),
                class_name="flex flex-wrap items-center gap-1.5",
            ),
            class_name="flex flex-wrap items-center justify-between gap-2",
        ),
        rx.el.p(
            row["note"],
            class_name="mt-1 text-[0.7rem] font-medium leading-relaxed text-slate-600",
        ),
        rx.el.p(
            f"{row['decided']} · {row['decided_by']}",
            class_name="mt-1 text-[0.65rem] font-medium text-slate-400",
        ),
        class_name="relative w-full min-w-0 border-l border-slate-200 pb-4 pl-4",
    )


def _decision_card(row) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    row["name"],
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    row["email"],
                    class_name="text-xs font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                chip(f"requested · {row['requested_role']}", "amber"),
                chip(f"current · {row['role']}", "navy"),
                class_name="flex flex-wrap items-center gap-1.5",
            ),
            class_name="flex flex-wrap items-start justify-between gap-3",
        ),
        rx.el.p(
            row["audit"],
            class_name="mt-2 text-[0.7rem] font-medium text-slate-500",
        ),
        rx.cond(
            row["note"] != "",
            rx.el.p(
                row["note"],
                class_name="mt-1 rounded-lg border border-slate-200 bg-[#FBFAF7] px-3 py-2 text-xs font-medium text-slate-600",
            ),
            rx.fragment(),
        ),
        rx.el.form(
            select_field(
                "Decision",
                "decision",
                rx.fragment(
                    rx.el.option("Approve access", value="approve"),
                    rx.el.option("Reject request", value="reject"),
                ),
                default_value="approve",
            ),
            textarea_field(
                "Decision note",
                "note",
                placeholder="Recorded in the approval audit trail (required for rejection).",
                rows="2",
            ),
            teal_button("Record decision", type="submit"),
            on_submit=lambda form_data: AdminState.record_decision(
                row["id"], form_data
            ),
            reset_on_submit=True,
            class_name="mt-3 flex w-full flex-col gap-3",
        ),
        class_name="w-full min-w-0 rounded-xl border border-amber-200 bg-amber-50/40 p-4",
    )


def _user_row(row) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.div(
                rx.image(
                    src=f"https://api.dicebear.com/9.x/initials/svg?seed={row['email']}",
                    class_name="size-8 shrink-0 rounded-full bg-slate-100",
                ),
                rx.el.div(
                    rx.el.p(
                        row["name"],
                        class_name="truncate text-xs font-semibold text-[#0A1B33]",
                    ),
                    rx.el.p(
                        row["email"],
                        class_name="truncate text-[0.7rem] font-medium text-slate-500",
                    ),
                    rx.el.p(
                        row["phone"],
                        class_name="truncate text-[0.7rem] font-medium text-slate-400",
                    ),
                    class_name="min-w-0",
                ),
                class_name="flex min-w-0 items-center gap-2",
            )
        ),
        cell(
            rx.el.div(
                chip(row["role"], "teal"),
                rx.cond(
                    row["requested_role"] != row["role"],
                    chip(f"req · {row['requested_role']}", "amber"),
                    rx.fragment(),
                ),
                rx.cond(
                    row["is_self"],
                    chip("you", "green"),
                    rx.fragment(),
                ),
                class_name="flex flex-col items-start gap-1",
            )
        ),
        cell(
            rx.el.div(
                status_pill(row["approval_status"]),
                rx.cond(
                    row["is_active"],
                    chip("active", "green"),
                    chip("deactivated", "red"),
                ),
                class_name="flex flex-col items-start gap-1",
            )
        ),
        cell(
            rx.el.p(
                row["audit"],
                class_name="max-w-[16rem] text-[0.7rem] font-medium text-slate-600",
            ),
            rx.el.p(
                f"Joined {row['joined']}",
                class_name="text-[0.65rem] font-medium text-slate-400",
            ),
        ),
        cell(
            rx.el.p(
                row["last_login"],
                class_name="text-[0.7rem] font-medium text-slate-600",
            )
        ),
        cell(
            rx.el.form(
                select_field(
                    "Role",
                    "role",
                    rx.foreach(
                        AdminState.role_choices,
                        lambda option: rx.el.option(option, value=option),
                    ),
                    default_value=row["role"],
                ),
                rx.el.input(
                    name="role_note",
                    placeholder="Reason (optional)",
                    class_name="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs font-medium text-slate-900 outline-hidden focus:border-teal-500",
                ),
                rx.el.button(
                    "Apply role",
                    type="submit",
                    class_name="w-full rounded-lg bg-[#0A1B33] px-2.5 py-1.5 text-[0.7rem] font-semibold text-white hover:bg-[#12304f]",
                ),
                on_submit=lambda form_data: AdminState.change_role(
                    row["id"], form_data
                ),
                class_name="flex w-40 flex-col gap-1.5",
            )
        ),
        cell(
            rx.el.div(
                rx.cond(
                    row["approval_status"] == "suspended",
                    rx.el.button(
                        rx.icon("circle-check", class_name="h-3.5 w-3.5"),
                        "Reinstate",
                        on_click=lambda: AdminState.set_account_state(
                            row["id"], False
                        ),
                        class_name="flex w-full items-center justify-center gap-1 rounded-lg bg-teal-600 px-2.5 py-1.5 text-[0.7rem] font-semibold text-white hover:bg-teal-500",
                    ),
                    rx.el.button(
                        rx.icon("ban", class_name="h-3.5 w-3.5"),
                        "Suspend",
                        disabled=row["is_self"],
                        on_click=lambda: AdminState.set_account_state(
                            row["id"], True
                        ),
                        class_name="flex w-full items-center justify-center gap-1 rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-[0.7rem] font-semibold text-red-700 hover:bg-red-100 disabled:opacity-40",
                    ),
                ),
                rx.cond(
                    row["is_active"],
                    rx.fragment(),
                    rx.el.button(
                        "Activate",
                        on_click=lambda: AdminState.set_account_state(
                            row["id"], False
                        ),
                        class_name="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-[0.7rem] font-semibold text-slate-700 hover:bg-slate-100",
                    ),
                ),
                class_name="flex w-28 flex-col gap-1.5",
            )
        ),
        class_name=row_class(),
    )


def _metrics() -> rx.Component:
    return rx.el.div(
        metric_tile(
            "Accounts",
            AdminState.totals["users"].to_string(),
            "users",
            "In the registry",
        ),
        metric_tile(
            "Pending",
            AdminState.pending_count.to_string(),
            "shield-alert",
            "Awaiting decision",
        ),
        metric_tile(
            "Suspended",
            AdminState.totals["suspended"].to_string(),
            "ban",
            "Access withdrawn",
        ),
        metric_tile(
            "Administrators",
            AdminState.totals["admins"].to_string(),
            "shield-check",
            "Control centre access",
        ),
        class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
    )


def _approvals_panel() -> rx.Component:
    return panel(
        "Pending access requests",
        "Each decision is written to the approval audit trail with the deciding administrator and timestamp.",
        rx.cond(
            AdminState.is_loading,
            loading_rows(2),
            rx.cond(
                AdminState.pending_count > 0,
                rx.el.div(
                    rx.foreach(AdminState.pending_users, _decision_card),
                    class_name="grid w-full grid-cols-1 gap-4 xl:grid-cols-2",
                ),
                empty_block(
                    "Queue clear",
                    "There are no pending trainer or administrator access requests.",
                    "shield-check",
                ),
            ),
        ),
        icon="shield-check",
    )


def _directory_panel(title: str, description: str) -> rx.Component:
    return panel(
        title,
        description,
        rx.el.div(
            filter_input(
                "Search name, email or phone",
                AdminState.search_query,
                AdminState.set_search_query.debounce(400),
            ),
            filter_select(
                AdminState.role_filter_options,
                AdminState.role_filter,
                AdminState.set_role_filter,
            ),
            filter_select(
                AdminState.status_filter_options,
                AdminState.status_filter,
                AdminState.set_status_filter,
            ),
            ghost_button("Clear", on_click=AdminState.clear_filters),
            class_name="flex w-full flex-col gap-3 sm:flex-row sm:items-center",
        ),
        rx.cond(
            AdminState.is_loading,
            loading_rows(4),
            rx.cond(
                AdminState.filtered_users.length() > 0,
                data_table(
                    table_head(
                        th("Account", "user"),
                        th("Roles", "id-card"),
                        th("Status", "shield"),
                        th("Approval audit", "history"),
                        th("Last session", "clock"),
                        th("Role change", "repeat"),
                        th("Account state", "toggle-left"),
                    ),
                    rx.el.tbody(
                        rx.foreach(AdminState.filtered_users, _user_row)
                    ),
                ),
                empty_block(
                    "No accounts match",
                    "Adjust the search text or clear the role and status filters.",
                    "search-x",
                ),
            ),
        ),
        icon="users",
    )


def admin_users_page() -> rx.Component:
    return admin_page(
        "Users",
        "Account directory",
        "Every registered account with its role, approval state, audit trail and last session. Self-demotion and self-suspension are blocked.",
        AdminState.error_message,
        AdminState.success_message,
        _metrics(),
        _directory_panel(
            "Account directory",
            "Filter by role or approval status and search by name, email or phone.",
        ),
    )


def admin_approvals_page() -> rx.Component:
    return admin_page(
        "Approvals",
        "Access approvals",
        "Decide pending trainer and administrator access requests. Every decision is written to the approval audit trail with the deciding administrator and timestamp.",
        AdminState.error_message,
        AdminState.success_message,
        _metrics(),
        _approvals_panel(),
    )


def _scopes_panel() -> rx.Component:
    return panel(
        "Permission scopes",
        "What each role can view, create and approve, where its data boundary sits, and the approval it needs before the workspace unlocks.",
        _role_counts(),
        rx.el.div(
            rx.foreach(PERMISSION_SCOPES, _scope_card),
            class_name="grid w-full grid-cols-1 gap-4 xl:grid-cols-3",
        ),
        rx.el.div(
            rx.el.p(
                "Guardrails currently enforced",
                class_name="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-slate-500",
            ),
            rx.el.p(
                "· An administrator can never demote or suspend their own account.",
                class_name="text-xs font-medium text-slate-600",
            ),
            rx.el.p(
                "· At least one approved administrator must remain at all times.",
                class_name="text-xs font-medium text-slate-600",
            ),
            rx.el.p(
                "· Every escalation or demotion needs a written reason and is recorded in the approval audit trail.",
                class_name="text-xs font-medium text-slate-600",
            ),
            rx.el.p(
                "· Suspended accounts keep their full history but lose workspace access until reinstated.",
                class_name="text-xs font-medium text-slate-600",
            ),
            class_name="cc-inset flex w-full flex-col gap-1.5 p-3",
        ),
        rx.el.div(
            rx.foreach(ROLE_OPERATIONS_COPY, _role_copy),
            class_name="grid w-full grid-cols-1 gap-3 lg:grid-cols-3",
        ),
        icon="shield",
    )


def _role_operations_panel() -> rx.Component:
    return panel(
        "Role transitions with workload context",
        "Each account shows its live workload, the impact a transition would have, and the guardrail that applies. A written reason is mandatory.",
        rx.el.div(
            filter_input(
                "Search name or email",
                AdminRoleOpsState.role_query,
                AdminRoleOpsState.set_role_query.debounce(400),
            ),
            filter_select(
                AdminRoleOpsState.role_scope_options,
                AdminRoleOpsState.role_scope_filter,
                AdminRoleOpsState.set_role_scope_filter,
            ),
            class_name="flex w-full flex-col gap-3 sm:flex-row sm:items-center",
        ),
        rx.cond(
            AdminRoleOpsState.is_loading,
            loading_rows(3),
            rx.cond(
                AdminRoleOpsState.filtered_context.length() > 0,
                rx.el.div(
                    rx.foreach(
                        AdminRoleOpsState.filtered_context, _context_card
                    ),
                    class_name="grid w-full grid-cols-1 gap-4 xl:grid-cols-2",
                ),
                empty_block(
                    "No accounts match",
                    "Clear the role filter or adjust the search text.",
                    "search-x",
                ),
            ),
        ),
        icon="user-cog",
    )


def _audit_panel() -> rx.Component:
    return panel(
        "Recent role decisions",
        "The last 25 approval and role-transition records, with the deciding administrator, timestamp and recorded reason.",
        rx.cond(
            AdminRoleOpsState.is_loading,
            loading_rows(2),
            rx.cond(
                AdminRoleOpsState.audit_entries.length() > 0,
                rx.el.ul(
                    rx.foreach(AdminRoleOpsState.audit_entries, _audit_entry),
                    class_name="flex w-full min-w-0 flex-col pl-2",
                ),
                empty_block(
                    "No decisions recorded yet",
                    "Approvals, rejections and role changes are written here as they happen.",
                    "history",
                ),
            ),
        ),
        icon="history",
    )


def admin_roles_page() -> rx.Component:
    return admin_page(
        "Role Management",
        "Role management",
        "Permission scopes, live role counts, workload context and audited transitions across trainee, trainer and administrator roles.",
        AdminRoleOpsState.error_message,
        AdminRoleOpsState.success_message,
        _scopes_panel(),
        _role_operations_panel(),
        _audit_panel(),
        _directory_panel(
            "Account directory",
            "Search an account to review its approval audit, last session and account state controls.",
        ),
    )

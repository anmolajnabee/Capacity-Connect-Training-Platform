"""Courses & trainers oversight for the control centre."""

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
    loading_rows,
    metric_tile,
    panel,
    progress_bar,
    select_field,
    teal_button,
    textarea_field,
)
from app.states.admin_course_ops_state import AdminCourseOpsState
from app.states.admin_oversight_state import AdminOversightState

OPERATIONS_COPY: list[tuple[str, str]] = [
    (
        "Course records lived in separate spreadsheets",
        "Lifecycle status, staffing, content coverage, assessments, assignments and certificates are read from one registry record per course.",
    ),
    (
        "Courses were published before they were deliverable",
        "Publication is blocked until a trainer is accountable, material is published, dates and the nomination deadline are valid, and capacity and duration are positive.",
    ),
    (
        "Trainers were staffed by availability, not capability",
        "Every assignment stores a weighted competency match score, an assignment role and an auditable staffing note.",
    ),
]


def _operations_note(item: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("triangle-alert", class_name="h-3.5 w-3.5 text-amber-600"),
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


def _check_row(check: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.cond(
            check["passed"],
            rx.icon(
                "circle-check",
                class_name="mt-0.5 h-3.5 w-3.5 shrink-0 text-teal-700",
            ),
            rx.icon(
                "circle-alert",
                class_name="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600",
            ),
        ),
        rx.el.div(
            rx.el.p(
                check["label"],
                class_name="text-[0.75rem] font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                check["detail"],
                class_name="text-[0.7rem] font-medium leading-relaxed text-slate-500",
            ),
            class_name="min-w-0",
        ),
        class_name=rx.cond(
            check["passed"],
            "flex w-full min-w-0 items-start gap-2 rounded-lg border border-teal-200 bg-teal-50/40 px-2.5 py-2",
            "flex w-full min-w-0 items-start gap-2 rounded-lg border border-amber-200 bg-amber-50/50 px-2.5 py-2",
        ),
    )


def _lifecycle_controls(row: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.cond(
            AdminCourseOpsState.confirm_course_id == row["id"],
            rx.el.div(
                rx.el.p(
                    row["next_hint"],
                    class_name="text-[0.7rem] font-medium leading-relaxed text-slate-600",
                ),
                rx.el.div(
                    rx.el.button(
                        rx.icon("check", class_name="h-3.5 w-3.5"),
                        rx.el.span("Confirm"),
                        on_click=lambda: AdminCourseOpsState.apply_transition(
                            row["id"], row["target"]
                        ),
                        class_name="cc-press flex items-center gap-1.5 rounded-[0.875rem] bg-teal-600 px-3 py-2 text-[0.75rem] font-semibold text-white transition-colors duration-200 hover:bg-teal-500",
                    ),
                    rx.el.button(
                        "Cancel",
                        on_click=AdminCourseOpsState.cancel_transition,
                        class_name="cc-press rounded-[0.875rem] border border-slate-300 bg-white px-3 py-2 text-[0.75rem] font-semibold text-slate-700 transition-colors duration-200 hover:bg-slate-50",
                    ),
                    class_name="mt-2 flex flex-wrap items-center gap-2",
                ),
                class_name="w-full rounded-[0.875rem] border border-sky-200 bg-sky-50/60 p-3",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("circle_arrow_right", class_name="h-3.5 w-3.5"),
                    rx.el.span(row["next_label"]),
                    disabled=row["blocked"],
                    on_click=lambda: AdminCourseOpsState.request_transition(
                        row["id"], row["target"]
                    ),
                    class_name="cc-press flex items-center gap-1.5 rounded-[0.875rem] bg-[#0A1B33] px-3 py-2 text-[0.75rem] font-semibold text-white transition-colors duration-200 hover:bg-[#12304f] disabled:cursor-not-allowed disabled:opacity-40",
                ),
                rx.cond(
                    row["blocked"],
                    rx.el.p(
                        f"{row['blockers'].length()} blocker(s) must be cleared before publication.",
                        class_name="text-[0.7rem] font-semibold text-amber-700",
                    ),
                    rx.el.p(
                        row["next_hint"],
                        class_name="text-[0.7rem] font-medium text-slate-500",
                    ),
                ),
                rx.el.a(
                    rx.icon("grid-3x3", class_name="h-3.5 w-3.5"),
                    rx.el.span("Competency match"),
                    href="/admin/competency",
                    class_name="flex w-fit items-center gap-1 text-[0.7rem] font-semibold text-sky-700 hover:underline",
                ),
                class_name="flex w-full flex-col items-start gap-2",
            ),
        ),
        class_name="w-full min-w-0",
    )


def _lifecycle_card(row: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    row["code"],
                    class_name="text-[0.7rem] font-semibold uppercase tracking-wider text-teal-700",
                ),
                rx.el.p(
                    row["title"],
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    f"{row['window']} · nominations close {row['deadline']}",
                    class_name="text-[0.7rem] font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                status_pill(row["status"]),
                chip(f"{row['readiness']}% ready", "navy"),
                class_name="flex shrink-0 flex-col items-end gap-1",
            ),
            class_name="flex w-full flex-wrap items-start justify-between gap-3",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Publication readiness",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-slate-500",
                ),
                rx.el.span(
                    f"{row['readiness']}%",
                    class_name="text-[0.75rem] font-semibold text-[#0A1B33]",
                ),
                class_name="flex items-center justify-between gap-2",
            ),
            progress_bar(row["readiness"], "navy"),
            class_name="mt-3 flex w-full flex-col gap-1.5",
        ),
        rx.el.div(
            rx.foreach(row["checks"], _check_row),
            class_name="mt-3 grid w-full grid-cols-1 gap-2 md:grid-cols-2",
        ),
        rx.el.div(
            chip(f"{row['enrolled']} / {row['capacity']} seats", "navy"),
            chip(f"{row['fill']}% filled", "teal"),
            chip(f"{row['active']} active", "teal"),
            chip(f"{row['at_risk']} at risk", "amber"),
            chip(f"{row['completion']}% completed", "green"),
            chip(
                f"{row['published_resources']}/{row['total_resources']} resources published",
                "navy",
            ),
            chip(f"{row['assessments']} assessments", "teal"),
            chip(f"{row['assignments']} assignments", "navy"),
            chip(f"{row['certificates']} certificates", "green"),
            chip(f"{row['trainer_count']} trainers", "amber"),
            class_name="mt-3 flex w-full flex-wrap items-center gap-1.5",
        ),
        rx.el.p(
            f"Delivery team · {row['trainers']}",
            class_name="mt-2 text-[0.7rem] font-medium text-slate-600",
        ),
        rx.el.div(
            _lifecycle_controls(row),
            class_name="mt-3 w-full border-t border-slate-200 pt-3",
        ),
        class_name="cc-card w-full min-w-0 p-4",
    )


def _lifecycle_panel() -> rx.Component:
    return panel(
        "Course lifecycle control",
        "Draft → published → archived → draft, with the exact readiness checks and blockers behind every control. Administrator only; each change reloads oversight.",
        rx.el.div(
            metric_tile(
                "Publish ready",
                AdminCourseOpsState.metrics["publish_ready"].to_string(),
                "circle-check",
                "Drafts clearing every check",
            ),
            metric_tile(
                "Blocked drafts",
                AdminCourseOpsState.metrics["blocked"].to_string(),
                "circle-alert",
                "Readiness gaps to clear",
            ),
            metric_tile(
                "Unstaffed",
                AdminCourseOpsState.metrics["unstaffed"].to_string(),
                "user-x",
                "No trainer accountable",
            ),
            metric_tile(
                "Single-trainer",
                AdminCourseOpsState.metrics["understaffed"].to_string(),
                "users",
                "Understaffed for cover",
            ),
            class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
        ),
        rx.el.div(
            filter_select(
                AdminCourseOpsState.lifecycle_options,
                AdminCourseOpsState.lifecycle_filter,
                AdminCourseOpsState.set_lifecycle_filter,
            ),
            class_name="flex w-full flex-col gap-3 sm:flex-row sm:items-center",
        ),
        rx.cond(
            AdminCourseOpsState.is_loading,
            loading_rows(3),
            rx.cond(
                AdminCourseOpsState.filtered_course_rows.length() > 0,
                rx.el.div(
                    rx.foreach(
                        AdminCourseOpsState.filtered_course_rows,
                        _lifecycle_card,
                    ),
                    class_name="grid w-full grid-cols-1 gap-4 xl:grid-cols-2",
                ),
                empty_block(
                    "No courses in this state",
                    "Change the lifecycle filter to review drafts, published or archived programmes.",
                    "book-open",
                ),
            ),
        ),
        rx.el.div(
            rx.foreach(OPERATIONS_COPY, _operations_note),
            class_name="grid w-full grid-cols-1 gap-3 lg:grid-cols-3",
        ),
        icon="list-checks",
    )


def _staffing_form() -> rx.Component:
    return rx.el.form(
        select_field(
            "Course",
            "course_id",
            rx.foreach(
                AdminCourseOpsState.unstaffed_choices,
                lambda option: rx.el.option(
                    f"{option['label']} · {option['trainer_count']} trainer(s) · {option['status']}",
                    value=option["id"].to_string(),
                ),
            ),
        ),
        select_field(
            "Approved trainer",
            "trainer_id",
            rx.foreach(
                AdminCourseOpsState.trainer_choices,
                lambda option: rx.el.option(
                    option["label"], value=option["id"].to_string()
                ),
            ),
        ),
        select_field(
            "Assignment role",
            "assignment_role",
            rx.foreach(
                AdminCourseOpsState.assignment_role_options,
                lambda option: rx.el.option(option, value=option),
            ),
        ),
        textarea_field(
            "Staffing note (auditable, 10+ characters)",
            "note",
            placeholder="Why this trainer, for this cohort, at this time.",
            rows="2",
        ),
        teal_button("Assign trainer", type="submit"),
        on_submit=AdminCourseOpsState.assign_trainer,
        reset_on_submit=True,
        class_name="grid w-full grid-cols-1 items-end gap-3 md:grid-cols-2 xl:grid-cols-5",
    )


def _staffing_row(row: rx.Var) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.p(
                row["trainer"],
                class_name="text-xs font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                row["email"],
                class_name="text-[0.7rem] font-medium text-slate-500",
            ),
            rx.el.p(
                row["designation"],
                class_name="text-[0.65rem] font-medium text-slate-400",
            ),
        ),
        cell(
            rx.el.p(
                f"{row['code']} · {row['course']}",
                class_name="max-w-[16rem] text-xs font-medium text-slate-700",
            ),
            status_pill(row["course_status"]),
        ),
        cell(
            rx.el.div(
                chip(row["assignment_role"], "navy"),
                status_pill(row["status"]),
                class_name="flex flex-col items-start gap-1",
            )
        ),
        cell(
            rx.el.div(
                rx.el.span(
                    f"{row['match_score']:.1f}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["match_score"], "sky"),
                rx.el.a(
                    "See matched skills",
                    href="/admin/competency",
                    class_name="text-[0.65rem] font-semibold text-sky-700 hover:underline",
                ),
                class_name="flex w-28 flex-col gap-1",
            )
        ),
        cell(
            rx.el.div(
                chip(f"{row['cohort']} trainees", "teal"),
                chip(f"{row['trainer_courses']} courses", "navy"),
                class_name="flex flex-col items-start gap-1",
            )
        ),
        cell(
            rx.el.p(
                row["note"],
                class_name="max-w-[18rem] text-[0.7rem] font-medium text-slate-600",
            ),
            rx.el.p(
                f"Assigned by {row['assigned_by']}",
                class_name="text-[0.65rem] font-medium text-slate-400",
            ),
        ),
        cell(
            rx.el.button(
                rx.icon("user-minus", class_name="h-3.5 w-3.5"),
                rx.el.span("Withdraw"),
                on_click=lambda: AdminCourseOpsState.remove_assignment(
                    row["id"]
                ),
                class_name="cc-press flex items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-[0.7rem] font-semibold text-red-700 transition-colors duration-200 hover:bg-red-100",
            )
        ),
        class_name=row_class(),
    )


def _staffing_panel() -> rx.Component:
    return panel(
        "Trainer staffing",
        "Assignment role, persisted competency match score, approval status and live workload for every course-trainer pairing. Duplicates and non-approved accounts are rejected.",
        _staffing_form(),
        rx.cond(
            AdminCourseOpsState.is_loading,
            loading_rows(3),
            rx.cond(
                AdminCourseOpsState.staffing_rows.length() > 0,
                data_table(
                    table_head(
                        th("Trainer", "user-pen"),
                        th("Course", "book-open"),
                        th("Role", "id-card"),
                        th("Match score", "grid-3x3"),
                        th("Workload", "layers"),
                        th("Staffing note", "file-text"),
                        th("Action", "settings"),
                    ),
                    rx.el.tbody(
                        rx.foreach(
                            AdminCourseOpsState.staffing_rows, _staffing_row
                        )
                    ),
                ),
                empty_block(
                    "No staffing on record",
                    "Assign an approved trainer above, or rank candidates in competency mapping first.",
                    "user-pen",
                ),
            ),
        ),
        icon="user-pen",
    )


def _course_row(row) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.p(
                row["code"],
                class_name="text-[0.7rem] font-semibold uppercase tracking-wider text-teal-700",
            ),
            rx.el.p(
                row["title"],
                class_name="max-w-[18rem] text-xs font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                row["window"],
                class_name="text-[0.65rem] font-medium text-slate-500",
            ),
        ),
        cell(
            rx.el.div(
                status_pill(row["status"]),
                chip(row["category"], "navy"),
                chip(row["mode"], "teal"),
                class_name="flex flex-col items-start gap-1",
            )
        ),
        cell(
            rx.el.div(
                rx.el.span(
                    f"{row['enrolled']} / {row['capacity']}",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["fill"], "navy"),
                rx.el.span(
                    f"{row['fill']}% of capacity",
                    class_name="text-[0.65rem] font-medium text-slate-500",
                ),
                class_name="flex w-28 flex-col gap-1",
            )
        ),
        cell(
            rx.el.div(
                rx.el.span(
                    f"{row['completion']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["completion"]),
                rx.el.div(
                    chip(f"{row['active']} active", "teal"),
                    chip(f"{row['at_risk']} risk", "amber"),
                    class_name="flex flex-wrap gap-1",
                ),
                class_name="flex w-32 flex-col gap-1",
            )
        ),
        cell(
            rx.el.div(
                chip(f"{row['resources']} resources", "navy"),
                chip(f"{row['assessments']} assessments", "teal"),
                chip(f"{row['certificates']} certificates", "green"),
                class_name="flex flex-col items-start gap-1",
            )
        ),
        cell(
            rx.el.p(
                row["trainers"],
                class_name="max-w-[14rem] text-xs font-medium text-slate-700",
            ),
            rx.cond(
                row["trainer_count"] == 0,
                rx.el.a(
                    "Map a trainer",
                    href="/admin/competency",
                    class_name="mt-1 flex w-fit items-center gap-1 text-[0.7rem] font-semibold text-amber-700 hover:underline",
                ),
                rx.el.p(
                    f"{row['trainer_count']} assigned",
                    class_name="text-[0.65rem] font-medium text-slate-500",
                ),
            ),
        ),
        class_name=row_class(),
    )


def _trainer_row(row) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.div(
                rx.image(
                    src=f"https://api.dicebear.com/9.x/notionists/svg?seed={row['email']}",
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
                    class_name="min-w-0",
                ),
                class_name="flex min-w-0 items-center gap-2",
            )
        ),
        cell(
            rx.el.p(
                row["designation"],
                class_name="text-xs font-semibold text-slate-700",
            ),
            rx.el.p(
                row["department"],
                class_name="text-[0.7rem] font-medium text-slate-500",
            ),
            rx.el.p(
                row["specialization"],
                class_name="max-w-[16rem] text-[0.65rem] font-medium text-slate-400",
            ),
        ),
        cell(
            rx.el.div(
                status_pill(row["approval"]),
                rx.cond(
                    row["available"],
                    chip("available", "green"),
                    chip("unavailable", "amber"),
                ),
                class_name="flex flex-col items-start gap-1",
            )
        ),
        cell(
            rx.el.div(
                chip(f"{row['courses']} courses", "teal"),
                chip(f"{row['cohort']} trainees", "navy"),
                chip(f"{row['teachable']} teachable skills", "green"),
                class_name="flex flex-col items-start gap-1",
            )
        ),
        cell(
            rx.el.p(
                row["top_skill"],
                class_name="text-xs font-medium text-slate-700",
            ),
            rx.el.p(
                f"{row['years']:.1f} yrs training · {row['rating']:.1f}★",
                class_name="text-[0.7rem] font-medium text-slate-500",
            ),
        ),
        cell(
            rx.el.div(
                rx.el.span(
                    f"{row['profile_completion']}%",
                    class_name="text-[0.7rem] font-semibold text-slate-700",
                ),
                progress_bar(row["profile_completion"], "amber"),
                class_name="flex w-24 flex-col gap-1",
            )
        ),
        class_name=row_class(),
    )


def competency_callout(title: str, description: str) -> rx.Component:
    """Entry point into the weighted competency mapping workspace."""
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("grid-3x3", class_name="h-5 w-5 text-sky-700"),
                class_name="flex size-10 shrink-0 items-center justify-center rounded-[0.875rem] border border-sky-200 bg-sky-50",
            ),
            rx.el.div(
                rx.el.p(
                    title,
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    description,
                    class_name="mt-0.5 text-xs font-medium leading-relaxed text-slate-600",
                ),
                class_name="min-w-0",
            ),
            class_name="flex min-w-0 items-start gap-3",
        ),
        rx.el.a(
            rx.icon("arrow-right", class_name="h-4 w-4"),
            rx.el.span("Open competency mapping"),
            href="/admin/competency",
            class_name="cc-focus-sky flex w-fit shrink-0 items-center gap-2 rounded-[0.875rem] bg-[#0A1B33] px-4 py-2 text-sm font-semibold text-white outline-hidden transition-all duration-200 hover:bg-[#12304f]",
        ),
        class_name="cc-card flex w-full flex-wrap items-center justify-between gap-4 p-4",
    )


def _metrics() -> rx.Component:
    return rx.el.div(
        metric_tile(
            "Courses",
            AdminOversightState.courses.length().to_string(),
            "book-open",
            "In the catalogue",
        ),
        metric_tile(
            "Trainers",
            AdminOversightState.trainers.length().to_string(),
            "user-pen",
            "Registered faculty",
        ),
        metric_tile(
            "Enrolment records",
            AdminOversightState.enrollments.length().to_string(),
            "clipboard-list",
            "Most recent 150",
        ),
        metric_tile(
            "Assessments",
            AdminOversightState.assessments.length().to_string(),
            "list-checks",
            "Across all courses",
        ),
        class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
    )


def _courses_panel() -> rx.Component:
    return panel(
        "Course delivery register",
        "Search by code, title, category or trainer, and filter by publication status.",
        rx.el.div(
            filter_input(
                "Search courses or trainers",
                AdminOversightState.course_query,
                AdminOversightState.set_course_query.debounce(400),
            ),
            filter_select(
                AdminOversightState.course_status_options,
                AdminOversightState.course_status_filter,
                AdminOversightState.set_course_status_filter,
            ),
            class_name="flex w-full flex-col gap-3 sm:flex-row sm:items-center",
        ),
        rx.cond(
            AdminOversightState.is_loading,
            loading_rows(4),
            rx.cond(
                AdminOversightState.filtered_courses.length() > 0,
                data_table(
                    table_head(
                        th("Course", "book-open"),
                        th("Classification", "tag"),
                        th("Cohort load", "users"),
                        th("Outcomes", "badge-check"),
                        th("Content", "library"),
                        th("Trainers", "user-pen"),
                    ),
                    rx.el.tbody(
                        rx.foreach(
                            AdminOversightState.filtered_courses,
                            _course_row,
                        )
                    ),
                ),
                empty_block(
                    "No courses match",
                    "Clear the status filter or adjust the search text.",
                    "search-x",
                ),
            ),
        ),
        icon="book-open",
    )


def _trainers_panel() -> rx.Component:
    return panel(
        "Trainer register",
        "Expertise, availability, teaching load and profile completeness for every trainer account.",
        rx.cond(
            AdminOversightState.is_loading,
            loading_rows(3),
            rx.cond(
                AdminOversightState.trainers.length() > 0,
                data_table(
                    table_head(
                        th("Trainer", "user"),
                        th("Position", "briefcase"),
                        th("Status", "shield"),
                        th("Load", "layers"),
                        th("Peak competency", "trending-up"),
                        th("Profile", "gauge"),
                    ),
                    rx.el.tbody(
                        rx.foreach(AdminOversightState.trainers, _trainer_row)
                    ),
                ),
                empty_block(
                    "No trainers registered",
                    "Approved trainer accounts appear here with their expertise and load.",
                    "user-pen",
                ),
            ),
        ),
        icon="user-pen",
    )


def admin_courses_page() -> rx.Component:
    return admin_page(
        "Courses",
        "Course oversight",
        "Every programme in the catalogue with cohort load, delivery outcomes, learning material coverage and the trainers responsible.",
        AdminCourseOpsState.error_message,
        AdminCourseOpsState.success_message,
        _metrics(),
        _lifecycle_panel(),
        _staffing_panel(),
        _courses_panel(),
        competency_callout(
            "Competency mapping for course staffing",
            "Rank every approved trainer against a course's weighted required skills, with transparent match scores and matched-skill detail.",
        ),
    )


def admin_trainers_page() -> rx.Component:
    return admin_page(
        "Trainers",
        "Trainer oversight",
        "Expertise, availability, teaching load and profile completeness for every trainer account in the institution.",
        AdminCourseOpsState.error_message,
        AdminCourseOpsState.success_message,
        _metrics(),
        _staffing_panel(),
        _trainers_panel(),
        competency_callout(
            "Compare trainers by competency",
            "Open the competency matrix to see each trainer's proficiency evidence, gaps and weighted suitability for any course.",
        ),
    )

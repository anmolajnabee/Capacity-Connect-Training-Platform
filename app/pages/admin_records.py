"""Assessments, enrolment participation and certification records."""

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
)
from app.states.admin_certification_state import (
    AdminCertificationState,
    RequestRow,
)
from app.states.admin_oversight_state import AdminOversightState


def _priority_chip(priority: rx.Var) -> rx.Component:
    return rx.el.span(
        priority,
        class_name=rx.match(
            priority,
            (
                "critical",
                "w-fit rounded-full border border-red-200 bg-red-100 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-red-700",
            ),
            (
                "high",
                "w-fit rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-amber-800",
            ),
            (
                "normal",
                "w-fit rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-sky-700",
            ),
            "w-fit rounded-full border border-slate-300 bg-slate-100 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-slate-600",
        ),
    )


def _request_row(row: RequestRow) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.p(
                row["trainee"],
                class_name="text-xs font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                row["email"],
                class_name="text-[0.7rem] font-medium text-slate-500",
            ),
        ),
        cell(
            rx.el.p(
                row["code"],
                class_name="text-[0.7rem] font-semibold uppercase tracking-wider text-sky-700",
            ),
            rx.el.p(
                row["course"],
                class_name="max-w-[16rem] text-xs font-medium text-slate-700",
            ),
        ),
        cell(
            rx.el.div(
                status_pill(row["status"]),
                _priority_chip(row["priority"]),
                class_name="flex flex-col items-start gap-1",
            )
        ),
        cell(
            rx.el.div(
                rx.el.span(
                    f"{row['progress']}% evidence",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["progress"], "sky"),
                rx.el.span(
                    f"best {row['average_score']:.1f}% · {row['assessments_passed']}/{row['assessments_total']} passed",
                    class_name="text-[0.65rem] font-medium text-slate-500",
                ),
                class_name="flex w-36 flex-col gap-1",
            )
        ),
        cell(
            rx.el.p(
                row["requested_at"],
                class_name="text-[0.7rem] font-medium text-slate-600",
            ),
            rx.el.p(
                row["age_label"],
                class_name=rx.cond(
                    row["is_overdue"],
                    "text-[0.65rem] font-semibold text-red-600",
                    "text-[0.65rem] font-medium text-slate-500",
                ),
            ),
        ),
        cell(
            rx.cond(
                row["has_certificate"],
                rx.el.div(
                    rx.el.p(
                        row["certificate_number"],
                        class_name="font-mono text-[0.7rem] font-semibold text-[#0A1B33]",
                    ),
                    rx.el.p(
                        f"Verify · {row['verification_code']}",
                        class_name="text-[0.65rem] font-medium text-slate-500",
                    ),
                    class_name="flex flex-col",
                ),
                rx.el.span(
                    "Not issued",
                    class_name="text-[0.7rem] font-medium text-slate-400",
                ),
            )
        ),
        cell(
            rx.el.button(
                rx.cond(
                    AdminCertificationState.active_id == row["id"],
                    "Close",
                    "Review",
                ),
                on_click=lambda: AdminCertificationState.select_request(
                    row["id"]
                ),
                class_name="cc-press w-fit rounded-lg border border-sky-300 bg-sky-50 px-3 py-1.5 text-[0.7rem] font-semibold text-sky-800 transition-colors hover:bg-sky-100",
            )
        ),
        class_name=row_class(),
    )


def _decision_console() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    "Evidence to decision",
                    class_name="text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.h3(
                    f"{AdminCertificationState.active_request['code']} · {AdminCertificationState.active_request['course']}",
                    class_name="mt-0.5 text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    f"{AdminCertificationState.active_request['trainee']} · {AdminCertificationState.active_request['email']} · enrolment {AdminCertificationState.active_request['enrollment_status']}",
                    class_name="text-[0.7rem] font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                status_pill(AdminCertificationState.active_request["status"]),
                _priority_chip(
                    AdminCertificationState.active_request["priority"]
                ),
                rx.cond(
                    AdminCertificationState.active_request["eligible_snapshot"],
                    chip("Snapshot eligible", "green"),
                    chip("Snapshot not eligible", "amber"),
                ),
                class_name="flex flex-wrap items-center gap-2",
            ),
            class_name="flex w-full flex-col items-start justify-between gap-3 lg:flex-row lg:items-center",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    "Trainee justification",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.p(
                    AdminCertificationState.active_request["justification"],
                    class_name="mt-1 text-xs font-medium leading-relaxed text-slate-700",
                ),
                class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-white p-3",
            ),
            rx.el.div(
                rx.el.p(
                    "Evidence snapshot at submission",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.p(
                    AdminCertificationState.active_request["eligibility_note"],
                    class_name="mt-1 text-xs font-medium leading-relaxed text-slate-700",
                ),
                rx.el.p(
                    f"Raised {AdminCertificationState.active_request['requested_at']} · {AdminCertificationState.active_request['age_label']} · last review {AdminCertificationState.active_request['reviewed_at']} by {AdminCertificationState.active_request['reviewer']}",
                    class_name="mt-2 text-[0.65rem] font-medium text-slate-500",
                ),
                class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-white p-3",
            ),
            class_name="mt-3 grid w-full min-w-0 grid-cols-1 gap-3 lg:grid-cols-2",
        ),
        rx.el.label(
            rx.el.span(
                "Decision note (required when rejecting)",
                class_name="block text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
            ),
            rx.el.textarea(
                rows="3",
                placeholder="Record what was verified, or exactly what the trainee must complete before resubmitting.",
                default_value=AdminCertificationState.decision_note,
                on_change=AdminCertificationState.set_decision_note.debounce(
                    400
                ),
                class_name="cc-focus mt-1 w-full rounded-[0.875rem] border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-900 outline-hidden transition-colors duration-200 focus:border-sky-500",
            ),
            class_name="mt-3 flex w-full flex-col",
        ),
        rx.el.div(
            rx.cond(
                AdminCertificationState.active_request["can_approve"],
                rx.el.button(
                    rx.icon("check", class_name="h-3.5 w-3.5"),
                    "Approve",
                    on_click=lambda: AdminCertificationState.approve_request(
                        AdminCertificationState.active_id
                    ),
                    class_name="cc-press flex w-fit items-center gap-1.5 rounded-lg bg-[#0A1B33] px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-[#12304f]",
                ),
                rx.fragment(),
            ),
            rx.cond(
                AdminCertificationState.active_request["can_issue"],
                rx.el.button(
                    rx.icon("stamp", class_name="h-3.5 w-3.5"),
                    "Issue certificate",
                    on_click=lambda: AdminCertificationState.issue_certificate(
                        AdminCertificationState.active_id
                    ),
                    class_name="cc-press flex w-fit items-center gap-1.5 rounded-lg bg-sky-600 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-sky-500",
                ),
                rx.fragment(),
            ),
            rx.cond(
                AdminCertificationState.active_request["can_reject"],
                rx.el.button(
                    rx.icon("circle-x", class_name="h-3.5 w-3.5"),
                    "Reject with reason",
                    on_click=lambda: AdminCertificationState.reject_request(
                        AdminCertificationState.active_id
                    ),
                    class_name="cc-press flex w-fit items-center gap-1.5 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 transition-colors hover:bg-red-100",
                ),
                rx.fragment(),
            ),
            rx.el.p(
                "Approval never issues silently — issuance is a separate, logged step that generates the certificate number and verification code.",
                class_name="text-[0.65rem] font-medium leading-relaxed text-slate-500",
            ),
            class_name="mt-3 flex w-full flex-wrap items-center gap-2",
        ),
        rx.cond(
            AdminCertificationState.active_request["decision_note"],
            rx.el.p(
                f"Last recorded decision · {AdminCertificationState.active_request['decision_note']}",
                class_name="mt-2 text-[0.7rem] font-medium leading-relaxed text-slate-600",
            ),
            rx.fragment(),
        ),
        class_name="cc-fade w-full min-w-0 rounded-[0.875rem] border border-sky-200 bg-sky-50/40 p-4",
    )


def _triage_panel() -> rx.Component:
    return panel(
        "Certificate request triage queue",
        "Replaces spreadsheet and email certificate chasing: every request is visible, aged, evidenced and auditable in one queue.",
        rx.el.div(
            metric_tile(
                "Pending",
                AdminCertificationState.metrics["pending"].to_string(),
                "hourglass",
                f"{AdminCertificationState.metrics['overdue']} beyond 7 days",
            ),
            metric_tile(
                "Approved",
                AdminCertificationState.metrics["approved"].to_string(),
                "badge-check",
                "Awaiting issuance",
            ),
            metric_tile(
                "Rejected",
                AdminCertificationState.metrics["rejected"].to_string(),
                "circle-x",
                "Returned with a reason",
            ),
            metric_tile(
                "Issued",
                AdminCertificationState.metrics["issued"].to_string(),
                "award",
                f"{AdminCertificationState.metrics['total']} requests on record",
            ),
            class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
        ),
        rx.el.div(
            filter_input(
                "Search by trainee, email or course code",
                AdminCertificationState.query,
                AdminCertificationState.set_query.debounce(400),
            ),
            filter_select(
                AdminCertificationState.status_options,
                AdminCertificationState.status_filter,
                AdminCertificationState.set_status_filter,
            ),
            class_name="flex w-full flex-col gap-3 sm:flex-row sm:items-center",
        ),
        rx.cond(
            AdminCertificationState.is_loading,
            loading_rows(3),
            rx.cond(
                AdminCertificationState.filtered_requests.length() > 0,
                data_table(
                    table_head(
                        th("Trainee", "user"),
                        th("Course", "book-open"),
                        th("State", "shield"),
                        th("Evidence", "activity"),
                        th("Raised", "calendar-clock"),
                        th("Certificate", "award"),
                        th("Action", "gavel"),
                    ),
                    rx.el.tbody(
                        rx.foreach(
                            AdminCertificationState.filtered_requests,
                            _request_row,
                        )
                    ),
                ),
                empty_block(
                    "No requests in this view",
                    "Change the status filter or clear the search to see the rest of the certification queue.",
                    "inbox",
                ),
            ),
        ),
        rx.cond(
            AdminCertificationState.active_request,
            _decision_console(),
            rx.fragment(),
        ),
        icon="gavel",
    )


def _assessment_row(row) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.p(
                row["title"],
                class_name="max-w-[18rem] text-xs font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                f"{row['code']} · {row['course']}",
                class_name="max-w-[18rem] text-[0.7rem] font-medium text-slate-500",
            ),
        ),
        cell(status_pill(row["status"])),
        cell(
            rx.el.div(
                chip(f"{row['questions']} questions", "navy"),
                chip(f"{row['time_limit']} min", "teal"),
                class_name="flex flex-col items-start gap-1",
            )
        ),
        cell(
            rx.el.p(
                f"{row['passing_marks']:.0f} of {row['total_marks']:.0f}",
                class_name="text-xs font-semibold text-slate-700",
            ),
            rx.el.p(
                "pass mark",
                class_name="text-[0.65rem] font-medium text-slate-400",
            ),
        ),
        cell(
            rx.el.div(
                rx.el.span(
                    f"{row['pass_rate']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["pass_rate"]),
                rx.el.span(
                    f"{row['passes']} of {row['results']} graded",
                    class_name="text-[0.65rem] font-medium text-slate-500",
                ),
                class_name="flex w-32 flex-col gap-1",
            )
        ),
        cell(
            rx.el.p(
                f"{row['avg_score']:.1f}%",
                class_name="text-xs font-semibold text-slate-700",
            ),
            rx.el.p(
                f"{row['attempts']} attempts",
                class_name="text-[0.65rem] font-medium text-slate-500",
            ),
        ),
        cell(
            rx.el.p(
                row["deadline"],
                class_name="text-[0.7rem] font-medium text-slate-600",
            )
        ),
        class_name=row_class(),
    )


def _enrollment_row(row) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.p(
                row["trainee"],
                class_name="text-xs font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                row["email"],
                class_name="text-[0.7rem] font-medium text-slate-500",
            ),
        ),
        cell(
            rx.el.p(
                row["code"],
                class_name="text-[0.7rem] font-semibold uppercase tracking-wider text-teal-700",
            ),
            rx.el.p(
                row["course"],
                class_name="max-w-[16rem] text-xs font-medium text-slate-700",
            ),
        ),
        cell(chip(row["status"], "navy")),
        cell(
            rx.el.div(
                rx.el.span(
                    f"{row['progress']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["progress"]),
                class_name="flex w-28 flex-col gap-1",
            )
        ),
        cell(
            rx.el.p(
                row["enrolled"],
                class_name="text-[0.7rem] font-medium text-slate-600",
            )
        ),
        cell(
            rx.el.p(
                row["last_activity"],
                class_name="text-[0.7rem] font-medium text-slate-600",
            )
        ),
        class_name=row_class(),
    )


def _certificate_row(row) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.p(
                row["number"],
                class_name="text-xs font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                f"Verify · {row['verification']}",
                class_name="text-[0.65rem] font-medium text-slate-500",
            ),
        ),
        cell(
            rx.el.p(
                row["trainee"],
                class_name="text-xs font-semibold text-slate-700",
            )
        ),
        cell(
            rx.el.p(
                row["course"],
                class_name="max-w-[18rem] text-xs font-medium text-slate-700",
            )
        ),
        cell(
            rx.el.p(
                f"{row['score']:.1f}%",
                class_name="text-xs font-semibold text-[#0A1B33]",
            ),
            chip(row["grade"], "teal"),
        ),
        cell(
            rx.el.p(
                row["issued"],
                class_name="text-[0.7rem] font-medium text-slate-600",
            )
        ),
        cell(
            rx.cond(
                row["revoked"],
                chip("revoked", "red"),
                chip("valid", "green"),
            )
        ),
        class_name=row_class(),
    )


def _metrics() -> rx.Component:
    return rx.el.div(
        metric_tile(
            "Assessments",
            AdminOversightState.assessments.length().to_string(),
            "list-checks",
            "Authored across courses",
        ),
        metric_tile(
            "Certificates",
            AdminOversightState.certificates.length().to_string(),
            "award",
            "Issued records",
        ),
        metric_tile(
            "Enrolments",
            AdminOversightState.enrollments.length().to_string(),
            "clipboard-list",
            "Most recent participation",
        ),
        metric_tile(
            "Courses",
            AdminOversightState.courses.length().to_string(),
            "book-open",
            "Delivering these records",
        ),
        class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
    )


def _assessments_panel() -> rx.Component:
    return panel(
        "Assessment register",
        "Pass rates and mean percentages computed from graded result records.",
        rx.el.div(
            filter_select(
                AdminOversightState.assessment_status_options,
                AdminOversightState.assessment_status_filter,
                AdminOversightState.set_assessment_status_filter,
            ),
            class_name="flex w-full flex-col gap-3 sm:flex-row sm:items-center",
        ),
        rx.cond(
            AdminOversightState.is_loading,
            loading_rows(3),
            rx.cond(
                AdminOversightState.filtered_assessments.length() > 0,
                data_table(
                    table_head(
                        th("Assessment", "list-checks"),
                        th("Status", "shield"),
                        th("Format", "settings"),
                        th("Marks", "percent"),
                        th("Pass rate", "badge-check"),
                        th("Mean score", "activity"),
                        th("Deadline", "calendar-clock"),
                    ),
                    rx.el.tbody(
                        rx.foreach(
                            AdminOversightState.filtered_assessments,
                            _assessment_row,
                        )
                    ),
                ),
                empty_block(
                    "No assessments match",
                    "Change the status filter to see draft, open or closed assessments.",
                    "list-checks",
                ),
            ),
        ),
        icon="list-checks",
    )


def _participation_panel() -> rx.Component:
    return panel(
        "Participation register",
        "Search enrolments by trainee, email or course code.",
        rx.el.div(
            filter_input(
                "Search enrolments",
                AdminOversightState.enrollment_query,
                AdminOversightState.set_enrollment_query.debounce(400),
            ),
            class_name="flex w-full flex-col gap-3 sm:flex-row sm:items-center",
        ),
        rx.cond(
            AdminOversightState.is_loading,
            loading_rows(4),
            rx.cond(
                AdminOversightState.filtered_enrollments.length() > 0,
                data_table(
                    table_head(
                        th("Trainee", "user"),
                        th("Course", "book-open"),
                        th("Status", "flag"),
                        th("Progress", "activity"),
                        th("Enrolled", "calendar"),
                        th("Last activity", "clock"),
                    ),
                    rx.el.tbody(
                        rx.foreach(
                            AdminOversightState.filtered_enrollments,
                            _enrollment_row,
                        )
                    ),
                ),
                empty_block(
                    "No enrolments match",
                    "Participation records appear as trainees enrol in courses.",
                    "clipboard-list",
                ),
            ),
        ),
        icon="clipboard-list",
    )


def _certificates_panel() -> rx.Component:
    return panel(
        "Certification register",
        "Certificate numbers, verification codes, grades and revocation state.",
        rx.cond(
            AdminOversightState.is_loading,
            loading_rows(2),
            rx.cond(
                AdminOversightState.certificates.length() > 0,
                data_table(
                    table_head(
                        th("Certificate", "award"),
                        th("Trainee", "user"),
                        th("Course", "book-open"),
                        th("Result", "percent"),
                        th("Issued", "calendar"),
                        th("Validity", "shield-check"),
                    ),
                    rx.el.tbody(
                        rx.foreach(
                            AdminOversightState.certificates,
                            _certificate_row,
                        )
                    ),
                ),
                empty_block(
                    "No certificates issued yet",
                    "Certificates appear once trainees complete a course and pass its assessment.",
                    "award",
                ),
            ),
        ),
        icon="award",
    )


def _assignment_row(row) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.p(
                row["title"],
                class_name="max-w-[18rem] text-xs font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                f"{row['code']} · {row['course']}",
                class_name="max-w-[18rem] text-[0.7rem] font-medium text-slate-500",
            ),
        ),
        cell(
            rx.el.div(
                status_pill(row["status"]),
                chip(row["assignment_type"], "navy"),
                class_name="flex flex-col items-start gap-1",
            )
        ),
        cell(
            rx.el.p(
                row["trainer"],
                class_name="text-xs font-medium text-slate-700",
            )
        ),
        cell(
            rx.el.div(
                rx.el.span(
                    f"{row['submitted']} of {row['cohort']} · {row['completion']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["completion"], "sky"),
                class_name="flex w-32 flex-col gap-1",
            )
        ),
        cell(
            rx.el.div(
                rx.el.span(
                    f"{row['graded']} graded · {row['graded_percent']}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                progress_bar(row["graded_percent"], "navy"),
                class_name="flex w-32 flex-col gap-1",
            )
        ),
        cell(
            rx.el.p(
                f"{row['total_marks']:.0f} marks",
                class_name="text-xs font-semibold text-slate-700",
            ),
            rx.el.p(
                f"{row['late']} late",
                class_name="text-[0.65rem] font-medium text-slate-500",
            ),
        ),
        cell(
            rx.el.p(
                row["due"],
                class_name="text-[0.7rem] font-medium text-slate-600",
            )
        ),
        class_name=row_class(),
    )


def _submission_row(row) -> rx.Component:
    return rx.el.tr(
        cell(
            rx.el.p(
                row["trainee"],
                class_name="text-xs font-semibold text-[#0A1B33]",
            )
        ),
        cell(
            rx.el.p(
                row["assignment"],
                class_name="max-w-[16rem] text-xs font-medium text-slate-700",
            ),
            rx.el.p(
                row["course"],
                class_name="max-w-[16rem] text-[0.7rem] font-medium text-slate-500",
            ),
        ),
        cell(
            rx.el.div(
                status_pill(row["status"]),
                rx.cond(row["is_late"], chip("late", "red"), rx.fragment()),
                class_name="flex flex-col items-start gap-1",
            )
        ),
        cell(
            rx.el.p(
                row["submitted"],
                class_name="text-[0.7rem] font-medium text-slate-600",
            )
        ),
        cell(
            rx.el.p(
                f"{row['marks']:.1f} / {row['total_marks']:.0f}",
                class_name="text-xs font-semibold text-slate-700",
            )
        ),
        cell(
            rx.el.p(
                row["grader"],
                class_name="text-[0.7rem] font-medium text-slate-600",
            )
        ),
        class_name=row_class(),
    )


def _assignments_panel() -> rx.Component:
    return panel(
        "Assignment oversight",
        "Read-only view of trainer-authored assignments, submission completion and grading progress across the institution.",
        rx.el.div(
            metric_tile(
                "Assignments",
                AdminOversightState.assignment_metrics[
                    "assignments"
                ].to_string(),
                "clipboard-list",
                f"{AdminOversightState.assignment_metrics['published']} published",
            ),
            metric_tile(
                "Submissions",
                AdminOversightState.assignment_metrics[
                    "submissions"
                ].to_string(),
                "inbox",
                f"{AdminOversightState.assignment_metrics['late']} late",
            ),
            metric_tile(
                "Completion",
                f"{AdminOversightState.assignment_metrics['completion']}%",
                "activity",
                "Cohort submission rate",
            ),
            metric_tile(
                "Graded",
                AdminOversightState.assignment_metrics["graded"].to_string(),
                "badge-check",
                f"{AdminOversightState.assignment_metrics['graded_percent']}% of submissions",
            ),
            class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
        ),
        rx.cond(
            AdminOversightState.is_loading,
            loading_rows(3),
            rx.cond(
                AdminOversightState.assignment_rows.length() > 0,
                rx.el.div(
                    data_table(
                        table_head(
                            th("Assignment", "clipboard-list"),
                            th("State", "shield"),
                            th("Trainer", "user-pen"),
                            th("Submissions", "activity"),
                            th("Grading", "badge-check"),
                            th("Marks", "percent"),
                            th("Due", "calendar-clock"),
                        ),
                        rx.el.tbody(
                            rx.foreach(
                                AdminOversightState.assignment_rows,
                                _assignment_row,
                            )
                        ),
                    ),
                    rx.el.p(
                        "Recent submissions",
                        class_name="mt-4 text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
                    ),
                    rx.cond(
                        AdminOversightState.submission_rows.length() > 0,
                        data_table(
                            table_head(
                                th("Trainee", "user"),
                                th("Assignment", "clipboard-list"),
                                th("Status", "flag"),
                                th("Submitted", "clock"),
                                th("Marks", "percent"),
                                th("Grader", "user-check"),
                            ),
                            rx.el.tbody(
                                rx.foreach(
                                    AdminOversightState.submission_rows,
                                    _submission_row,
                                )
                            ),
                        ),
                        empty_block(
                            "No submissions recorded yet",
                            "Trainee submissions will appear here as assignments are worked on.",
                            "inbox",
                        ),
                    ),
                    class_name="flex w-full min-w-0 flex-col gap-2",
                ),
                empty_block(
                    "No assignments authored yet",
                    "Trainers can publish course assignments from their workspace; records appear here automatically.",
                    "clipboard-list",
                ),
            ),
        ),
        icon="clipboard-list",
    )


def admin_assessments_page() -> rx.Component:
    return admin_page(
        "Assessments",
        "Assessment oversight",
        "Assessment outcomes across every course, with pass rates and mean scores computed from graded results, plus live enrolment participation.",
        AdminOversightState.error_message,
        "",
        _metrics(),
        _assessments_panel(),
        _assignments_panel(),
        _participation_panel(),
    )


def admin_certifications_page() -> rx.Component:
    return admin_page(
        "Certifications",
        "Certification queue & records",
        "Review certificate requests against a single source of completion evidence, then issue numbered certificates — with every decision, reviewer and timestamp on record.",
        rx.cond(
            AdminCertificationState.error_message,
            AdminCertificationState.error_message,
            AdminOversightState.error_message,
        ),
        AdminCertificationState.success_message,
        _triage_panel(),
        _metrics(),
        _certificates_panel(),
    )

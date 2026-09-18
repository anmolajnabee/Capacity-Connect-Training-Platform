"""Results history, certificate records and course feedback."""

from __future__ import annotations

import reflex as rx

from app.components.trainee_shell import trainee_page
from app.components.trainee_ui import (
    chip,
    empty_block,
    ghost_button,
    loading_rows,
    metric_tile,
    panel,
    progress_bar,
    select_field,
    teal_button,
    textarea_field,
)
from app.states.trainee_assessment_state import (
    CertificateItem,
    ResultItem,
    TraineeAssessmentState,
)
from app.states.trainee_certification_state import (
    ReadinessRow,
    TraineeCertificationState,
)
from app.states.trainee_learning_state import (
    FeedbackCourse,
    TraineeLearningState,
)


# ------------------------------------------------------------------ results
def _result_row(result: ResultItem) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.div(
                rx.el.p(
                    result["assessment_title"],
                    class_name="truncate text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    f"{result['course_code']} · attempt {result['attempt_number']}",
                    class_name="truncate text-[0.7rem] font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.span(
                f"{result['score']:.1f} / {result['total_marks']:.1f}",
                class_name="text-sm font-medium text-slate-700",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.span(
                f"{result['percentage']}%",
                class_name="text-sm font-semibold text-[#0A1B33]",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(chip(result["grade"], "navy"), class_name="px-3 py-2"),
        rx.el.td(
            rx.el.span(
                f"{result['correct_count']} ✓ · {result['incorrect_count']} ✗ · {result['unanswered_count']} –",
                class_name="whitespace-nowrap text-xs font-medium text-slate-600",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.span(
                result["time_taken"],
                class_name="whitespace-nowrap text-xs font-medium text-slate-600",
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.cond(
                result["is_passed"],
                chip("Passed", "green"),
                chip("Not passed", "red"),
            ),
            class_name="px-3 py-2",
        ),
        rx.el.td(
            rx.el.span(
                result["graded_at"],
                class_name="whitespace-nowrap text-xs font-medium text-slate-500",
            ),
            class_name="px-3 py-2",
        ),
        class_name="border-b border-slate-100 odd:bg-white even:bg-[#FBFAF7] hover:bg-teal-50/60",
    )


def _results_header(label: str, icon: str) -> rx.Component:
    return rx.el.th(
        rx.el.div(
            rx.icon(icon, class_name="h-3.5 w-3.5 text-teal-700"),
            rx.el.span(label),
            class_name="flex items-center gap-1.5",
        ),
        class_name="whitespace-nowrap px-3 py-2 text-left text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
    )


def trainee_results_page() -> rx.Component:
    return trainee_page(
        "Results",
        "Assessment results history",
        "Every graded attempt with score, grade, answer breakdown and pass status.",
        TraineeAssessmentState.error_message,
        TraineeAssessmentState.success_message,
        rx.el.div(
            metric_tile(
                "Graded attempts",
                TraineeAssessmentState.results.length().to_string(),
                "clipboard-list",
            ),
            metric_tile(
                "Passed",
                TraineeAssessmentState.passed_count.to_string(),
                "circle-check",
            ),
            metric_tile(
                "Average score",
                f"{TraineeAssessmentState.average_percentage}%",
                "gauge",
            ),
            metric_tile(
                "Certificates",
                TraineeAssessmentState.certificates.length().to_string(),
                "award",
                "Issued on course completion",
            ),
            class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
        ),
        rx.cond(
            TraineeAssessmentState.is_loading,
            loading_rows(4),
            rx.cond(
                TraineeAssessmentState.results.length() > 0,
                panel(
                    "Results ledger",
                    "Newest graded attempt first.",
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    _results_header("Assessment", "file-text"),
                                    _results_header("Score", "sigma"),
                                    _results_header("Percentage", "percent"),
                                    _results_header("Grade", "award"),
                                    _results_header("Breakdown", "list-checks"),
                                    _results_header("Time", "timer"),
                                    _results_header("Outcome", "flag"),
                                    _results_header("Graded", "calendar"),
                                ),
                                class_name="bg-slate-50",
                            ),
                            rx.el.tbody(
                                rx.foreach(
                                    TraineeAssessmentState.results, _result_row
                                )
                            ),
                            class_name="table-auto w-full min-w-[54rem]",
                        ),
                        class_name="w-full overflow-x-auto rounded-lg border border-slate-200",
                    ),
                    icon="chart-line",
                ),
                empty_block(
                    "No graded results yet",
                    "Complete a questionnaire under Assessments to see scored results here.",
                    "chart-line",
                ),
            ),
        ),
    )


# ------------------------------------------------------------- certificates
def _certificate_card(item: CertificateItem) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            chip(item["course_code"], "navy"),
            rx.cond(
                item["is_revoked"],
                chip("Revoked", "red"),
                chip("Valid", "green"),
            ),
            class_name="flex flex-wrap items-center gap-2",
        ),
        rx.el.h3(
            item["course_title"],
            class_name="mt-3 text-base font-semibold leading-snug text-[#0A1B33]",
        ),
        rx.el.p(
            item["certificate_number"],
            class_name="mt-1 font-mono text-xs font-semibold tracking-wide text-teal-700",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Issued",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    item["issued_at"],
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Final score",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    f"{item['final_score']:.1f}%",
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Grade",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    item["grade"],
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            rx.el.div(
                rx.el.span(
                    "Verification code",
                    class_name="block text-[0.6rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                rx.el.span(
                    item["verification_code"],
                    class_name="font-mono text-xs font-semibold text-[#0A1B33]",
                ),
            ),
            class_name="mt-3 grid w-full grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
        ),
        rx.el.div(
            rx.icon("stamp", class_name="h-3.5 w-3.5 text-teal-700"),
            rx.el.span(
                f"Issued by {item['issued_by']}",
                class_name="truncate text-[0.7rem] font-medium text-slate-600",
            ),
            class_name="mt-3 flex items-center gap-2",
        ),
        rx.el.a(
            rx.icon("qr-code", class_name="h-4 w-4"),
            "Verify certificate & QR",
            href=f"/verify/{item['verification_code']}",
            class_name="cc-focus mt-4 flex w-fit items-center gap-2 rounded-lg border border-teal-300 bg-teal-50 px-3 py-2 text-sm font-semibold text-teal-800 hover:bg-teal-100",
        ),
        class_name="flex h-full w-full min-w-0 flex-col rounded-xl border border-slate-200 bg-white p-4",
    )


def _evidence_cell(
    label: str, value: rx.Var | str, hint: rx.Var | str, icon: str
) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, class_name="h-3.5 w-3.5 text-teal-700"),
            rx.el.span(
                label,
                class_name="text-[0.6rem] font-semibold uppercase tracking-[0.14em] text-slate-500",
            ),
            class_name="flex items-center gap-1.5",
        ),
        rx.el.p(
            value,
            class_name="mt-1 text-sm font-semibold leading-none text-[#0A1B33]",
        ),
        rx.el.p(
            hint,
            class_name="mt-1 truncate text-[0.65rem] font-medium text-slate-500",
        ),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-white p-2.5",
    )


def _timeline_step(
    label: str, detail: rx.Var | str, done: rx.Var | bool
) -> rx.Component:
    return rx.el.li(
        rx.el.span(
            class_name=rx.cond(
                done,
                "mt-1 size-2 shrink-0 rounded-full bg-teal-600",
                "mt-1 size-2 shrink-0 rounded-full bg-slate-300",
            )
        ),
        rx.el.div(
            rx.el.p(
                label,
                class_name="text-[0.7rem] font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                detail,
                class_name="text-[0.65rem] font-medium leading-relaxed text-slate-500",
            ),
            class_name="min-w-0",
        ),
        class_name="flex items-start gap-2",
    )


def _request_form(row: ReadinessRow) -> rx.Component:
    return rx.el.form(
        rx.el.p(
            "State the purpose of the certificate — the reviewing administrator sees this alongside your evidence snapshot.",
            class_name="text-xs font-medium leading-relaxed text-slate-600",
        ),
        textarea_field(
            "Purpose / justification (30–600 characters)",
            "justification",
            "",
            "e.g. Required for my promotion dossier; the board needs a verifiable certificate number.",
            rows="3",
        ),
        rx.el.div(
            teal_button("Submit request", type="submit"),
            ghost_button(
                "Cancel",
                type="button",
                on_click=TraineeCertificationState.close_request,
            ),
            class_name="flex flex-wrap items-center gap-2",
        ),
        on_submit=TraineeCertificationState.submit_request,
        key=f"cert-request-{row['course_id']}",
        class_name="mt-3 flex w-full flex-col gap-3 rounded-lg border border-teal-200 bg-teal-50/40 p-3",
    )


def _readiness_card(row: ReadinessRow) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.el.div(
                chip(row["code"], "navy"),
                chip(row["enrollment_status"], "teal"),
                rx.cond(
                    row["has_certificate"],
                    chip("Certificate issued", "green"),
                    rx.cond(
                        row["is_eligible"],
                        chip("Eligible", "green"),
                        chip("Evidence incomplete", "amber"),
                    ),
                ),
                class_name="flex flex-wrap items-center gap-2",
            ),
            rx.el.h3(
                row["title"],
                class_name="mt-2 text-sm font-semibold leading-snug text-[#0A1B33]",
            ),
            class_name="min-w-0",
        ),
        rx.el.div(
            _evidence_cell(
                "Resources",
                f"{row['resource_percent']}%",
                f"{row['resource_done']} of {row['resource_total']} completed",
                "book-open",
            ),
            _evidence_cell(
                "Best passed score",
                f"{row['best_score']:.1f}%",
                f"{row['assessments_passed']} of {row['assessments_total']} assessments passed",
                "gauge",
            ),
            _evidence_cell(
                "Assignments",
                f"{row['assignments_percent']}%",
                f"{row['assignments_submitted']} of {row['assignments_total']} submitted · {row['assignments_graded']} graded",
                "clipboard-list",
            ),
            _evidence_cell(
                "Profile completeness",
                f"{row['profile_completion']}%",
                "Institutional record quality",
                "user-check",
            ),
            class_name="mt-3 grid w-full min-w-0 grid-cols-2 gap-2 lg:grid-cols-4",
        ),
        rx.el.div(
            progress_bar(row["resource_percent"]),
            class_name="mt-3",
        ),
        rx.cond(
            row["is_eligible"],
            rx.el.p(
                row["missing_label"],
                class_name="mt-3 text-xs font-semibold text-teal-700",
            ),
            rx.el.div(
                rx.el.p(
                    row["missing_label"],
                    class_name="text-[0.7rem] font-semibold uppercase tracking-wider text-amber-700",
                ),
                rx.el.ul(
                    rx.foreach(
                        row["missing"],
                        lambda item: rx.el.li(
                            rx.icon(
                                "circle-alert",
                                class_name="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600",
                            ),
                            rx.el.span(
                                item,
                                class_name="text-xs font-medium leading-relaxed text-slate-600",
                            ),
                            class_name="flex items-start gap-2",
                        ),
                    ),
                    class_name="mt-1.5 flex flex-col gap-1",
                ),
                class_name="mt-3 w-full rounded-lg border border-amber-200 bg-amber-50/60 p-3",
            ),
        ),
        rx.cond(
            row["has_request"],
            rx.el.div(
                rx.el.div(
                    rx.el.span(
                        row["request_status_label"],
                        class_name="text-xs font-semibold text-[#0A1B33]",
                    ),
                    rx.cond(
                        row["snapshot_eligible"],
                        chip("Snapshot: eligible", "green"),
                        chip("Snapshot: not eligible", "amber"),
                    ),
                    class_name="flex flex-wrap items-center gap-2",
                ),
                rx.el.ul(
                    _timeline_step("Requested", row["requested_at"], True),
                    _timeline_step(
                        "Reviewed",
                        f"{row['reviewed_at']} · {row['reviewer']}",
                        row["request_status"] != "pending",
                    ),
                    _timeline_step(
                        "Issued",
                        rx.cond(
                            row["has_certificate"],
                            row["certificate_number"],
                            "Awaiting the secretariat's issuance step",
                        ),
                        row["has_certificate"],
                    ),
                    class_name="mt-2 flex flex-col gap-2",
                ),
                rx.cond(
                    row["decision_note"],
                    rx.el.p(
                        row["decision_note"],
                        class_name="mt-2 text-xs font-medium leading-relaxed text-slate-600",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    row["snapshot_note"],
                    rx.el.p(
                        f"Evidence at submission · {row['snapshot_note']}",
                        class_name="mt-2 text-[0.65rem] font-medium leading-relaxed text-slate-500",
                    ),
                    rx.fragment(),
                ),
                class_name="mt-3 w-full rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
            ),
            rx.cond(
                row["is_eligible"],
                rx.cond(
                    (TraineeCertificationState.request_open)
                    & (
                        TraineeCertificationState.request_course_id
                        == row["course_id"]
                    ),
                    _request_form(row),
                    rx.el.button(
                        rx.icon("send", class_name="h-3.5 w-3.5"),
                        "Request certificate",
                        on_click=lambda: TraineeCertificationState.open_request(
                            row
                        ),
                        class_name="cc-press mt-3 flex w-fit items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-teal-500",
                    ),
                ),
                rx.el.p(
                    "Requests open automatically once every requirement above is met.",
                    class_name="mt-3 text-[0.7rem] font-medium text-slate-500",
                ),
            ),
        ),
        class_name="cc-fade flex h-full w-full min-w-0 flex-col rounded-xl border border-slate-200 bg-white p-4",
    )


def _readiness_panel() -> rx.Component:
    return panel(
        "Certification readiness & request centre",
        "One auditable place for certificate requests — no spreadsheet chasing, no email follow-ups. Every course below shows the completion evidence the secretariat will see.",
        rx.el.div(
            metric_tile(
                "Ready to request",
                TraineeCertificationState.eligible_count.to_string(),
                "badge-check",
                "All evidence on record",
            ),
            metric_tile(
                "In the queue",
                TraineeCertificationState.pending_count.to_string(),
                "hourglass",
                "Awaiting administrator review",
            ),
            metric_tile(
                "Issued",
                TraineeCertificationState.issued_count.to_string(),
                "award",
                "Numbered and verifiable",
            ),
            metric_tile(
                "Needs work",
                TraineeCertificationState.blocked_count.to_string(),
                "circle-alert",
                "Requirements still outstanding",
            ),
            class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
        ),
        rx.cond(
            TraineeCertificationState.is_loading,
            loading_rows(3),
            rx.cond(
                TraineeCertificationState.readiness.length() > 0,
                rx.el.div(
                    rx.foreach(
                        TraineeCertificationState.readiness, _readiness_card
                    ),
                    class_name="grid w-full min-w-0 grid-cols-1 gap-4 xl:grid-cols-2",
                ),
                empty_block(
                    "No enrolments to certify yet",
                    "Enrol in a course and complete its resources, assessments and assignments to build a certification evidence record.",
                    "badge-check",
                ),
            ),
        ),
        icon="badge-check",
    )


def trainee_certificates_page() -> rx.Component:
    return trainee_page(
        "Certificates",
        "Certificates & certification requests",
        "Numbered certificates with verification codes, plus a transparent request queue backed by a single source of completion evidence.",
        rx.cond(
            TraineeCertificationState.error_message,
            TraineeCertificationState.error_message,
            TraineeAssessmentState.error_message,
        ),
        rx.cond(
            TraineeCertificationState.success_message,
            TraineeCertificationState.success_message,
            TraineeAssessmentState.success_message,
        ),
        rx.cond(
            TraineeAssessmentState.is_loading,
            loading_rows(3),
            rx.cond(
                TraineeAssessmentState.certificates.length() > 0,
                panel(
                    "Issued certificates",
                    "Quote the verification code when an authority validates your certification.",
                    rx.el.div(
                        rx.foreach(
                            TraineeAssessmentState.certificates,
                            _certificate_card,
                        ),
                        class_name="grid w-full min-w-0 grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3",
                    ),
                    icon="award",
                ),
                empty_block(
                    "No certificates yet",
                    "Complete every resource in a course and pass its assessment to earn a certificate record.",
                    "award",
                ),
            ),
        ),
        _readiness_panel(),
    )


# ----------------------------------------------------------------- feedback
def _rating_select(label: str, name: str, value: rx.Var) -> rx.Component:
    return select_field(
        label,
        name,
        rx.foreach(
            TraineeLearningState.rating_options,
            lambda option: rx.el.option(
                option.to_string(), value=option.to_string()
            ),
        ),
        value.to_string(),
    )


def _feedback_form() -> rx.Component:
    return panel(
        "Course feedback",
        "Rate each dimension from 1 to 5 and add at least 20 characters of comments.",
        rx.el.div(
            chip(TraineeLearningState.active_feedback["code"], "navy"),
            rx.el.p(
                TraineeLearningState.active_feedback["title"],
                class_name="truncate text-sm font-semibold text-[#0A1B33]",
            ),
            rx.el.span(
                TraineeLearningState.active_feedback["trainer_name"],
                class_name="text-xs font-medium text-slate-500",
            ),
            class_name="flex min-w-0 flex-wrap items-center gap-2",
        ),
        rx.el.form(
            rx.el.div(
                _rating_select(
                    "Overall",
                    "overall_rating",
                    TraineeLearningState.active_feedback["overall_rating"],
                ),
                _rating_select(
                    "Content",
                    "content_rating",
                    TraineeLearningState.active_feedback["content_rating"],
                ),
                _rating_select(
                    "Trainer",
                    "trainer_rating",
                    TraineeLearningState.active_feedback["trainer_rating"],
                ),
                _rating_select(
                    "Relevance",
                    "relevance_rating",
                    TraineeLearningState.active_feedback["relevance_rating"],
                ),
                class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
            ),
            textarea_field(
                "Comments (minimum 20 characters)",
                "comments",
                TraineeLearningState.active_feedback["comments"],
                "What worked well, what was missing, how applicable was the training?",
                rows="4",
            ),
            textarea_field(
                "Suggestions",
                "suggestions",
                TraineeLearningState.active_feedback["suggestions"],
                "Optional suggestions for the next batch.",
            ),
            rx.el.label(
                rx.el.input(
                    type="checkbox",
                    name="is_anonymous",
                    class_name="size-4 rounded border-slate-300 text-teal-600",
                ),
                rx.el.span(
                    "Submit anonymously",
                    class_name="text-xs font-semibold text-slate-600",
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.div(
                teal_button("Save feedback", type="submit"),
                ghost_button(
                    "Cancel",
                    type="button",
                    on_click=TraineeLearningState.close_feedback,
                ),
                class_name="flex flex-wrap items-center gap-2",
            ),
            on_submit=TraineeLearningState.submit_feedback,
            key=f"feedback-{TraineeLearningState.active_feedback['course_id']}",
            class_name="mt-3 flex w-full flex-col gap-4 rounded-lg border border-slate-200 bg-white p-3",
        ),
        icon="message-square",
    )


def _feedback_card(item: FeedbackCourse) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            chip(item["code"], "navy"),
            rx.cond(
                item["submitted"],
                chip("Submitted", "green"),
                chip("Pending", "amber"),
            ),
            class_name="flex flex-wrap items-center gap-2",
        ),
        rx.el.h3(
            item["title"],
            class_name="mt-3 text-sm font-semibold leading-snug text-[#0A1B33]",
        ),
        rx.el.p(
            item["trainer_name"],
            class_name="mt-0.5 truncate text-xs font-medium text-slate-500",
        ),
        rx.cond(
            item["submitted"],
            rx.el.div(
                rx.el.div(
                    rx.el.span(
                        f"Overall {item['overall_rating']}/5",
                        class_name="text-xs font-semibold text-teal-700",
                    ),
                    rx.el.span(
                        f"Content {item['content_rating']}/5 · Trainer {item['trainer_rating']}/5 · Relevance {item['relevance_rating']}/5",
                        class_name="text-[0.7rem] font-medium text-slate-500",
                    ),
                    class_name="flex flex-col",
                ),
                rx.el.p(
                    item["comments"],
                    class_name="mt-2 line-clamp-3 text-xs font-medium leading-relaxed text-slate-600",
                ),
                rx.el.span(
                    f"Last updated {item['updated']}",
                    class_name="mt-1 block text-[0.65rem] font-medium text-slate-400",
                ),
                class_name="mt-3 w-full rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
            ),
            rx.el.p(
                "No feedback recorded for this completed course yet.",
                class_name="mt-3 text-xs font-medium text-slate-500",
            ),
        ),
        rx.el.button(
            rx.icon("pencil-line", class_name="h-3.5 w-3.5"),
            rx.cond(item["submitted"], "Update feedback", "Give feedback"),
            on_click=lambda: TraineeLearningState.open_feedback(item),
            class_name="mt-3 flex w-fit items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-[#0A1B33] transition-colors hover:border-teal-300 hover:bg-teal-50",
        ),
        class_name="flex h-full w-full min-w-0 flex-col rounded-xl border border-slate-200 bg-white p-4",
    )


def trainee_feedback_page() -> rx.Component:
    return trainee_page(
        "Feedback",
        "Post-course feedback",
        "Feedback opens once a course reaches 100% completion; you can update it any time.",
        TraineeLearningState.error_message,
        TraineeLearningState.success_message,
        rx.cond(
            TraineeLearningState.feedback_open, _feedback_form(), rx.fragment()
        ),
        rx.cond(
            TraineeLearningState.is_loading,
            loading_rows(3),
            rx.cond(
                TraineeLearningState.feedback_courses.length() > 0,
                panel(
                    "Completed courses",
                    "One feedback record per completed course.",
                    rx.el.div(
                        rx.foreach(
                            TraineeLearningState.feedback_courses,
                            _feedback_card,
                        ),
                        class_name="grid w-full min-w-0 grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3",
                    ),
                    icon="message-square",
                ),
                empty_block(
                    "No completed courses yet",
                    "Finish all resources in an enrolled course to unlock its feedback form.",
                    "message-square",
                ),
            ),
        ),
    )

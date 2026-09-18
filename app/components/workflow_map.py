"""Fragmented process → connected workflow map, shared by public and admin."""

from __future__ import annotations

import reflex as rx

# (problem, connected workflow, feature label, feature href)
WORKFLOW_ROWS: list[tuple[str, str, str, str]] = [
    (
        "Training records scattered across spreadsheets and inboxes",
        "One registry holds accounts, courses, enrolments, results and certificates",
        "Course catalogue",
        "/courses",
    ),
    (
        "No traceable proof that a nominated officer finished a course",
        "Enrolment progress, graded results and certificate numbers stay linked to the trainee record",
        "Certification records",
        "/admin/certifications",
    ),
    (
        "Trainer material sits on personal drives and is lost between batches",
        "Trainers upload to a course-scoped library that every enrolled trainee reads from",
        "Trainer library",
        "/admin/courses",
    ),
    (
        "Skills are claimed, never evidenced",
        "Proficiency scores, qualifications and experience are recorded per skill and reused for staffing",
        "Competency mapping",
        "/admin/competency",
    ),
    (
        "Performance problems surface only after a batch ends",
        "Cohort views separate high-performing, at-risk, inactive and incomplete trainees while a course runs",
        "Analytics",
        "/admin/analytics",
    ),
    (
        "Assessment setting and marking is manual",
        "MCQ assessments are authored once, timed, auto-scored and released as results",
        "Assessments",
        "/admin/assessments",
    ),
    (
        "Trainers are picked by availability, not capability",
        "Weighted skill matching ranks approved trainers per course with transparent match scores",
        "Trainer staffing",
        "/admin/trainers",
    ),
    (
        "Notices reach only part of the intended audience",
        "Announcements are published to a chosen audience or course cohort and recorded",
        "Announcements",
        "/announcements",
    ),
    (
        "No single view of institutional capacity",
        "The control centre reads live counts across users, delivery, assessment and certification",
        "Admin oversight",
        "/admin",
    ),
]


def _workflow_row(item: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("unlink", class_name="h-3.5 w-3.5 text-amber-600"),
                rx.el.span(
                    "Fragmented today",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-amber-700",
                ),
                class_name="flex items-center gap-1.5",
            ),
            rx.el.p(
                item[0],
                class_name="mt-1.5 text-xs font-medium leading-relaxed text-slate-600",
            ),
            class_name="min-w-0 flex-1 rounded-[0.875rem] border border-amber-200 bg-amber-50/50 p-3",
        ),
        rx.el.div(
            rx.icon(
                "arrow-right",
                class_name="hidden h-4 w-4 shrink-0 text-slate-400 sm:block",
            ),
            rx.icon(
                "arrow-down",
                class_name="h-4 w-4 shrink-0 text-slate-400 sm:hidden",
            ),
            class_name="flex shrink-0 items-center justify-center",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("link", class_name="h-3.5 w-3.5 text-teal-700"),
                rx.el.span(
                    "Connected in CAPACITY CONNECT",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-teal-700",
                ),
                class_name="flex items-center gap-1.5",
            ),
            rx.el.p(
                item[1],
                class_name="mt-1.5 text-xs font-medium leading-relaxed text-slate-700",
            ),
            rx.el.a(
                rx.el.span(item[2]),
                rx.icon("arrow-up-right", class_name="h-3.5 w-3.5"),
                href=item[3],
                class_name="cc-focus mt-2 flex w-fit items-center gap-1 rounded-lg border border-teal-200 bg-white px-2 py-1 text-[0.7rem] font-semibold text-teal-800 outline-hidden transition-colors duration-200 hover:bg-teal-50",
            ),
            class_name="min-w-0 flex-[1.3] rounded-[0.875rem] border border-teal-200 bg-teal-50/40 p-3",
        ),
        class_name="cc-hover flex w-full min-w-0 flex-col gap-2 rounded-[0.875rem] border border-slate-200 bg-white p-3 sm:flex-row sm:items-stretch",
    )


def workflow_map(metrics: rx.Component) -> rx.Component:
    """Problem → feature map with real registry metrics supplied by the caller."""
    return rx.el.div(
        metrics,
        rx.el.div(
            rx.foreach(WORKFLOW_ROWS, _workflow_row),
            class_name="grid w-full grid-cols-1 gap-3 xl:grid-cols-2",
        ),
        rx.el.p(
            "Every line maps to a feature that already exists in this "
            "registry; the figures above are read live from it.",
            class_name="text-[0.7rem] font-medium text-slate-500",
        ),
        class_name="flex w-full min-w-0 flex-col gap-4",
    )

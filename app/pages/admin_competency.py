"""Competency mapping: weighted skill matrix and ranked trainer comparison."""

from __future__ import annotations

import reflex as rx

from app.components.admin_shell import admin_page
from app.components.trainee_ui import (
    chip,
    empty_block,
    loading_rows,
    metric_tile,
    panel,
    progress_bar,
)
from app.states.admin_competency_state import AdminCompetencyState


def _course_button(course) -> rx.Component:
    return rx.el.button(
        rx.el.div(
            rx.el.span(
                course["code"],
                class_name="text-[0.7rem] font-semibold uppercase tracking-wider",
            ),
            rx.el.span(
                course["status"],
                class_name="text-[0.6rem] font-semibold uppercase tracking-wider opacity-70",
            ),
            class_name="flex items-center justify-between gap-2",
        ),
        rx.el.p(
            course["title"],
            class_name="mt-1 text-left text-xs font-semibold leading-snug",
        ),
        rx.el.p(
            f"{course['skills']} required skills · {course['trainers']} assigned",
            class_name="mt-1 text-left text-[0.65rem] font-medium opacity-80",
        ),
        on_click=lambda: AdminCompetencyState.select_course(course["id"]),
        class_name=rx.cond(
            AdminCompetencyState.selected_course_id == course["id"],
            "w-full min-w-0 rounded-xl border border-teal-500 bg-[#0A1B33] p-3 text-white",
            "w-full min-w-0 rounded-xl border border-slate-200 bg-white p-3 text-slate-700 transition-colors hover:border-teal-300 hover:bg-teal-50/50",
        ),
    )


def _requirement_card(row) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    row["name"],
                    class_name="text-xs font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    row["category"],
                    class_name="text-[0.65rem] font-medium uppercase tracking-wider text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.cond(
                row["mandatory"],
                chip("mandatory", "amber"),
                chip("desirable", "navy"),
            ),
            class_name="flex items-start justify-between gap-2",
        ),
        rx.el.div(
            rx.el.span(
                f"target {row['target']}% · {row['minimum_level']}",
                class_name="text-[0.7rem] font-semibold text-teal-700",
            ),
            rx.el.span(
                f"weight {row['weight']:.1f} ({row['weight_share']}%)",
                class_name="text-[0.7rem] font-medium text-slate-500",
            ),
            class_name="mt-2 flex flex-wrap items-center justify-between gap-2",
        ),
        rx.el.div(progress_bar(row["weight_share"], "navy"), class_name="mt-2"),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def _matrix_cell(cell_data) -> rx.Component:
    return rx.el.div(
        rx.el.p(
            cell_data["name"],
            class_name="truncate text-[0.65rem] font-semibold uppercase tracking-wider",
        ),
        rx.el.div(
            rx.el.span(
                f"{cell_data['score']}%",
                class_name="text-sm font-semibold",
            ),
            rx.el.span(
                f"/ {cell_data['target']}%",
                class_name="text-[0.65rem] font-medium opacity-70",
            ),
            class_name="mt-1 flex items-baseline gap-1",
        ),
        rx.el.p(
            cell_data["level"],
            class_name="truncate text-[0.6rem] font-medium opacity-75",
        ),
        class_name=rx.cond(
            cell_data["met"],
            "w-full min-w-0 rounded-lg border border-teal-300 bg-teal-50 p-2 text-teal-900",
            "w-full min-w-0 rounded-lg border border-amber-300 bg-amber-50 p-2 text-amber-900",
        ),
    )


def _match_card(row, rank: rx.Var) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.el.span(
                        f"#{rank + 1}",
                        class_name="flex size-8 shrink-0 items-center justify-center rounded-lg bg-[#0A1B33] text-xs font-semibold text-white",
                    ),
                    rx.el.div(
                        rx.el.p(
                            row["name"],
                            class_name="truncate text-sm font-semibold text-[#0A1B33]",
                        ),
                        rx.el.p(
                            f"{row['designation']} · {row['department']}",
                            class_name="truncate text-[0.7rem] font-medium text-slate-500",
                        ),
                        class_name="min-w-0",
                    ),
                    class_name="flex min-w-0 items-center gap-3",
                ),
                rx.el.p(
                    row["specialization"],
                    class_name="mt-2 max-w-xl text-[0.7rem] font-medium leading-relaxed text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                rx.el.p(
                    f"{row['score']:.1f}%",
                    class_name="text-2xl font-semibold leading-none text-teal-700",
                ),
                rx.el.p(
                    "weighted match",
                    class_name="mt-1 text-[0.65rem] font-semibold uppercase tracking-wider text-slate-500",
                ),
                class_name="shrink-0 text-right",
            ),
            class_name="flex flex-wrap items-start justify-between gap-4",
        ),
        rx.el.div(progress_bar(row["score"]), class_name="mt-3"),
        rx.el.div(
            chip(
                f"{row['matched_count']} of {row['required_count']} skills met",
                "teal",
            ),
            chip(f"{row['coverage']}% coverage", "navy"),
            chip(f"{row['years']:.1f} yrs training", "navy"),
            chip(f"{row['rating']:.1f}★", "green"),
            chip(f"{row['load']} trainees taught", "navy"),
            rx.cond(
                row["available"],
                chip("available", "green"),
                chip("unavailable", "amber"),
            ),
            rx.cond(
                row["recommended"],
                chip("recommended", "amber"),
                rx.fragment(),
            ),
            rx.cond(
                row["is_assigned"],
                chip(f"assigned · {row['assignment_role']}", "green"),
                rx.fragment(),
            ),
            class_name="mt-3 flex flex-wrap items-center gap-1.5",
        ),
        rx.el.div(
            rx.foreach(row["cells"], _matrix_cell),
            class_name="mt-3 grid w-full grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-4",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    "Matched skills",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-teal-700",
                ),
                rx.cond(
                    row["matched"].length() > 0,
                    rx.el.div(
                        rx.foreach(
                            row["matched"],
                            lambda item: rx.el.li(
                                item,
                                class_name="text-[0.7rem] font-medium text-slate-600",
                            ),
                        ),
                        class_name="mt-1 flex flex-col gap-0.5",
                    ),
                    rx.el.p(
                        "No required skill meets its target level yet.",
                        class_name="mt-1 text-[0.7rem] font-medium text-slate-500",
                    ),
                ),
                class_name="w-full min-w-0 rounded-lg border border-teal-200 bg-teal-50/50 p-3",
            ),
            rx.el.div(
                rx.el.p(
                    "Competency gaps",
                    class_name="text-[0.65rem] font-semibold uppercase tracking-wider text-amber-700",
                ),
                rx.cond(
                    row["gaps"].length() > 0,
                    rx.el.div(
                        rx.foreach(
                            row["gaps"],
                            lambda item: rx.el.li(
                                item,
                                class_name="text-[0.7rem] font-medium text-slate-600",
                            ),
                        ),
                        class_name="mt-1 flex flex-col gap-0.5",
                    ),
                    rx.el.p(
                        "Every required skill is met or exceeded.",
                        class_name="mt-1 text-[0.7rem] font-medium text-slate-500",
                    ),
                ),
                class_name="w-full min-w-0 rounded-lg border border-amber-200 bg-amber-50/50 p-3",
            ),
            class_name="mt-3 grid w-full grid-cols-1 gap-3 md:grid-cols-2",
        ),
        rx.el.div(
            rx.cond(
                row["is_assigned"],
                rx.el.button(
                    rx.icon("user-minus", class_name="h-3.5 w-3.5"),
                    "Remove assignment",
                    on_click=lambda: AdminCompetencyState.remove_assignment(
                        row["trainer_id"]
                    ),
                    class_name="flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-[0.7rem] font-semibold text-red-700 hover:bg-red-100",
                ),
                rx.el.button(
                    rx.icon("user-plus", class_name="h-3.5 w-3.5"),
                    "Assign to this course",
                    on_click=lambda: AdminCompetencyState.assign_trainer(
                        row["trainer_id"]
                    ),
                    class_name="flex items-center gap-1.5 rounded-lg bg-teal-600 px-3 py-2 text-[0.7rem] font-semibold text-white hover:bg-teal-500",
                ),
            ),
            rx.el.span(
                f"Score = Σ(proficiency × weight) ÷ Σ(weight) over {row['required_count']} required skills.",
                class_name="text-[0.65rem] font-medium text-slate-500",
            ),
            class_name="mt-3 flex flex-wrap items-center gap-3",
        ),
        class_name=rx.cond(
            row["recommended"],
            "w-full min-w-0 rounded-xl border-2 border-teal-500 bg-white p-4",
            "w-full min-w-0 rounded-xl border border-slate-200 bg-white p-4",
        ),
    )


def admin_competency_page() -> rx.Component:
    return admin_page(
        "Trainers",
        "Competency matrix and trainer ranking",
        "Select a course, read its weighted skill requirements, then compare every approved trainer's proficiency evidence with a transparent match score.",
        AdminCompetencyState.error_message,
        AdminCompetencyState.success_message,
        rx.el.div(
            metric_tile(
                "Courses mapped",
                AdminCompetencyState.courses.length().to_string(),
                "book-open",
                "In the catalogue",
            ),
            metric_tile(
                "Required skills",
                AdminCompetencyState.required_skills.length().to_string(),
                "grid-3x3",
                f"Total weight {AdminCompetencyState.total_weight:.1f}",
            ),
            metric_tile(
                "Trainers compared",
                AdminCompetencyState.matches.length().to_string(),
                "users",
                "Approved and active",
            ),
            metric_tile(
                "Best match",
                f"{AdminCompetencyState.top_score:.1f}%",
                "trending-up",
                "Highest weighted score",
            ),
            class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
        ),
        panel(
            "Select a course",
            "Mapping runs against the selected course's weighted required skills.",
            rx.cond(
                AdminCompetencyState.courses.length() > 0,
                rx.el.div(
                    rx.foreach(AdminCompetencyState.courses, _course_button),
                    class_name="grid w-full grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3",
                ),
                empty_block(
                    "No courses to map",
                    "Courses appear here once they exist in the catalogue.",
                    "book-open",
                ),
            ),
            icon="list",
        ),
        panel(
            "Weighted skill requirement",
            AdminCompetencyState.selected_course_label,
            rx.cond(
                AdminCompetencyState.is_loading,
                loading_rows(2),
                rx.cond(
                    AdminCompetencyState.required_skills.length() > 0,
                    rx.el.div(
                        rx.foreach(
                            AdminCompetencyState.required_skills,
                            _requirement_card,
                        ),
                        class_name="grid w-full grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4",
                    ),
                    empty_block(
                        "No required skills defined",
                        "Add weighted required skills to this course to enable competency matching.",
                        "grid-3x3",
                    ),
                ),
            ),
            icon="scale",
        ),
        panel(
            "Ranked trainer comparison",
            "Each card shows the trainer's proficiency against every required skill, the matched skills, the gaps and the persisted match score.",
            rx.cond(
                AdminCompetencyState.is_loading,
                loading_rows(3),
                rx.cond(
                    AdminCompetencyState.matches.length() > 0,
                    rx.el.div(
                        rx.foreach(
                            AdminCompetencyState.matches,
                            lambda row, index: _match_card(row, index),
                        ),
                        class_name="flex w-full flex-col gap-4",
                    ),
                    empty_block(
                        "Nothing to rank yet",
                        "Define required skills for the selected course and record trainer proficiency to compute match scores.",
                        "grid-3x3",
                    ),
                ),
            ),
            icon="trophy",
        ),
    )

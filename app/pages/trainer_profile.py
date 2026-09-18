"""Trainer professional expertise profile with qualifications, experience and skills."""

from __future__ import annotations

import reflex as rx

from app.components.trainee_ui import (
    chip,
    empty_block,
    field,
    ghost_button,
    loading_rows,
    panel,
    primary_button,
    progress_bar,
    select_field,
    teal_button,
    textarea_field,
)
from app.components.trainer_shell import trainer_page
from app.states.trainer_state import LEVELS, TrainerState


def _profile_form() -> rx.Component:
    return rx.el.form(
        rx.el.div(
            field(
                "Designation",
                "designation",
                TrainerState.designation,
                "Senior Scientist (Training)",
                required=True,
            ),
            field(
                "Department",
                "department",
                TrainerState.department,
                "Weather Forecasting & Modelling",
            ),
            field(
                "Organization",
                "organization",
                TrainerState.organization,
                "National Institute of Meteorological Training",
            ),
            field(
                "Highest qualification",
                "highest_qualification",
                TrainerState.highest_qualification,
                "Ph.D. Atmospheric Sciences",
            ),
            field(
                "Years of training experience",
                "years_of_training",
                TrainerState.years_of_training.to_string(),
                "12",
                input_type="number",
                step="0.5",
            ),
            field(
                "Languages of instruction",
                "languages",
                TrainerState.languages,
                "English, Hindi",
            ),
            class_name="grid w-full grid-cols-1 gap-4 md:grid-cols-2",
        ),
        field(
            "Specialization",
            "specialization",
            TrainerState.specialization,
            "Numerical weather prediction, satellite meteorology",
        ),
        textarea_field(
            "Professional summary",
            "bio",
            TrainerState.bio,
            "Describe your training focus, programmes led and institutional roles.",
            rows="4",
        ),
        select_field(
            "Availability for new cohorts",
            "is_available",
            rx.fragment(
                rx.el.option("Available", value="available"),
                rx.el.option("Not available", value="unavailable"),
            ),
            rx.cond(TrainerState.is_available, "available", "unavailable"),
        ),
        primary_button(
            "Save expertise profile",
            type="submit",
            disabled=TrainerState.is_loading,
        ),
        on_submit=TrainerState.save_profile,
        class_name="flex w-full min-w-0 flex-col gap-4",
    )


def _qualification_row(row) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                f"{row['degree']} · {row['field_of_study']}",
                class_name="text-sm font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                row["institution"],
                class_name="text-xs font-medium text-slate-600",
            ),
            rx.el.div(
                chip(
                    f"{row['start_year']} – {row['end_year']}",
                    "navy",
                ),
                rx.cond(
                    row["grade"] != "",
                    chip(f"Grade {row['grade']}", "teal"),
                    rx.fragment(),
                ),
                rx.cond(
                    row["verified"],
                    chip("Verified", "green"),
                    chip("Unverified", "amber"),
                ),
                class_name="mt-2 flex flex-wrap items-center gap-2",
            ),
            class_name="min-w-0",
        ),
        rx.el.button(
            rx.icon("trash-2", class_name="h-4 w-4"),
            on_click=lambda: TrainerState.delete_qualification(row["id"]),
            title="Remove qualification",
            class_name="flex size-8 shrink-0 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-500 transition-colors hover:border-red-300 hover:text-red-600",
        ),
        class_name="flex w-full min-w-0 items-start justify-between gap-3 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def _experience_row(row) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                row["role_title"],
                class_name="text-sm font-semibold text-[#0A1B33]",
            ),
            rx.el.p(
                f"{row['organization']} · {row['location']}",
                class_name="text-xs font-medium text-slate-600",
            ),
            rx.el.div(
                chip(
                    f"{row['start_date']} → {row['end_date']}",
                    "navy",
                ),
                rx.cond(
                    row["is_current"],
                    chip("Current role", "green"),
                    rx.fragment(),
                ),
                class_name="mt-2 flex flex-wrap items-center gap-2",
            ),
            rx.cond(
                row["responsibilities"] != "",
                rx.el.p(
                    row["responsibilities"],
                    class_name="mt-2 text-xs font-medium leading-relaxed text-slate-600",
                ),
                rx.fragment(),
            ),
            class_name="min-w-0",
        ),
        rx.el.button(
            rx.icon("trash-2", class_name="h-4 w-4"),
            on_click=lambda: TrainerState.delete_experience(row["id"]),
            title="Remove experience",
            class_name="flex size-8 shrink-0 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-500 transition-colors hover:border-red-300 hover:text-red-600",
        ),
        class_name="flex w-full min-w-0 items-start justify-between gap-3 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def _skill_row(row) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    row["name"],
                    class_name="truncate text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    row["category"],
                    class_name="truncate text-[0.7rem] font-medium uppercase tracking-wider text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                rx.el.span(
                    f"{row['score']}%",
                    class_name="text-sm font-semibold text-teal-700",
                ),
                chip(row["level"], "navy"),
                rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda: TrainerState.delete_skill(row["id"]),
                    title="Remove teachable skill",
                    class_name="flex size-8 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-500 transition-colors hover:border-red-300 hover:text-red-600",
                ),
                class_name="flex shrink-0 items-center gap-2",
            ),
            class_name="flex items-start justify-between gap-3",
        ),
        rx.el.div(progress_bar(row["score"]), class_name="mt-2"),
        rx.el.p(
            f"{row['years']:.1f} yrs of practice · teachable",
            class_name="mt-2 text-[0.7rem] font-medium text-slate-500",
        ),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def trainer_profile_page() -> rx.Component:
    return trainer_page(
        "My Profile",
        "Professional expertise profile",
        "Your designation, credentials, career record and teachable competencies drive course matching and trainee confidence.",
        TrainerState.error_message,
        TrainerState.success_message,
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    "Profile completeness",
                    class_name="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500",
                ),
                rx.el.p(
                    f"{TrainerState.profile_completion}%",
                    class_name="mt-1 text-2xl font-semibold text-[#0A1B33]",
                ),
                progress_bar(TrainerState.profile_completion),
                class_name="w-full min-w-0 rounded-xl border border-slate-200 bg-white p-4",
            ),
            rx.el.div(
                rx.el.p(
                    "Trainee rating",
                    class_name="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500",
                ),
                rx.el.p(
                    f"{TrainerState.rating_average:.1f} / 5",
                    class_name="mt-1 text-2xl font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    f"{TrainerState.rating_count} feedback records",
                    class_name="mt-1 text-xs font-medium text-slate-500",
                ),
                class_name="w-full min-w-0 rounded-xl border border-slate-200 bg-white p-4",
            ),
            rx.el.div(
                rx.el.p(
                    "Teachable skills",
                    class_name="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500",
                ),
                rx.el.p(
                    TrainerState.teachable_count.to_string(),
                    class_name="mt-1 text-2xl font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    "Used for competency matching",
                    class_name="mt-1 text-xs font-medium text-slate-500",
                ),
                class_name="w-full min-w-0 rounded-xl border border-slate-200 bg-white p-4",
            ),
            class_name="grid w-full grid-cols-1 gap-4 md:grid-cols-3",
        ),
        panel(
            "Expertise details",
            "Keep this current — administrators use it when matching trainers to courses.",
            rx.cond(TrainerState.is_loading, loading_rows(3), _profile_form()),
            icon="user-pen",
        ),
        rx.el.div(
            panel(
                "Qualifications",
                "Academic and professional credentials.",
                rx.el.form(
                    rx.el.div(
                        field("Degree", "degree", "", "Ph.D.", required=True),
                        field(
                            "Field of study",
                            "field_of_study",
                            "",
                            "Atmospheric Sciences",
                        ),
                        field(
                            "Institution",
                            "institution",
                            "",
                            "Indian Institute of Tropical Meteorology",
                            required=True,
                        ),
                        field("Grade", "grade", "", "Distinction"),
                        field(
                            "Start year",
                            "start_year",
                            "",
                            "2006",
                            input_type="number",
                        ),
                        field(
                            "End year",
                            "end_year",
                            "",
                            "2011",
                            input_type="number",
                        ),
                        class_name="grid w-full grid-cols-1 gap-4 sm:grid-cols-2",
                    ),
                    teal_button("Add qualification", type="submit"),
                    on_submit=TrainerState.add_qualification,
                    reset_on_submit=True,
                    class_name="flex w-full flex-col gap-4",
                ),
                rx.cond(
                    TrainerState.qualifications.length() > 0,
                    rx.el.div(
                        rx.foreach(
                            TrainerState.qualifications, _qualification_row
                        ),
                        class_name="flex w-full flex-col gap-3",
                    ),
                    empty_block(
                        "No qualifications recorded",
                        "Add your degrees and certifications so trainees can see your credentials.",
                        "graduation-cap",
                    ),
                ),
                icon="graduation-cap",
            ),
            panel(
                "Work experience",
                "Institutional roles and responsibilities.",
                rx.el.form(
                    rx.el.div(
                        field(
                            "Role title",
                            "role_title",
                            "",
                            "Senior Scientist (Training)",
                            required=True,
                        ),
                        field(
                            "Organization",
                            "organization",
                            "",
                            "NIMT",
                            required=True,
                        ),
                        field("Location", "location", "", "New Delhi"),
                        select_field(
                            "Currently in this role",
                            "is_current",
                            rx.fragment(
                                rx.el.option("No", value="past"),
                                rx.el.option("Yes", value="current"),
                            ),
                            "past",
                        ),
                        field(
                            "Start date",
                            "start_date",
                            "",
                            input_type="date",
                            required=True,
                        ),
                        field("End date", "end_date", "", input_type="date"),
                        class_name="grid w-full grid-cols-1 gap-4 sm:grid-cols-2",
                    ),
                    textarea_field(
                        "Responsibilities",
                        "responsibilities",
                        "",
                        "Curriculum design, trainer certification, competency audits.",
                    ),
                    teal_button("Add experience", type="submit"),
                    on_submit=TrainerState.add_experience,
                    reset_on_submit=True,
                    class_name="flex w-full flex-col gap-4",
                ),
                rx.cond(
                    TrainerState.experiences.length() > 0,
                    rx.el.div(
                        rx.foreach(TrainerState.experiences, _experience_row),
                        class_name="flex w-full flex-col gap-3",
                    ),
                    empty_block(
                        "No experience records",
                        "Add your professional roles to complete the expertise dossier.",
                        "briefcase",
                    ),
                ),
                icon="briefcase",
            ),
            class_name="grid w-full grid-cols-1 gap-6 xl:grid-cols-2",
        ),
        panel(
            "Teachable skill proficiency",
            "Add or update a skill — saving an existing skill overwrites its level, score and practice years.",
            rx.el.form(
                rx.el.div(
                    field(
                        "Skill name",
                        "skill_name",
                        "",
                        "Radar Meteorology",
                        required=True,
                    ),
                    field(
                        "Category",
                        "category",
                        "",
                        "Remote Sensing",
                    ),
                    select_field(
                        "Level",
                        "level",
                        rx.foreach(
                            LEVELS,
                            lambda level: rx.el.option(level, value=level),
                        ),
                        "advanced",
                    ),
                    field(
                        "Proficiency score (0–100)",
                        "score",
                        "",
                        "85",
                        input_type="number",
                    ),
                    field(
                        "Years of practice",
                        "years",
                        "",
                        "6",
                        input_type="number",
                        step="0.5",
                    ),
                    class_name="grid w-full grid-cols-1 gap-4 md:grid-cols-3",
                ),
                rx.el.div(
                    teal_button("Save teachable skill", type="submit"),
                    ghost_button(
                        "Reload profile",
                        type="button",
                        on_click=TrainerState.load_profile,
                    ),
                    class_name="flex flex-wrap items-center gap-3",
                ),
                on_submit=TrainerState.save_skill,
                reset_on_submit=True,
                class_name="flex w-full flex-col gap-4",
            ),
            rx.cond(
                TrainerState.skills.length() > 0,
                rx.el.div(
                    rx.foreach(TrainerState.skills, _skill_row),
                    class_name="grid w-full grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3",
                ),
                empty_block(
                    "No teachable skills yet",
                    "Declare the competencies you can deliver so the competency matrix can match you to courses.",
                    "target",
                ),
            ),
            icon="target",
        ),
    )

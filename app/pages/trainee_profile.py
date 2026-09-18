"""Trainee professional profile: details, qualifications, experience, skills."""

from __future__ import annotations

import reflex as rx

from app.components.trainee_shell import trainee_page
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
    skill_meter,
    teal_button,
    textarea_field,
)
from app.states.trainee_state import (
    ExperienceItem,
    QualificationItem,
    SkillMeter,
    TraineeState,
)


def _completion_band() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                "Profile completeness",
                class_name="text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500",
            ),
            rx.el.span(
                f"{TraineeState.profile_completion}%",
                class_name="text-sm font-semibold text-teal-700",
            ),
            class_name="flex items-center justify-between gap-3",
        ),
        rx.el.div(
            progress_bar(TraineeState.profile_completion), class_name="mt-2"
        ),
        rx.el.p(
            "Designation, station, qualifications, experience and skill meters each raise completeness.",
            class_name="mt-2 text-xs font-medium text-slate-500",
        ),
        class_name="w-full rounded-xl border border-slate-200 bg-white p-4",
    )


def _profile_form() -> rx.Component:
    return panel(
        "Professional profile",
        "Institutional posting details used across enrolment, matching and certification.",
        rx.el.form(
            rx.el.div(
                field(
                    "Designation",
                    "designation",
                    TraineeState.profile["designation"],
                    "Assistant Meteorologist",
                    required=True,
                ),
                field(
                    "Department",
                    "department",
                    TraineeState.profile["department"],
                    "Forecasting",
                ),
                field(
                    "Organization",
                    "organization",
                    TraineeState.profile["organization"],
                    "Regional Meteorological Centre",
                ),
                field(
                    "Employee code",
                    "employee_code",
                    TraineeState.profile["employee_code"],
                    "EMP-00421",
                ),
                field(
                    "Station",
                    "station",
                    TraineeState.profile["station"],
                    "Pune observatory",
                    required=True,
                ),
                field(
                    "Region",
                    "region",
                    TraineeState.profile["region"],
                    "Western region",
                ),
                field(
                    "Date of joining",
                    "date_of_joining",
                    TraineeState.profile["date_of_joining"],
                    input_type="date",
                ),
                field(
                    "Total experience (years)",
                    "total_experience_years",
                    TraineeState.profile["total_experience_years"],
                    "4.5",
                    input_type="number",
                    step="0.1",
                ),
                class_name="grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4",
            ),
            rx.el.div(
                textarea_field(
                    "Professional summary",
                    "bio",
                    TraineeState.profile["bio"],
                    "Short summary of your institutional role and focus areas.",
                ),
                textarea_field(
                    "Career goal",
                    "career_goal",
                    TraineeState.profile["career_goal"],
                    "The competency you intend to build next.",
                ),
                class_name="mt-4 grid w-full grid-cols-1 gap-4 lg:grid-cols-2",
            ),
            rx.el.div(
                primary_button("Save profile", type="submit"),
                class_name="mt-4 flex w-full justify-end",
            ),
            on_submit=TraineeState.save_profile,
            key=f"profile-{TraineeState.profile_completion}",
            class_name="w-full",
        ),
        icon="id-card",
    )


def _qualification_row(record: QualificationItem) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    record["degree"],
                    class_name="truncate text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    record["field_of_study"],
                    class_name="truncate text-xs font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.cond(
                record["is_verified"],
                chip("Verified", "green"),
                chip("Unverified", "amber"),
            ),
            class_name="flex items-start justify-between gap-3",
        ),
        rx.el.div(
            rx.el.span(
                record["institution"],
                class_name="truncate text-xs font-medium text-slate-600",
            ),
            rx.el.span(
                f"{record['start_year']} – {record['end_year']}",
                class_name="text-xs font-medium text-slate-500",
            ),
            rx.cond(
                record["grade"] != "",
                chip(record["grade"], "navy"),
                rx.fragment(),
            ),
            class_name="mt-2 flex flex-wrap items-center gap-3",
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("pencil", class_name="h-3.5 w-3.5"),
                "Edit",
                on_click=lambda: TraineeState.edit_qualification(record),
                class_name="flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100",
            ),
            rx.el.button(
                rx.icon("trash-2", class_name="h-3.5 w-3.5"),
                "Remove",
                on_click=lambda: TraineeState.delete_qualification(
                    record["id"]
                ),
                class_name="flex items-center gap-1 rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-100",
            ),
            class_name="mt-3 flex items-center gap-2",
        ),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def _qualifications_panel() -> rx.Component:
    return panel(
        "Qualifications",
        "Degrees and certifications on record for competency verification.",
        rx.el.form(
            rx.el.div(
                field(
                    "Degree / certification",
                    "degree",
                    TraineeState.qualification_form["degree"],
                    "M.Sc. Atmospheric Science",
                    required=True,
                ),
                field(
                    "Field of study",
                    "field_of_study",
                    TraineeState.qualification_form["field_of_study"],
                    "Numerical weather prediction",
                ),
                field(
                    "Institution",
                    "institution",
                    TraineeState.qualification_form["institution"],
                    "University",
                    required=True,
                ),
                field(
                    "Start year",
                    "start_year",
                    TraineeState.qualification_form["start_year"],
                    "2016",
                    input_type="number",
                ),
                field(
                    "End year",
                    "end_year",
                    TraineeState.qualification_form["end_year"],
                    "2018",
                    input_type="number",
                ),
                field(
                    "Grade",
                    "grade",
                    TraineeState.qualification_form["grade"],
                    "First class",
                ),
                class_name="grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3",
            ),
            rx.el.div(
                teal_button(
                    TraineeState.qualification_form_title, type="submit"
                ),
                rx.cond(
                    TraineeState.editing_qualification_id > 0,
                    ghost_button(
                        "Cancel edit",
                        type="button",
                        on_click=TraineeState.cancel_qualification_edit,
                    ),
                    rx.fragment(),
                ),
                class_name="mt-4 flex flex-wrap items-center gap-2",
            ),
            on_submit=TraineeState.save_qualification,
            key=f"qual-{TraineeState.editing_qualification_id}",
            class_name="w-full rounded-lg border border-slate-200 bg-white p-3",
        ),
        rx.cond(
            TraineeState.qualifications.length() > 0,
            rx.el.div(
                rx.foreach(TraineeState.qualifications, _qualification_row),
                class_name="grid w-full grid-cols-1 gap-3 lg:grid-cols-2",
            ),
            empty_block(
                "No qualifications recorded",
                "Add your degrees and certifications to strengthen competency verification.",
                "graduation-cap",
            ),
        ),
        icon="graduation-cap",
    )


def _experience_row(record: ExperienceItem) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    record["role_title"],
                    class_name="truncate text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    record["organization"],
                    class_name="truncate text-xs font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.cond(
                record["is_current"],
                chip("Current", "green"),
                chip("Past", "navy"),
            ),
            class_name="flex items-start justify-between gap-3",
        ),
        rx.el.div(
            rx.el.span(
                record["location"],
                class_name="truncate text-xs font-medium text-slate-600",
            ),
            rx.el.span(
                f"{record['start_date']} → {record['end_date']}",
                class_name="text-xs font-medium text-slate-500",
            ),
            class_name="mt-2 flex flex-wrap items-center gap-3",
        ),
        rx.el.p(
            record["responsibilities"],
            class_name="mt-2 line-clamp-3 text-xs font-medium leading-relaxed text-slate-600",
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("pencil", class_name="h-3.5 w-3.5"),
                "Edit",
                on_click=lambda: TraineeState.edit_experience(record),
                class_name="flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100",
            ),
            rx.el.button(
                rx.icon("trash-2", class_name="h-3.5 w-3.5"),
                "Remove",
                on_click=lambda: TraineeState.delete_experience(record["id"]),
                class_name="flex items-center gap-1 rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-100",
            ),
            class_name="mt-3 flex items-center gap-2",
        ),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def _experience_panel() -> rx.Component:
    return panel(
        "Work experience",
        "Postings and assignments that evidence practical competency.",
        rx.el.form(
            rx.el.div(
                field(
                    "Role title",
                    "role_title",
                    TraineeState.experience_form["role_title"],
                    "Observer",
                    required=True,
                ),
                field(
                    "Organization",
                    "organization",
                    TraineeState.experience_form["organization"],
                    "Regional centre",
                    required=True,
                ),
                field(
                    "Location",
                    "location",
                    TraineeState.experience_form["location"],
                    "Nagpur",
                ),
                field(
                    "Start date",
                    "start_date",
                    TraineeState.experience_form["start_date"],
                    input_type="date",
                    required=True,
                ),
                field(
                    "End date",
                    "end_date",
                    TraineeState.experience_form["end_date"],
                    input_type="date",
                ),
                rx.el.label(
                    rx.el.input(
                        type="checkbox",
                        name="is_current",
                        default_checked=TraineeState.experience_form[
                            "is_current"
                        ],
                        class_name="size-4 rounded border-slate-300 text-teal-600",
                    ),
                    rx.el.span(
                        "This is my current posting",
                        class_name="text-xs font-semibold text-slate-600",
                    ),
                    class_name="mt-6 flex items-center gap-2",
                ),
                class_name="grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3",
            ),
            textarea_field(
                "Responsibilities",
                "responsibilities",
                TraineeState.experience_form["responsibilities"],
                "Key duties, instruments handled, forecasting products owned.",
            ),
            rx.el.div(
                teal_button(TraineeState.experience_form_title, type="submit"),
                rx.cond(
                    TraineeState.editing_experience_id > 0,
                    ghost_button(
                        "Cancel edit",
                        type="button",
                        on_click=TraineeState.cancel_experience_edit,
                    ),
                    rx.fragment(),
                ),
                class_name="mt-4 flex flex-wrap items-center gap-2",
            ),
            on_submit=TraineeState.save_experience,
            key=f"exp-{TraineeState.editing_experience_id}",
            class_name="flex w-full flex-col gap-4 rounded-lg border border-slate-200 bg-white p-3",
        ),
        rx.cond(
            TraineeState.experiences.length() > 0,
            rx.el.div(
                rx.foreach(TraineeState.experiences, _experience_row),
                class_name="grid w-full grid-cols-1 gap-3 lg:grid-cols-2",
            ),
            empty_block(
                "No experience recorded",
                "Add your postings so trainers can calibrate course difficulty.",
                "briefcase",
            ),
        ),
        icon="briefcase",
    )


def _skill_row(skill: SkillMeter) -> rx.Component:
    return rx.el.div(
        skill_meter(skill),
        rx.el.button(
            rx.icon("trash-2", class_name="h-3.5 w-3.5"),
            "Remove skill",
            on_click=lambda: TraineeState.delete_skill(skill["id"]),
            class_name="mt-2 flex w-fit items-center gap-1 rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs font-semibold text-red-700 hover:bg-red-100",
        ),
        class_name="w-full min-w-0",
    )


def _skills_panel() -> rx.Component:
    return panel(
        "Skill meters",
        "Add a skill or resubmit an existing one to update its proficiency score.",
        rx.el.form(
            rx.el.div(
                select_field(
                    "Skill",
                    "skill_id",
                    rx.foreach(
                        TraineeState.skill_catalog,
                        lambda option: rx.el.option(
                            option["name"], value=option["id"].to_string()
                        ),
                    ),
                ),
                select_field(
                    "Proficiency level",
                    "level",
                    rx.foreach(
                        TraineeState.level_options,
                        lambda level: rx.el.option(level, value=level),
                    ),
                ),
                field(
                    "Score (0-100)",
                    "proficiency_score",
                    "50",
                    input_type="number",
                ),
                field(
                    "Years of practice",
                    "years_of_practice",
                    "1",
                    input_type="number",
                    step="0.1",
                ),
                class_name="grid w-full grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4",
            ),
            rx.el.div(
                teal_button("Save skill proficiency", type="submit"),
                class_name="mt-4 flex w-full justify-end",
            ),
            on_submit=TraineeState.save_skill,
            class_name="w-full rounded-lg border border-slate-200 bg-white p-3",
        ),
        rx.cond(
            TraineeState.has_skills,
            rx.el.div(
                rx.foreach(TraineeState.skills, _skill_row),
                class_name="grid w-full grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3",
            ),
            empty_block(
                "Competency matrix is empty",
                "Select a skill from the library, set a score and save it.",
                "grid-3x3",
            ),
        ),
        icon="grid-3x3",
    )


def trainee_profile_page() -> rx.Component:
    return trainee_page(
        "My Profile",
        "Professional profile & competency matrix",
        "Keep your posting details, qualifications, experience and skill meters current.",
        TraineeState.error_message,
        TraineeState.success_message,
        rx.cond(
            TraineeState.is_loading,
            loading_rows(6),
            rx.el.div(
                _completion_band(),
                _profile_form(),
                _skills_panel(),
                _qualifications_panel(),
                _experience_panel(),
                class_name="flex w-full min-w-0 flex-col gap-6",
            ),
        ),
    )

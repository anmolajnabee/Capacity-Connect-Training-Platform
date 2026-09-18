"""My learning: enrolled courses, module library and resource completion."""

from __future__ import annotations

import reflex as rx

from app.components.trainee_shell import trainee_page
from app.components.trainee_ui import (
    chip,
    empty_block,
    loading_rows,
    panel,
    progress_bar,
    status_chip,
)
from app.states.trainee_learning_state import (
    EnrolledCourse,
    ModuleGroup,
    ResourceItem,
    TraineeLearningState,
)


def _enrollment_button(item: EnrolledCourse) -> rx.Component:
    return rx.el.button(
        rx.el.div(
            chip(item["code"], "navy"),
            status_chip(item["status"], item["status_key"] == "completed"),
            class_name="flex flex-wrap items-center gap-2",
        ),
        rx.el.p(
            item["title"],
            class_name="mt-2 line-clamp-2 text-left text-sm font-semibold text-[#0A1B33]",
        ),
        rx.el.p(
            item["trainer_name"],
            class_name="mt-1 truncate text-left text-[0.7rem] font-medium text-slate-500",
        ),
        rx.el.div(
            progress_bar(item["progress"]),
            class_name="mt-2 w-full",
        ),
        rx.el.div(
            rx.el.span(
                f"{item['completed_resources']}/{item['total_resources']} resources",
                class_name="text-[0.7rem] font-medium text-slate-500",
            ),
            rx.el.span(
                f"{item['progress']}%",
                class_name="text-[0.7rem] font-semibold text-teal-700",
            ),
            class_name="mt-1 flex items-center justify-between gap-2",
        ),
        on_click=lambda: TraineeLearningState.select_enrollment(
            item["enrollment_id"]
        ),
        class_name=rx.cond(
            TraineeLearningState.selected_enrollment_id
            == item["enrollment_id"],
            "w-full min-w-0 rounded-lg border-2 border-teal-500 bg-teal-50 p-3 text-left",
            "w-full min-w-0 rounded-lg border border-slate-200 bg-white p-3 text-left transition-colors hover:border-teal-300",
        ),
    )


def _resource_row(resource: ResourceItem) -> rx.Component:
    return rx.el.div(
        rx.el.button(
            rx.cond(
                resource["is_completed"],
                rx.icon("circle-check", class_name="h-5 w-5 text-teal-600"),
                rx.icon("circle", class_name="h-5 w-5 text-slate-400"),
            ),
            on_click=lambda: TraineeLearningState.toggle_resource(
                resource["id"]
            ),
            title="Toggle completion",
            class_name="mt-0.5 shrink-0",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    resource["title"],
                    class_name=rx.cond(
                        resource["is_completed"],
                        "truncate text-sm font-semibold text-slate-500 line-through",
                        "truncate text-sm font-semibold text-[#0A1B33]",
                    ),
                ),
                chip(resource["resource_type"], "navy"),
                class_name="flex min-w-0 flex-wrap items-center gap-2",
            ),
            rx.el.p(
                resource["description"],
                class_name="mt-1 line-clamp-2 text-xs font-medium leading-relaxed text-slate-500",
            ),
            rx.el.div(
                rx.el.span(
                    f"{resource['duration_minutes']} min",
                    class_name="text-[0.7rem] font-medium text-slate-500",
                ),
                rx.cond(
                    resource["external_url"] != "",
                    rx.el.a(
                        "Open resource",
                        rx.icon("external-link", class_name="h-3.5 w-3.5"),
                        href=resource["external_url"],
                        target="_blank",
                        rel="noreferrer",
                        class_name="flex items-center gap-1 text-[0.7rem] font-semibold text-teal-700 hover:text-teal-600",
                    ),
                    rx.fragment(),
                ),
                class_name="mt-1 flex flex-wrap items-center gap-3",
            ),
            class_name="min-w-0 flex-1",
        ),
        class_name="flex w-full min-w-0 items-start gap-3 rounded-lg border border-slate-200 bg-white p-3",
    )


def _module_group(module: ModuleGroup) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.icon("folder-open", class_name="h-4 w-4 text-teal-700"),
                rx.el.p(
                    module["name"],
                    class_name="truncate text-sm font-semibold text-[#0A1B33]",
                ),
                class_name="flex min-w-0 items-center gap-2",
            ),
            rx.el.span(
                f"{module['completed']}/{module['total']} done",
                class_name="shrink-0 text-[0.7rem] font-semibold text-teal-700",
            ),
            class_name="flex items-center justify-between gap-3",
        ),
        rx.el.div(progress_bar(module["percent"]), class_name="mt-2"),
        rx.el.div(
            rx.foreach(module["resources"], _resource_row),
            class_name="mt-3 flex w-full flex-col gap-2",
        ),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def trainee_learning_page() -> rx.Component:
    return trainee_page(
        "My Learning",
        "My learning & module library",
        "Work through structured modules; every completion toggle recalculates your enrolment progress.",
        TraineeLearningState.error_message,
        TraineeLearningState.success_message,
        rx.cond(
            TraineeLearningState.is_loading,
            loading_rows(5),
            rx.cond(
                TraineeLearningState.enrollments.length() > 0,
                rx.el.div(
                    rx.el.div(
                        panel(
                            "My enrolments",
                            "Select a course to open its module library.",
                            rx.el.div(
                                rx.foreach(
                                    TraineeLearningState.enrollments,
                                    _enrollment_button,
                                ),
                                class_name="flex w-full flex-col gap-3",
                            ),
                            icon="book-open",
                        ),
                        class_name="w-full min-w-0 xl:w-[22rem] xl:shrink-0",
                    ),
                    rx.el.div(
                        panel(
                            "Module library",
                            "Documents, datasets, slide decks and recordings per module.",
                            rx.el.div(
                                rx.el.div(
                                    chip(
                                        TraineeLearningState.selected_code,
                                        "navy",
                                    ),
                                    rx.el.p(
                                        TraineeLearningState.selected_title,
                                        class_name="truncate text-sm font-semibold text-[#0A1B33]",
                                    ),
                                    class_name="flex min-w-0 items-center gap-2",
                                ),
                                rx.el.div(
                                    progress_bar(
                                        TraineeLearningState.selected_progress
                                    ),
                                    rx.el.span(
                                        f"{TraineeLearningState.selected_progress}%",
                                        class_name="w-10 shrink-0 text-right text-xs font-semibold text-teal-700",
                                    ),
                                    class_name="mt-2 flex items-center gap-3",
                                ),
                                class_name="w-full rounded-lg border border-slate-200 bg-white p-3",
                            ),
                            rx.cond(
                                TraineeLearningState.has_modules,
                                rx.el.div(
                                    rx.foreach(
                                        TraineeLearningState.modules,
                                        _module_group,
                                    ),
                                    class_name="flex w-full flex-col gap-4",
                                ),
                                empty_block(
                                    "No resources published yet",
                                    "Your trainer has not published module content for this course.",
                                    "library",
                                ),
                            ),
                            icon="library",
                        ),
                        class_name="w-full min-w-0 flex-1",
                    ),
                    class_name="flex w-full min-w-0 flex-col gap-6 xl:flex-row",
                ),
                empty_block(
                    "You have no enrolments yet",
                    "Head to Course discovery to enrol in a published course and unlock its module library.",
                    "compass",
                ),
            ),
        ),
    )


def _resource_course_chip(item: EnrolledCourse) -> rx.Component:
    """Compact course switcher used by the dedicated resources view."""
    return rx.el.button(
        rx.icon("folder", class_name="h-3.5 w-3.5 shrink-0"),
        rx.el.span(item["code"], class_name="whitespace-nowrap"),
        rx.el.span(
            f"{item['completed_resources']}/{item['total_resources']}",
            class_name="rounded-full bg-white/70 px-1.5 text-[0.65rem] font-semibold text-slate-600",
        ),
        on_click=lambda: TraineeLearningState.select_enrollment(
            item["enrollment_id"]
        ),
        title=item["title"],
        class_name=rx.cond(
            TraineeLearningState.selected_enrollment_id
            == item["enrollment_id"],
            "cc-focus flex shrink-0 items-center gap-2 rounded-[0.875rem] border border-teal-500 bg-teal-50 px-3 py-2 text-xs font-semibold text-teal-800 outline-hidden",
            "cc-focus flex shrink-0 items-center gap-2 rounded-[0.875rem] border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 outline-hidden transition-all duration-200 hover:border-teal-300 hover:text-teal-700",
        ),
    )


def trainee_resources_page() -> rx.Component:
    """Learning Resources: the module material library, focused for study."""
    return trainee_page(
        "Learning Resources",
        "Learning resources",
        "Every published document, dataset, slide deck and recording for the courses you are enrolled in, grouped by module.",
        TraineeLearningState.error_message,
        TraineeLearningState.success_message,
        rx.cond(
            TraineeLearningState.is_loading,
            loading_rows(5),
            rx.cond(
                TraineeLearningState.enrollments.length() > 0,
                rx.el.div(
                    panel(
                        "Choose a course",
                        "Switch between your enrolments to browse their published material.",
                        rx.el.div(
                            rx.foreach(
                                TraineeLearningState.enrollments,
                                _resource_course_chip,
                            ),
                            class_name="cc-worknav flex w-full items-center gap-2 overflow-x-auto pb-1",
                        ),
                        rx.el.div(
                            rx.el.div(
                                chip(
                                    TraineeLearningState.selected_code,
                                    "navy",
                                ),
                                rx.el.p(
                                    TraineeLearningState.selected_title,
                                    class_name="truncate text-sm font-semibold text-[#0A1B33]",
                                ),
                                class_name="flex min-w-0 items-center gap-2",
                            ),
                            rx.el.div(
                                progress_bar(
                                    TraineeLearningState.selected_progress
                                ),
                                rx.el.span(
                                    f"{TraineeLearningState.selected_progress}%",
                                    class_name="w-10 shrink-0 text-right text-xs font-semibold text-teal-700",
                                ),
                                class_name="mt-2 flex items-center gap-3",
                            ),
                            class_name="cc-inset w-full p-3",
                        ),
                        icon="compass",
                    ),
                    panel(
                        "Module material",
                        "Marking a resource complete recalculates the progress of the enrolment it belongs to.",
                        rx.cond(
                            TraineeLearningState.has_modules,
                            rx.el.div(
                                rx.foreach(
                                    TraineeLearningState.modules,
                                    _module_group,
                                ),
                                class_name="grid w-full grid-cols-1 gap-4 xl:grid-cols-2",
                            ),
                            empty_block(
                                "No resources published yet",
                                "Your trainer has not published module content for this course.",
                                "library",
                            ),
                        ),
                        icon="library",
                    ),
                    class_name="flex w-full min-w-0 flex-col gap-6",
                ),
                empty_block(
                    "No enrolments yet",
                    "Enrol in a published course from Courses to unlock its learning resources.",
                    "compass",
                ),
            ),
        ),
    )

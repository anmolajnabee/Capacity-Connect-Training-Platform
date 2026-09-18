"""Trainer resource library: grouped material and validated uploads."""

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
    select_field,
    textarea_field,
)
from app.components.trainer_shell import trainer_page
from app.states.trainer_resource_state import TrainerResourceState

UPLOAD_ID = "trainer_resource_upload"


def _dropzone() -> rx.Component:
    return rx.el.div(
        rx.upload.root(
            rx.el.div(
                rx.icon("cloud-upload", class_name="h-7 w-7 text-teal-700"),
                rx.el.p(
                    "Click or drop a file to stage it",
                    class_name="mt-2 text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    TrainerResourceState.allowed_hint,
                    class_name="mt-1 max-w-md text-xs font-medium text-slate-500",
                ),
                class_name="flex flex-col items-center justify-center px-4 py-8 text-center",
            ),
            id=UPLOAD_ID,
            multiple=False,
            max_files=1,
            accept={
                "video/mp4": [".mp4"],
                "video/webm": [".webm"],
                "application/pdf": [".pdf"],
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
                    ".docx"
                ],
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": [
                    ".pptx"
                ],
                "text/plain": [".txt", ".md"],
                "text/csv": [".csv"],
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
                    ".xlsx"
                ],
            },
            on_drop=TrainerResourceState.handle_upload(
                rx.upload_files(upload_id=UPLOAD_ID)
            ),
            class_name="w-full cursor-pointer rounded-lg border-2 border-dashed border-teal-300 bg-teal-50/40 transition-colors hover:bg-teal-50",
        ),
        rx.cond(
            TrainerResourceState.is_uploading,
            rx.el.p(
                "Uploading and validating the file…",
                class_name="text-xs font-medium text-teal-700",
            ),
            rx.fragment(),
        ),
        rx.cond(
            TrainerResourceState.pending_file != "",
            rx.el.div(
                rx.icon("file-check-2", class_name="h-4 w-4 text-green-600"),
                rx.el.p(
                    TrainerResourceState.pending_file,
                    class_name="truncate text-xs font-semibold text-green-700",
                ),
                rx.el.button(
                    "Discard",
                    on_click=TrainerResourceState.clear_pending_file,
                    type="button",
                    class_name="ml-auto text-xs font-semibold text-slate-500 hover:text-red-600",
                ),
                class_name="flex w-full items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3 py-2",
            ),
            rx.fragment(),
        ),
        class_name="flex w-full flex-col gap-3",
    )


def _resource_form() -> rx.Component:
    return rx.el.form(
        rx.el.div(
            select_field(
                "Course",
                "course_id",
                rx.foreach(
                    TrainerResourceState.course_options,
                    lambda option: rx.el.option(
                        option["label"], value=option["id"].to_string()
                    ),
                ),
            ),
            field(
                "Module",
                "module_name",
                "",
                "Module 1 — Fundamentals",
                required=True,
            ),
            field("Title", "title", "", "Model Physics Primer", required=True),
            field(
                "Duration (minutes)",
                "duration_minutes",
                "",
                "45",
                input_type="number",
            ),
            field(
                "External link (optional)",
                "external_url",
                "",
                "https://…",
            ),
            select_field(
                "Visibility",
                "publish",
                rx.fragment(
                    rx.el.option("Publish to trainees", value="publish"),
                    rx.el.option("Keep unpublished", value="draft"),
                ),
                "publish",
            ),
            class_name="grid w-full grid-cols-1 gap-4 md:grid-cols-2",
        ),
        textarea_field(
            "Description / notes",
            "description",
            "",
            "What the trainee should take away from this material.",
        ),
        primary_button(
            "Save resource",
            type="submit",
            disabled=TrainerResourceState.is_uploading,
        ),
        on_submit=TrainerResourceState.create_resource,
        reset_on_submit=True,
        class_name="flex w-full flex-col gap-4",
    )


def _resource_item(item) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    item["title"],
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    item["description"],
                    class_name="mt-0.5 line-clamp-2 text-xs font-medium leading-relaxed text-slate-600",
                ),
                rx.el.div(
                    chip(item["resource_type"], "teal"),
                    chip(f"{item['minutes']} min", "navy"),
                    rx.cond(
                        item["published"],
                        chip("published", "green"),
                        chip("unpublished", "amber"),
                    ),
                    rx.cond(
                        item["is_owner"],
                        chip("your upload", "navy"),
                        chip("co-trainer upload", "navy"),
                    ),
                    class_name="mt-2 flex flex-wrap items-center gap-2",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                rx.cond(
                    item["file_name"] != "",
                    rx.el.a(
                        rx.icon("download", class_name="h-4 w-4"),
                        href=rx.get_upload_url(item["file_name"]),
                        is_external=True,
                        title="Open file",
                        class_name="flex size-8 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-600 hover:border-teal-300 hover:text-teal-700",
                    ),
                    rx.fragment(),
                ),
                rx.el.button(
                    rx.cond(
                        item["published"],
                        rx.icon("eye-off", class_name="h-4 w-4"),
                        rx.icon("eye", class_name="h-4 w-4"),
                    ),
                    on_click=lambda: TrainerResourceState.toggle_publish(
                        item["id"]
                    ),
                    title="Publish / unpublish",
                    class_name="flex size-8 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-600 hover:border-teal-300 hover:text-teal-700",
                ),
                rx.el.button(
                    rx.icon("trash-2", class_name="h-4 w-4"),
                    on_click=lambda: TrainerResourceState.delete_resource(
                        item["id"]
                    ),
                    title="Delete resource",
                    class_name="flex size-8 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-500 hover:border-red-300 hover:text-red-600",
                ),
                class_name="flex shrink-0 items-center gap-2",
            ),
            class_name="flex items-start justify-between gap-3",
        ),
        class_name="w-full min-w-0 rounded-lg border border-slate-200 bg-[#FBFAF7] p-3",
    )


def _group(group) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    group["course_code"],
                    class_name="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-teal-700",
                ),
                rx.el.p(
                    group["course_title"],
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    group["module"],
                    class_name="text-xs font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            chip(f"{group['count']} items", "navy"),
            class_name="flex items-start justify-between gap-3 border-b border-slate-200 pb-3",
        ),
        rx.el.div(
            rx.foreach(group["items"], _resource_item),
            class_name="mt-3 flex w-full flex-col gap-3",
        ),
        class_name="w-full min-w-0 rounded-xl border border-slate-200 bg-white p-4",
    )


def _library_stats() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                "Library items",
                class_name="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500",
            ),
            rx.el.p(
                TrainerResourceState.total_resources.to_string(),
                class_name="mt-1 text-2xl font-semibold text-[#0A1B33]",
            ),
            class_name="w-full rounded-xl border border-slate-200 bg-white p-4",
        ),
        rx.el.div(
            rx.el.p(
                "Published",
                class_name="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500",
            ),
            rx.el.p(
                TrainerResourceState.published_count.to_string(),
                class_name="mt-1 text-2xl font-semibold text-teal-700",
            ),
            class_name="w-full rounded-xl border border-slate-200 bg-white p-4",
        ),
        rx.el.div(
            rx.el.p(
                "Module groups",
                class_name="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500",
            ),
            rx.el.p(
                TrainerResourceState.groups.length().to_string(),
                class_name="mt-1 text-2xl font-semibold text-[#0A1B33]",
            ),
            class_name="w-full rounded-xl border border-slate-200 bg-white p-4",
        ),
        class_name="grid w-full grid-cols-1 gap-4 md:grid-cols-3",
    )


def _upload_panel() -> rx.Component:
    return panel(
        "Upload new material",
        "Stage a file, then record its module, title and visibility. Uploads are checked for format structure, content and size; SHA-256 integrity metadata is recorded.",
        rx.cond(
            TrainerResourceState.has_courses,
            rx.el.div(
                _dropzone(),
                _resource_form(),
                class_name="grid w-full grid-cols-1 gap-6 xl:grid-cols-[1fr_1.4fr]",
            ),
            empty_block(
                "No assigned courses",
                "You can only upload material to courses you are assigned to teach.",
                "presentation",
            ),
        ),
        icon="upload",
    )


def _library_panel() -> rx.Component:
    return panel(
        "Library by course and module",
        "Only material for your assigned courses is shown; deletion is restricted to your own uploads.",
        rx.cond(
            TrainerResourceState.is_loading,
            loading_rows(3),
            rx.cond(
                TrainerResourceState.groups.length() > 0,
                rx.el.div(
                    rx.foreach(TrainerResourceState.groups, _group),
                    class_name="grid w-full grid-cols-1 gap-5 xl:grid-cols-2",
                ),
                empty_block(
                    "The library is empty",
                    "Upload your first module resource to give the cohort something to study.",
                    "library",
                ),
            ),
        ),
        rx.el.div(
            ghost_button(
                "Refresh library",
                on_click=TrainerResourceState.load_library,
            ),
            class_name="flex w-full justify-end",
        ),
        icon="library",
    )


def trainer_library_page() -> rx.Component:
    return trainer_page(
        "Trainer Library",
        "Trainer library",
        "Every video, PDF, slide deck, dataset and note published into the modules of the courses you teach.",
        TrainerResourceState.error_message,
        TrainerResourceState.success_message,
        _library_stats(),
        _library_panel(),
        rx.el.div(
            rx.el.a(
                rx.icon("cloud-upload", class_name="h-4 w-4"),
                rx.el.span("Upload new content"),
                href="/trainer/upload",
                class_name="cc-focus-amber flex w-fit items-center gap-2 rounded-[0.875rem] border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-800 outline-hidden transition-all duration-200 hover:bg-amber-100",
            ),
            class_name="flex w-full",
        ),
    )


def trainer_upload_page() -> rx.Component:
    return trainer_page(
        "Upload Content",
        "Upload content",
        "Stage a file, describe it, then publish it into a module of one of your assigned courses.",
        TrainerResourceState.error_message,
        TrainerResourceState.success_message,
        _library_stats(),
        _upload_panel(),
        rx.el.div(
            rx.el.a(
                rx.icon("library", class_name="h-4 w-4"),
                rx.el.span("Review the trainer library"),
                href="/trainer/library",
                class_name="cc-focus-amber flex w-fit items-center gap-2 rounded-[0.875rem] border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-800 outline-hidden transition-all duration-200 hover:bg-amber-100",
            ),
            class_name="flex w-full",
        ),
    )

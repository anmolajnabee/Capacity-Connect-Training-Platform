"""Announcement publishing: create, edit, publish, unpublish and delete."""

from __future__ import annotations

import reflex as rx

from app.components.admin_shell import (
    admin_page,
    filter_select,
    status_pill,
)
from app.components.trainee_ui import (
    chip,
    empty_block,
    field,
    ghost_button,
    loading_rows,
    metric_tile,
    panel,
    select_field,
    teal_button,
    textarea_field,
)
from app.states.admin_announcement_state import AdminAnnouncementState
from app.components.email_ledger import email_ledger


def _audience_options() -> rx.Component:
    return rx.foreach(
        AdminAnnouncementState.audience_options,
        lambda option: rx.el.option(option, value=option),
    )


def _course_options() -> rx.Component:
    return rx.fragment(
        rx.el.option("Organization-wide (no course)", value="0"),
        rx.foreach(
            AdminAnnouncementState.course_choices,
            lambda choice: rx.el.option(
                choice["label"], value=choice["id"].to_string()
            ),
        ),
    )


def _checkbox(label: str, name: str, checked: bool = False) -> rx.Component:
    return rx.el.label(
        rx.el.input(
            type="checkbox",
            name=name,
            default_checked=checked,
            class_name="size-4 rounded border-slate-300 text-teal-600",
        ),
        rx.el.span(
            label,
            class_name="text-xs font-semibold text-slate-600",
        ),
        class_name="flex w-fit items-center gap-2",
    )


def _create_form() -> rx.Component:
    return rx.el.form(
        rx.el.div(
            field(
                "Title", "title", placeholder="Notice headline", required=True
            ),
            select_field("Audience", "audience", _audience_options()),
            class_name="grid w-full grid-cols-1 gap-3 md:grid-cols-2",
        ),
        textarea_field(
            "Body",
            "body",
            placeholder="What should this audience know and by when?",
            rows="4",
        ),
        rx.el.div(
            select_field("Linked course", "course_id", _course_options()),
            field(
                "Publication date",
                "published_at",
                default_value=AdminAnnouncementState.today_input,
                input_type="date",
            ),
            field("Expiry date (optional)", "expires_at", input_type="date"),
            class_name="grid w-full grid-cols-1 gap-3 md:grid-cols-3",
        ),
        rx.el.div(
            _checkbox("Pin to the top", "is_pinned"),
            _checkbox("Publish immediately", "publish_now", True),
            class_name="flex flex-wrap items-center gap-5",
        ),
        teal_button("Create notice", type="submit"),
        on_submit=AdminAnnouncementState.create_notice,
        reset_on_submit=True,
        class_name="flex w-full flex-col gap-4",
    )


def _edit_form(row) -> rx.Component:
    return rx.el.form(
        rx.el.div(
            field(
                "Title",
                "title",
                default_value=row["title"],
                required=True,
            ),
            select_field(
                "Audience",
                "audience",
                _audience_options(),
                default_value=row["audience"],
            ),
            class_name="grid w-full grid-cols-1 gap-3 md:grid-cols-2",
        ),
        textarea_field("Body", "body", default_value=row["body"], rows="4"),
        rx.el.div(
            select_field(
                "Linked course",
                "course_id",
                _course_options(),
                default_value=row["course_id"].to_string(),
            ),
            field(
                "Publication date",
                "published_at",
                default_value=row["published_input"],
                input_type="date",
            ),
            field(
                "Expiry date (optional)",
                "expires_at",
                default_value=row["expires_input"],
                input_type="date",
            ),
            class_name="grid w-full grid-cols-1 gap-3 md:grid-cols-3",
        ),
        _checkbox("Pin to the top", "is_pinned", row["is_pinned"]),
        rx.el.div(
            teal_button("Save changes", type="submit"),
            ghost_button(
                "Cancel",
                type="button",
                on_click=AdminAnnouncementState.cancel_edit,
            ),
            class_name="flex flex-wrap items-center gap-2",
        ),
        on_submit=lambda form_data: AdminAnnouncementState.update_notice(
            row["id"], form_data
        ),
        class_name="mt-3 flex w-full flex-col gap-4 rounded-lg border border-slate-200 bg-[#FBFAF7] p-4",
    )


def _notice_card(row) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    row["title"],
                    class_name="text-sm font-semibold text-[#0A1B33]",
                ),
                rx.el.p(
                    row["course_label"],
                    class_name="mt-0.5 text-[0.7rem] font-medium text-slate-500",
                ),
                class_name="min-w-0",
            ),
            rx.el.div(
                chip(row["audience"], "teal"),
                rx.cond(
                    row["is_published"],
                    status_pill("published"),
                    status_pill("draft"),
                ),
                rx.cond(
                    row["is_pinned"],
                    chip("pinned", "amber"),
                    rx.fragment(),
                ),
                class_name="flex flex-wrap items-center gap-1.5",
            ),
            class_name="flex flex-wrap items-start justify-between gap-3",
        ),
        rx.el.p(
            row["body"],
            class_name="mt-2 text-xs font-medium leading-relaxed text-slate-600",
        ),
        rx.el.div(
            rx.el.span(
                f"Published · {row['published_display']}",
                class_name="text-[0.65rem] font-medium text-slate-500",
            ),
            rx.el.span(
                f"Expires · {row['expires_display']}",
                class_name="text-[0.65rem] font-medium text-slate-500",
            ),
            rx.el.span(
                f"By {row['author']}",
                class_name="text-[0.65rem] font-medium text-slate-500",
            ),
            class_name="mt-2 flex flex-wrap items-center gap-3",
        ),
        rx.el.div(
            rx.el.button(
                rx.icon("pencil", class_name="h-3.5 w-3.5"),
                "Edit",
                on_click=lambda: AdminAnnouncementState.start_edit(row["id"]),
                class_name="flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-[0.7rem] font-semibold text-slate-700 hover:bg-slate-100",
            ),
            rx.cond(
                row["is_published"],
                rx.el.button(
                    rx.icon("eye-off", class_name="h-3.5 w-3.5"),
                    "Unpublish",
                    on_click=lambda: AdminAnnouncementState.set_published(
                        row["id"], False
                    ),
                    class_name="flex items-center gap-1 rounded-lg border border-amber-300 bg-amber-50 px-2.5 py-1.5 text-[0.7rem] font-semibold text-amber-800 hover:bg-amber-100",
                ),
                rx.el.button(
                    rx.icon("send", class_name="h-3.5 w-3.5"),
                    "Publish",
                    on_click=lambda: AdminAnnouncementState.set_published(
                        row["id"], True
                    ),
                    class_name="flex items-center gap-1 rounded-lg bg-teal-600 px-2.5 py-1.5 text-[0.7rem] font-semibold text-white hover:bg-teal-500",
                ),
            ),
            rx.el.button(
                rx.icon("trash-2", class_name="h-3.5 w-3.5"),
                "Delete",
                on_click=lambda: AdminAnnouncementState.delete_notice(
                    row["id"]
                ),
                class_name="flex items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-2.5 py-1.5 text-[0.7rem] font-semibold text-red-700 hover:bg-red-100",
            ),
            class_name="mt-3 flex flex-wrap items-center gap-2",
        ),
        rx.cond(
            AdminAnnouncementState.editing_id == row["id"],
            _edit_form(row),
            rx.fragment(),
        ),
        class_name="w-full min-w-0 rounded-xl border border-slate-200 bg-white p-4",
    )


def admin_announcements_page() -> rx.Component:
    return admin_page(
        "Announcements",
        "Announcement publishing",
        "Compose notices for a role audience or a specific course cohort, with publication and expiry date validation.",
        AdminAnnouncementState.error_message,
        AdminAnnouncementState.success_message,
        rx.el.div(
            metric_tile(
                "Notices",
                AdminAnnouncementState.notices.length().to_string(),
                "megaphone",
                "All records",
            ),
            metric_tile(
                "Published",
                AdminAnnouncementState.published_count.to_string(),
                "send",
                "Visible to audiences",
            ),
            metric_tile(
                "Unpublished",
                AdminAnnouncementState.draft_count.to_string(),
                "eye-off",
                "Held back from readers",
            ),
            metric_tile(
                "Linkable courses",
                AdminAnnouncementState.course_choices.length().to_string(),
                "book-open",
                "Available for targeting",
            ),
            class_name="grid w-full grid-cols-2 gap-4 lg:grid-cols-4",
        ),
        panel(
            "Compose a notice",
            "The expiry date must fall after the publication date; the body needs at least 20 characters.",
            _create_form(),
            icon="pen-line",
        ),
        panel(
            "Published register",
            "Filter by audience, then edit, publish, unpublish or delete any notice.",
            rx.el.div(
                filter_select(
                    AdminAnnouncementState.audience_filters,
                    AdminAnnouncementState.audience_filter,
                    AdminAnnouncementState.set_audience_filter,
                ),
                class_name="flex w-full flex-col gap-3 sm:flex-row sm:items-center",
            ),
            rx.cond(
                AdminAnnouncementState.is_loading,
                loading_rows(3),
                rx.cond(
                    AdminAnnouncementState.filtered_notices.length() > 0,
                    rx.el.div(
                        rx.foreach(
                            AdminAnnouncementState.filtered_notices,
                            _notice_card,
                        ),
                        class_name="flex w-full flex-col gap-4",
                    ),
                    empty_block(
                        "No notices for this audience",
                        "Compose a notice above or clear the audience filter.",
                        "megaphone",
                    ),
                ),
            ),
            icon="megaphone",
        ),
        email_ledger(),
    )

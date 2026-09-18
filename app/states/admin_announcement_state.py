"""Announcement publishing for the admin control centre."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import select, func
from app.models import EmailDelivery
from app.services.email_notifications import (
    enqueue,
    dispatch_pending,
    retry_delivery,
    sender_configuration,
    safe_log,
    publication_due,
)

from app.models import (
    Announcement,
    AnnouncementAudience,
    Course,
    User,
)
from app.states.admin_state import admin_guard, stamp

logger = logging.getLogger(__name__)

AUDIENCES: list[str] = [
    AnnouncementAudience.ALL.value,
    AnnouncementAudience.TRAINEES.value,
    AnnouncementAudience.TRAINERS.value,
    AnnouncementAudience.ADMINS.value,
]


def _parse_date(value: str) -> dt.datetime | None:
    text = value.strip()
    if not text:
        return None
    return dt.datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=dt.UTC)


def _date_input(value: dt.datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d")


class NoticeRow(TypedDict):
    id: int
    title: str
    body: str
    audience: str
    course_id: int
    course_label: str
    author: str
    is_pinned: bool
    is_published: bool
    published_display: str
    expires_display: str
    published_input: str
    expires_input: str


class CourseChoice(TypedDict):
    id: int
    label: str


class AdminAnnouncementState(rx.State):
    email_loading: bool = False
    email_message: str = ""
    email_configuration: str = "Not checked"
    delivery_records: list[dict[str, str]] = []
    delivery_metrics: dict[str, int] = {
        "pending": 0,
        "sending": 0,
        "accepted": 0,
        "retry": 0,
        "blocked": 0,
        "failed": 0,
    }
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    notices: list[NoticeRow] = []
    course_choices: list[CourseChoice] = []
    audience_filter: str = "All"
    editing_id: int = 0

    @rx.var
    def audience_options(self) -> list[str]:
        return AUDIENCES

    @rx.var
    def audience_filters(self) -> list[str]:
        return ["All"] + AUDIENCES

    @rx.var
    def today_input(self) -> str:
        return dt.date.today().strftime("%Y-%m-%d")

    @rx.var
    def filtered_notices(self) -> list[NoticeRow]:
        if self.audience_filter == "All":
            return self.notices
        return [
            row
            for row in self.notices
            if row["audience"] == self.audience_filter
        ]

    @rx.var
    def published_count(self) -> int:
        return len([row for row in self.notices if row["is_published"]])

    @rx.var
    def draft_count(self) -> int:
        return len([row for row in self.notices if not row["is_published"]])

    @rx.event
    def set_audience_filter(self, value: str):
        self.audience_filter = value

    @rx.event
    def start_edit(self, notice_id: int):
        self.editing_id = notice_id
        self.error_message = ""
        self.success_message = ""

    @rx.event
    def cancel_edit(self):
        self.editing_id = 0

    @rx.event
    async def load_announcements(self):
        self.error_message = ""
        if await admin_guard(self) == 0:
            self.error_message = "Administrator access is required."
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load(session)
        except Exception as exception:
            logging.exception(f"Error loading announcements: {exception}")
            self.error_message = "Could not load announcements."
        self.is_loading = False
        yield AdminAnnouncementState.load_email_delivery

    @rx.event
    async def load_email_delivery(self):
        self.delivery_records = []
        if await admin_guard(self) == 0:
            self.email_message = "Administrator access required."
            return
        self.email_loading = True
        yield
        try:
            async with rx.asession() as session:
                counts = (
                    await session.execute(
                        select(EmailDelivery.status, func.count()).group_by(
                            EmailDelivery.status
                        )
                    )
                ).all()
                self.delivery_metrics = {
                    key: 0
                    for key in (
                        "pending",
                        "sending",
                        "accepted",
                        "retry",
                        "blocked",
                        "failed",
                    )
                }
                for status, count in counts:
                    self.delivery_metrics[status] = count
                rows = (
                    await session.scalars(
                        select(EmailDelivery)
                        .order_by(EmailDelivery.id.desc())
                        .limit(50)
                    )
                ).all()
                self.delivery_records = [
                    {
                        "id": str(row.id),
                        "event": row.event_type,
                        "recipient": row.recipient_email,
                        "status": row.status,
                        "attempts": str(row.attempt_count),
                        "scheduled": stamp(row.scheduled_at),
                        "accepted": stamp(row.accepted_at),
                        "error": row.last_error_category
                        if row.last_error_category
                        in (
                            "sender_domain_unverified",
                            "provider_configuration",
                            "provider_validation",
                            "provider_unavailable",
                            "rate_limited",
                            "recipient_ineligible",
                            "acceptance_unknown",
                        )
                        else "",
                    }
                    for row in rows
                ]
            _, self.email_configuration = await sender_configuration()
        except Exception:
            logging.exception("Unexpected error")
            safe_log("delivery_ledger_failed")
            self.email_message = "Could not load email delivery records."
        self.email_loading = False

    @rx.event
    async def retry_email_delivery(self, delivery_id: str):
        uid = await admin_guard(self)
        if not uid:
            self.email_message = "Administrator access required."
            return
        try:
            async with rx.asession() as session:
                changed = await retry_delivery(session, uid, int(delivery_id))
                await session.commit()
            self.email_message = (
                "Queued for retry."
                if changed
                else "This record cannot be retried. Unknown acceptance requires reconciliation."
            )
        except Exception:
            logging.exception("Unexpected error")
            safe_log("delivery_retry_failed")
            self.email_message = "Could not retry this record."
        return AdminAnnouncementState.load_email_delivery

    @rx.event
    async def dispatch_pending_email(self):
        if await admin_guard(self) == 0:
            self.email_message = "Administrator access required."
            return
        if self.email_loading:
            return
        self.email_loading = True
        yield
        try:
            count = await dispatch_pending()
            self.email_message = (
                f"Processed {count} records. Review statuses below."
            )
        except Exception:
            logging.exception("Unexpected error")
            safe_log("manual_dispatch_failed")
            self.email_message = (
                "Processing unavailable. Queued records remain saved."
            )
        self.email_loading = False
        yield AdminAnnouncementState.load_email_delivery

    async def _load(self, session) -> None:
        courses = (
            await session.execute(select(Course).order_by(Course.code))
        ).scalars()
        self.course_choices = [
            {"id": course.id, "label": f"{course.code} · {course.title}"}
            for course in courses
        ]
        labels = {
            choice["id"]: choice["label"] for choice in self.course_choices
        }
        rows = (
            await session.execute(
                select(Announcement).order_by(
                    Announcement.is_pinned.desc(),
                    Announcement.created_at.desc(),
                )
            )
        ).scalars()
        notices: list[NoticeRow] = []
        for notice in rows:
            author = ""
            if notice.author_id:
                author = (
                    await session.scalar(
                        select(User.full_name).where(
                            User.id == notice.author_id
                        )
                    )
                    or ""
                )
            notices.append(
                {
                    "id": notice.id,
                    "title": notice.title,
                    "body": notice.body,
                    "audience": notice.audience,
                    "course_id": notice.course_id or 0,
                    "course_label": labels.get(
                        notice.course_id or 0, "Organization-wide"
                    ),
                    "author": author or "Control centre",
                    "is_pinned": bool(notice.is_pinned),
                    "is_published": bool(notice.is_published),
                    "published_display": stamp(notice.published_at),
                    "expires_display": stamp(notice.expires_at),
                    "published_input": _date_input(notice.published_at),
                    "expires_input": _date_input(notice.expires_at),
                }
            )
        self.notices = notices

    def _validate(self, form_data: dict[str, Any]) -> str:
        title = str(form_data.get("title", "")).strip()
        body = str(form_data.get("body", "")).strip()
        audience = str(form_data.get("audience", "")).strip()
        if len(title) < 6:
            return "Give the notice a title of at least 6 characters."
        if len(body) < 20:
            return "The notice body should be at least 20 characters."
        if audience not in AUDIENCES:
            return "Choose a valid audience."
        try:
            published = _parse_date(str(form_data.get("published_at", "")))
            expires = _parse_date(str(form_data.get("expires_at", "")))
        except ValueError:
            return "Dates must be valid calendar dates."
        if published is None:
            return "Choose a publication date."
        if str(
            form_data.get("publish_now", "")
        ) == "on" and not publication_due(published):
            return "Publish immediately requires today or an earlier date. Save future notices as unpublished drafts."
        if expires is not None and expires <= published:
            return "The expiry date must fall after the publication date."
        return ""

    @rx.event
    async def create_notice(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        admin_id = await admin_guard(self)
        if admin_id == 0:
            self.error_message = (
                "Only an approved administrator may publish notices."
            )
            return
        problem = self._validate(form_data)
        if problem:
            self.error_message = problem
            return
        try:
            async with rx.asession() as session:
                course_raw = str(form_data.get("course_id", "0")).strip()
                notice = Announcement(
                    title=str(form_data.get("title", "")).strip(),
                    body=str(form_data.get("body", "")).strip(),
                    audience=str(form_data.get("audience", "")).strip(),
                    course_id=int(course_raw)
                    if course_raw.isdigit() and course_raw != "0"
                    else None,
                    author_id=admin_id,
                    is_pinned=str(form_data.get("is_pinned", "")) == "on",
                    is_published=str(form_data.get("publish_now", "")) == "on",
                    published_at=_parse_date(
                        str(form_data.get("published_at", ""))
                    ),
                    expires_at=_parse_date(
                        str(form_data.get("expires_at", ""))
                    ),
                )
                session.add(notice)
                await session.flush()
                if notice.is_published:
                    await enqueue(session, "announcement_published", notice)
                await session.commit()
        except Exception as exception:
            logging.exception(f"Error creating announcement: {exception}")
            self.error_message = "Could not create that notice. Try again."
            return
        self.success_message = "Notice created."
        return AdminAnnouncementState.load_announcements

    @rx.event
    async def update_notice(self, notice_id: int, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        admin_id = await admin_guard(self)
        if admin_id == 0:
            self.error_message = (
                "Only an approved administrator may edit notices."
            )
            return
        problem = self._validate(form_data)
        if problem:
            self.error_message = problem
            return
        try:
            async with rx.asession() as session:
                notice = await session.get(Announcement, notice_id)
                if notice is None:
                    self.error_message = "That notice no longer exists."
                    return
                course_raw = str(form_data.get("course_id", "0")).strip()
                notice.title = str(form_data.get("title", "")).strip()
                notice.body = str(form_data.get("body", "")).strip()
                notice.audience = str(form_data.get("audience", "")).strip()
                notice.course_id = (
                    int(course_raw)
                    if course_raw.isdigit() and course_raw != "0"
                    else None
                )
                notice.is_pinned = str(form_data.get("is_pinned", "")) == "on"
                notice.published_at = _parse_date(
                    str(form_data.get("published_at", ""))
                )
                notice.expires_at = _parse_date(
                    str(form_data.get("expires_at", ""))
                )
                if not publication_due(notice.published_at):
                    notice.is_published = False
                await session.commit()
        except Exception as exception:
            logging.exception(f"Error updating announcement: {exception}")
            self.error_message = "Could not save that notice. Try again."
            return
        self.editing_id = 0
        self.success_message = "Notice updated. Future-dated notices remain unpublished until manually published."
        return AdminAnnouncementState.load_announcements

    @rx.event
    async def set_published(self, notice_id: int, publish: bool):
        self.error_message = ""
        self.success_message = ""
        if await admin_guard(self) == 0:
            self.error_message = (
                "Only an approved administrator may publish notices."
            )
            return
        try:
            async with rx.asession() as session:
                notice = await session.get(Announcement, notice_id)
                if notice is None:
                    self.error_message = "That notice no longer exists."
                    return
                if (
                    publish
                    and notice.published_at is not None
                    and not publication_due(notice.published_at)
                ):
                    notice.is_published = False
                    await session.commit()
                    self.error_message = "Future-dated notices must remain unpublished. Publish manually when the date arrives."
                    await self._load(session)
                    return
                newly_published = publish and not notice.is_published
                notice.is_published = publish
                if publish and notice.published_at is None:
                    notice.published_at = dt.datetime.now(dt.UTC)
                if newly_published:
                    await enqueue(session, "announcement_published", notice)
                await session.commit()
        except Exception as exception:
            logging.exception(f"Error publishing announcement: {exception}")
            self.error_message = "Could not change that notice. Try again."
            return
        self.success_message = (
            "Notice published." if publish else "Notice unpublished."
        )
        return AdminAnnouncementState.load_announcements

    @rx.event
    async def delete_notice(self, notice_id: int):
        self.error_message = ""
        self.success_message = ""
        if await admin_guard(self) == 0:
            self.error_message = (
                "Only an approved administrator may delete notices."
            )
            return
        try:
            async with rx.asession() as session:
                notice = await session.get(Announcement, notice_id)
                if notice is None:
                    self.error_message = "That notice no longer exists."
                    return
                await session.delete(notice)
                await session.commit()
        except Exception as exception:
            logging.exception(f"Error deleting announcement: {exception}")
            self.error_message = "Could not delete that notice. Try again."
            return
        self.editing_id = 0
        self.success_message = "Notice deleted."
        return AdminAnnouncementState.load_announcements

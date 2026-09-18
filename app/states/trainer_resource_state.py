"""Trainer resource library: uploads, metadata, publish and delete."""

from __future__ import annotations

import logging
import hashlib
from pathlib import Path
import re
import secrets
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import select

from app.models import (
    Course,
    LearningResource,
    ResourceType,
    AssignmentSubmission,
    Certificate,
)
from app.security import validate_resource_content, valid_resource_url
from app.services.private_files import (
    delete_private,
    download_filename,
    read_private,
    write_private,
)
from app.states.trainer_state import trainer_course_ids, trainer_guard

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
EXTENSION_TYPES: dict[str, str] = {
    ".mp4": ResourceType.VIDEO.value,
    ".webm": ResourceType.VIDEO.value,
    ".pdf": ResourceType.DOCUMENT.value,
    ".docx": ResourceType.DOCUMENT.value,
    ".txt": ResourceType.DOCUMENT.value,
    ".md": ResourceType.DOCUMENT.value,
    ".pptx": ResourceType.SLIDES.value,
    ".csv": ResourceType.DATASET.value,
    ".xlsx": ResourceType.DATASET.value,
}
ALLOWED_TEXT = "PDF, MP4, WebM, TXT, Markdown, CSV, DOCX, PPTX, XLSX · max 50 MB · content validated"


class ResourceRow(TypedDict):
    id: int
    title: str
    description: str
    module: str
    resource_type: str
    has_file: bool
    minutes: int
    published: bool
    is_owner: bool
    course_id: int
    course_title: str
    course_code: str


class ModuleGroup(TypedDict):
    key: str
    course_title: str
    course_code: str
    module: str
    count: int
    items: list[ResourceRow]


class CourseOption(TypedDict):
    id: int
    label: str


def safe_file_name(name: str) -> str:
    base = name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    stem, _, suffix = base.rpartition(".")
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", stem or base).strip("-")[:60]
    suffix = re.sub(r"[^A-Za-z0-9]+", "", suffix).lower()
    token = secrets.token_hex(16)
    return (
        f"{stem or 'resource'}-{token}.{suffix}"
        if suffix
        else f"{stem}-{token}"
    )


class TrainerResourceState(rx.State):
    is_loading: bool = False
    is_uploading: bool = False
    error_message: str = ""
    success_message: str = ""

    groups: list[ModuleGroup] = []
    course_options: list[CourseOption] = []
    total_resources: int = 0
    published_count: int = 0
    pending_file: str = ""
    _staged_file: str = ""
    _staged_owner: int = 0

    async def _remove_unreferenced(self, session, filename: str) -> None:
        if not filename or Path(filename).name != filename:
            return
        for model in (LearningResource, AssignmentSubmission, Certificate):
            if await session.scalar(
                select(model.id).where(model.file_name == filename).limit(1)
            ):
                return
        delete_private(filename)

    @rx.var
    def allowed_hint(self) -> str:
        return ALLOWED_TEXT

    @rx.var
    def has_courses(self) -> bool:
        return len(self.course_options) > 0

    async def _load(self, session, trainer_id: int) -> None:
        course_ids = await trainer_course_ids(session, trainer_id)
        courses = (
            (
                await session.scalars(
                    select(Course)
                    .where(Course.id.in_(course_ids))
                    .order_by(Course.title)
                )
            ).all()
            if course_ids
            else []
        )
        self.course_options = [
            {"id": course.id, "label": f"{course.code} · {course.title}"}
            for course in courses
        ]
        titles = {course.id: (course.title, course.code) for course in courses}
        rows: list[ResourceRow] = []
        if course_ids:
            resource_rows = (
                await session.scalars(
                    select(LearningResource)
                    .where(LearningResource.course_id.in_(course_ids))
                    .order_by(
                        LearningResource.course_id,
                        LearningResource.module_name,
                        LearningResource.sort_order,
                    )
                )
            ).all()
            for resource in resource_rows:
                title, code = titles.get(resource.course_id, ("Course", ""))
                rows.append(
                    {
                        "id": resource.id,
                        "title": resource.title,
                        "description": resource.description,
                        "module": resource.module_name or "Unsorted module",
                        "resource_type": resource.resource_type,
                        "has_file": bool(resource.file_name),
                        "minutes": int(resource.duration_minutes),
                        "published": resource.is_published,
                        "is_owner": resource.uploaded_by_id == trainer_id,
                        "course_id": resource.course_id,
                        "course_title": title,
                        "course_code": code,
                    }
                )
        groups: list[ModuleGroup] = []
        index: dict[str, int] = {}
        for row in rows:
            key = f"{row['course_id']}::{row['module']}"
            if key not in index:
                index[key] = len(groups)
                groups.append(
                    {
                        "key": key,
                        "course_title": row["course_title"],
                        "course_code": row["course_code"],
                        "module": row["module"],
                        "count": 0,
                        "items": [],
                    }
                )
            group = groups[index[key]]
            group["items"].append(row)
            group["count"] = len(group["items"])
        self.groups = groups
        self.total_resources = len(rows)
        self.published_count = len([row for row in rows if row["published"]])

    @rx.event
    async def load_library(self):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                await self._load(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error loading trainer library: {exception}")
            self.error_message = "Could not load your resource library."
        self.is_loading = False

    @rx.event
    async def handle_upload(self, files: list[rx.UploadFile]):
        """Validate and store an uploaded resource file."""
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        if not files:
            self.error_message = "Select a file to upload."
            return
        self.is_uploading = True
        stored = ""
        try:
            upload = files[0]
            original = upload.name or "resource"
            suffix = (
                f".{original.rsplit('.', 1)[-1].lower()}"
                if "." in original
                else ""
            )
            if suffix not in EXTENSION_TYPES:
                self.is_uploading = False
                self.error_message = (
                    f"Unsupported file type. Allowed: {ALLOWED_TEXT}."
                )
                return
            data = await upload.read(MAX_UPLOAD_BYTES + 1)
            if len(data) == 0:
                self.is_uploading = False
                self.error_message = "The selected file is empty."
                return
            if len(data) > MAX_UPLOAD_BYTES:
                self.is_uploading = False
                self.error_message = "File exceeds the 50 MB upload limit."
                return
            validate_resource_content(data, suffix)
            if self._staged_file:
                async with rx.asession() as session:
                    await self._remove_unreferenced(session, self._staged_file)
            stored = safe_file_name(original)
            write_private(stored, data)
        except Exception as exception:
            logging.exception(f"Error uploading resource file: {exception}")
            self.is_uploading = False
            self.error_message = "Upload failed. Try again."
            return
        self.is_uploading = False
        self.pending_file = stored
        self._staged_file = stored
        self._staged_owner = trainer_id
        self.success_message = (
            f"File staged as {stored}. Complete the details and publish it."
        )

    @rx.event
    async def clear_pending_file(self):
        try:
            trainer_id = await trainer_guard(self)
            if not trainer_id or self._staged_owner != trainer_id:
                return
            async with rx.asession() as session:
                await self._remove_unreferenced(session, self._staged_file)
            self.pending_file = ""
            self._staged_file = ""
            self._staged_owner = 0
            self.error_message = ""
            self.success_message = "Staged file discarded."
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.error_message = "Could not discard the staged file. Retry."

    @rx.event
    async def create_resource(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            self.error_message = "Approved trainer access is required."
            return
        title = str(form_data.get("title", "")).strip()
        module = str(form_data.get("module_name", "")).strip()
        external_url = str(form_data.get("external_url", "")).strip()
        if len(title) < 3:
            self.error_message = (
                "Enter a resource title of at least 3 characters."
            )
            return
        if not module:
            self.error_message = "Assign the resource to a module."
            return
        if external_url and not valid_resource_url(external_url):
            self.error_message = "Use an HTTPS link with a valid host, no embedded credentials, and at most 500 characters."
            return
        if self._staged_file and self._staged_owner != trainer_id:
            self.error_message = (
                "Stage the file again under your current account."
            )
            return
        if not self._staged_file and not external_url:
            self.error_message = (
                "Upload a file or provide an external link for this resource."
            )
            return
        try:
            course_id = int(form_data.get("course_id") or 0)
        except ValueError:
            course_id = 0
        try:
            minutes = int(float(form_data.get("duration_minutes") or 0))
        except ValueError:
            minutes = 0
        if minutes < 0 or minutes > 1200:
            self.error_message = "Duration must be between 0 and 1200 minutes."
            return
        try:
            async with rx.asession() as session:
                if course_id not in await trainer_course_ids(
                    session, trainer_id
                ):
                    self.error_message = "You are not assigned to that course."
                    return
                content_type, byte_size, digest = "", 0, ""
                if self._staged_file:
                    data = read_private(self._staged_file)
                    content_type = validate_resource_content(
                        data, Path(self._staged_file).suffix
                    )
                    byte_size = len(data)
                    digest = hashlib.sha256(data).hexdigest()
                resource_type = (
                    EXTENSION_TYPES.get(
                        f".{self._staged_file.rsplit('.', 1)[-1].lower()}",
                        ResourceType.DOCUMENT.value,
                    )
                    if self._staged_file
                    else ResourceType.LINK.value
                )
                last = await session.scalar(
                    select(LearningResource.sort_order)
                    .where(
                        LearningResource.course_id == course_id,
                        LearningResource.module_name == module,
                    )
                    .order_by(LearningResource.sort_order.desc())
                )
                session.add(
                    LearningResource(
                        course_id=course_id,
                        uploaded_by_id=trainer_id,
                        title=title,
                        description=str(
                            form_data.get("description", "")
                        ).strip(),
                        resource_type=resource_type,
                        module_name=module,
                        file_name=self._staged_file,
                        content_type=content_type,
                        file_size_bytes=byte_size,
                        sha256_digest=digest,
                        external_url=external_url,
                        duration_minutes=minutes,
                        sort_order=int(last or 0) + 1,
                        is_published=str(form_data.get("publish", ""))
                        == "publish",
                    )
                )
                await session.commit()
                await self._load(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error creating resource: {exception}")
            self.error_message = "Could not save the resource metadata."
            return
        self.pending_file = ""
        self._staged_file = ""
        self._staged_owner = 0
        self.success_message = f"Resource saved: {title}."

    async def _owned(self, session, resource_id: int, trainer_id: int):
        resource = await session.get(LearningResource, resource_id)
        if resource is None:
            return None
        if resource.course_id not in await trainer_course_ids(
            session, trainer_id
        ):
            return None
        return resource

    @rx.event
    async def download_resource(self, resource_id: int):
        self.error_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        try:
            async with rx.asession() as session:
                resource = await self._owned(session, resource_id, trainer_id)
                if resource is None or not resource.file_name:
                    self.error_message = "That resource file is unavailable."
                    return
                data = read_private(resource.file_name)
                filename = download_filename(resource.title, resource.file_name)
        except Exception as exception:
            logging.exception(
                f"Error downloading resource: {type(exception).__name__}"
            )
            self.error_message = "That resource file is unavailable."
            return
        return rx.download(data=data, filename=filename)

    @rx.event
    async def toggle_publish(self, resource_id: int):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        try:
            async with rx.asession() as session:
                resource = await self._owned(session, resource_id, trainer_id)
                if resource is None:
                    self.error_message = (
                        "You can only manage resources for your own courses."
                    )
                    return
                resource.is_published = not resource.is_published
                published = resource.is_published
                await session.commit()
                await self._load(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error toggling resource: {exception}")
            self.error_message = "Could not update the resource."
            return
        self.success_message = (
            "Resource published." if published else "Resource unpublished."
        )

    @rx.event
    async def delete_resource(self, resource_id: int):
        self.error_message = ""
        self.success_message = ""
        trainer_id = await trainer_guard(self)
        if trainer_id == 0:
            return
        try:
            async with rx.asession() as session:
                resource = await self._owned(session, resource_id, trainer_id)
                if resource is None or resource.uploaded_by_id != trainer_id:
                    self.error_message = (
                        "Only the uploading trainer can delete this resource."
                    )
                    return
                filename = resource.file_name
                await session.delete(resource)
                await session.commit()
                await self._remove_unreferenced(session, filename)
                await self._load(session, trainer_id)
        except Exception as exception:
            logging.exception(f"Error deleting resource: {exception}")
            self.error_message = "Could not delete the resource."
            return
        self.success_message = "Resource deleted."

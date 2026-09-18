"""Administrator certificate request triage: review, approve, reject, issue."""

from __future__ import annotations

import datetime as dt
import logging
import uuid
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    Certificate,
    CertificateRequest,
    CertificateRequestStatus,
    Course,
    Enrollment,
    User,
)
from app.states.admin_state import admin_guard, stamp
from app.states.trainee_state import grade_for
from app.services.email_notifications import enqueue

logger = logging.getLogger(__name__)

MAX_DECISION_NOTE = 600


class RequestRow(TypedDict):
    id: int
    trainee: str
    email: str
    code: str
    course: str
    status: str
    justification: str
    requested_at: str
    reviewed_at: str
    reviewer: str
    decision_note: str
    age_days: int
    age_label: str
    priority: str
    is_overdue: bool
    progress: int
    average_score: float
    assessments_passed: int
    assessments_total: int
    eligible_snapshot: bool
    eligibility_note: str
    enrollment_status: str
    has_certificate: bool
    certificate_number: str
    verification_code: str
    can_approve: bool
    can_reject: bool
    can_issue: bool


class AdminCertificationState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    requests: list[RequestRow] = []
    metrics: dict[str, int] = {
        "total": 0,
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "issued": 0,
        "overdue": 0,
    }

    status_filter: str = "pending"
    query: str = ""
    active_id: int = 0
    decision_note: str = ""

    @rx.var
    def status_options(self) -> list[str]:
        return ["All", "pending", "approved", "rejected", "issued"]

    @rx.var
    def filtered_requests(self) -> list[RequestRow]:
        query = self.query.strip().lower()
        rows: list[RequestRow] = []
        for row in self.requests:
            if (
                self.status_filter != "All"
                and row["status"] != self.status_filter
            ):
                continue
            if query and query not in (
                f"{row['trainee']} {row['email']} {row['code']} {row['course']}".lower()
            ):
                continue
            rows.append(row)
        return rows

    @rx.var
    def active_request(self) -> RequestRow | None:
        for row in self.requests:
            if row["id"] == self.active_id:
                return row
        return None

    @rx.event
    def set_status_filter(self, value: str):
        self.status_filter = value

    @rx.event
    def set_query(self, value: str):
        self.query = value

    @rx.event
    def set_decision_note(self, value: str):
        self.decision_note = value

    @rx.event
    def select_request(self, request_id: int):
        self.error_message = ""
        self.success_message = ""
        self.active_id = 0 if self.active_id == request_id else request_id
        self.decision_note = ""

    # -------------------------------------------------------------- loading
    async def _load(self, session) -> None:
        now = dt.datetime.now(dt.UTC)
        triples = (
            await session.execute(
                select(CertificateRequest, Course, User)
                .join(Course, Course.id == CertificateRequest.course_id)
                .join(User, User.id == CertificateRequest.trainee_id)
                .order_by(CertificateRequest.requested_at.asc())
                .limit(200)
            )
        ).all()
        rows: list[RequestRow] = []
        metrics = {
            "total": 0,
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "issued": 0,
            "overdue": 0,
        }
        for request, course, user in triples:
            requested = request.requested_at
            if requested.tzinfo is None:
                requested = requested.replace(tzinfo=dt.UTC)
            age_days = max(int((now - requested).days), 0)
            reviewer = ""
            if request.reviewed_by_id:
                reviewer = (
                    await session.scalar(
                        select(User.full_name).where(
                            User.id == request.reviewed_by_id
                        )
                    )
                    or ""
                )
            certificate = None
            if request.certificate_id:
                certificate = await session.get(
                    Certificate, request.certificate_id
                )
            if certificate is None:
                certificate = await session.scalar(
                    select(Certificate).where(
                        Certificate.course_id == request.course_id,
                        Certificate.trainee_id == request.trainee_id,
                    )
                )
            enrollment_status = (
                await session.scalar(
                    select(Enrollment.status).where(
                        Enrollment.course_id == request.course_id,
                        Enrollment.trainee_id == request.trainee_id,
                    )
                )
                or "not enrolled"
            )
            is_open = request.status in (
                CertificateRequestStatus.PENDING.value,
                CertificateRequestStatus.APPROVED.value,
            )
            overdue = is_open and age_days >= 7
            priority = (
                "critical"
                if is_open and age_days >= 14
                else (
                    "high" if overdue else ("normal" if is_open else "closed")
                )
            )
            metrics["total"] += 1
            if request.status in metrics:
                metrics[request.status] += 1
            if overdue:
                metrics["overdue"] += 1
            rows.append(
                {
                    "id": request.id,
                    "trainee": user.full_name,
                    "email": user.email,
                    "code": course.code,
                    "course": course.title,
                    "status": request.status,
                    "justification": request.justification,
                    "requested_at": stamp(request.requested_at),
                    "reviewed_at": stamp(request.reviewed_at),
                    "reviewer": reviewer or "Unassigned",
                    "decision_note": request.decision_note,
                    "age_days": age_days,
                    "age_label": (
                        "Raised today"
                        if age_days == 0
                        else f"{age_days} day(s) in queue"
                    ),
                    "priority": priority,
                    "is_overdue": overdue,
                    "progress": int(round(request.progress_percent)),
                    "average_score": round(float(request.average_score), 1),
                    "assessments_passed": int(request.assessments_passed),
                    "assessments_total": int(request.assessments_total),
                    "eligible_snapshot": bool(request.is_eligible_snapshot),
                    "eligibility_note": request.eligibility_note
                    or "No evidence snapshot was captured.",
                    "enrollment_status": str(enrollment_status).replace(
                        "_", " "
                    ),
                    "has_certificate": certificate is not None,
                    "certificate_number": certificate.certificate_number
                    if certificate
                    else "",
                    "verification_code": certificate.verification_code
                    if certificate
                    else "",
                    "can_approve": request.status
                    == CertificateRequestStatus.PENDING.value,
                    "can_reject": request.status
                    in (
                        CertificateRequestStatus.PENDING.value,
                        CertificateRequestStatus.APPROVED.value,
                    ),
                    "can_issue": request.status
                    == CertificateRequestStatus.APPROVED.value,
                }
            )
        rows.sort(
            key=lambda row: (row["status"] != "pending", -row["age_days"])
        )
        self.requests = rows
        self.metrics = metrics

    @rx.event
    async def load_requests(self):
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
            logging.exception(
                f"Error loading certificate requests: {exception}"
            )
            self.error_message = "Could not load the certification queue."
        self.is_loading = False

    # ------------------------------------------------------------ decisions
    async def _new_certificate_number(self, session) -> str:
        year = dt.datetime.now(dt.UTC).year
        count = int(
            await session.scalar(select(func.count()).select_from(Certificate))
            or 0
        )
        for offset in range(1, 500):
            candidate = f"CC-CERT-{year}-{count + offset:06d}"
            clash = await session.scalar(
                select(Certificate.id).where(
                    Certificate.certificate_number == candidate
                )
            )
            if clash is None:
                return candidate
        return f"CC-CERT-{year}-{uuid.uuid4().hex[:8].upper()}"

    @rx.event
    async def approve_request(self, request_id: int):
        self.error_message = ""
        self.success_message = ""
        admin_id = await admin_guard(self)
        if admin_id == 0:
            self.error_message = "Administrator access is required."
            return
        note = self.decision_note.strip()[:MAX_DECISION_NOTE]
        try:
            async with rx.asession() as session:
                request = await session.get(CertificateRequest, request_id)
                if request is None:
                    self.error_message = "That request no longer exists."
                    return
                if request.status != CertificateRequestStatus.PENDING.value:
                    self.error_message = (
                        "Only a pending request can be approved; this one is "
                        f"already {request.status}."
                    )
                    return
                if not request.is_eligible_snapshot:
                    self.error_message = (
                        "The submitted evidence snapshot is not eligible — reject "
                        "the request with a reason instead."
                    )
                    return
                request.status = CertificateRequestStatus.APPROVED.value
                request.reviewed_by_id = admin_id
                request.reviewed_at = dt.datetime.now(dt.UTC)
                request.decision_note = (
                    note
                    or "Completion evidence verified against the course record."
                )
                await session.commit()
                await self._load(session)
        except Exception as exception:
            logging.exception(f"Error approving request: {exception}")
            self.error_message = "Could not record the approval. Try again."
            return
        self.decision_note = ""
        self.success_message = (
            "Approved and logged. Issuance remains a separate controlled step — "
            "issue the certificate when the number is to be generated."
        )

    @rx.event
    async def reject_request(self, request_id: int):
        self.error_message = ""
        self.success_message = ""
        admin_id = await admin_guard(self)
        if admin_id == 0:
            self.error_message = "Administrator access is required."
            return
        reason = self.decision_note.strip()
        if len(reason) < 10:
            self.error_message = (
                "A rejection reason of at least 10 characters is required so the "
                "trainee knows exactly what to fix."
            )
            return
        try:
            async with rx.asession() as session:
                request = await session.get(CertificateRequest, request_id)
                if request is None:
                    self.error_message = "That request no longer exists."
                    return
                if request.status in (
                    CertificateRequestStatus.REJECTED.value,
                    CertificateRequestStatus.ISSUED.value,
                ):
                    self.error_message = (
                        f"This request is already {request.status} and cannot be "
                        "rejected."
                    )
                    return
                request.status = CertificateRequestStatus.REJECTED.value
                request.reviewed_by_id = admin_id
                request.reviewed_at = dt.datetime.now(dt.UTC)
                request.decision_note = reason[:MAX_DECISION_NOTE]
                await session.commit()
                await self._load(session)
        except Exception as exception:
            logging.exception(f"Error rejecting request: {exception}")
            self.error_message = "Could not record the rejection. Try again."
            return
        self.decision_note = ""
        self.success_message = (
            "Rejection recorded with a reason and visible to the trainee."
        )

    @rx.event
    async def issue_certificate(self, request_id: int):
        self.error_message = ""
        self.success_message = ""
        admin_id = await admin_guard(self)
        if admin_id == 0:
            self.error_message = "Administrator access is required."
            return
        note = self.decision_note.strip()[:MAX_DECISION_NOTE]
        number = ""
        try:
            async with rx.asession() as session:
                request = await session.get(CertificateRequest, request_id)
                if request is None:
                    self.error_message = "That request no longer exists."
                    return
                if request.status == CertificateRequestStatus.ISSUED.value:
                    existing = (
                        await session.get(Certificate, request.certificate_id)
                        if request.certificate_id
                        else None
                    )
                    self.error_message = (
                        "This certificate has already been issued"
                        + (
                            f" as {existing.certificate_number}."
                            if existing
                            else "."
                        )
                    )
                    return
                if request.status != CertificateRequestStatus.APPROVED.value:
                    self.error_message = (
                        "Approve the request first — issuance is a separate, "
                        "controlled step."
                    )
                    return
                certificate = await session.scalar(
                    select(Certificate).where(
                        Certificate.course_id == request.course_id,
                        Certificate.trainee_id == request.trainee_id,
                    )
                )
                now = dt.datetime.now(dt.UTC)
                if certificate is None:
                    number = await self._new_certificate_number(session)
                    certificate = Certificate(
                        certificate_number=number,
                        course_id=request.course_id,
                        trainee_id=request.trainee_id,
                        issued_by_id=admin_id,
                        issued_at=now,
                        final_score=float(request.average_score),
                        grade=grade_for(float(request.average_score)),
                        verification_code=(
                            f"VRF-{uuid.uuid4().hex[:4].upper()}-"
                            f"{uuid.uuid4().hex[:4].upper()}"
                        ),
                    )
                    session.add(certificate)
                    await session.flush()
                else:
                    number = certificate.certificate_number
                await enqueue(session, "certificate_issued", certificate)
                request.certificate_id = certificate.id
                request.status = CertificateRequestStatus.ISSUED.value
                request.reviewed_by_id = admin_id
                request.reviewed_at = now
                request.decision_note = (
                    note
                    or f"Certificate {number} issued against verified evidence."
                )
                await session.commit()
                await self._load(session)
        except Exception as exception:
            logging.exception(f"Error issuing certificate: {exception}")
            self.error_message = "Could not issue the certificate. Try again."
            return
        self.decision_note = ""
        self.success_message = (
            f"Certificate {number} issued, numbered and logged against your "
            "administrator account."
        )
        from app.states.admin_oversight_state import AdminOversightState

        return AdminOversightState.load_oversight

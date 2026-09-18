"""Certification readiness evidence and trainee certificate requests."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, TypedDict

import reflex as rx
from sqlalchemy import func, select

from app.models import (
    Assessment,
    AssessmentResult,
    AssessmentStatus,
    AssignmentStatus,
    AssignmentSubmission,
    Certificate,
    CertificateRequest,
    CertificateRequestStatus,
    Course,
    CourseAssignment,
    Enrollment,
    EnrollmentStatus,
    LearningResource,
    ResourceProgress,
    TraineeProfile,
    User,
)
from app.seed import ensure_seed_data

logger = logging.getLogger(__name__)

MIN_JUSTIFICATION = 30
MAX_JUSTIFICATION = 600
MIN_PROFILE_COMPLETION = 60


class ReadinessRow(TypedDict):
    course_id: int
    code: str
    title: str
    enrollment_status: str
    resource_total: int
    resource_done: int
    resource_percent: int
    progress_percent: int
    assessments_total: int
    assessments_passed: int
    best_score: float
    assignments_total: int
    assignments_submitted: int
    assignments_graded: int
    assignments_percent: int
    profile_completion: int
    is_eligible: bool
    missing: list[str]
    missing_label: str
    has_request: bool
    request_status: str
    request_status_label: str
    requested_at: str
    reviewed_at: str
    reviewer: str
    decision_note: str
    snapshot_note: str
    snapshot_progress: int
    snapshot_score: float
    snapshot_eligible: bool
    has_certificate: bool
    certificate_number: str
    certificate_issued: str
    verification_code: str


def _stamp(value: dt.datetime | None) -> str:
    if value is None:
        return "—"
    moment = value if value.tzinfo else value.replace(tzinfo=dt.UTC)
    return moment.strftime("%d %b %Y, %H:%M UTC")


class TraineeCertificationState(rx.State):
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    readiness: list[ReadinessRow] = []
    request_open: bool = False
    request_course_id: int = 0
    request_course_label: str = ""
    is_submitting: bool = False

    async def _uid(self) -> int:
        from app.security import validate_role

        return await validate_role(self, "trainee")

    # ------------------------------------------------------------- computed
    @rx.var
    def eligible_count(self) -> int:
        return len(
            [
                row
                for row in self.readiness
                if row["is_eligible"] and not row["has_request"]
            ]
        )

    @rx.var
    def pending_count(self) -> int:
        return len(
            [
                row
                for row in self.readiness
                if row["request_status"] == "pending"
            ]
        )

    @rx.var
    def issued_count(self) -> int:
        return len([row for row in self.readiness if row["has_certificate"]])

    @rx.var
    def blocked_count(self) -> int:
        return len(
            [
                row
                for row in self.readiness
                if not row["is_eligible"] and not row["has_certificate"]
            ]
        )

    # -------------------------------------------------------------- loading
    async def _evaluate(self, session, uid: int) -> list[ReadinessRow]:
        active_user = await session.scalar(
            select(User.id).where(
                User.id == uid,
                User.role == "trainee",
                User.is_active.is_(True),
                User.approval_status == "approved",
            )
        )
        profile_completion = int(
            await session.scalar(
                select(TraineeProfile.profile_completion).where(
                    TraineeProfile.user_id == uid
                )
            )
            or 0
        )
        pairs = (
            await session.execute(
                select(Enrollment, Course)
                .join(Course, Course.id == Enrollment.course_id)
                .where(
                    Enrollment.trainee_id == uid,
                    Enrollment.status != EnrollmentStatus.DROPPED.value,
                )
                .order_by(Course.title)
            )
        ).all()
        rows: list[ReadinessRow] = []
        for enrollment, course in pairs:
            resource_total = int(
                await session.scalar(
                    select(func.count())
                    .select_from(LearningResource)
                    .where(
                        LearningResource.course_id == course.id,
                        LearningResource.is_published.is_(True),
                    )
                )
                or 0
            )
            resource_done = int(
                await session.scalar(
                    select(func.count())
                    .select_from(ResourceProgress)
                    .join(
                        LearningResource,
                        LearningResource.id == ResourceProgress.resource_id,
                    )
                    .where(
                        LearningResource.course_id == course.id,
                        LearningResource.is_published.is_(True),
                        ResourceProgress.enrollment_id == enrollment.id,
                        ResourceProgress.is_completed.is_(True),
                    )
                )
                or 0
            )
            resource_percent = (
                int(round(resource_done * 100 / resource_total))
                if resource_total
                else int(round(enrollment.progress_percent))
            )
            assessment_ids = list(
                (
                    await session.execute(
                        select(Assessment.id).where(
                            Assessment.course_id == course.id,
                            Assessment.status != AssessmentStatus.DRAFT.value,
                        )
                    )
                )
                .scalars()
                .all()
            )
            assessments_passed = 0
            best_score = 0.0
            if assessment_ids:
                assessments_passed = int(
                    await session.scalar(
                        select(
                            func.count(
                                func.distinct(AssessmentResult.assessment_id)
                            )
                        ).where(
                            AssessmentResult.trainee_id == uid,
                            AssessmentResult.assessment_id.in_(assessment_ids),
                            AssessmentResult.is_passed.is_(True),
                        )
                    )
                    or 0
                )
                best_score = float(
                    await session.scalar(
                        select(func.max(AssessmentResult.percentage)).where(
                            AssessmentResult.trainee_id == uid,
                            AssessmentResult.assessment_id.in_(assessment_ids),
                            AssessmentResult.is_passed.is_(True),
                        )
                    )
                    or 0.0
                )
            assignment_ids = list(
                (
                    await session.execute(
                        select(CourseAssignment.id).where(
                            CourseAssignment.course_id == course.id,
                            CourseAssignment.status.in_(
                                ["published", "closed"]
                            ),
                        )
                    )
                )
                .scalars()
                .all()
            )
            assignments_submitted = 0
            assignments_graded = 0
            if assignment_ids:
                assignments_submitted = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(AssignmentSubmission)
                        .where(
                            AssignmentSubmission.trainee_id == uid,
                            AssignmentSubmission.assignment_id.in_(
                                assignment_ids
                            ),
                            AssignmentSubmission.status.in_(
                                ["submitted", "late", "graded"]
                            ),
                        )
                    )
                    or 0
                )
                assignments_graded = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(AssignmentSubmission)
                        .join(
                            CourseAssignment,
                            CourseAssignment.id
                            == AssignmentSubmission.assignment_id,
                        )
                        .where(
                            AssignmentSubmission.trainee_id == uid,
                            AssignmentSubmission.assignment_id.in_(
                                assignment_ids
                            ),
                            AssignmentSubmission.status == "graded",
                            AssignmentSubmission.marks_awarded
                            >= CourseAssignment.passing_marks,
                        )
                    )
                    or 0
                )
            assignments_total = len(assignment_ids)
            assignments_percent = (
                int(round(assignments_submitted * 100 / assignments_total))
                if assignments_total
                else 100
            )

            missing: list[str] = []
            if not active_user:
                missing.append(
                    "An active, approved trainee account is required"
                )
            if resource_percent < 100:
                missing.append(
                    f"Complete all {resource_total} learning resources "
                    f"({resource_done} done, {resource_percent}%)"
                )
            if assessment_ids and assessments_passed < len(assessment_ids):
                missing.append("Pass every required official course assessment")
            if assignments_total and assignments_graded < assignments_total:
                missing.append(
                    f"Obtain passing grades for all {assignments_total} required assignments "
                    f"({assignments_graded} passed)"
                )
            if profile_completion < MIN_PROFILE_COMPLETION:
                missing.append(
                    f"Raise professional profile completeness to {MIN_PROFILE_COMPLETION}% "
                    f"(currently {profile_completion}%)"
                )
            if enrollment.status == EnrollmentStatus.AT_RISK.value:
                missing.append(
                    "Clear the at-risk flag with your trainer before requesting certification"
                )
            is_eligible = len(missing) == 0

            request = await session.scalar(
                select(CertificateRequest).where(
                    CertificateRequest.course_id == course.id,
                    CertificateRequest.trainee_id == uid,
                )
            )
            certificate = await session.scalar(
                select(Certificate).where(
                    Certificate.course_id == course.id,
                    Certificate.trainee_id == uid,
                )
            )
            reviewer = ""
            if request is not None and request.reviewed_by_id:
                reviewer = (
                    await session.scalar(
                        select(User.full_name).where(
                            User.id == request.reviewed_by_id
                        )
                    )
                    or ""
                )
            status_labels = {
                "pending": "In the secretariat queue",
                "approved": "Approved — awaiting issuance",
                "rejected": "Returned for action",
                "issued": "Certificate issued",
            }
            rows.append(
                {
                    "course_id": course.id,
                    "code": course.code,
                    "title": course.title,
                    "enrollment_status": enrollment.status.replace("_", " "),
                    "resource_total": resource_total,
                    "resource_done": resource_done,
                    "resource_percent": min(resource_percent, 100),
                    "progress_percent": int(round(enrollment.progress_percent)),
                    "assessments_total": len(assessment_ids),
                    "assessments_passed": assessments_passed,
                    "best_score": round(best_score, 1),
                    "assignments_total": assignments_total,
                    "assignments_submitted": assignments_submitted,
                    "assignments_graded": assignments_graded,
                    "assignments_percent": min(assignments_percent, 100),
                    "profile_completion": profile_completion,
                    "is_eligible": is_eligible,
                    "missing": missing,
                    "missing_label": (
                        "All completion evidence is on record."
                        if is_eligible
                        else f"{len(missing)} requirement(s) outstanding"
                    ),
                    "has_request": request is not None,
                    "request_status": request.status if request else "",
                    "request_status_label": (
                        status_labels.get(request.status, request.status)
                        if request
                        else ""
                    ),
                    "requested_at": _stamp(request.requested_at)
                    if request
                    else "—",
                    "reviewed_at": _stamp(request.reviewed_at)
                    if request
                    else "—",
                    "reviewer": reviewer or "Awaiting reviewer",
                    "decision_note": request.decision_note if request else "",
                    "snapshot_note": request.eligibility_note
                    if request
                    else "",
                    "snapshot_progress": int(round(request.progress_percent))
                    if request
                    else 0,
                    "snapshot_score": round(float(request.average_score), 1)
                    if request
                    else 0.0,
                    "snapshot_eligible": bool(request.is_eligible_snapshot)
                    if request
                    else False,
                    "has_certificate": certificate is not None,
                    "certificate_number": certificate.certificate_number
                    if certificate
                    else "",
                    "certificate_issued": _stamp(certificate.issued_at)
                    if certificate
                    else "—",
                    "verification_code": certificate.verification_code
                    if certificate
                    else "",
                }
            )
        return rows

    @rx.event
    async def load_readiness(self):
        ensure_seed_data()
        self.error_message = ""
        uid = await self._uid()
        if uid <= 0:
            self.readiness = []
            return
        self.is_loading = True
        yield
        try:
            async with rx.asession() as session:
                self.readiness = await self._evaluate(session, uid)
        except Exception as exception:
            logging.exception(
                f"Error loading certification readiness: {exception}"
            )
            self.error_message = (
                "Could not assemble your completion evidence. Retry shortly."
            )
        self.is_loading = False

    # -------------------------------------------------------------- request
    @rx.event
    def open_request(self, row: ReadinessRow):
        self.error_message = ""
        self.success_message = ""
        self.request_open = True
        self.request_course_id = row["course_id"]
        self.request_course_label = f"{row['code']} · {row['title']}"

    @rx.event
    def close_request(self):
        self.request_open = False
        self.request_course_id = 0
        self.request_course_label = ""

    @rx.event
    async def submit_request(self, form_data: dict[str, Any]):
        self.error_message = ""
        self.success_message = ""
        uid = await self._uid()
        if uid <= 0:
            yield rx.redirect("/login")
            return
        course_id = self.request_course_id
        if course_id <= 0:
            self.error_message = "Choose a course before submitting a request."
            return
        justification = str(form_data.get("justification", "")).strip()
        if len(justification) < MIN_JUSTIFICATION:
            self.error_message = (
                f"Describe the purpose of the certificate in at least "
                f"{MIN_JUSTIFICATION} characters."
            )
            return
        if len(justification) > MAX_JUSTIFICATION:
            self.error_message = (
                f"Keep the justification under {MAX_JUSTIFICATION} characters."
            )
            return
        self.is_submitting = True
        yield
        try:
            async with rx.asession() as session:
                enrollment = await session.scalar(
                    select(Enrollment).where(
                        Enrollment.course_id == course_id,
                        Enrollment.trainee_id == uid,
                    )
                )
                if enrollment is None:
                    self.is_submitting = False
                    self.error_message = (
                        "You are not enrolled in that course, so no certificate "
                        "can be requested."
                    )
                    return
                existing = await session.scalar(
                    select(CertificateRequest).where(
                        CertificateRequest.course_id == course_id,
                        CertificateRequest.trainee_id == uid,
                    )
                )
                if existing is not None:
                    self.is_submitting = False
                    self.error_message = (
                        "A certificate request already exists for this course — "
                        "track its status below instead of raising a duplicate."
                    )
                    return
                rows = await self._evaluate(session, uid)
                target = next(
                    (row for row in rows if row["course_id"] == course_id), None
                )
                if target is None:
                    self.is_submitting = False
                    self.error_message = "That course record could not be read."
                    return
                if not target["is_eligible"]:
                    self.readiness = rows
                    self.is_submitting = False
                    self.error_message = (
                        "Certification evidence is incomplete: "
                        f"{'; '.join(target['missing'])}."
                    )
                    return
                snapshot = (
                    f"Resources {target['resource_done']}/{target['resource_total']} "
                    f"({target['resource_percent']}%); assessments passed "
                    f"{target['assessments_passed']}/{target['assessments_total']} "
                    f"with best score {target['best_score']:.1f}%; assignments "
                    f"{target['assignments_submitted']}/{target['assignments_total']} "
                    f"submitted, {target['assignments_graded']} graded; profile "
                    f"completeness {target['profile_completion']}%; enrolment "
                    f"status {target['enrollment_status']}."
                )
                session.add(
                    CertificateRequest(
                        course_id=course_id,
                        trainee_id=uid,
                        enrollment_id=enrollment.id,
                        justification=justification,
                        status=CertificateRequestStatus.PENDING.value,
                        progress_percent=float(
                            min(target["resource_percent"], 100)
                        ),
                        average_score=float(min(target["best_score"], 100.0)),
                        assessments_passed=target["assessments_passed"],
                        assessments_total=target["assessments_total"],
                        is_eligible_snapshot=True,
                        eligibility_note=snapshot,
                    )
                )
                await session.commit()
                self.readiness = await self._evaluate(session, uid)
        except Exception as exception:
            logging.exception(
                f"Error submitting certificate request: {exception}"
            )
            self.is_submitting = False
            self.error_message = "Could not lodge the request. Try again."
            return
        self.is_submitting = False
        self.request_open = False
        self.request_course_id = 0
        self.request_course_label = ""
        self.success_message = (
            "Request lodged with the certification secretariat. Your completion "
            "evidence was captured as a snapshot for the audit trail — no email "
            "follow-up is needed."
        )

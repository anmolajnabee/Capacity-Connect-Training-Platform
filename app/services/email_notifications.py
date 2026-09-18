import reflex as rx
import asyncio
import datetime as dt
import hashlib
import html
import logging
import os
import re
from email.utils import parseaddr
from urllib.parse import urlsplit

import resend
from sqlalchemy import select, or_, exists, update, text
from sqlalchemy.dialects.postgresql import insert
from app import models as m

PATHS = {
    "announcement_published": "/announcements",
    "assignment_published": "/trainee/assignments",
    "assignment_deadline": "/trainee/assignments",
    "assessment_deadline": "/trainee/assessments",
    "assessment_result": "/trainee/results",
    "assignment_graded": "/trainee/assignments",
    "certificate_issued": "/trainee/certificates",
    "account_approval": "/account",
    "account_status": "/account",
}
MAX_ATTEMPTS = 6


def now():
    return dt.datetime.now(dt.UTC)


def event_key(kind: str, source: str, uid: int) -> str:
    return f"cc/{kind}/{hashlib.sha256(source.encode()).hexdigest()}/{uid}"


def valid_email(address: str) -> bool:
    return (
        len(address) <= 255
        and bool(
            re.fullmatch(
                r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+",
                address,
            )
        )
        and ".." not in address
    )


def bounded_name(value: str) -> str:
    return " ".join(
        "".join(c for c in value if c.isprintable() or c.isspace()).split()
    )[:120]


def publication_due(value: dt.datetime | None) -> bool:
    if value is None:
        return False
    return (
        value.replace(tzinfo=dt.UTC) <= now()
        if value.tzinfo is None
        else value <= now()
    )


def recipient_eligible(user, row) -> bool:
    return bool(
        user
        and user.email == row.recipient_email
        and (
            user.is_active
            or row.event_type in ("account_approval", "account_status")
        )
    )


def display_name(session, kind: str, source) -> str:
    record = None
    if kind == "announcement_published":
        record = session.get(m.Announcement, source.id)
    elif kind in ("assignment_published", "assignment_deadline"):
        record = session.get(m.CourseAssignment, source.id)
    elif kind == "assessment_deadline":
        record = session.get(m.Assessment, source.id)
    elif kind == "assignment_graded":
        record = session.get(m.CourseAssignment, source.assignment_id)
    elif kind == "assessment_result":
        record = session.get(m.Assessment, source.assessment_id)
    elif kind == "certificate_issued":
        record = session.get(m.Course, source.course_id)
    return bounded_name(record.title or "") if record is not None else ""


def render(kind: str, summary: str, name: str = "") -> tuple[str, str, str]:
    path = PATHS[kind]
    title = kind.replace("_", " ").capitalize()
    name = bounded_name(name)
    if name:
        title = f"{title}: {name}"
    summary = summary[:500]
    base = os.getenv("CC_PUBLIC_URL", "").rstrip("/")
    parsed = urlsplit(base)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path
    ):
        base = ""
    link = f"{base}{path}"
    plain = f"CAPACITY CONNECT\n\n{title}\n{summary}\n\nOpen your workspace: {link}\nSign in to review the record."
    body = f'<!doctype html><html lang="en"><body><main><h1>CAPACITY CONNECT</h1><h2>{html.escape(title)}</h2><p>{html.escape(summary)}</p><p><a href="{html.escape(link, quote=True)}">Review in your workspace</a></p><p>Sign in to review the record.</p></main></body></html>'
    return title, plain, body


def cohort(course_id: int):
    return select(m.Enrollment.trainee_id).where(
        m.Enrollment.course_id == course_id, m.Enrollment.status != "dropped"
    )


def recipients(kind: str, source):
    query = select(m.User)
    if kind not in ("account_approval", "account_status"):
        query = query.where(m.User.is_active.is_(True))
    if kind == "announcement_published":
        role = {
            "trainees": "trainee",
            "trainers": "trainer",
            "admins": "admin",
        }.get(source.audience)
        if role:
            query = query.where(m.User.role == role)
        if source.course_id:
            trainers = select(m.CourseTrainerAssignment.trainer_id).where(
                m.CourseTrainerAssignment.course_id == source.course_id,
                m.CourseTrainerAssignment.status == "approved",
            )
            query = query.where(
                or_(
                    m.User.id.in_(cohort(source.course_id)),
                    m.User.id.in_(trainers),
                )
            )
    elif kind in (
        "assignment_published",
        "assignment_deadline",
        "assessment_deadline",
    ):
        query = query.where(
            m.User.role == "trainee", m.User.id.in_(cohort(source.course_id))
        )
        if kind == "assignment_deadline":
            query = query.where(
                ~exists(
                    select(m.AssignmentSubmission.id).where(
                        m.AssignmentSubmission.assignment_id == source.id,
                        m.AssignmentSubmission.trainee_id == m.User.id,
                        m.AssignmentSubmission.submitted_at.is_not(None),
                    )
                )
            )
    else:
        uid = source.id if isinstance(source, m.User) else source.trainee_id
        query = query.where(m.User.id == uid)
    return query.order_by(m.User.id)


def queue_sync(session, kind: str, source, revision: str = "") -> int:
    """Called only by authorized business handlers; never commits or calls transport."""
    if kind not in PATHS:
        raise ValueError("Unsupported notification event")
    session.flush()
    if kind == "announcement_published" and (
        not source.is_published or not publication_due(source.published_at)
    ):
        return 0
    identity = f"{source.id}/{revision}"
    summary = {
        "announcement_published": "A new announcement is available for your audience.",
        "assignment_published": "A new course assignment is available.",
        "assignment_deadline": "Your assignment deadline is approaching. Review the due time in your workspace.",
        "assessment_deadline": "An assessment deadline is approaching. Review the due time in your workspace.",
        "assessment_result": "Your assessment result is now available.",
        "assignment_graded": "Your assignment grade and feedback are now available.",
        "certificate_issued": "Your course certificate has been issued.",
        "account_approval": "An administrator has recorded a decision on your access request.",
        "account_status": "An administrator has updated your account status.",
    }[kind]
    subject, plain, body = render(
        kind, summary, display_name(session, kind, source)
    )
    count = 0
    last = 0
    while True:
        users = session.scalars(
            recipients(kind, source).where(m.User.id > last).limit(200)
        ).all()
        if not users:
            break
        for user in users:
            last = user.id
            if not valid_email(user.email):
                continue
            key = event_key(kind, identity, user.id)
            result = session.execute(
                insert(m.EmailDelivery)
                .values(
                    event_key=key,
                    event_type=kind,
                    recipient_user_id=user.id,
                    recipient_email=user.email,
                    recipient_name=user.full_name,
                    recipient_role=user.role,
                    subject=subject,
                    text_body=plain,
                    html_body=body,
                    action_path=PATHS[kind],
                    status="pending",
                    scheduled_at=now(),
                    attempt_count=0,
                )
                .on_conflict_do_nothing(index_elements=["event_key"])
                .returning(m.EmailDelivery.id)
            ).scalar()
            if result:
                session.add(
                    m.Notification(
                        audience="user",
                        user_id=user.id,
                        course_id=getattr(source, "course_id", None),
                        title=subject,
                        body=summary,
                        action_path=PATHS[kind],
                        status="published",
                    )
                )
                count += 1
    return count


async def enqueue(session, kind: str, source, revision: str = "") -> int:
    return await session.run_sync(
        lambda sync: queue_sync(sync, kind, source, revision)
    )


def classify(error: Exception) -> tuple[str, str]:
    code = str(getattr(error, "code", ""))
    if code == "429":
        return "retry", "rate_limited"
    if code in ("401", "403"):
        return "blocked", "provider_configuration"
    if code in ("400", "404", "409", "422"):
        return "failed", "provider_validation"
    return "retry", "provider_unavailable"


def backoff(attempt: int) -> int:
    return min(3600, 30 * 2 ** min(max(attempt - 1, 0), 7))


def safe_log(category: str):
    # Do not include the original exception, SQL parameters or SDK payload.
    logging.exception(
        f"Error: {category}",
        exc_info=(RuntimeError, RuntimeError(category), None),
    )


async def sender_configuration() -> tuple[str, str]:
    key = os.getenv("RESEND_API_KEY", "")
    if not key:
        return "", "provider_configuration"
    resend.api_key = key
    configured = os.getenv("RESEND_FROM_EMAIL", "").strip()
    if configured:
        address = parseaddr(configured)[1]
        if not valid_email(address) or address.lower().endswith("@resend.dev"):
            return "", "sender_domain_unverified"
        return configured, "configured_sender"
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(resend.Domains.list, {"limit": 100}), 20
        )
        for domain in response.get("data", []):
            name = domain.get("name", "")
            if (
                domain.get("status") == "verified"
                and (domain.get("capabilities") or {}).get("sending")
                == "enabled"
                and valid_email(f"notifications@{name}")
            ):
                return (
                    f"CAPACITY CONNECT <notifications@{name}>",
                    "verified_sender",
                )
        return "", "sender_domain_unverified"
    except Exception as error:
        logging.exception("Unexpected error")
        safe_log("sender_lookup_failed")
        return "", classify(error)[1]


async def require_admin(session, uid: int):
    allowed = await session.scalar(
        select(m.User.id).where(
            m.User.id == uid,
            m.User.role == "admin",
            m.User.is_active.is_(True),
            m.User.approval_status == "approved",
        )
    )
    if not allowed:
        raise PermissionError("Administrator access required")


async def retry_delivery(session, uid: int, delivery_id: int) -> bool:
    await require_admin(session, uid)
    row = await session.scalar(
        select(m.EmailDelivery)
        .where(m.EmailDelivery.id == delivery_id)
        .with_for_update()
    )
    if (
        row is None
        or row.status not in ("blocked", "retry", "failed")
        or row.provider_message_id
        or row.last_error_category == "acceptance_unknown"
    ):
        return False
    row.status = "pending"
    row.attempt_count = 0
    row.next_attempt_at = now()
    row.last_error_category = ""
    row.last_error_summary = ""
    return True


async def dispatch_pending(limit: int = 20) -> int:
    sender, config = await sender_configuration()
    processed = 0
    # A database advisory lock serializes provider pacing across app instances.
    async with rx.asession() as gate:
        locked = await gate.scalar(
            text("SELECT pg_try_advisory_xact_lock(26075019)")
        )
        if not locked:
            return 0
        async with rx.asession() as session:
            await session.execute(
                update(m.EmailDelivery)
                .where(
                    m.EmailDelivery.status == "sending",
                    m.EmailDelivery.updated_at
                    < now() - dt.timedelta(minutes=10),
                )
                .values(
                    status="blocked",
                    last_error_category="acceptance_unknown",
                    last_error_summary="Provider reconciliation required before retry.",
                )
            )
            await session.commit()
        for _ in range(min(max(limit, 1), 20)):
            async with rx.asession() as session:
                row = await session.scalar(
                    select(m.EmailDelivery)
                    .where(
                        m.EmailDelivery.status.in_(("pending", "retry")),
                        m.EmailDelivery.scheduled_at <= now(),
                        or_(
                            m.EmailDelivery.next_attempt_at.is_(None),
                            m.EmailDelivery.next_attempt_at <= now(),
                        ),
                    )
                    .order_by(m.EmailDelivery.id)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                if row is None:
                    break
                user = (
                    await session.get(m.User, row.recipient_user_id)
                    if row.recipient_user_id
                    else None
                )
                if not recipient_eligible(user, row):
                    row.status = "blocked"
                    row.last_error_category = "recipient_ineligible"
                    await session.commit()
                    continue
                if not sender:
                    row.status = "blocked"
                    row.last_error_category = config
                    await session.commit()
                    processed += 1
                    continue
                row.status = "sending"
                row.attempt_count += 1
                row.updated_at = now()
                row_id, attempt = row.id, row.attempt_count
                key = row.event_key
                params = {
                    "from": sender,
                    "to": [row.recipient_email],
                    "subject": row.subject,
                    "text": row.text_body,
                    "html": row.html_body,
                }
                await session.commit()
            status, category, provider_id = "accepted", "", ""
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        resend.Emails.send,
                        params,
                        options={"idempotency_key": key},
                    ),
                    30,
                )
                provider_id = str(response.get("id", ""))[:256]
                if not provider_id:
                    status, category = "blocked", "acceptance_unknown"
            except (TimeoutError, ConnectionError):
                logging.exception("Unexpected error")
                safe_log("acceptance_unknown")
                status, category = "blocked", "acceptance_unknown"
            except Exception as error:
                logging.exception("Unexpected error")
                safe_log("provider_request_failed")
                status, category = classify(error)
                if status == "retry" and attempt >= MAX_ATTEMPTS:
                    status = "failed"
            async with rx.asession() as session:
                row = await session.get(
                    m.EmailDelivery, row_id, with_for_update=True
                )
                if row and row.status == "sending":
                    row.status = status
                    row.last_error_category = category
                    row.last_error_summary = category
                    row.provider_message_id = provider_id or None
                    row.accepted_at = now() if status == "accepted" else None
                    row.next_attempt_at = (
                        now() + dt.timedelta(seconds=backoff(attempt))
                        if status == "retry"
                        else None
                    )
                    await session.commit()
            processed += 1
            await asyncio.sleep(0.6)
    return processed


async def sweep_deadlines():
    async with rx.asession() as session:
        moment = now()
        for model, field, kind, published in (
            (
                m.CourseAssignment,
                m.CourseAssignment.due_at,
                "assignment_deadline",
                m.CourseAssignment.status == "published",
            ),
            (
                m.Assessment,
                m.Assessment.deadline_at,
                "assessment_deadline",
                m.Assessment.status == "open",
            ),
        ):
            last = 0
            for _ in range(10):
                records = (
                    await session.scalars(
                        select(model)
                        .where(
                            published,
                            field > moment,
                            field <= moment + dt.timedelta(hours=48),
                            model.id > last,
                        )
                        .order_by(model.id)
                        .limit(100)
                    )
                ).all()
                if not records:
                    break
                for source in records:
                    last = source.id
                    due = getattr(source, field.key)
                    if due.tzinfo is None:
                        due = due.replace(tzinfo=dt.UTC)
                    if (
                        kind == "assignment_deadline"
                        and not source.is_published
                    ):
                        continue
                    if (
                        kind == "assessment_deadline"
                        and source.opens_at
                        and source.opens_at > moment
                    ):
                        continue
                    hours = 24 if due <= moment + dt.timedelta(hours=24) else 48
                    await enqueue(
                        session, kind, source, f"{due.isoformat()}/{hours}h"
                    )
                await session.commit()


async def email_worker():
    await asyncio.sleep(5)
    while True:
        try:
            await asyncio.wait_for(sweep_deadlines(), 90)
            await asyncio.wait_for(dispatch_pending(), 90)
        except Exception:
            logging.exception("Unexpected error")
            safe_log("email_worker_cycle_failed")
        await asyncio.sleep(60)

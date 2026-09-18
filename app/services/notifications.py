import reflex as rx
import datetime as dt
from sqlalchemy import select, or_, and_
from app import models as m


def recipient_query(uid: int, role: str):
    now = dt.datetime.now(dt.UTC)
    courses = (
        select(m.Enrollment.course_id)
        .where(m.Enrollment.trainee_id == uid, m.Enrollment.status != "dropped")
        .union(
            select(m.CourseTrainerAssignment.course_id).where(
                m.CourseTrainerAssignment.trainer_id == uid,
                m.CourseTrainerAssignment.status == "approved",
            )
        )
    )
    orgs = select(m.UserOrganizationAssignment.organization_id).where(
        m.UserOrganizationAssignment.user_id == uid,
        m.UserOrganizationAssignment.status == "active",
        m.UserOrganizationAssignment.starts_at <= now,
        or_(
            m.UserOrganizationAssignment.ends_at.is_(None),
            m.UserOrganizationAssignment.ends_at > now,
        ),
    )
    return select(m.Notification).where(
        m.Notification.status == "published",
        or_(
            m.Notification.expires_at.is_(None), m.Notification.expires_at > now
        ),
        or_(
            m.Notification.audience == "all",
            m.Notification.audience
            == {
                "trainee": "trainees",
                "trainer": "trainers",
                "admin": "admins",
            }.get(role, "none"),
            and_(
                m.Notification.audience == "user", m.Notification.user_id == uid
            ),
            and_(
                m.Notification.audience == "course",
                m.Notification.course_id.in_(courses),
            ),
            and_(
                m.Notification.audience == "organization",
                m.Notification.organization_id.in_(orgs),
            ),
        ),
    )


def receipts(
    session, uid: int, role: str, mark_id: int = -1
) -> list[dict[str, str]]:
    notices = session.scalars(
        recipient_query(uid, role)
        .order_by(m.Notification.created_at.desc(), m.Notification.id.desc())
        .limit(500)
    ).all()
    if mark_id > 0 and mark_id not in {n.id for n in notices}:
        raise ValueError("Notification is not available to this recipient.")
    saved = {
        r.notification_id: r
        for r in session.scalars(
            select(m.NotificationReceipt).where(
                m.NotificationReceipt.user_id == uid,
                m.NotificationReceipt.notification_id.in_(
                    [n.id for n in notices]
                ),
            )
        )
    }
    rows = []
    for notice in notices:
        receipt = saved.get(notice.id)
        if not receipt:
            receipt = m.NotificationReceipt(
                notification_id=notice.id, user_id=uid
            )
            session.add(receipt)
        if mark_id == 0 or mark_id == notice.id:
            receipt.read_state = "read"
            receipt.read_at = dt.datetime.now(dt.UTC)
        rows.append(
            {
                "id": str(notice.id),
                "title": notice.title,
                "body": notice.body,
                "status": receipt.read_state,
            }
        )
    return rows

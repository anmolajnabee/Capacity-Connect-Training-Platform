import reflex as rx
import datetime as dt
import os
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4
from types import SimpleNamespace
import asyncio
import inspect
from sqlalchemy import select, func
from app import models as m
from app.security import sign_session, read_session, SESSION_LIFETIME
from app.services.email_notifications import (
    event_key,
    valid_email,
    render,
    classify,
    backoff,
    enqueue,
    recipients,
    retry_delivery,
    sender_configuration,
    recipient_eligible,
    display_name,
    publication_due,
    queue_sync,
    email_worker,
    PATHS,
)


class EmailContracts(unittest.TestCase):
    def test_deterministic_keys(self):
        self.assertEqual(
            event_key("assignment_deadline", "9/24h", 2),
            event_key("assignment_deadline", "9/24h", 2),
        )
        self.assertNotEqual(
            event_key("assignment_deadline", "9/24h", 2),
            event_key("assignment_deadline", "9/48h", 2),
        )
        self.assertLessEqual(
            len(event_key("announcement_published", "x" * 10000, 1)), 256
        )

    def test_escaping_and_fixed_path(self):
        _, plain, body = render("assessment_result", '<script>"&</script>')
        self.assertNotIn("<script>", body)
        self.assertIn("&lt;script&gt;", body)
        self.assertIn("/trainee/results", plain)
        self.assertNotIn("is_correct", body)
        with self.assertRaises(KeyError):
            render("//evil.example", "test")

    def test_account_recipient_exception_is_narrow(self):
        address = f"{uuid4().hex}@example.org"
        user = SimpleNamespace(email=address, is_active=False)
        for kind in PATHS:
            row = SimpleNamespace(event_type=kind, recipient_email=address)
            self.assertEqual(
                recipient_eligible(user, row),
                kind in ("account_approval", "account_status"),
            )
            self.assertFalse(recipient_eligible(None, row))
            row.recipient_email = f"{uuid4().hex}@example.org"
            self.assertFalse(recipient_eligible(user, row))
        account = m.User(email=address)
        account.id = 1
        for kind in ("account_approval", "account_status"):
            self.assertNotIn(
                "is_active IS true", str(recipients(kind, account))
            )

    def test_future_publication_is_blocked(self):
        moment = dt.datetime.now(dt.UTC)
        future = moment + dt.timedelta(days=2)
        self.assertFalse(publication_due(future))
        self.assertTrue(publication_due(moment - dt.timedelta(days=1)))
        self.assertFalse(publication_due(None))
        source = SimpleNamespace(is_published=True, published_at=future)
        session = MagicMock()
        self.assertEqual(
            queue_sync(session, "announcement_published", source), 0
        )
        session.execute.assert_not_called()
        from app.states.public_state import PublicState
        from app.states.admin_announcement_state import AdminAnnouncementState

        self.assertIn(
            "Announcement.published_at <= func.now()",
            inspect.getsource(PublicState._load_announcements),
        )
        form = {
            "title": "Notice title",
            "body": "A sufficiently long notice body.",
            "audience": "all",
            "published_at": future.strftime("%Y-%m-%d"),
            "publish_now": "on",
        }
        self.assertIn(
            "Publish immediately", AdminAnnouncementState._validate(None, form)
        )
        form["publish_now"] = ""
        self.assertEqual(AdminAnnouncementState._validate(None, form), "")

    def test_trusted_event_names_are_bounded_and_escaped(self):
        session = MagicMock()
        session.get.return_value = SimpleNamespace(
            title="<b>Climate & water</b>\r\n" * 30
        )
        source = SimpleNamespace(
            id=1,
            assignment_id=2,
            assessment_id=3,
            course_id=4,
            feedback="PRIVATE",
            answers="PRIVATE",
        )
        for kind in (
            "announcement_published",
            "assignment_published",
            "assignment_deadline",
            "assessment_deadline",
            "assignment_graded",
            "assessment_result",
            "certificate_issued",
        ):
            name = display_name(session, kind, source)
            self.assertLessEqual(len(name), 120)
            subject, plain, body = render(kind, "Review your workspace.", name)
            self.assertIn("Climate", subject)
            self.assertNotIn("\n", subject)
            self.assertNotIn("<b>", body)
            self.assertIn("&lt;b&gt;", body)
            self.assertNotIn("PRIVATE", plain)

    def test_successful_login_sets_timestamp_before_commit(self):
        from app.states.auth_state import AuthState

        source = inspect.getsource(AuthState.handle_login.fn)
        success = source[source.index("user.failed_login_count = 0") :]
        self.assertIn("user.locked_until = None", success)
        self.assertLess(
            success.index("user.last_login_at = moment"),
            success.index("session.commit()"),
        )

    def test_email_validation(self):
        self.assertTrue(valid_email("person@example.org"))
        for address in (
            "a\nb@example.org",
            "a@localhost",
            "x..y@example.org",
            "Name <a@example.org>",
        ):
            self.assertFalse(valid_email(address))

    def test_retry_classification(self):
        error = RuntimeError("private provider response")
        error.code = 429
        self.assertEqual(classify(error), ("retry", "rate_limited"))
        error.code = 422
        self.assertEqual(classify(error), ("failed", "provider_validation"))
        error.code = 401
        self.assertEqual(classify(error), ("blocked", "provider_configuration"))
        self.assertEqual(backoff(1), 30)
        self.assertLessEqual(backoff(100), 3600)

    def test_expiry_tampering_future_legacy(self):
        with patch.dict(os.environ, {"CC_SESSION_SECRET": "test-only-secret"}):
            with patch("app.security.time.time", return_value=1000000):
                token = sign_session(21)
                self.assertEqual(read_session(token), 21)
                self.assertEqual(read_session(f"22{token[2:]}"), 0)
                self.assertEqual(read_session("21.legacy"), 0)
            with patch(
                "app.security.time.time",
                return_value=1000000 + SESSION_LIFETIME,
            ):
                self.assertEqual(read_session(token), 0)
            with patch("app.security.time.time", return_value=999999):
                self.assertEqual(read_session(token), 0)


class TransportConfiguration(unittest.IsolatedAsyncioTestCase):
    async def test_worker_cancellation_has_no_error_traceback(self):
        with (
            patch(
                "app.services.email_notifications.asyncio.sleep",
                new=AsyncMock(side_effect=asyncio.CancelledError),
            ),
            patch(
                "app.services.email_notifications.logging.exception"
            ) as error_log,
            patch(
                "app.services.email_notifications.safe_log"
            ) as safe_error_log,
            patch("app.services.email_notifications.rx.asession") as session,
            patch("resend.Domains.list") as domains,
            patch("resend.Emails.send") as send,
        ):
            with self.assertRaises(asyncio.CancelledError):
                await email_worker()
            error_log.assert_not_called()
            safe_error_log.assert_not_called()
            session.assert_not_called()
            domains.assert_not_called()
            send.assert_not_called()

    async def test_no_domain_blocks(self):
        with (
            patch.dict(
                os.environ,
                {"RESEND_API_KEY": "test-only", "RESEND_FROM_EMAIL": ""},
            ),
            patch("resend.Domains.list", return_value={"data": []}),
        ):
            self.assertEqual(
                await sender_configuration(), ("", "sender_domain_unverified")
            )


@unittest.skipUnless(
    os.getenv("CC_EMAIL_DATABASE_TESTS") == "1",
    "Requires migrated disposable test database; never production",
)
class DatabaseEmailContracts(unittest.IsolatedAsyncioTestCase):
    async def test_scope_duplicates_deadlines_and_admin_guards(self):
        async with rx.asession() as session:
            try:
                admin = m.User(
                    email=f"{uuid4().hex}@example.org",
                    role="admin",
                    approval_status="approved",
                )
                trainee = m.User(
                    email=f"{uuid4().hex}@example.org", role="trainee"
                )
                dropped = m.User(
                    email=f"{uuid4().hex}@example.org", role="trainee"
                )
                outsider = m.User(
                    email=f"{uuid4().hex}@example.org", role="trainee"
                )
                course = m.Course(
                    code=uuid4().hex, title=f"Course {uuid4().hex}"
                )
                session.add_all([admin, trainee, dropped, outsider, course])
                await session.flush()
                session.add_all(
                    [
                        m.Enrollment(
                            course_id=course.id, trainee_id=trainee.id
                        ),
                        m.Enrollment(
                            course_id=course.id,
                            trainee_id=dropped.id,
                            status="dropped",
                        ),
                    ]
                )
                assignment = m.CourseAssignment(
                    course_id=course.id,
                    status="published",
                    is_published=True,
                    due_at=dt.datetime.now(dt.UTC) + dt.timedelta(hours=23),
                )
                session.add(assignment)
                await session.flush()
                selected = (
                    await session.scalars(
                        recipients("assignment_published", assignment)
                    )
                ).all()
                self.assertEqual([user.id for user in selected], [trainee.id])
                self.assertEqual(
                    await enqueue(session, "assignment_published", assignment),
                    1,
                )
                self.assertEqual(
                    await enqueue(session, "assignment_published", assignment),
                    0,
                )
                self.assertEqual(
                    await enqueue(
                        session, "assignment_deadline", assignment, "24h"
                    ),
                    1,
                )
                self.assertEqual(
                    await enqueue(
                        session, "assignment_deadline", assignment, "24h"
                    ),
                    0,
                )
                session.add(
                    m.AssignmentSubmission(
                        assignment_id=assignment.id,
                        trainee_id=trainee.id,
                        submitted_at=dt.datetime.now(dt.UTC),
                        status="submitted",
                    )
                )
                await session.flush()
                self.assertEqual(
                    await enqueue(
                        session, "assignment_deadline", assignment, "48h"
                    ),
                    0,
                )
                delivery = await session.scalar(
                    select(m.EmailDelivery)
                    .where(m.EmailDelivery.recipient_user_id == trainee.id)
                    .limit(1)
                )
                delivery.status = "accepted"
                self.assertFalse(
                    await retry_delivery(session, admin.id, delivery.id)
                )
                with self.assertRaises(PermissionError):
                    await retry_delivery(session, outsider.id, delivery.id)
                count = await session.scalar(
                    select(func.count())
                    .select_from(m.Notification)
                    .where(m.Notification.user_id == trainee.id)
                )
                self.assertEqual(count, 2)
            finally:
                await session.rollback()


if __name__ == "__main__":
    unittest.main()

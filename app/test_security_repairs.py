import reflex as rx
import ast
import inspect
import io
import logging
from pathlib import Path
import re
import secrets
import unittest
import zipfile
from unittest.mock import AsyncMock, patch

from app.security import (
    validate_resource_content,
    valid_resource_url,
    validate_role,
)
from app.services.evidence import score_to_level
from app.services.private_files import (
    MAX_PRIVATE_FILE_BYTES,
    download_filename,
    private_path,
    read_private,
    validate_filename,
    write_private,
)
from app.models import Certificate
from app.seed import DEMO_ACCESS_PASSWORD, DEMO_ACCOUNTS
from app.states import auth_state
from app.states.auth_state import PORTAL_OPTIONS


class ResourceValidationTests(unittest.TestCase):
    def test_text_formats(self):
        for suffix in (".txt", ".md", ".csv"):
            self.assertTrue(
                validate_resource_content(
                    b"Heading,Value\nRadar,4\n", suffix
                ).startswith("text/")
            )

    def test_binary_text_and_mismatches(self):
        for payload, suffix in (
            (b"hello\x00world", ".txt"),
            (b"MZexecutable", ".pdf"),
            (b"PK\x03\x04payload", ".zip"),
            (b"hello", ".mp4"),
            (b"hello", ".webm"),
            (b"", ".txt"),
        ):
            with self.subTest(suffix=suffix):
                with self.assertRaises((ValueError, UnicodeError)):
                    validate_resource_content(payload, suffix)

    def test_size_bound(self):
        with self.assertRaises(ValueError):
            validate_resource_content(b"x" * (50 * 1024 * 1024 + 1), ".txt")

    def test_office_requires_structure(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("readme.txt", "Not an Office document")
        with self.assertRaises(ValueError):
            validate_resource_content(buffer.getvalue(), ".docx")

    def test_office_and_macro_rejection(self):
        for macro in (False, True):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr(
                    "[Content_Types].xml",
                    '<Types><Override PartName="/word/document.xml" /></Types>',
                )
                archive.writestr("_rels/.rels", "<Relationships />")
                archive.writestr("word/document.xml", "<document />")
                if macro:
                    archive.writestr("word/vbaProject.bin", b"payload")
            if macro:
                with self.assertRaises(ValueError):
                    validate_resource_content(buffer.getvalue(), ".docx")
            else:
                self.assertIn(
                    "wordprocessingml",
                    validate_resource_content(buffer.getvalue(), ".docx"),
                )

    def test_external_url_policy(self):
        self.assertTrue(valid_resource_url("https://example.org/material.pdf"))
        for url in (
            "http://example.org",
            "https:///file",
            "https://user:secret@example.org",
            "javascript:alert(1)",
            "https://localhost",
            "https://bad_host.example",
            "https://example.org/\nfile",
            "https://example.org/" + "x" * 500,
        ):
            self.assertFalse(valid_resource_url(url))


class PrivateFileTests(unittest.TestCase):
    def test_filename_policy_and_bounds(self):
        for value in ("../x", "a/b", "a\\b", "/tmp/x", "", "x" * 129):
            with self.assertRaises(ValueError):
                validate_filename(value)
        with self.assertRaises(ValueError):
            download_filename("Title", "../secret.pdf")

    def test_private_round_trip_and_size_bound(self):
        import tempfile

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict("os.environ", {"CC_PRIVATE_UPLOAD_DIR": directory}),
        ):
            write_private("sample.txt", b"hello")
            self.assertEqual(read_private("sample.txt"), b"hello")
            with self.assertRaises(ValueError):
                write_private("large.txt", b"x" * (MAX_PRIVATE_FILE_BYTES + 1))
            self.assertEqual(
                private_path("sample.txt").parent.resolve(),
                Path(directory).resolve(),
            )


class EvidenceAndTokenTests(unittest.TestCase):
    def test_rubric_boundaries(self):
        for score, level in (
            (0, 1),
            (39.99, 1),
            (40, 2),
            (59.99, 2),
            (60, 3),
            (74.99, 3),
            (75, 4),
            (89.99, 4),
            (90, 5),
            (100, 5),
        ):
            self.assertEqual(score_to_level(score), level)

    def test_demo_access_password_is_server_side_and_exact(self):
        self.assertEqual(DEMO_ACCESS_PASSWORD, "Demo@1234")

    def test_demo_catalog_has_no_secrets(self):
        expected = {
            "trainee@capacityconnect.gov",
            "trainer@capacityconnect.gov",
            "admin@capacityconnect.gov",
        }
        emails = [account["email"] for account in DEMO_ACCOUNTS]
        self.assertEqual(set(emails), expected)
        self.assertEqual(len(emails), len(expected))
        for account in DEMO_ACCOUNTS:
            self.assertEqual(set(account), {"role", "email", "note"})
            self.assertNotIn(DEMO_ACCESS_PASSWORD, account.values())

    def test_portal_and_demo_catalogs_have_no_password_keys(self):
        for name, catalog in (
            ("portals", PORTAL_OPTIONS),
            ("demos", DEMO_ACCOUNTS),
        ):
            self.assertTrue(catalog)
            for index, entry in enumerate(catalog):
                with self.subTest(catalog=name, entry=index):
                    pending = [entry]
                    while pending:
                        value = pending.pop()
                        if isinstance(value, dict):
                            for key, child in value.items():
                                self.assertNotIn(
                                    "password", str(key).casefold()
                                )
                                pending.append(child)
                        elif isinstance(value, (list, tuple)):
                            pending.extend(value)

    def test_auth_state_has_no_password_field_or_demo_value(self):
        source = inspect.getsource(auth_state)
        self.assertNotIn('"password":', source)
        self.assertNotIn("'password':", source)
        self.assertNotIn(DEMO_ACCESS_PASSWORD, source)
        self.assertNotIn("DEMO_PASSWORD", source)
        self.assertNotIn("demo_password", source)

    def test_new_certificate_tokens(self):
        a = Certificate(certificate_number="TEST-A", course_id=1, trainee_id=1)
        b = Certificate(certificate_number="TEST-B", course_id=1, trainee_id=2)
        self.assertEqual(len(a.verification_code), 64)
        self.assertNotEqual(a.verification_code, b.verification_code)
        self.assertNotEqual(a.verification_code, a.certificate_number)


class SecuritySourceContracts(unittest.TestCase):
    """Inspect request-bound handlers without executing events or opening sessions."""

    def handler(self, module: str, class_name: str, method: str):
        path = Path(__file__).resolve().parent / "states" / f"{module}.py"
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception as e:
            logging.exception(f"Error: {e}")
            raise
        owner = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        )
        return next(
            node
            for node in owner.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == method
        )

    def trainee_handler(self, method: str):
        return self.handler(
            "trainee_assessment_state", "TraineeAssessmentState", method
        )

    def trainer_handler(self, method: str):
        return self.handler(
            "trainer_assessment_state", "TrainerAssessmentState", method
        )

    def assert_returning_guard(self, node, condition: str):
        guards = [
            child
            for child in ast.walk(node)
            if isinstance(child, ast.If)
            and condition in ast.unparse(child.test)
        ]
        self.assertTrue(guards, f"Missing rejection guard: {condition}")
        guard = guards[0]
        self.assertTrue(
            any(isinstance(statement, ast.Return) for statement in guard.body),
            f"Guard must return before continuing: {condition}",
        )
        return guard

    def test_submission_locks_owned_attempt_before_validation(self):
        source = ast.unparse(self.trainee_handler("submit_attempt"))
        query = (
            "select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id, "
            "AssessmentAttempt.trainee_id == uid).with_for_update()"
        )
        self.assertIn(query, source)
        self.assertLess(
            source.index(query), source.index("if attempt is None:")
        )
        self.assertLess(source.index(query), source.index("score = 0.0"))

    def test_submission_rejects_expiry_using_server_time(self):
        node = self.trainee_handler("submit_attempt")
        source = ast.unparse(node)
        guard = self.assert_returning_guard(
            node, "now > self._utc_datetime(attempt.expires_at)"
        )
        self.assertLess(
            source.index("now = dt.datetime.now(dt.UTC)"),
            source.index(ast.unparse(guard.test)),
        )
        self.assertIn("attempt.status = 'expired'", ast.unparse(guard))
        self.assertLess(
            guard.end_lineno,
            next(
                child.lineno
                for child in ast.walk(node)
                if isinstance(child, ast.Assign)
                and ast.unparse(child) == "score = 0.0"
            ),
        )

    def test_attempt_handlers_require_current_non_dropped_enrollment(self):
        for method in ("start_attempt", "submit_attempt"):
            with self.subTest(handler=method):
                node = self.trainee_handler(method)
                queries = [
                    ast.unparse(child)
                    for child in ast.walk(node)
                    if isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr == "where"
                    and "Enrollment.status" in ast.unparse(child)
                ]
                self.assertEqual(len(queries), 1)
                for predicate in (
                    "Enrollment.course_id == assessment.course_id",
                    "Enrollment.trainee_id == uid",
                    "Enrollment.status != 'dropped'",
                ):
                    self.assertIn(predicate, queries[0])
                self.assert_returning_guard(node, "not enrolled")

    def test_submission_scores_persisted_options_not_client_claims(self):
        node = self.trainee_handler("submit_attempt")
        source = ast.unparse(node)
        self.assertEqual([arg.arg for arg in node.args.args], ["self"])
        self.assertEqual(node.args.posonlyargs, [])
        self.assertEqual(node.args.kwonlyargs, [])
        self.assertIsNone(node.args.vararg)
        self.assertIsNone(node.args.kwarg)
        scoring_steps = (
            "score = 0.0",
            "option = await session.scalar(select(QuestionOption).where(QuestionOption.id == selected, QuestionOption.question_id == question.id))",
            "is_correct = bool(option is not None and option.is_correct)",
            "awarded = float(question.marks) if is_correct else 0.0",
            "score += awarded",
            "result = AssessmentResult(",
        )
        positions = []
        for step in scoring_steps:
            self.assertIn(step, source)
            positions.append(source.index(step))
        self.assertEqual(positions, sorted(positions))
        self.assertIn("score=score", source)
        self.assertIn("is_passed=is_passed", source)
        self.assertIn("score >= passing", source)

    def test_start_locks_before_counting_attempts_and_snapshots_expiry(self):
        source = ast.unparse(self.trainee_handler("start_attempt"))
        count = source.index("select(func.count(AssessmentAttempt.id))")
        for query in (
            "select(User).where(User.id == uid).with_for_update()",
            "select(Assessment).where(Assessment.id == assessment_id).with_for_update()",
        ):
            self.assertIn(query, source)
            self.assertLess(source.index(query), count)
        self.assertIn("if attempts_used >= assessment.max_attempts:", source)
        for snapshot in (
            "expires = self._utc_datetime(now + dt.timedelta(minutes=assessment.time_limit_minutes))",
            "expires = min(expires, self._utc_datetime(assessment.deadline_at))",
            "started_at=now, expires_at=expires",
        ):
            self.assertIn(snapshot, source)
            self.assertLess(
                source.index(snapshot), source.index("session.add(attempt)")
            )

    def test_public_certificate_where_uses_only_verification_token(self):
        node = self.handler(
            "certificate_verification_state",
            "CertificateVerificationState",
            "load",
        )
        queries = [
            child.args[0].value
            for child in ast.walk(node)
            if isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == "text"
            and child.args
            and isinstance(child.args[0], ast.Constant)
            and isinstance(child.args[0].value, str)
        ]
        lookups = [
            query for query in queries if "FROM cc_certificate cert" in query
        ]
        self.assertEqual(len(lookups), 1)
        where = re.split(r"\bWHERE\b", lookups[0], flags=re.IGNORECASE)[1]
        where = re.split(r"\bLIMIT\b", where, flags=re.IGNORECASE)[0].strip()
        self.assertRegex(where, r"^cert\.verification_code\s*=\s*:number$")
        self.assertNotIn("certificate_number", where.lower())

    def test_question_mutations_reject_non_draft_before_writes(self):
        for method in ("save_question", "delete_question"):
            with self.subTest(handler=method):
                node = self.trainer_handler(method)
                guard = self.assert_returning_guard(
                    node, "assessment.status != 'draft'"
                )
                writes = [
                    child
                    for child in ast.walk(node)
                    if isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and ast.unparse(child.func.value) == "session"
                    and child.func.attr in {"add", "delete", "flush", "commit"}
                ]
                self.assertTrue(writes)
                self.assertLess(
                    guard.end_lineno, min(child.lineno for child in writes)
                )

    def test_publishing_requires_each_questions_competency(self):
        node = self.trainer_handler("publish_assessment")
        loops = [
            child
            for child in ast.walk(node)
            if isinstance(child, ast.For)
            and ast.unparse(child.target) == "question"
            and ast.unparse(child.iter) == "questions"
        ]
        self.assertEqual(len(loops), 1)
        guard = self.assert_returning_guard(
            loops[0], "question.competency_id is None"
        )
        publish = [
            child
            for child in ast.walk(node)
            if isinstance(child, ast.Assign)
            and ast.unparse(child)
            == "assessment.status = AssessmentStatus.OPEN.value"
        ]
        self.assertEqual(len(publish), 1)
        self.assertLess(guard.end_lineno, publish[0].lineno)


class FreshRoleValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_cookie_denied_without_database(self):
        state = AsyncMock()
        auth = AsyncMock()
        auth.session_cookie = "invalid"
        state.get_state.return_value = auth
        with patch("app.security.rx.asession") as session:
            self.assertEqual(await validate_role(state, "trainer"), 0)
            session.assert_not_called()

    async def test_live_database_decision_not_cached_identity(self):
        state = AsyncMock()
        auth = AsyncMock()
        auth.session_cookie = "signed-cookie"
        auth.user_id = 999
        auth.role = "trainer"
        auth.approval_status = "approved"
        state.get_state.return_value = auth
        session = AsyncMock()
        session.scalar.return_value = None
        context = AsyncMock()
        context.__aenter__.return_value = session
        with (
            patch("app.security.read_session", return_value=7),
            patch("app.security.rx.asession", return_value=context),
        ):
            self.assertEqual(await validate_role(state, "trainer"), 0)
            session.scalar.assert_awaited_once()
            session.scalar.return_value = 7
            self.assertEqual(await validate_role(state, "trainer"), 7)


if __name__ == "__main__":
    unittest.main()

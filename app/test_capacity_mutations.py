import reflex as rx
import ast
import datetime as dt
import inspect
import unittest
from unittest.mock import patch
from app import models as m
from app.services.evidence import qualifying
from app.services.trainer_fit import WEIGHTS, weighted_score
from app.services.team_coverage import greedy_cover
from app.services.notifications import recipient_query
from app.services.capacity_ai import fallback, sanitize, answer
from app.states import practice_state


class CapacityMutationContracts(unittest.TestCase):
    def test_proficiency_requires_qualifying_verified_measurement(self):
        now = dt.datetime.now(dt.UTC)
        e = m.CompetencyEvidence(
            user_id=1,
            competency_id=1,
            source_reference="test",
            evidence_type="trainer_evaluation",
            measured_level=3,
            verification_status="verified",
            verifier_id=2,
            observed_at=now,
            verified_at=now,
        )
        self.assertTrue(qualifying(e))
        for kind in ["practice", "course_completion"]:
            e.evidence_type = kind
            self.assertFalse(qualifying(e))
        e.evidence_type = "trainer_evaluation"
        e.verification_status = "pending"
        self.assertFalse(qualifying(e))
        e.verification_status = "verified"
        e.measured_level = None
        self.assertFalse(qualifying(e))

    def test_fit_arithmetic(self):
        self.assertEqual(list(WEIGHTS.values()), [40, 25, 15, 10, 10])
        scores = dict(zip(WEIGHTS, [80, 60, 90, 100, 40]))
        self.assertAlmostEqual(weighted_score(scores), 74.5)
        composite = (
            scores["competency_coverage"] * 40
            + scores["domain_alignment"] * 25
            + scores["qualification"] * 10
        ) / 75
        self.assertAlmostEqual(
            weighted_score(scores),
            (
                composite * 75
                + scores["experience"] * 15
                + scores["observed_effectiveness"] * 10
            )
            / 100,
        )

    def test_greedy_coverage_and_no_empty_members(self):
        required = {1, 2, 3}
        candidates = {4: {1, 2}, 7: {2, 3}, 9: set()}
        chosen = greedy_cover(required, candidates)
        self.assertEqual(chosen, [4, 7])
        self.assertEqual(
            set().union(*(candidates[k] for k in chosen)), required
        )
        self.assertEqual(greedy_cover({9}, candidates), [])
        self.assertEqual(greedy_cover(required, {1: required, 2: {1}}), [1])

    def test_notification_ownership_scope_is_bound(self):
        query = recipient_query(37, "trainee")
        sql = str(query)
        self.assertIn("cc_notification.user_id", sql)
        self.assertIn("cc_enrollment.trainee_id", sql)
        self.assertIn("cc_user_organization_assignment.user_id", sql)
        self.assertIn(37, query.compile().params.values())
        self.assertNotIn("37", sql)

    def test_practice_has_no_official_writes(self):
        tree = ast.parse(inspect.getsource(practice_state))
        model_attributes = {
            n.attr
            for n in ast.walk(tree)
            if isinstance(n, ast.Attribute)
            and isinstance(n.value, ast.Name)
            and n.value.id == "m"
        }
        self.assertNotIn("AssessmentResult", model_attributes)
        self.assertNotIn("QuestionOption", model_attributes)
        self.assertNotIn("UserCompetency", model_attributes)
        self.assertNotIn("CompetencyEvidence", model_attributes)
        self.assertIn("PracticeQuestionOption", model_attributes)

    def test_grounded_fallback_is_explicit_and_bounded(self):
        text = fallback("Explain Mistake", [], [], "")
        self.assertIn("Database-grounded fallback", text)
        self.assertIn("No approved resource text", text)
        self.assertIn("cannot disclose", text)
        self.assertNotIn("verified level 5", text)
        self.assertEqual(sanitize("password=secret-value"), "[redacted]")
        self.assertLessEqual(len(sanitize("x" * 30000)), 20000)
        self.assertTrue(callable(rx.asession))


class AssistantFallbackContract(unittest.IsolatedAsyncioTestCase):
    async def test_missing_key_does_not_require_network(self):
        with patch.dict("os.environ", {"GOOGLE_API_KEY": ""}):
            result, model = await answer("Explain Concept", "", [], [], "")
        self.assertEqual(model, "database-fallback")
        self.assertIn("Database-grounded fallback", result)


if __name__ == "__main__":
    unittest.main()

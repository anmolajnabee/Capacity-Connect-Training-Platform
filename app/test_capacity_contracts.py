import reflex as rx
import unittest
from app.states.competency_workspace_state import GAP_CTE
from app.states.registry_workspace_state import QUERIES


class CapacityReadContracts(unittest.TestCase):
    def test_gap_baseline_is_evidence_bound(self):
        self.assertIn("e.measured_level=uc.current_level", GAP_CTE)
        self.assertIn("e.verified_at=uc.last_verified_at", GAP_CTE)
        self.assertIn(
            "e.evidence_type NOT IN ('practice','course_completion')", GAP_CTE
        )
        self.assertNotIn("cc_user_skill", GAP_CTE)
        self.assertNotIn("COALESCE(v.current_level,0)", GAP_CTE)

    def test_registry_queries_remain_read_only(self):
        for name, query in QUERIES.items():
            with self.subTest(view=name):
                for operation in (
                    "INSERT INTO",
                    "UPDATE cc_",
                    "DELETE FROM",
                    "ALTER TABLE",
                    "CREATE TABLE",
                ):
                    self.assertNotIn(operation.lower(), query.lower())
                self.assertTrue(":uid" in query or ":role" in query)

    def test_formative_records_do_not_expose_official_keys(self):
        self.assertNotIn("cc_question_option", QUERIES["practice"])
        self.assertNotIn("cc_assessment_result", QUERIES["practice"])
        self.assertIn("pa.user_id=:uid", QUERIES["practice"])

    def test_effectiveness_is_verified_and_paired(self):
        self.assertIn(
            "o.verification_status='verified'", QUERIES["effectiveness"]
        )
        self.assertIn(
            "post.observed_at>pre.observed_at", QUERIES["effectiveness"]
        )
        self.assertIn(
            "observed_competency_improvement", QUERIES["effectiveness"]
        )
        self.assertNotIn("cc_practice_attempt", QUERIES["effectiveness"])

    def test_state_uses_reflex(self):
        self.assertTrue(callable(rx.asession))


if __name__ == "__main__":
    unittest.main()

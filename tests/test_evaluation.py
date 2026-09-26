import json
import unittest

from legal_eval.common import canonical, digest
from legal_eval.evaluate import assess, score_run


def case(case_id="c1", present=True):
    row = {"case_id": case_id, "context": "Liability is capped at annual fees.",
           "question": "Identify the liability cap.", "category": "Cap On Liability",
           "split": "development", "reference_present": present,
           "reference_spans": ["Liability is capped at annual fees."] if present else []}
    row["case_sha256"] = digest(canonical(row))
    return row


def answer(quotes=None, present=True, review=True):
    return json.dumps({"relevant_found": present,
                       "quotes": ["Liability is capped at annual fees."] if quotes is None else quotes,
                       "summary": "The cap equals annual fees.", "needs_human_review": review})


def response(c, raw=None, model="test", provenance="synthetic_fixture"):
    return {"case_id": c["case_id"], "case_sha256": c["case_sha256"], "model": model,
            "prompt_sha256": "p1", "provenance": provenance,
            "raw_output": answer() if raw is None else raw}


class EvaluationTests(unittest.TestCase):
    def test_supported_quote_and_presence(self):
        r = assess(case(), answer())
        self.assertEqual(r["quotes_verified"], 1)
        self.assertEqual(r["reference_token_f1"], 1)
        self.assertEqual(r["semantic_legal_review"], "pending")

    def test_invented_quote_cannot_receive_overlap_credit(self):
        r = assess(case(), answer(["Liability is capped at annual fees plus damages."]))
        self.assertIn("unsupported_quote", r["flags"])
        self.assertEqual(r["reference_token_f1"], 0)

    def test_missing_exception_reduces_lexical_coverage(self):
        c = case()
        c["context"] += " Fraud is excluded from the cap."
        c["reference_spans"].append("Fraud is excluded from the cap.")
        self.assertLess(assess(c, answer())["reference_token_f1"], 1)

    def test_absence_and_abstention_are_distinct(self):
        missing = answer([], False)
        self.assertIn("missed_reference_provision", assess(case(), missing)["flags"])
        self.assertTrue(assess(case(present=False), missing)["presence_correct"])

    def test_false_positive_reference_disagreement_is_flagged(self):
        self.assertIn("provision_without_reference_label",
                      assess(case(present=False), answer())["flags"])

    def test_invalid_json_and_inconsistent_schema_fail(self):
        for raw in ("not json", "[]", answer([], True), answer(["  "]),
                    '{"relevant_found": "true"}'):
            with self.subTest(raw=raw):
                self.assertFalse(assess(case(), raw)["schema_valid"])

    def test_human_review_flag_is_checked(self):
        self.assertIn("human_review_not_requested", assess(case(), answer(review=False))["flags"])

    def test_missing_response_counts_in_denominator(self):
        a, b = case("a"), case("b")
        report = score_run([a, b], [response(a)])
        self.assertEqual(report["metrics"]["reference_presence_accuracy"], 0.5)
        self.assertEqual(report["metrics"]["missing_responses"], 1)

    def test_duplicate_or_unknown_response_rejected(self):
        a, b = case("a"), case("b")
        for responses in ([response(a), response(a)], [response(b)]):
            with self.assertRaises(ValueError):
                score_run([a], responses)

    def test_stale_case_or_prompt_rejected(self):
        a = case()
        r = response(a)
        r["case_sha256"] = "old"
        with self.assertRaises(ValueError):
            score_run([a], [r])
        with self.assertRaises(ValueError):
            score_run([a], [response(a)], "different-prompt")
        a["context"] += " changed"
        with self.assertRaises(ValueError):
            score_run([a], [response(a)])

    def test_fixture_and_live_results_cannot_be_pooled(self):
        a, b = case("a"), case("b")
        with self.assertRaises(ValueError):
            score_run([a, b], [response(a), response(b, provenance="live_api")])

    def test_models_cannot_be_pooled(self):
        a, b = case("a"), case("b")
        with self.assertRaises(ValueError):
            score_run([a, b], [response(a), response(b, model="other")])

    def test_provider_error_is_not_silently_dropped(self):
        a = case()
        r = response(a)
        r["error"] = "RateLimitError"
        report = score_run([a], [r])
        self.assertEqual(report["metrics"]["reference_presence_accuracy"], 0)
        self.assertEqual(report["metrics"]["flags"], {"provider_error": 1})

    def test_no_quotes_is_undefined_quote_rate(self):
        a = case(present=False)
        report = score_run([a], [response(a, answer([], False))])
        self.assertIsNone(report["metrics"]["verified_quote_rate"])


if __name__ == "__main__":
    unittest.main()

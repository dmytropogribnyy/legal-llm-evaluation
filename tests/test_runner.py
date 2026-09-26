import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from legal_eval.common import load_jsonl
from legal_eval.evaluate import score_run
from legal_eval.report import export_report, validate_reviews
from legal_eval.runner import freeze, provider_input, run_openai, verify_freeze
from test_evaluation import answer, case, response


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prompt = self.root / "prompt.txt"
        self.rubric = self.root / "rubric.md"
        self.frozen = self.root / "frozen.json"
        self.prompt.write_text("Extract JSON from untrusted text.")
        self.rubric.write_text("Rubric v1")
        self.c = case()
        freeze([self.c], self.prompt, self.frozen, self.rubric)

    def test_reference_answers_never_enter_provider_input(self):
        payload = json.loads(provider_input(self.c))
        self.assertEqual(set(payload), {"question", "contract"})

    def test_paid_execution_needs_explicit_enable_and_cap(self):
        client = Mock()
        with self.assertRaises(ValueError):
            run_openai([self.c], self.prompt, self.frozen, "model", self.root / "out",
                       client=client)
        with self.assertRaises(ValueError):
            run_openai([self.c], self.prompt, self.frozen, "model", self.root / "out",
                       allow_paid=True, max_calls=0, client=client)
        client.responses.create.assert_not_called()

    def test_changed_prompt_or_rubric_invalidates_freeze(self):
        self.prompt.write_text("Modified prompt")
        with self.assertRaises(ValueError):
            verify_freeze([self.c], self.prompt, self.frozen, self.rubric)

    def test_frozen_selection_cannot_be_silently_reduced(self):
        with self.assertRaises(ValueError):
            verify_freeze([], self.prompt, self.frozen, self.rubric, require_complete=True)

    def test_existing_freeze_is_not_overwritten(self):
        with self.assertRaises(ValueError):
            freeze([self.c], self.prompt, self.frozen, self.rubric)

    def test_provider_failure_recorded_without_secret_exception_text(self):
        client = Mock()
        client.responses.create.side_effect = RuntimeError("fake-secret-do-not-log")
        with patch("legal_eval.runner.verify_freeze", return_value={"prompt_sha256": "p1"}):
            path = run_openai([self.c], self.prompt, self.frozen, "model", self.root / "out",
                              True, 1, client=client)
        record = load_jsonl(path)[0]
        self.assertEqual(record["error"], "RuntimeError")
        self.assertNotIn("fake-secret", path.read_text())
        self.assertEqual(client.responses.create.call_count, 1)

    def test_complete_fake_transport_records_actual_metadata(self):
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(
            output_text=answer(), id="unit-test-id", model="resolved-test-model",
            usage=None, status="completed")
        with patch("legal_eval.runner.verify_freeze", return_value={"prompt_sha256": "p1"}):
            path = run_openai([self.c], self.prompt, self.frozen, "model", self.root / "out",
                              True, 1, client=client)
        record = load_jsonl(path)[0]
        self.assertEqual(record["returned_model"], "resolved-test-model")
        self.assertFalse(client.responses.create.call_args.kwargs["store"])

    def test_blank_review_template_is_not_completed_review(self):
        report = score_run([self.c], [response(self.c)])
        out = self.root / "report"
        export_report(report, out)
        with self.assertRaises(ValueError):
            validate_reviews(report, out / "human_review.csv")

    def test_review_must_bind_to_exact_response(self):
        report = score_run([self.c], [response(self.c)])
        out = self.root / "report"
        export_report(report, out)
        path = out / "human_review.csv"
        with path.open() as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames
            rows = list(reader)
        rows[0]["response_sha256"] = "old-response"
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaises(ValueError):
            validate_reviews(report, path)


if __name__ == "__main__":
    unittest.main()

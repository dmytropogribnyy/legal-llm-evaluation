"""Regression cases found during the v0.3.1 audit; no network or model inference."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from legal_eval.common import canonical, digest, load_json, load_jsonl
from legal_eval.evaluate import score_run
from legal_eval.report import REVIEW_FIELDS, export_report, validate_reviews
from legal_eval.runner import freeze, run_openai, verify_freeze
from test_evaluation import answer, case, response


def rehash(c):
    c.pop("case_sha256", None)
    c["case_sha256"] = digest(canonical(c))
    return c


class AuditGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prompt = self.root / "prompt.txt"
        self.prompt.write_text("Extract JSON from untrusted source text.")
        self.cases = [case("first"), case("second")]
        self.frozen = self.root / "freeze.json"
        freeze(self.cases, self.prompt, self.frozen)

    def client(self):
        c = Mock()
        c.responses.create.return_value = SimpleNamespace(
            output_text=answer(), id="fixture-response", model="resolved-fixture-v1",
            usage=None, status="completed")
        return c

    def run_fake(self, client, name="run", **kwargs):
        return run_openai(self.cases, self.prompt, self.frozen, "fixture-alias",
                          self.root / name, True, 2, client=client, **kwargs)

    def test_empty_and_duplicate_freezes_are_rejected(self):
        for cases in ([], [self.cases[0], self.cases[0]]):
            with self.assertRaises(ValueError):
                freeze(cases, self.prompt, self.root / "bad-freeze.json")
            self.assertFalse((self.root / "bad-freeze.json").exists())

    def test_duplicate_frozen_input_fails_before_provider_call(self):
        self.cases.append(self.cases[0])
        client = self.client()
        with self.assertRaises(ValueError):
            run_openai(self.cases, self.prompt, self.frozen, "fixture", self.root / "run",
                       True, 3, client=client)
        client.responses.create.assert_not_called()

    def test_full_selection_protocol_checked_at_freeze_and_verification(self):
        c = rehash(dict(self.cases[0], selection_protocol="cuad-full-corpus-v1",
                        selection_protocol_sha256=digest(Path("docs/FULL_CORPUS_PROTOCOL.md").read_bytes())))
        frozen = self.root / "full-freeze.json"
        freeze([c], self.prompt, frozen)
        original = Path.read_bytes
        def changed(path):
            return b"changed full selection document" if str(path).replace("\\", "/") == "docs/FULL_CORPUS_PROTOCOL.md" else original(path)
        with patch.object(Path, "read_bytes", changed):
            with self.assertRaisesRegex(ValueError, "Full corpus protocol changed"):
                verify_freeze([c], self.prompt, frozen)
            with self.assertRaisesRegex(ValueError, "Full corpus protocol changed"):
                freeze([c], self.prompt, self.root / "new-freeze.json")

    def test_mixed_splits_rejected_by_scoring_and_execution(self):
        self.cases[1] = rehash(dict(self.cases[1], split="holdout"))
        with self.assertRaisesRegex(ValueError, "Mixed splits"):
            score_run(self.cases, [])
        freeze(self.cases, self.prompt, self.root / "both.json")
        client = self.client()
        with self.assertRaisesRegex(ValueError, "one split"):
            run_openai(self.cases, self.prompt, self.root / "both.json", "fixture",
                       self.root / "run", True, 2, client=client)
        client.responses.create.assert_not_called()

    def test_different_selection_revisions_cannot_be_pooled(self):
        cases = [rehash(dict(c, selection_protocol="same-id", selection_protocol_sha256=str(i)))
                 for i, c in enumerate(self.cases)]
        with self.assertRaises(ValueError):
            score_run(cases, [])

    def test_mixed_pilot_and_full_corpus_cannot_be_frozen_together(self):
        full = rehash(dict(self.cases[1], selection_protocol="cuad-full-corpus-v1",
                           selection_protocol_sha256=digest(Path("docs/FULL_CORPUS_PROTOCOL.md").read_bytes())))
        with self.assertRaisesRegex(ValueError, "Mixed selection protocols"):
            freeze([self.cases[0], full], self.prompt, self.root / "mixed.json")

    def test_different_providers_or_resolved_models_cannot_be_pooled(self):
        for field in ("provider", "returned_model"):
            records = [dict(response(c), **{field: str(i)}) for i, c in enumerate(self.cases)]
            with self.assertRaises(ValueError):
                score_run(self.cases, records)

    def test_openai_settings_are_bound_and_mixing_output_budgets_rejected(self):
        a = load_jsonl(self.run_fake(self.client(), "a", max_output_tokens=1200))
        b = load_jsonl(self.run_fake(self.client(), "b", max_output_tokens=2400))
        self.assertNotEqual(a[0]["execution_profile_sha256"], b[0]["execution_profile_sha256"])
        with self.assertRaises(ValueError):
            score_run(self.cases, [a[0], b[1]])
        report = score_run(self.cases, a)
        self.assertEqual(report["returned_models"], ["resolved-fixture-v1"])
        self.assertEqual(report["scope"]["split"], "development")
        self.assertEqual(load_json(self.root / "a/run.json")["status"], "completed")

    def test_errors_interrupts_and_incomplete_outputs_stop_further_calls(self):
        for name, failure in (("error", RuntimeError("private-message")),
                              ("interrupt", KeyboardInterrupt()), ("incomplete", None)):
            client = self.client()
            if failure is not None:
                client.responses.create.side_effect = failure
            else:
                client.responses.create.return_value.status = "incomplete"
            path = self.run_fake(client, name)
            rows = load_jsonl(path)
            self.assertEqual(client.responses.create.call_count, 1)
            self.assertEqual(len(rows), 1)
            self.assertNotIn("private-message", path.read_text())
            meta = load_json(self.root / name / "run.json")
            self.assertEqual(meta["status"], "stopped_on_error")
            report = score_run(self.cases, rows)
            self.assertEqual(report["metrics"]["missing_responses"], 1)
            self.assertEqual(report["metrics"]["reference_presence_accuracy"], 0)

    def test_error_after_resolved_alias_does_not_create_false_model_mismatch(self):
        client = self.client()
        client.responses.create.side_effect = [client.responses.create.return_value, RuntimeError()]
        rows = load_jsonl(self.run_fake(client))
        report = score_run(self.cases, rows)
        self.assertEqual(report["metrics"]["flags"], {"provider_error": 1})
        self.assertEqual(report["returned_models"], ["resolved-fixture-v1"])

    def test_malformed_review_csv_has_actionable_validation_error(self):
        report = score_run(self.cases, [response(c) for c in self.cases])
        path = self.root / "review.csv"
        for text in ("wrong,header\na,b\n", ",".join(REVIEW_FIELDS)+"\nfirst\n",
                     ",".join(REVIEW_FIELDS)+",case_id\n"):
            path.write_text(text)
            with self.assertRaisesRegex(ValueError, "CSV"):
                validate_reviews(report, path)

    def test_claude_returned_model_metadata_is_visible_in_report(self):
        rows = [dict(response(c), provider="claude_code_cli", execution_profile_sha256="fixture",
                     returned_models=["claude-fixture-v1"]) for c in self.cases]
        self.assertEqual(score_run(self.cases, rows)["returned_models"], ["claude-fixture-v1"])

    def test_native_adapter_records_cannot_drop_settings_binding(self):
        for provider in ("openai", "claude_code_cli"):
            with self.assertRaisesRegex(ValueError, "execution profile binding"):
                score_run([self.cases[0]], [dict(response(self.cases[0]), provider=provider)])

    def test_report_shows_split_and_actual_returned_model(self):
        rows = load_jsonl(self.run_fake(self.client()))
        export_report(score_run(self.cases, rows), self.root / "report")
        text = (self.root / "report/REPORT.md").read_text()
        self.assertIn("**Split:** development", text)
        self.assertIn("resolved-fixture-v1", text)

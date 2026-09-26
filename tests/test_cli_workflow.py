"""Cross-process operator workflow on isolated source fixtures; never invokes an LLM."""

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from legal_eval.common import digest, load_json, load_jsonl, save_json, write_jsonl
from legal_eval.report import REVIEW_FIELDS


class CliWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="legal eval CLI ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = Path(__file__).resolve().parents[1]
        for folder in ("legal_eval", "docs", "prompts"):
            shutil.copytree(
                source / folder,
                self.root / folder,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        documents, pilot = [], []
        for i in range(3):
            text = f"Fixture {i}: liability cap is 10 euros. Unicode: café\\u2028section.".replace(
                "\\u2028", "\u2028"
            )
            title = f"Offline fixture {i}"
            qas = [
                {
                    "id": title + "__" + cat,
                    "question": "Find " + cat,
                    "is_impossible": cat == "Governing Law",
                    "answers": []
                    if cat == "Governing Law"
                    else [{"answer_start": 0, "text": text}],
                }
                for cat in ("Cap On Liability", "Governing Law")
            ]
            documents.append(
                {"title": title, "paragraphs": [{"context": text, "qas": qas}]}
            )
            pilot.append(
                {
                    "contract_sha256": digest(text),
                    "split": "holdout" if i == 2 else "development",
                }
            )
        raw = self.root / "data/raw/CUAD_v1.json"
        save_json(raw, {"data": documents})
        save_json(
            self.root / "data/source.json",
            {
                "sha256": digest(raw.read_bytes()),
                "size_bytes": raw.stat().st_size,
                "revision": "offline-fixture",
                "url": "https://example.invalid/never-requested",
            },
        )
        save_json(self.root / "data/selection_manifest.json", {"cases": pilot})
        self.env = dict(os.environ, PYTHONUTF8="1")
        self.env.pop("PYTHONPATH", None)

    def cli(self, *args, ok=True):
        result = subprocess.run(
            [sys.executable, "-m", "legal_eval", *args],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def batch(self):
        self.cli("fetch")  # Verified cache; fixture URL is never contacted.
        self.cli("prepare-corpus")
        self.cli("corpus-batch", "--limit", "3", "--out", "runs/batch")
        self.cli(
            "freeze",
            "--cases",
            "runs/batch/cases.jsonl",
            "--out",
            "runs/batch/freeze.json",
        )
        self.cli(
            "export-claude",
            "--cases",
            "runs/batch/cases.jsonl",
            "--frozen",
            "runs/batch/freeze.json",
            "--out",
            "runs/input",
        )
        return load_jsonl(self.root / "runs/batch/cases.jsonl")

    def score(self, ok=True):
        return self.cli(
            "score",
            "--cases",
            "runs/batch/cases.jsonl",
            "--frozen",
            "runs/batch/freeze.json",
            "--responses",
            "runs/responses.jsonl",
            "--out",
            "runs/report",
            ok=ok,
        )

    def test_complete_offline_operator_workflow_with_review_validation(self):
        cases = self.batch()
        manifest = load_json(self.root / "runs/input/bundle.json")
        for task in manifest["tasks"]:
            self.assertEqual(
                set(load_json(self.root / "runs/input" / task["file"])),
                {"question", "contract"},
            )
        prompt_hash = load_json(self.root / "runs/batch/freeze.json")["prompt_sha256"]
        rows = [
            {
                "case_id": c["case_id"],
                "case_sha256": c["case_sha256"],
                "model": "offline-fixture-not-a-model",
                "provenance": "synthetic_fixture",
                "prompt_sha256": prompt_hash,
                "raw_output": json.dumps(
                    {
                        "relevant_found": c["reference_present"],
                        "quotes": c["reference_spans"],
                        "summary": "Controlled fixture only",
                        "needs_human_review": True,
                    }
                ),
            }
            for c in cases
        ]
        write_jsonl(self.root / "runs/responses.jsonl", rows)
        self.score()
        report = load_json(self.root / "runs/report/metrics.json")
        self.assertEqual(report["metrics"]["received_responses"], 3)
        self.assertIn(
            "Evaluator self-check", (self.root / "runs/report/REPORT.md").read_text()
        )
        # This only tests CSV validation; these are NOT human legal reviews.
        with (self.root / "runs/report/human_review.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS)
            writer.writeheader()
            for row in report["rows"]:
                review = {
                    f: "Offline validation fixture; not a human review"
                    for f in REVIEW_FIELDS
                }
                review.update(
                    case_id=row["case_id"],
                    response_sha256=row["response_sha256"],
                    reviewed_at_utc="2026-09-26T00:00:00+00:00",
                    severity="none",
                    disposition="accept",
                )
                for f in REVIEW_FIELDS:
                    if f.endswith("_0_2"):
                        review[f] = "0"
                writer.writerow(review)
        result = self.cli(
            "validate-review",
            "--report",
            "runs/report/metrics.json",
            "--reviews",
            "runs/report/human_review.csv",
        )
        self.assertEqual(json.loads(result.stdout)["complete_reviews"], 3)
        self.assertFalse(json.loads(result.stdout)["identity_independently_verified"])
        self.cli(
            "freeze",
            "--cases",
            "runs/batch/cases.jsonl",
            "--out",
            "runs/batch/freeze.json",
            ok=False,
        )
        self.score(ok=False)  # Reports cannot overwrite existing evidence.

    def test_empty_responses_remain_missing_and_stale_case_cannot_be_scored(self):
        self.batch()
        write_jsonl(self.root / "runs/responses.jsonl", [])
        self.score()
        report = load_json(self.root / "runs/report/metrics.json")
        self.assertEqual(report["metrics"]["missing_responses"], 3)
        cases = load_jsonl(self.root / "runs/batch/cases.jsonl")
        cases[0]["context"] += " changed"
        write_jsonl(self.root / "runs/batch/cases.jsonl", cases)
        result = self.cli(
            "score",
            "--cases",
            "runs/batch/cases.jsonl",
            "--frozen",
            "runs/batch/freeze.json",
            "--responses",
            "runs/responses.jsonl",
            "--out",
            "runs/rejected",
            ok=False,
        )
        self.assertIn("Case content changed", result.stderr)
        self.assertFalse((self.root / "runs/rejected").exists())

    def test_damaged_cached_source_rejected_without_preparation(self):
        (self.root / "data/raw/CUAD_v1.json").write_text("broken source")
        result = self.cli("fetch", ok=False)
        self.assertIn("size/hash mismatch", result.stderr)
        self.assertFalse((self.root / "data/prepared").exists())

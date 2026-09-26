import copy
import json
import tempfile
import unittest
from pathlib import Path

from legal_eval.claude_code import export_bundle, read_bundle
from legal_eval.common import canonical, digest, load_json, load_jsonl, save_json
from legal_eval.corpus import build_catalog, inspect_contract, make_batch, prepare_corpus
from legal_eval.runner import freeze, verify_freeze


def document(title, text, present=True):
    return {"title": title, "paragraphs": [{"context": text, "qas": [
        {"id": title + "__" + category, "question": "Find " + category,
         "answers": [{"answer_start": 0, "text": text[:5]}] if present else [],
         "is_impossible": not present} for category in ("Alpha", "Beta")]}]}


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = {"data": [document("A", "First complete contract."),
                             document("B", "Second complete contract.", False),
                             document("C", "Third complete contract."),
                             document("D", "Third complete contract.")]}
        self.pilot = {"cases": [{"contract_sha256": digest(d["paragraphs"][0]["context"]),
                                 "split": "holdout" if d["title"] == "B" else "development"}
                                for d in self.raw["data"]]}
        self.source = {"sha256": "fixture", "revision": "fixture", "url": "fixture"}

    def prepare(self, raw=None):
        raw = self.raw if raw is None else raw
        raw_file = self.root / "source.json"
        save_json(raw_file, raw)
        self.source["sha256"] = digest(raw_file.read_bytes())
        save_json(self.root / "pin.json", self.source)
        save_json(self.root / "pilot.json", self.pilot)
        folder = self.root / "catalog"
        summary = prepare_corpus(raw_file, folder, self.root / "pin.json", self.root / "pilot.json")
        return folder, summary

    def test_exact_duplicates_share_split_and_only_one_is_eligible(self):
        contracts, tasks, summary = build_catalog(self.raw, self.source, self.pilot)
        self.assertEqual((len(contracts), len(tasks), summary["eligible_deduplicated_tasks"]), (3, 8, 6))
        self.assertEqual(sum(t["duplicate_suppressed"] for t in tasks), 2)
        for contract in contracts:
            self.assertEqual({t["split"] for t in tasks if t["contract_sha256"] == contract["contract_sha256"]},
                             {contract["split"]})

    def test_disagreeing_duplicate_annotations_are_quarantined(self):
        self.raw["data"][-1]["paragraphs"][0]["qas"][0].update(answers=[], is_impossible=True)
        _, tasks, summary = build_catalog(self.raw, self.source, self.pilot)
        self.assertEqual(summary["conflicting_unique_contract_categories"], 1)
        self.assertEqual(summary["eligible_deduplicated_tasks"], 5)
        ambiguous = [t for t in tasks if t["annotation_conflict"]]
        self.assertEqual(len(ambiguous), 2)
        folder, _ = self.prepare()
        batch = make_batch(folder, self.root / "batch")
        selected = load_jsonl(self.root / "batch/cases.jsonl")
        self.assertFalse(any(c["annotation_conflict"] or c["duplicate_suppressed"] for c in selected))
        self.assertEqual(batch["selected_tasks"], 3)

    def test_bad_offsets_and_presence_fail_closed(self):
        for mode in ("offset", "presence"):
            raw = copy.deepcopy(self.raw)
            qa = raw["data"][0]["paragraphs"][0]["qas"][0]
            if mode == "offset":
                qa["answers"][0]["answer_start"] = -1
            else:
                qa["is_impossible"] = True
            with self.assertRaises(ValueError):
                build_catalog(raw, self.source, self.pilot)

    def test_source_hash_and_conflicting_pilot_fail(self):
        self.pilot["cases"].append({"contract_sha256": self.pilot["cases"][0]["contract_sha256"], "split": "holdout"})
        with self.assertRaises(ValueError):
            build_catalog(self.raw, self.source, self.pilot)
        save_json(self.root / "raw.json", self.raw)
        save_json(self.root / "pin.json", self.source)
        with self.assertRaises(ValueError):
            prepare_corpus(self.root / "raw.json", self.root / "out", self.root / "pin.json")

    def test_source_order_does_not_change_selection(self):
        a = build_catalog(self.raw, self.source, {"cases": []})
        self.raw["data"].reverse()
        b = build_catalog(self.raw, self.source, {"cases": []})
        self.assertEqual(a, b)

    def test_pagination_covers_selection_without_overlap_and_freezes(self):
        folder, _ = self.prepare()
        first = make_batch(folder, self.root / "one", limit=3)
        second = make_batch(folder, self.root / "two", offset=3, limit=3)
        self.assertEqual(len(set(first["case_ids"] + second["case_ids"])), 4)
        self.assertEqual(first["eligible_tasks_for_filters"], 4)
        cases = load_jsonl(self.root / "one/cases.jsonl")
        self.assertEqual(len({c["category"] for c in cases[:2]}), 2)
        frozen = self.root / "freeze.json"
        freeze(cases, "prompts/extract_v1.txt", frozen)
        verify_freeze(cases, "prompts/extract_v1.txt", frozen, require_complete=True)
        cases[0]["context"] = "tampered"
        with self.assertRaises(ValueError):
            verify_freeze(cases, "prompts/extract_v1.txt", frozen)

    def test_invalid_filters_empty_page_and_overwrite_rejected(self):
        folder, _ = self.prepare()
        for kwargs in ({"categories": ["Unknown"]}, {"offset": -1}, {"offset": 999},
                       {"limit": 31}, {"max_context_characters": 400001}, {"split": "test"}):
            with self.assertRaises(ValueError):
                make_batch(folder, self.root / "bad", **kwargs)
        make_batch(folder, self.root / "batch")
        with self.assertRaises(FileExistsError):
            make_batch(folder, self.root / "batch")

    def test_catalog_tamper_detected(self):
        folder, _ = self.prepare()
        with (folder / "tasks.jsonl").open("a") as stream:
            stream.write("{}\n")
        with self.assertRaises(ValueError):
            make_batch(folder, self.root / "bad")

    def test_long_contract_explicit_opt_in_preserves_full_context_without_gold(self):
        text = "contract " * 6000
        self.raw = {"data": [document("Long", text)]}
        self.pilot = {"cases": [{"contract_sha256": digest(text), "split": "development"}]}
        folder, _ = self.prepare()
        with self.assertRaises(ValueError):
            make_batch(folder, self.root / "short")
        make_batch(folder, self.root / "long", max_context_characters=400000)
        cases = load_jsonl(self.root / "long/cases.jsonl")
        self.assertEqual(cases[0]["context"], text)
        freeze(cases, "prompts/extract_v1.txt", self.root / "freeze.json")
        with self.assertRaises(ValueError):
            export_bundle(cases, "prompts/extract_v1.txt", self.root / "freeze.json", "development", self.root / "rejected")
        export_bundle(cases, "prompts/extract_v1.txt", self.root / "freeze.json", "development",
                      self.root / "bundle", max_context_characters=400000)
        manifest, _, inputs = read_bundle(self.root / "bundle")
        self.assertEqual(json.loads(inputs[0]), {"question": cases[0]["question"], "contract": text})
        self.assertNotIn("reference_spans", canonical(manifest))
        manifest["max_context_characters"] = 400001
        save_json(self.root / "bundle/bundle.json", manifest)
        with self.assertRaises(ValueError):
            read_bundle(self.root / "bundle")

    def test_unicode_line_separators_in_real_contract_text_roundtrip(self):
        text = "Clause A\u0085Clause B\u2028Clause C\u2029End"
        self.raw = {"data": [document("Unicode", text)]}
        self.pilot = {"cases": [{"contract_sha256": digest(text), "split": "development"}]}
        folder, _ = self.prepare()
        make_batch(folder, self.root / "unicode")
        self.assertEqual(load_jsonl(self.root / "unicode/cases.jsonl")[0]["context"], text)

    def test_inspection_exports_complete_text_and_original_annotations(self):
        folder, _ = self.prepare()
        key = digest("Third complete contract.")
        result = inspect_contract(folder, key, self.root / "inspection")
        self.assertEqual(result["split"], "development")
        self.assertEqual((self.root / "inspection/contract.txt").read_text(), "Third complete contract.")
        self.assertEqual(len(load_json(self.root / "inspection/annotations.json")), 4)

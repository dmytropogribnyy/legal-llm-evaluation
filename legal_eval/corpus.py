"""Versioned full CUAD catalog and bounded, reference-free execution preparation."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from itertools import zip_longest
from pathlib import Path
import json

from .common import canonical, digest, load_json, load_jsonl, save_json, write_jsonl

PROTOCOL = "cuad-full-corpus-v1"
MAX_CONTEXT = 400_000


def context_limit(value):
    if type(value) is not int or not 1 <= value <= MAX_CONTEXT:
        raise ValueError("Context character limit must be 1..400000")
    return value


def build_catalog(raw, source, pilot):
    inherited = {}
    for case in pilot["cases"]:
        key, split = case["contract_sha256"], case["split"]
        if split not in ("development", "holdout") or inherited.get(key, split) != split:
            raise ValueError("Conflicting pilot split")
        inherited[key] = split
    groups = defaultdict(list)
    ids = set()
    for document in raw["data"]:
        if len(document["paragraphs"]) != 1:
            raise ValueError("Expected one full context per source document")
        paragraph = document["paragraphs"][0]
        context = paragraph["context"]
        if not isinstance(context, str) or not context:
            raise ValueError("Empty source context")
        categories = set()
        for qa in paragraph["qas"]:
            category = qa["id"].rsplit("__", 1)[-1]
            if qa["id"] in ids or category in categories:
                raise ValueError("Duplicate source question ID/category")
            ids.add(qa["id"])
            categories.add(category)
            if bool(qa["answers"]) == qa["is_impossible"]:
                raise ValueError("Contradictory source presence annotation")
            for answer in qa["answers"]:
                start, text = answer["answer_start"], answer["text"]
                if type(start) is not int or start < 0 or not text or context[start:start+len(text)] != text:
                    raise ValueError("Invalid source annotation offset")
        groups[digest(context)].append(document)
    if not set(inherited) <= set(groups):
        raise ValueError("Pilot contracts missing from source")
    contracts, tasks, conflicts = [], [], []
    for key, documents in sorted(groups.items()):
        documents.sort(key=lambda d: d["title"])
        context = documents[0]["paragraphs"][0]["context"]
        split = inherited.get(key, "holdout" if int(digest(PROTOCOL + key)[:8], 16) % 5 == 0
                              else "development")
        variants = defaultdict(set)
        for document in documents:
            for qa in document["paragraphs"][0]["qas"]:
                category = qa["id"].rsplit("__", 1)[-1]
                signature = canonical({"question": qa["question"], "present": not qa["is_impossible"],
                                       "answers": sorted((a["answer_start"], a["text"]) for a in qa["answers"])})
                variants[category].add(signature)
        ambiguous = {cat for cat, values in variants.items() if len(values) > 1}
        contracts.append({"contract_sha256": key, "context": context, "characters": len(context),
                          "titles": [d["title"] for d in documents], "split": split,
                          "pilot_split_preserved": key in inherited})
        for category in sorted(ambiguous):
            conflicts.append({"contract_sha256": key, "category": category,
                              "titles": [d["title"] for d in documents]})
        for index, document in enumerate(documents):
            for qa in document["paragraphs"][0]["qas"]:
                category = qa["id"].rsplit("__", 1)[-1]
                tasks.append({"case_id": "cuad-full-" + digest(qa["id"])[:16],
                              "source_question_id": qa["id"], "contract_title": document["title"],
                              "contract_sha256": key, "category": category, "split": split,
                              "question": qa["question"], "reference_spans": [a["text"] for a in qa["answers"]],
                              "reference_offsets": [a["answer_start"] for a in qa["answers"]],
                              "reference_present": bool(qa["answers"]),
                              "duplicate_suppressed": index > 0, "annotation_conflict": category in ambiguous,
                              "reference_origin": "CUAD publisher annotations", "owner_legal_review": "pending",
                              "dataset_sha256": source["sha256"], "selection_protocol": PROTOCOL})
    tasks.sort(key=lambda t: t["case_id"])
    eligible = [t for t in tasks if not t["duplicate_suppressed"] and not t["annotation_conflict"]]
    coverage = []
    for category in sorted({t["category"] for t in tasks}):
        row = {"category": category}
        for split in ("development", "holdout"):
            counts = Counter(t["reference_present"] for t in eligible if t["category"] == category and t["split"] == split)
            row[split] = {"positive": counts[True], "negative": counts[False]}
        coverage.append(row)
    summary = {"protocol": PROTOCOL, "dataset_sha256": source["sha256"],
               "dataset_revision": source["revision"], "source_url": source["url"],
               "source_document_records": len(raw["data"]), "unique_contract_texts": len(contracts),
               "source_tasks": len(tasks), "eligible_deduplicated_tasks": len(eligible),
               "duplicate_suppressed_tasks": sum(t["duplicate_suppressed"] for t in tasks),
               "conflicting_unique_contract_categories": len(conflicts), "conflicts": conflicts,
               "categories": coverage, "category_count": len(coverage),
               "split_contracts": dict(Counter(c["split"] for c in contracts)),
               "pilot_contract_splits_preserved": len(inherited),
               "context_characters": {"min": min(c["characters"] for c in contracts),
                                      "max": max(c["characters"] for c in contracts),
                                      "total_unique": sum(c["characters"] for c in contracts)},
               "contracts_within_default_40000": sum(c["characters"] <= 40000 for c in contracts),
               "owner_legal_review": "pending", "live_model_runs": "not measured by corpus preparation"}
    return contracts, tasks, summary


def prepare_corpus(raw_file="data/raw/CUAD_v1.json", out="data/prepared/full-cuad",
                   source_file="data/source.json", pilot_file="data/selection_manifest.json"):
    source = load_json(source_file)
    content = Path(raw_file).read_bytes()
    if digest(content) != source["sha256"]:
        raise ValueError("Source hash mismatch")
    contracts, tasks, summary = build_catalog(json.loads(content), source, load_json(pilot_file))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    write_jsonl(out / "contracts.jsonl", contracts)
    write_jsonl(out / "tasks.jsonl", tasks)
    with (out / "contract_index.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, lineterminator="\n", fieldnames=["contract_sha256", "split", "characters", "source_records", "canonical_title"])
        writer.writeheader()
        for contract in contracts:
            writer.writerow({"contract_sha256": contract["contract_sha256"], "split": contract["split"],
                             "characters": contract["characters"], "source_records": len(contract["titles"]),
                             "canonical_title": contract["titles"][0]})
    summary["files"] = {name: digest((out / name).read_bytes()) for name in ("contracts.jsonl", "tasks.jsonl", "contract_index.csv")}
    summary["pilot_manifest_sha256"] = digest(Path(pilot_file).read_bytes())
    summary["selection_protocol_sha256"] = digest(Path("docs/FULL_CORPUS_PROTOCOL.md").read_bytes())
    save_json(out / "catalog.json", summary)
    return summary


def load_catalog(folder):
    folder = Path(folder)
    catalog = load_json(folder / "catalog.json")
    if catalog["protocol"] != PROTOCOL:
        raise ValueError("Unsupported catalog protocol")
    for name in ("contracts.jsonl", "tasks.jsonl", "contract_index.csv"):
        if digest((folder / name).read_bytes()) != catalog["files"][name]:
            raise ValueError("Catalog data changed after preparation")
    if catalog["selection_protocol_sha256"] != digest(Path("docs/FULL_CORPUS_PROTOCOL.md").read_bytes()):
        raise ValueError("Full corpus protocol changed after preparation")
    contracts = {c["contract_sha256"]: c for c in load_jsonl(folder / "contracts.jsonl")}
    return catalog, contracts, load_jsonl(folder / "tasks.jsonl")


def make_batch(folder, out, split="development", categories=None, offset=0, limit=30,
               max_context_characters=40000):
    context_limit(max_context_characters)
    if split not in ("development", "holdout") or offset < 0 or not 1 <= limit <= 30:
        raise ValueError("Use a valid split, nonnegative offset and 1..30 tasks")
    catalog, contracts, tasks = load_catalog(folder)
    available = {t["category"] for t in tasks}
    categories = sorted(set(categories or available))
    if not set(categories) <= available:
        raise ValueError("Unknown category; see catalog.json")
    buckets = {cat: [] for cat in categories}
    for task in tasks:
        if (task["split"] == split and task["category"] in buckets and not task["duplicate_suppressed"]
                and not task["annotation_conflict"]
                and contracts[task["contract_sha256"]]["characters"] <= max_context_characters):
            buckets[task["category"]].append(task)
    # Category round-robin; case hashes break ties. No gold labels determine ordering.
    ordered = [task for row in zip_longest(*(buckets[cat] for cat in categories)) for task in row if task]
    selected = ordered[offset:offset+limit]
    if not selected:
        raise ValueError("No tasks at this offset with these filters")
    cases = []
    for task in selected:
        case = dict(task, context=contracts[task["contract_sha256"]]["context"],
                    selection_protocol_sha256=catalog["selection_protocol_sha256"])
        case["case_sha256"] = digest(canonical(case))
        cases.append(case)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    write_jsonl(out / "cases.jsonl", cases)
    manifest = {"protocol": PROTOCOL, "catalog_sha256": digest((Path(folder) / "catalog.json").read_bytes()),
                "split": split, "categories": categories, "offset": offset, "requested_limit": limit,
                "max_context_characters": max_context_characters, "eligible_tasks_for_filters": len(ordered),
                "selected_tasks": len(cases), "next_offset": offset+len(cases),
                "case_ids": [c["case_id"] for c in cases],
                "cases_sha256": digest((out / "cases.jsonl").read_bytes()),
                "selection_protocol_sha256": catalog["selection_protocol_sha256"]}
    save_json(out / "batch.json", manifest)
    return manifest


def inspect_contract(folder, key, out):
    catalog, contracts, tasks = load_catalog(folder)
    if key not in contracts:
        raise ValueError("Unknown contract SHA-256; use contracts.jsonl")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    contract = contracts[key]
    (out / "contract.txt").write_bytes(contract["context"].encode("utf-8"))
    save_json(out / "annotations.json", [t for t in tasks if t["contract_sha256"] == key])
    save_json(out / "provenance.json", {k: v for k, v in contract.items() if k != "context"})
    return {"out": str(out), "split": contract["split"],
            "note": "Viewing holdout annotations exposes it; record exposure and do not tune against it."}

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import urlopen

from .common import canonical, digest, load_json, save_json, write_jsonl

CATEGORIES = ("Cap On Liability", "Termination For Convenience", "Governing Law")
SEED = "contract-review-pilot-v1"
MAX_CONTEXT = 40_000


def select_group(candidates, count, minimum):
    """Greedy label coverage, deterministic hash-order tie break; no model output used."""
    pool = list(candidates)
    selected = []
    coverage = {(category, label): 0 for category in CATEGORIES for label in (False, True)}
    for _ in range(count):
        if not pool:
            raise ValueError("Not enough eligible contracts")
        def contribution(row):
            return sum(coverage[(cat, bool(row[2][cat]["answers"]))] < minimum
                       for cat in CATEGORIES)
        best = max(range(len(pool)), key=lambda i: contribution(pool[i]))
        row = pool.pop(best)
        selected.append(row)
        for cat in CATEGORIES:
            coverage[(cat, bool(row[2][cat]["answers"]))] += 1
    if any(n < minimum for n in coverage.values()):
        raise ValueError("Selection cannot satisfy declared label coverage")
    return selected, pool


def fetch(source_file="data/source.json", destination="data/raw/CUAD_v1.json"):
    source = load_json(source_file)
    path = Path(destination)
    if path.exists():
        content = path.read_bytes()
    else:
        with urlopen(source["url"], timeout=60) as response:
            content = response.read(source["size_bytes"] + 1)
    if len(content) != source["size_bytes"] or digest(content) != source["sha256"]:
        raise ValueError("Dataset size/hash mismatch; source was not accepted")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def build_cases(raw, source, contracts=10, development_contracts=3):
    if not 0 < development_contracts < contracts:
        raise ValueError("Both development and holdout contracts are required")
    eligible = []
    for document in raw["data"]:
        # No truncation or gold-guided cropping: send the complete supplied context.
        if len(document["paragraphs"]) != 1:
            continue
        paragraph = document["paragraphs"][0]
        context = paragraph["context"]
        qas = {q["id"].rsplit("__", 1)[-1]: q for q in paragraph["qas"]}
        if len(context) > MAX_CONTEXT or not all(c in qas for c in CATEGORIES):
            continue
        eligible.append((document["title"], context, qas))
    eligible.sort(key=lambda row: digest(SEED + row[0]))
    # De-duplicate complete contract text before allocating groups.
    unique, seen = [], set()
    for row in eligible:
        key = digest(row[1])
        if key not in seen:
            seen.add(key)
            unique.append(row)
    if len(unique) < contracts:
        raise ValueError("Not enough eligible contracts")
    development, remaining = select_group(unique, development_contracts, 1)
    holdout, _ = select_group(remaining, contracts - development_contracts, 2)
    cases = []
    for i, (title, context, qas) in enumerate(development + holdout):
        for category in CATEGORIES:
            qa = qas[category]
            answers = qa["answers"]
            for answer in answers:
                start, text = answer["answer_start"], answer["text"]
                if context[start:start + len(text)] != text:
                    raise ValueError(f"Invalid source annotation offset: {qa['id']}")
            if bool(answers) == qa["is_impossible"]:
                raise ValueError("Contradictory source presence annotation")
            row = {
                "case_id": "cuad-" + digest(qa["id"])[:16],
                "source_question_id": qa["id"], "contract_title": title,
                "contract_sha256": digest(context), "category": category,
                "split": "development" if i < development_contracts else "holdout",
                "question": qa["question"], "context": context,
                "reference_spans": [a["text"] for a in answers],
                "reference_present": bool(answers),
                "reference_origin": "CUAD publisher annotations",
                "owner_legal_review": "pending",
                "dataset_sha256": source["sha256"],
            }
            row["case_sha256"] = digest(canonical(row))
            cases.append(row)
    return cases, len(unique)


def prepare(raw_file="data/raw/CUAD_v1.json", out="data/prepared",
            source_file="data/source.json"):
    source = load_json(source_file)
    content = Path(raw_file).read_bytes()
    if digest(content) != source["sha256"]:
        raise ValueError("Source hash mismatch")
    cases, eligible = build_cases(json.loads(content), source)
    out = Path(out)
    write_jsonl(out / "cases.jsonl", cases)
    manifest = {
        "protocol": "contract-review-pilot-v1", "seed": SEED,
        "dataset_sha256": source["sha256"], "dataset_revision": source["revision"],
        "max_context_characters": MAX_CONTEXT, "eligible_unique_contracts": eligible,
        "selection": "greedy label coverage; SHA-256 order breaks ties",
        "minimum_per_category_label": {"development": 1, "holdout": 2},
        "contract_count": len({c["contract_sha256"] for c in cases}),
        "case_count": len(cases), "categories": list(CATEGORIES),
        "cases": [{k: v for k, v in c.items() if k not in
                   ("context", "reference_spans", "question")} for c in cases],
        "source": source["url"], "owner_legal_review": "pending",
    }
    save_json(out / "manifest.json", manifest)
    return manifest

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .common import save_json

REVIEW_FIELDS = ["case_id", "response_sha256", "reviewer", "reviewed_at_utc",
                 "legal_accuracy_0_2", "material_completeness_0_2",
                 "supported_reasoning_0_2", "uncertainty_handling_0_2",
                 "severity", "disposition", "rationale", "source_reference"]


def export_report(report, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    save_json(out / "metrics.json", report)
    metrics = report["metrics"]
    run = report["model_run"]
    label = run[2] if run else "no_responses"
    title = "Evaluator self-check" if label == "synthetic_fixture" else "Automated evaluation report"
    lines = [f"# {title}", "", f"**Response provenance:** {label}",
             f"**Model label:** {run[0] if run else 'none'}", "",
             "Human legal review is pending. These metrics do not establish legal correctness,",
             "model superiority, client acceptance, or EU AI Act compliance.", "",
             "| Metric | Value |", "|---|---|"]
    for key, value in metrics.items():
        if key == "flags":
            continue
        if isinstance(value, float):
            value = f"{value:.4f}"
        lines.append(f"| {key} | {'N/A' if value is None else value} |")
    lines += ["", "## Category counts", "",
              "| Category | Expected | Reference positives | Presence correct | Schema valid |",
              "|---|---|---|---|---|"]
    for category, values in report["by_category"].items():
        lines.append(f"| {category} | {values['expected_cases']} | "
                     f"{values['reference_positive_cases']} | {values['presence_correct_count']} | "
                     f"{values['schema_valid_count']} |")
    lines += ["", "## Cases requiring attention", ""]
    for row in report["rows"]:
        if row["flags"]:
            lines.append(f"- `{row['case_id']}`: {', '.join(row['flags'])}")
    lines += ["", "Review every case, including unflagged responses. A real quote does not",
              "prove that the summary correctly interprets it. Lexical overlap is diagnostic only.", ""]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    with (out / "human_review.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        for row in report["rows"]:
            writer.writerow({"case_id": row["case_id"],
                             "response_sha256": row["response_sha256"]})


def validate_reviews(report, csv_file):
    expected = {r["case_id"]: r["response_sha256"] for r in report["rows"]}
    seen = set()
    with Path(csv_file).open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            case_id = row["case_id"]
            if case_id in seen or case_id not in expected:
                raise ValueError("Unknown/duplicate human review")
            seen.add(case_id)
            if not expected[case_id] or row["response_sha256"] != expected[case_id]:
                raise ValueError("Review belongs to a missing or different response")
            for field in REVIEW_FIELDS:
                if not row.get(field, "").strip():
                    raise ValueError(f"Incomplete human review: {field}")
            reviewed_at = datetime.fromisoformat(row["reviewed_at_utc"])
            if reviewed_at.utcoffset() is None or reviewed_at.utcoffset().total_seconds() != 0:
                raise ValueError("Review timestamp must include a UTC offset")
            for field in REVIEW_FIELDS:
                if field.endswith("_0_2") and row[field] not in ("0", "1", "2"):
                    raise ValueError("Review score must be 0, 1 or 2")
            if row["severity"] not in ("none", "minor", "major", "critical"):
                raise ValueError("Unknown severity")
            if row["disposition"] not in ("accept", "revise", "reject"):
                raise ValueError("Unknown disposition")
    if set(expected) != seen:
        raise ValueError("Human reviews do not cover the complete report")
    return {"complete_reviews": len(seen), "identity_independently_verified": False,
            "note": "Checks completeness and binding; does not authenticate reviewer identity."}

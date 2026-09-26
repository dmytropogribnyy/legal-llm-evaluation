from __future__ import annotations

import json
import re
from collections import Counter

from .common import canonical, digest


def normalize(text):
    return " ".join(text.split())


def tokens(text):
    return re.findall(r"\w+", text.lower())


def token_f1(predicted, reference):
    p, r = Counter(tokens(predicted)), Counter(tokens(reference))
    overlap = sum((p & r).values())
    if not p or not r or not overlap:
        return 0.0
    precision, recall = overlap / sum(p.values()), overlap / sum(r.values())
    return 2 * precision * recall / (precision + recall)


def verify_case(case):
    body = {k: v for k, v in case.items() if k != "case_sha256"}
    if digest(canonical(body)) != case["case_sha256"]:
        raise ValueError("Case content changed without a new manifest")


def validate_cases(cases):
    if not cases or any(not isinstance(c, dict) or not isinstance(c.get("case_id"), str)
                        or not c["case_id"].strip() for c in cases):
        raise ValueError("Cases require nonempty string IDs")
    if len({c["case_id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate case IDs")
    for case in cases:
        verify_case(case)


def assess(case, raw_output):
    result = {"case_id": case["case_id"], "category": case["category"],
              "split": case["split"], "schema_valid": False,
              "presence_correct": False, "quotes_total": 0,
              "quotes_verified": 0, "reference_token_f1": 0.0,
              "flags": [], "semantic_legal_review": "pending"}
    try:
        output = json.loads(raw_output)
        if (not isinstance(output, dict)
                or type(output.get("relevant_found")) is not bool
                or type(output.get("needs_human_review")) is not bool
                or not isinstance(output.get("summary"), str)
                or not isinstance(output.get("quotes"), list)
                or not all(isinstance(q, str) and q.strip() for q in output["quotes"])
                or bool(output["quotes"]) != output["relevant_found"]):
            raise ValueError("Invalid schema or inconsistent presence/quotes")
    except (ValueError, TypeError):
        result["flags"].append("invalid_output_schema")
        return result
    result["schema_valid"] = True
    predicted, reference = output["relevant_found"], case["reference_present"]
    result["presence_correct"] = predicted == reference
    quotes = output["quotes"]
    result["quotes_total"] = len(quotes)
    verified = [q for q in quotes if normalize(q) in normalize(case["context"])]
    result["quotes_verified"] = len(verified)
    if len(verified) != len(quotes):
        result["flags"].append("unsupported_quote")
    if reference and not predicted:
        result["flags"].append("missed_reference_provision")
    if predicted and not reference:
        result["flags"].append("provision_without_reference_label")
    if not output["needs_human_review"]:
        result["flags"].append("human_review_not_requested")
    # All annotated spans count; selecting one easy alternative must not mask omissions.
    # Lexical overlap is a diagnostic, never a score for legal interpretation.
    if case["reference_spans"]:
        result["reference_token_f1"] = token_f1(
            " ".join(verified), " ".join(case["reference_spans"]))
    return result


def score_run(cases, responses, expected_prompt_sha256=None):
    validate_cases(cases)
    index = {c["case_id"]: c for c in cases}
    splits = {c["split"] for c in cases}
    protocols = {(c.get("selection_protocol", "legacy-or-fixture"),
                  c.get("selection_protocol_sha256", "")) for c in cases}
    if len(splits) != 1 or len(protocols) != 1:
        raise ValueError("Mixed splits or selection protocols: use separate reports")
    seen, rows, run_keys, returned_models = set(), [], set(), set()
    for response in responses:
        case_id = response["case_id"]
        if case_id not in index or case_id in seen:
            raise ValueError("Unknown or duplicate response case ID")
        seen.add(case_id)
        case = index[case_id]
        if response["case_sha256"] != case["case_sha256"]:
            raise ValueError("Response belongs to a different case revision")
        if expected_prompt_sha256 and response["prompt_sha256"] != expected_prompt_sha256:
            raise ValueError("Prompt differs from the frozen protocol")
        if response.get("provenance") not in ("live_api", "imported", "synthetic_fixture"):
            raise ValueError("Explicit response provenance is required")
        profile = response.get("execution_profile_sha256", "")
        if response.get("provider") in ("claude_code_cli", "openai") and not profile:
            raise ValueError("Native adapter responses need an execution profile binding")
        run_keys.add((response["model"], response["prompt_sha256"], response["provenance"],
                      profile, response.get("provider", "unspecified")))
        if not response.get("error"):
            resolved = response.get("returned_models", [])
            if not isinstance(resolved, list) or not all(isinstance(m, str) and m for m in resolved):
                raise ValueError("Invalid returned model metadata")
            returned_models.update(resolved)
            if response.get("returned_model"):
                if not isinstance(response["returned_model"], str):
                    raise ValueError("Invalid returned model metadata")
                returned_models.add(response["returned_model"])
        if response.get("error"):
            row = assess(case, "")
            row["flags"] = ["provider_error"]
        else:
            row = assess(case, response["raw_output"])
        row["response_sha256"] = digest(canonical(response))
        rows.append(row)
    if len(run_keys) > 1 or len(returned_models) > 1:
        raise ValueError("Mixed model, provider, prompt, provenance or execution profile: use separate reports")
    for case_id in sorted(set(index) - seen):
        row = assess(index[case_id], "")
        row["flags"] = ["missing_response"]
        row["response_sha256"] = ""
        rows.append(row)
    quote_count = sum(r["quotes_total"] for r in rows)
    positives = [r for r in rows if index[r["case_id"]]["reference_present"]]
    metrics = {
        "expected_cases": len(cases), "received_responses": len(responses),
        "missing_responses": len(cases) - len(responses),
        "schema_valid_rate": sum(r["schema_valid"] for r in rows) / len(cases),
        "reference_presence_accuracy": sum(r["presence_correct"] for r in rows) / len(cases),
        "verified_quote_rate": (sum(r["quotes_verified"] for r in rows) / quote_count
                                if quote_count else None),
        "quote_count": quote_count,
        "mean_positive_reference_token_f1": (sum(r["reference_token_f1"] for r in positives)
                                              / len(positives) if positives else None),
        "human_semantic_reviews_completed": 0,
        "flags": dict(Counter(f for r in rows for f in r["flags"])),
    }
    category_metrics = {}
    for category in sorted({c["category"] for c in cases}):
        subset = [r for r in rows if r["category"] == category]
        category_metrics[category] = {
            "expected_cases": len(subset),
            "reference_positive_cases": sum(index[r["case_id"]]["reference_present"] for r in subset),
            "presence_correct_count": sum(r["presence_correct"] for r in subset),
            "schema_valid_count": sum(r["schema_valid"] for r in subset),
            "flags": dict(Counter(f for r in subset for f in r["flags"])),
        }
    return {"scope": {"split": next(iter(splits)), "selection_protocol": next(iter(protocols))[0],
                      "selection_protocol_sha256": next(iter(protocols))[1],
                      "expected_tasks": len(cases)},
            "returned_models": sorted(returned_models),
            "metrics": metrics, "by_category": category_metrics,
            "rows": rows, "model_run": list(next(iter(run_keys)))
            if run_keys else None, "conclusion": "Human legal review required; no release verdict"}

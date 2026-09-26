from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import canonical, digest, load_json, load_jsonl, save_json, write_jsonl
from .dataset import fetch, prepare
from .evaluate import score_run
from .report import export_report, validate_reviews
from .runner import freeze, run_openai, verify_freeze


def demo(out):
    contexts = [
        ("Supplier liability shall not exceed fees paid in the preceding twelve months.", True),
        ("Either party may terminate on thirty days' written notice.", True),
        ("The notice address is 10 Example Street.", False),
        ("The agreement is governed by the law of Example Jurisdiction.", True),
    ]
    cases = []
    for i, (context, present) in enumerate(contexts):
        row = {"case_id": f"fixture-{i + 1}", "category": "self_check",
               "split": "fixture", "context": context, "reference_present": present,
               "reference_spans": [context] if present else []}
        row["case_sha256"] = digest(canonical(row))
        cases.append(row)
    outputs = [
        {"relevant_found": True, "quotes": [contexts[0][0]], "summary": "Capped liability.",
         "needs_human_review": True},
        {"relevant_found": True, "quotes": ["Termination is immediate without notice."],
         "summary": "No notice needed.", "needs_human_review": False},
        {"relevant_found": False, "quotes": [], "summary": "No relevant provision found.",
         "needs_human_review": True},
        {"relevant_found": False, "quotes": [], "summary": "Not found.",
         "needs_human_review": True},
    ]
    responses = [{"case_id": c["case_id"], "case_sha256": c["case_sha256"],
                  "model": "controlled-fixture-not-a-model", "prompt_sha256": "fixture",
                  "provenance": "synthetic_fixture", "raw_output": json.dumps(o)}
                 for c, o in zip(cases, outputs)]
    report = score_run(cases, responses)
    export_report(report, out)
    write_jsonl(Path(out) / "fixture_responses.jsonl", responses)
    return report["metrics"]


def main():
    parser = argparse.ArgumentParser(description="Legal LLM Evaluation")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="Download and verify pinned public CUAD data")
    p = sub.add_parser("prepare", help="Build fixed contract-level split")
    p.add_argument("--out", default="data/prepared")
    p = sub.add_parser("freeze", help="Record prompt, protocol and case hashes")
    p.add_argument("--out", required=True)
    p.add_argument("--cases", default="data/prepared/cases.jsonl")
    p.add_argument("--prompt", default="prompts/extract_v1.txt")
    for name in ("run-openai", "score"):
        p = sub.add_parser(name)
        p.add_argument("--cases", default="data/prepared/cases.jsonl")
        p.add_argument("--prompt", default="prompts/extract_v1.txt")
        p.add_argument("--frozen", required=True)
        p.add_argument("--split", choices=["development", "holdout"], default="development")
        p.add_argument("--out", required=True)
        if name == "run-openai":
            p.add_argument("--model", required=True)
            p.add_argument("--allow-paid", action="store_true")
            p.add_argument("--max-calls", type=int, required=True)
            p.add_argument("--max-output-tokens", type=int, default=1200)
        else:
            p.add_argument("--responses", required=True)
    p = sub.add_parser("demo", help="Offline evaluator self-check; no model performance claim")
    p.add_argument("--out", required=True)
    p = sub.add_parser("validate-review")
    p.add_argument("--report", required=True)
    p.add_argument("--reviews", required=True)
    args = parser.parse_args()
    if args.command == "fetch":
        print(fetch())
    elif args.command == "prepare":
        m = prepare(out=args.out)
        print(json.dumps({"contracts": m["contract_count"], "cases": m["case_count"]}))
    elif args.command == "freeze":
        freeze(load_jsonl(args.cases), args.prompt, args.out)
        print(args.out)
    elif args.command == "demo":
        print(json.dumps(demo(args.out), indent=2))
    elif args.command == "validate-review":
        print(json.dumps(validate_reviews(load_json(args.report), args.reviews)))
    else:
        all_cases = load_jsonl(args.cases)
        frozen = verify_freeze(all_cases, args.prompt, args.frozen, require_complete=True)
        cases = [c for c in all_cases if c["split"] == args.split]
        if args.command == "run-openai":
            print(run_openai(cases, args.prompt, args.frozen, args.model, args.out,
                             args.allow_paid, args.max_calls, args.max_output_tokens))
        else:
            responses = load_jsonl(args.responses)
            report = score_run(cases, responses, frozen["prompt_sha256"])
            report["freeze_sha256"] = digest(Path(args.frozen).read_bytes())
            export_report(report, args.out)
            save_json(Path(args.out) / "source_manifest.json", {
                "case_ids": [c["case_id"] for c in cases], "split": args.split,
                "responses_sha256": digest(Path(args.responses).read_bytes())})
            print(args.out)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        raise SystemExit(str(exc)) from None

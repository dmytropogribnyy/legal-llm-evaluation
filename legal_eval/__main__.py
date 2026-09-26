from __future__ import annotations

import argparse
import json
from pathlib import Path

from .claude_code import export_bundle, preflight, run_bundle
from .common import canonical, digest, load_json, load_jsonl, save_json, write_jsonl
from .dataset import fetch, prepare
from .corpus import inspect_contract, make_batch, prepare_corpus
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
    p = sub.add_parser("prepare-corpus", help="Catalog all CUAD contracts and categories locally")
    p.add_argument("--out", default="data/prepared/full-cuad")
    p = sub.add_parser("corpus-batch", help="Prepare a bounded full-contract evaluation batch")
    p.add_argument("--corpus", default="data/prepared/full-cuad")
    p.add_argument("--out", required=True)
    p.add_argument("--split", choices=["development", "holdout"], default="development")
    p.add_argument("--category", action="append")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--max-context-characters", type=int, default=40000)
    p = sub.add_parser("inspect-contract", help="Export full text and annotations for local inspection")
    p.add_argument("--corpus", default="data/prepared/full-cuad")
    p.add_argument("--contract-sha256", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("freeze", help="Record prompt, protocol and case hashes")
    p.add_argument("--out", required=True)
    p.add_argument("--cases", default="data/prepared/cases.jsonl")
    p.add_argument("--prompt", default="prompts/extract_v1.txt")
    p = sub.add_parser("export-claude", help="Create a reference-free Claude Code input bundle")
    p.add_argument("--cases", default="data/prepared/cases.jsonl")
    p.add_argument("--prompt", default="prompts/extract_v1.txt")
    p.add_argument("--frozen", required=True)
    p.add_argument("--split", choices=["development", "holdout"], default="development")
    p.add_argument("--out", required=True)
    p.add_argument("--max-context-characters", type=int, default=40000)
    p = sub.add_parser("claude-doctor", help="Check CLI and subscription sign-in; no model calls")
    p.add_argument("--claude-bin", default="claude")
    p = sub.add_parser("run-claude", help="Evaluate through the official local Claude Code CLI")
    p.add_argument("--bundle", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-invocations", type=int, required=True)
    p.add_argument("--allow-subscription-usage", action="store_true")
    p.add_argument("--effort", choices=["low", "medium", "high"], default="medium")
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--claude-bin", default="claude")
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
            p.add_argument("--max-context-characters", type=int, default=40000)
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
    elif args.command == "prepare-corpus":
        summary = prepare_corpus(out=args.out)
        print(json.dumps({k: summary[k] for k in ("source_document_records", "unique_contract_texts", "source_tasks", "category_count")}))
    elif args.command == "corpus-batch":
        print(json.dumps(make_batch(args.corpus, args.out, args.split, args.category,
                                    args.offset, args.limit, args.max_context_characters), indent=2))
    elif args.command == "inspect-contract":
        print(json.dumps(inspect_contract(args.corpus, args.contract_sha256, args.out)))
    elif args.command == "freeze":
        freeze(load_jsonl(args.cases), args.prompt, args.out)
        print(args.out)
    elif args.command == "export-claude":
        print(export_bundle(load_jsonl(args.cases), args.prompt, args.frozen, args.split, args.out,
                            max_context_characters=args.max_context_characters))
    elif args.command == "claude-doctor":
        print(json.dumps(preflight(args.claude_bin), indent=2))
    elif args.command == "run-claude":
        result = run_bundle(args.bundle, args.model, args.out, args.max_invocations,
                            args.allow_subscription_usage, args.effort, args.timeout, args.claude_bin)
        print(result)
        if load_json(Path(args.out) / "run.json")["status"] != "completed":
            raise SystemExit("Run stopped on an error; retained results must be scored as partial")
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
                             args.allow_paid, args.max_calls, args.max_output_tokens,
                             max_context_characters=args.max_context_characters))
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

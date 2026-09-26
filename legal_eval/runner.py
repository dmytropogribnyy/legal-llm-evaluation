from __future__ import annotations

import json
import time
from pathlib import Path

from .common import canonical, digest, load_json, save_json, timestamp
from .evaluate import verify_case
from .corpus import context_limit


def freeze(cases, prompt_file, destination, rubric_file="docs/EVALUATION_PROTOCOL.md"):
    if Path(destination).exists():
        raise ValueError("Freeze already exists; use a new versioned file")
    for case in cases:
        verify_case(case)
    frozen = {
        "frozen_at": timestamp(),
        "prompt_sha256": digest(Path(prompt_file).read_bytes()),
        "rubric_sha256": digest(Path(rubric_file).read_bytes()),
        "cases": {c["case_id"]: c["case_sha256"] for c in cases},
    }
    save_json(destination, frozen)
    return frozen


def verify_freeze(cases, prompt_file, frozen_file,
                  rubric_file="docs/EVALUATION_PROTOCOL.md", require_complete=False):
    frozen = load_json(frozen_file)
    if frozen["prompt_sha256"] != digest(Path(prompt_file).read_bytes()):
        raise ValueError("Prompt changed after freeze")
    if frozen["rubric_sha256"] != digest(Path(rubric_file).read_bytes()):
        raise ValueError("Evaluation protocol changed after freeze")
    if require_complete and {c["case_id"] for c in cases} != set(frozen["cases"]):
        raise ValueError("Case file does not contain the complete frozen selection")
    for case in cases:
        verify_case(case)
        if frozen["cases"].get(case["case_id"]) != case["case_sha256"]:
            raise ValueError("Case not covered by this freeze")
    return frozen


def provider_input(case):
    # Explicit allowlist: no reference spans, source labels or review annotations.
    return json.dumps({"question": case["question"], "contract": case["context"]},
                      ensure_ascii=False)


def run_openai(cases, prompt_file, frozen_file, model, out,
               allow_paid=False, max_calls=0, max_output_tokens=1200, client=None,
               max_context_characters=40000):
    context_limit(max_context_characters)
    if not allow_paid:
        raise ValueError("Live calls need --allow-paid; offline commands use no API")
    if not model or not cases or max_calls < len(cases) or max_calls > 30:
        raise ValueError("Supply a model and a call cap covering the selected cases (maximum 30)")
    if not 128 <= max_output_tokens <= 4000:
        raise ValueError("Output token cap must be 128..4000")
    if any(len(c["context"]) > max_context_characters for c in cases):
        raise ValueError("Input exceeds selected context character limit; no silent truncation")
    frozen = verify_freeze(cases, prompt_file, frozen_file)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    if client is None:
        from openai import OpenAI
        client = OpenAI(max_retries=0, timeout=60)
    instructions = Path(prompt_file).read_text(encoding="utf-8")
    save_json(out / "run.json", {
        "started_at": timestamp(), "requested_model": model, "provider": "openai",
        "provenance": "live_api", "split": sorted({c["split"] for c in cases}),
        "case_ids": [c["case_id"] for c in cases],
        "prompt_sha256": frozen["prompt_sha256"],
        "freeze_sha256": digest(Path(frozen_file).read_bytes()),
        "max_calls": max_calls, "max_output_tokens": max_output_tokens,
        "max_context_characters": max_context_characters,
        "max_retries": 0, "store": False, "cost_usd": None,
        "cost_note": "Token/call caps are enforced; no dollar budget or free usage is claimed.",
    })
    with (out / "responses.jsonl").open("x", encoding="utf-8") as stream:
        for case in cases:
            started = time.monotonic()
            record = {"case_id": case["case_id"], "case_sha256": case["case_sha256"],
                      "model": model, "prompt_sha256": frozen["prompt_sha256"],
                      "provenance": "live_api", "started_at": timestamp(),
                      "raw_output": "", "error": None}
            # Persist attempted calls even if execution is interrupted before a response.
            with (out / "attempts.jsonl").open("a", encoding="utf-8") as attempts:
                attempts.write(canonical({"case_id": case["case_id"],
                                          "started_at": record["started_at"]}) + "\n")
            try:
                response = client.responses.create(
                    model=model, instructions=instructions, input=provider_input(case),
                    max_output_tokens=max_output_tokens, store=False,
                    text={"format": {"type": "json_object"}})
                record.update(raw_output=response.output_text, response_id=response.id,
                              returned_model=response.model,
                              usage=response.usage.model_dump() if response.usage else None,
                              provider_status=response.status)
                if response.status != "completed":
                    record["error"] = "response_incomplete"
            except Exception as exc:
                # Exception messages can contain credentials or provider request bodies.
                record["error"] = type(exc).__name__
            record["latency_seconds"] = round(time.monotonic() - started, 3)
            stream.write(canonical(record) + "\n")
            stream.flush()
    return out / "responses.jsonl"

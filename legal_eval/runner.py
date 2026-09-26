from __future__ import annotations

import json
import time
from pathlib import Path

from .common import canonical, digest, load_json, save_json, timestamp
from .evaluate import validate_cases
from .corpus import context_limit


def verify_selection_protocols(cases):
    """Bind the extra full-corpus selection document as well as the legacy rubric."""
    identities = {(c.get("selection_protocol"), c.get("selection_protocol_sha256")) for c in cases}
    if len(identities) > 1:
        raise ValueError("Mixed selection protocols: create separate freezes and runs")
    full_hash = None
    for case in cases:
        protocol = case.get("selection_protocol")
        recorded = case.get("selection_protocol_sha256")
        if protocol is None and recorded is None:
            continue
        if protocol != "cuad-full-corpus-v1":
            raise ValueError("Unsupported case selection protocol")
        if full_hash is None:
            full_hash = digest(Path("docs/FULL_CORPUS_PROTOCOL.md").read_bytes())
        if recorded != full_hash:
            raise ValueError("Full corpus protocol changed; rebuild cases and create a new freeze")


def freeze(cases, prompt_file, destination, rubric_file="docs/EVALUATION_PROTOCOL.md"):
    if Path(destination).exists():
        raise ValueError("Freeze already exists; use a new versioned file")
    validate_cases(cases)
    verify_selection_protocols(cases)
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
    validate_cases(cases)
    verify_selection_protocols(cases)
    frozen = load_json(frozen_file)
    if frozen["prompt_sha256"] != digest(Path(prompt_file).read_bytes()):
        raise ValueError("Prompt changed after freeze")
    if frozen["rubric_sha256"] != digest(Path(rubric_file).read_bytes()):
        raise ValueError("Evaluation protocol changed after freeze")
    if require_complete and {c["case_id"] for c in cases} != set(frozen["cases"]):
        raise ValueError("Case file does not contain the complete frozen selection")
    for case in cases:
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
    if len({c["split"] for c in cases}) != 1:
        raise ValueError("Select one split per provider run")
    out = Path(out)
    if out.exists():
        raise ValueError("Run directory exists; use a new name")
    if client is None:
        from openai import OpenAI
        client = OpenAI(max_retries=0, timeout=60)
    out.mkdir(parents=True, exist_ok=False)
    instructions = Path(prompt_file).read_text(encoding="utf-8")
    profile = {"profile": "openai-responses-v1", "requested_model": model,
               "max_output_tokens": max_output_tokens, "max_context_characters": max_context_characters,
               "max_retries": 0, "timeout_seconds": 60, "store": False, "output_format": "json_object"}
    profile_hash = digest(canonical(profile))
    metadata = {
        "started_at": timestamp(), "status": "running", "requested_model": model, "provider": "openai",
        "execution_profile": profile, "execution_profile_sha256": profile_hash,
        "expected_tasks": len(cases),
        "provenance": "live_api", "split": sorted({c["split"] for c in cases}),
        "case_ids": [c["case_id"] for c in cases],
        "prompt_sha256": frozen["prompt_sha256"],
        "freeze_sha256": digest(Path(frozen_file).read_bytes()),
        "max_calls": max_calls, "max_output_tokens": max_output_tokens,
        "max_context_characters": max_context_characters,
        "max_retries": 0, "store": False, "cost_usd": None,
        "cost_note": "Token/call caps are enforced; no dollar budget or free usage is claimed.",
    }
    save_json(out / "run.json", metadata)
    completed = 0
    with (out / "responses.jsonl").open("x", encoding="utf-8") as stream:
        for case in cases:
            started = time.monotonic()
            record = {"case_id": case["case_id"], "case_sha256": case["case_sha256"],
                      "model": model, "prompt_sha256": frozen["prompt_sha256"],
                      "provenance": "live_api", "provider": "openai",
                      "execution_profile_sha256": profile_hash, "started_at": timestamp(),
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
            except KeyboardInterrupt:
                record["error"] = "operator_interrupted"
            except Exception as exc:
                # Exception messages can contain credentials or provider request bodies.
                record["error"] = type(exc).__name__
            record["latency_seconds"] = round(time.monotonic() - started, 3)
            stream.write(canonical(record) + "\n")
            stream.flush()
            completed += 1
            if record["error"]:
                metadata["stop_reason"] = record["error"]
                break
    metadata.update(finished_at=timestamp(), received_responses=completed,
                    status="stopped_on_error" if metadata.get("stop_reason") else "completed")
    save_json(out / "run.json", metadata)
    return out / "responses.jsonl"

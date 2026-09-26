"""Official Claude Code CLI transport; never extracts subscription credentials."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .common import canonical, digest, load_json, save_json, timestamp
from .runner import provider_input, verify_freeze
from .corpus import context_limit


PROFILE = "claude-code-subscription-v1"
SETTINGS = {"disableAllHooks": True, "autoMemoryEnabled": False}
BLOCKED_ENV = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_OAUTH_TOKEN",
)


def export_bundle(cases, prompt_file, frozen_file, split, out,
                  rubric_file="docs/EVALUATION_PROTOCOL.md", max_context_characters=40000):
    """Export only input text and opaque bindings; no labels, spans or rubric."""
    context_limit(max_context_characters)
    frozen = verify_freeze(cases, prompt_file, frozen_file, rubric_file,
                           require_complete=True)
    selected = [c for c in cases if c["split"] == split]
    if split not in ("development", "holdout") or not 1 <= len(selected) <= 30:
        raise ValueError("Select a non-empty development or holdout split, at most 30 tasks")
    if any(len(c["context"]) > max_context_characters for c in selected):
        raise ValueError("Contract exceeds selected context character limit; no silent truncation")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "prompt.txt").write_bytes(Path(prompt_file).read_bytes())
    entries = []
    for i, case in enumerate(selected):
        filename = f"task-{i + 1:03d}.json"
        payload = provider_input(case).encode("utf-8")
        (out / filename).write_bytes(payload)
        entries.append({"file": filename, "input_sha256": digest(payload),
                        "case_id": case["case_id"], "case_sha256": case["case_sha256"]})
    manifest = {"format": "claude-input-bundle-v1", "split": split,
                "max_context_characters": max_context_characters,
                "created_at": timestamp(), "prompt_sha256": frozen["prompt_sha256"],
                "freeze_sha256": digest(Path(frozen_file).read_bytes()), "tasks": entries}
    save_json(out / "bundle.json", manifest)
    return out / "bundle.json"


def read_bundle(folder):
    folder = Path(folder)
    manifest = load_json(folder / "bundle.json")
    if (manifest.get("format") != "claude-input-bundle-v1"
            or manifest.get("split") not in ("development", "holdout")):
        raise ValueError("Unsupported input bundle")
    max_context_characters = context_limit(manifest.get("max_context_characters", 40000))
    prompt = (folder / "prompt.txt").read_bytes()
    if digest(prompt) != manifest["prompt_sha256"]:
        raise ValueError("Bundle prompt hash mismatch")
    tasks = manifest["tasks"]
    if not 1 <= len(tasks) <= 30 or len({t["case_id"] for t in tasks}) != len(tasks):
        raise ValueError("Empty, oversized or duplicate bundle")
    inputs = []
    for i, task in enumerate(tasks):
        # Never follow arbitrary paths supplied by a manifest.
        if task["file"] != f"task-{i + 1:03d}.json":
            raise ValueError("Unexpected bundle filename")
        path = folder / task["file"]
        if path.is_symlink():
            raise ValueError("Bundle input must not be a symlink")
        raw = path.read_bytes()
        payload = json.loads(raw)
        if (digest(raw) != task["input_sha256"]
                or set(payload) != {"question", "contract"}
                or not all(isinstance(v, str) and v.strip() for v in payload.values())
                or len(payload["contract"]) > max_context_characters):
            raise ValueError("Bundle input changed, contains extra fields or exceeds limits")
        inputs.append(raw.decode("utf-8"))
    return manifest, prompt, inputs


def check_environment(env):
    if env.get("CLAUDECODE"):
        raise ValueError("Run from a normal VS Code terminal, outside an active Claude Code agent")
    present = [name for name in BLOCKED_ENV if env.get(name)]
    if present:
        raise ValueError("Subscription mode refuses credential/provider overrides: " + ", ".join(present))


def resolve_cli(binary):
    path = shutil.which(binary)
    if not path or Path(path).suffix.lower() in (".cmd", ".bat"):
        raise ValueError("Install the official native Claude Code CLI on PATH (claude/claude.exe)")
    return str(Path(path).resolve())


def preflight(binary="claude", execute=subprocess.run, env=None):
    env = dict(os.environ if env is None else env)
    check_environment(env)
    binary = resolve_cli(binary)
    with tempfile.TemporaryDirectory(prefix="legal-eval-doctor-") as work:
        try:
            version = execute([binary, "--version"], cwd=work, env=env,
                              capture_output=True, text=True, encoding="utf-8", timeout=20)
            auth = execute([binary, "auth", "status"], cwd=work, env=env,
                           capture_output=True, text=True, encoding="utf-8", timeout=20)
            info = json.loads(auth.stdout)
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            raise ValueError("Claude Code preflight failed; check installation and sign-in locally") from exc
    if (version.returncode or auth.returncode or not isinstance(info, dict)
            or info.get("loggedIn") is not True):
        raise ValueError("Claude Code is not ready; sign in with your existing subscription")
    if (info.get("authMethod") != "claude.ai"
            or info.get("subscriptionType") not in ("pro", "max")
            or info.get("apiKeySource") not in (None, "", "none")):
        raise ValueError("Expected Pro/Max claude.ai login without an API-key source; check auth status")
    # Deliberately discard email, organization IDs and all other auth fields.
    return {"binary": binary, "cli_version": version.stdout.strip(),
            "auth_method": info["authMethod"], "subscription_type": info["subscriptionType"]}


def command(binary, prompt_path, model, effort):
    return [binary, "--safe-mode", "--restricted", "-p", "--output-format", "json",
            "--model", model, "--effort", effort, "--max-turns", "1",
            "--tools", "", "--disallowedTools", "mcp__*", "--strict-mcp-config",
            "--mcp-config", '{"mcpServers":{}}', "--setting-sources", "",
            "--settings", canonical(SETTINGS), "--disable-slash-commands", "--no-chrome",
            "--no-session-persistence", "--system-prompt-file", str(prompt_path)]


def decode_result(raw, returncode, requested_model):
    """Preserve model text verbatim; do not repair or grade it with another LLM."""
    try:
        envelope = json.loads(raw)
        if not isinstance(envelope, dict):
            raise ValueError("Not an object")
    except ValueError:
        return {"raw_output": "", "error": "invalid_cli_envelope"}
    models = sorted(envelope.get("modelUsage", {})) if isinstance(envelope.get("modelUsage"), dict) else []
    result = {"raw_output": envelope.get("result", ""), "error": None,
              "session_id": envelope.get("session_id"), "returned_models": models,
              "usage": envelope.get("usage"), "model_usage": envelope.get("modelUsage"),
              "cli_cost_estimate_usd": envelope.get("total_cost_usd"),
              "provider_subtype": envelope.get("subtype")}
    if "structured_output" in envelope:
        result["raw_output"] = canonical(envelope["structured_output"])
    if returncode or envelope.get("is_error") or envelope.get("subtype") != "success":
        result["error"] = "cli_execution_error"
    elif models != [requested_model]:
        result["error"] = "unexpected_or_missing_model_metadata"
    elif not isinstance(result["raw_output"], str):
        result["raw_output"] = ""
        result["error"] = "missing_result_text"
    return result


def run_bundle(bundle, model, out, max_invocations, allow_subscription_usage=False,
               effort="medium", timeout=180, binary="claude", execute=subprocess.run, env=None):
    manifest, prompt, inputs = read_bundle(bundle)
    if not allow_subscription_usage:
        raise ValueError("Live CLI use requires --allow-subscription-usage after checking your plan")
    if not re.fullmatch(r"claude-[A-Za-z0-9_.-]+", model):
        raise ValueError("Use a full Claude model ID, not a moving alias such as sonnet or opus")
    if not len(inputs) <= max_invocations <= 30 or not 30 <= timeout <= 600:
        raise ValueError("Invocation cap must cover the split (at most 30); timeout must be 30..600s")
    if effort not in ("low", "medium", "high"):
        raise ValueError("Choose a supported effort: low, medium or high")
    out = Path(out).resolve()
    if out.exists():
        raise ValueError("Run directory exists; use a new name")
    env = dict(os.environ if env is None else env)
    status = preflight(binary, execute, env)
    out.mkdir(parents=True)
    (out / "raw").mkdir()
    save_json(out / "input_manifest.json", manifest)
    profile = {"profile": PROFILE, "model": model, "effort": effort,
               "max_turns_per_invocation": 1, "timeout_seconds": timeout,
               "max_context_characters": manifest.get("max_context_characters", 40000),
               "argv_template": command("claude", "PROMPT_FILE", model, effort)}
    profile_hash = digest(canonical(profile))
    metadata = {"started_at": timestamp(), "status": "running", "provider": "claude_code_cli",
                "provenance": "imported", "requested_model": model, "execution_profile": profile,
                "execution_profile_sha256": profile_hash, "preflight": status,
                "bundle_sha256": digest((Path(bundle) / "bundle.json").read_bytes()),
                "freeze_sha256": manifest["freeze_sha256"], "split": manifest["split"],
                "expected_tasks": len(inputs), "max_invocations": max_invocations,
                "billing_note": "Uses existing Pro/Max login. Extra usage must be checked by owner. "
                                "CLI cost estimates are not subscription invoices. Internal retries "
                                "and provider calls are controlled by Claude Code, not this wrapper."}
    save_json(out / "run.json", metadata)
    completed = 0
    with (out / "responses.jsonl").open("x", encoding="utf-8") as stream:
        for i, (task, payload) in enumerate(zip(manifest["tasks"], inputs)):
            started = time.monotonic()
            record = {"case_id": task["case_id"], "case_sha256": task["case_sha256"],
                      "prompt_sha256": manifest["prompt_sha256"], "model": model,
                      "provider": "claude_code_cli", "provenance": "imported",
                      "execution_profile_sha256": profile_hash, "started_at": timestamp(),
                      "raw_output": "", "error": None}
            with (out / "attempts.jsonl").open("a", encoding="utf-8") as attempts:
                attempts.write(canonical({"case_id": task["case_id"],
                                          "started_at": record["started_at"]}) + "\n")
            try:
                # New working directory and CLI session for every task. Gold never enters it.
                with tempfile.TemporaryDirectory(prefix="legal-eval-input-") as work:
                    prompt_path = Path(work) / "prompt.txt"
                    prompt_path.write_bytes(prompt)
                    reply = execute(command(status["binary"], prompt_path, model, effort),
                                    input=payload, cwd=work, env=env, capture_output=True,
                                    text=True, encoding="utf-8", timeout=timeout)
                raw_path = out / "raw" / f"task-{i + 1:03d}.stdout.txt"
                raw_path.write_text(reply.stdout, encoding="utf-8")
                # stderr may contain environment diagnostics; keep it local, never print it.
                (out / "raw" / f"task-{i + 1:03d}.stderr.txt").write_text(reply.stderr, encoding="utf-8")
                record.update(decode_result(reply.stdout, reply.returncode, model))
                record["raw_stdout_sha256"] = digest(raw_path.read_bytes())
                record["returncode"] = reply.returncode
            except subprocess.TimeoutExpired as exc:
                for suffix, value in (("stdout", exc.stdout), ("stderr", exc.stderr)):
                    if value:
                        raw = value if isinstance(value, bytes) else value.encode("utf-8")
                        (out / "raw" / f"task-{i + 1:03d}.{suffix}.partial.txt").write_bytes(raw)
                record["error"] = "cli_timeout"
            except OSError:
                record["error"] = "cli_process_error"
            except KeyboardInterrupt:
                record["error"] = "operator_interrupted"
            record["latency_seconds"] = round(time.monotonic() - started, 3)
            stream.write(canonical(record) + "\n")
            stream.flush()
            completed += 1
            if record["error"]:
                metadata["stop_reason"] = record["error"]
                break  # Never burst through quota/auth/CLI failures or automatically retry.
    metadata.update(finished_at=timestamp(), received_responses=completed,
                    status="stopped_on_error" if metadata.get("stop_reason") else "completed")
    save_json(out / "run.json", metadata)
    return out / "responses.jsonl"

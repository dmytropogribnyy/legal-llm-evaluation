# Run the pilot with Claude Code in VS Code

**Execution profile:** `claude-code-subscription-v1` · **Implementation:** 0.2.0.
The adapter is covered by offline tests, including an actual subprocess fixture. A real Claude Code
subscription run on the owner's Windows machine is **pending**. This evaluates Claude through a
specified Claude Code configuration; it is not an evaluation of a client's deployed AI product.

## What you need

- Python 3.11+ and this repository opened in its own VS Code window.
- The official **native Claude Code CLI** available as `claude` / `claude.exe` in the terminal.
  The VS Code extension alone is not a substitute for this executable. A `.cmd` / `.bat` wrapper
  is rejected to avoid shell quoting differences. Follow the vendor's native installer instructions.
- An existing Pro or Max login through `claude auth login`. The project never extracts, copies or
  stores OAuth credentials. `claude-doctor` accepts the CLI's `claude.ai` / `pro` or `max` metadata;
  unknown or changed auth formats fail for inspection rather than guessing.
- A **full model ID** available to that account. Moving aliases such as `sonnet` and `opus` are
  rejected. The model reported by the CLI must match the requested ID; fallback/missing metadata
  stops the run. Choose effort supported by that model.

Use a normal VS Code terminal for model runs. Do not run the adapter from inside an active Claude
Code agent's Bash tool: nested `CLAUDECODE` sessions are rejected. An assistant may help prepare the
project, but it should hand the live command to the owner. Do not remove the nesting guard.

## 1. Prepare locally — no inference or API key

Run these one-line commands in PowerShell, from the repository root:

```powershell
python -m unittest discover -s tests -v
python -m legal_eval fetch
python -m legal_eval prepare
python -m legal_eval freeze --out runs/claude-protocol-v1.json
python -m legal_eval export-claude --frozen runs/claude-protocol-v1.json --split development --out runs/claude-dev-input-v1
python -m legal_eval claude-doctor
```

`fetch` downloads the pinned public CUAD file (about 40 MB). The remaining preparation is local;
`claude-doctor` checks CLI version and authentication metadata without a model prompt. Existing
freeze/bundle/run/report directories are never overwritten. Use new versioned paths for repeats.

The bundle contains `prompt.txt`, `bundle.json` and nine `task-*.json` input files. Each input has
only `question` and `contract`. The manifest contains opaque case hashes/IDs for joining results;
it contains no reference labels, expected answers, reference spans or review rubric. It still
contains contract text and belongs under ignored `runs/`, not in a public commit.

## 2. Run nine development tasks using your subscription

Before opting in, verify the subscription account, remaining allocation and whether **extra usage**
is enabled. To remain within the included allowance, disable extra usage in your account and do not
switch to Console/API billing. This wrapper cannot read or enforce account billing settings.

```powershell
$ClaudeModel = Read-Host 'Enter the full Claude model ID available to your account'
python -m legal_eval run-claude --bundle runs/claude-dev-input-v1 --model $ClaudeModel --effort medium --max-invocations 9 --allow-subscription-usage --out runs/claude-dev-run-v1
```

This invokes the official CLI sequentially, once per task. It consumes your normal Claude Code
allocation. It does not call the Anthropic API with a separate key, and does not call OpenAI.
Environment variables selecting API credentials or alternate providers are rejected by name;
their values are never displayed. No login or account setting is changed automatically.

Bounds: at most 30 CLI invocations per run, one agentic turn per invocation, 40,000 input characters
per contract and a 180-second subprocess timeout (configurable 30–600s). The wrapper does not retry.
The first CLI error, quota failure, timeout or unexpected model stops subsequent tasks. Claude Code
may make internal provider requests/retries: a CLI invocation is **not** a guaranteed single API
call. There is no hard dollar or output-token cap in this transport. CLI-reported costs are estimates,
not proof of a separate charge or an accurate subscription invoice.

## 3. Score and complete the legal review

```powershell
python -m legal_eval score --responses runs/claude-dev-run-v1/responses.jsonl --split development --frozen runs/claude-protocol-v1.json --out runs/claude-dev-report-v1
```

Open `REPORT.md` and `human_review.csv` in the report directory. Review the original contracts and
the saved model answers. Fill the rubric with the actual reviewer's decisions, then run:

```powershell
python -m legal_eval validate-review --report runs/claude-dev-report-v1/metrics.json --reviews runs/claude-dev-report-v1/human_review.csv
```

A stopped run can still be scored. Failed/missing tasks stay in the denominator; never delete them
to improve the score. Preserve the original directory and label a repeat explicitly. Do not call
a partial run complete. Review validation checks completeness and bindings, not legal correctness.

## 4. Holdout after development

Finish development and freeze the final prompt/protocol into a **new** file. Export a new bundle
with `--split holdout`, run it with `--max-invocations 21`, and score with `--split holdout` and that
same freeze. Use separate output directories for every model/configuration. Do not inspect holdout
answers to tune a model and then describe the same set as fresh confirmation.

## How context separation works

The Python controller reads prepared cases to export an allowlisted input bundle. Each model task
then runs in a new temporary directory containing only the supplied system-prompt file. The
question and contract arrive over stdin. No reference file path is passed to Claude.

The CLI profile uses `--safe-mode`, `--restricted`, a replacement system prompt, no built-in tools,
no MCP tools/servers, no browser integration or slash commands, no session continuation, and no
session persistence. User/project/local settings are excluded; hooks and auto memory are disabled
in the supplied settings. These are task-scoped restrictions; account credentials and other projects
are not modified. **Do not replace safe mode with `--bare`: bare mode skips subscription login.**

These are CLI context controls, not an operating-system sandbox or proof of provider-side isolation.
Managed enterprise policies/hooks may still apply and cannot be overridden here; a managed machine
needs administrator review or a suitably isolated approved environment. Public CUAD contracts may
already have appeared in model training; the local holdout is not a guarantee of unseen material.

Unsupported CLI flags fail without relaxing restrictions. Use a current official native CLI and
inspect compatibility locally. Live acceptance is pending; no tested Claude Code version is claimed
until its actual version has been recorded by a successful owner run.

## Evidence kept locally

- `input_manifest.json`: exact task selection, input hashes and freeze binding.
- `run.json`: CLI version, sanitized auth method/plan, model, effort, execution profile and status.
- `attempts.jsonl`: tasks attempted, written before invocation.
- `raw/`: original CLI stdout/stderr; partial output on timeout when available.
- `responses.jsonl`: model text, reported model/usage/session ID, errors, latency and profile hash.

CLI output is normalized as `provenance: imported`, `provider: claude_code_cli`. It is never labeled
as a direct API receipt. Model text is not repaired or rewritten before scoring. Different execution
profiles cannot be pooled into one report. Hashes verify consistency, not independent authenticity.
Keep these artifacts local: diagnostic output may contain private details. Provider/account retention
controls are separate from `--no-session-persistence`, which concerns local CLI session history.

## Troubleshooting

| Symptom | Action |
|---|---|
| Native CLI not found | Install the official native CLI, restart the terminal, check `claude --version` |
| API/provider override detected | Review that named variable locally; use a subscription-only terminal; do not print its value |
| Nested agent session | Run the displayed command yourself in an ordinary VS Code terminal |
| Unknown subscription/auth fields | Inspect `claude auth status` locally; keep personal details out of shared logs |
| Unsupported flag | Check/update the official CLI; keep the recorded failure and do not remove isolation flags |
| Quota/auth/model error | Stop, inspect local evidence, resolve the issue, then use a new run directory |
| Model ID differs or metadata missing | Verify the exact available model/configuration; do not relabel the response to force a pass |

## Official references checked 2026-09-26

- [CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Programmatic execution, JSON output and bare-mode authentication](https://code.claude.com/docs/en/headless)
- [Pro/Max subscription use and billing](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan)
- [VS Code integration](https://code.claude.com/docs/en/vs-code)

Authentication metadata fields are compatibility checks, not a billing guarantee. This is an
owner-operated local evaluation workflow; it is not a service for sharing subscription access.

## Full CUAD corpus (v0.3.0)

The steps above reproduce the original 30-task pilot. For all 509 unique texts and
41 categories, use the [full-corpus guide](FULL_CORPUS_GUIDE.md). It prepares small
versioned batches, freezes them and exports the same reference-free bundle format.
The default 40,000-character cap remains; an explicit `--max-context-characters 400000`
at batch selection and export allows long full contracts without truncation. Model
context and account usage limits still need to be checked before live execution.

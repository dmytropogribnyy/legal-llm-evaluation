# Operator runbook

## 1. Prepare the public-source pilot

Run from the repository root with Python 3.11+. `python -m legal_eval --help` lists commands.
`fetch` verifies the pinned upstream size and SHA-256. `prepare` writes a deterministic selection
under `data/prepared/`. For the complete 509-text / 41-category catalog, use the separate
[full-corpus guide](FULL_CORPUS_GUIDE.md). Compare the pilot manifest with `data/selection_manifest.json`; a discrepancy
requires investigation before model calls. Re-running preparation reproduces the selection.

The prepared JSONL contains contract text and reference spans. The provider input allowlist includes
only question and contract. The reference labels remain local. A hash is a consistency check, not
cryptographic proof of who authored or reviewed an artifact.

## 2. Review and freeze

The owner reviews the rubric and publisher annotations, starting with development contracts.
Document any corrections separately and issue a new dataset/protocol version. Use development
results to refine the prompt, then create a fresh freeze file with the final prompt and protocol.
Existing freezes and run/report directories are never overwritten by the CLI. Empty or duplicate
case selections are rejected. Full-corpus cases additionally bind the full-corpus selection document;
changing that document requires rebuilding cases and creating a new freeze.

The initial public preparation freeze establishes reproducibility; it is not an expert sign-off.
The local holdout should not be used to repeatedly tune the final prompt. If inspected during
development, disclose that exposure and select a new confirmation set.

## 3. Execute within a declared scope

For an existing Claude Code Pro/Max subscription, use the dedicated
[VS Code guide](CLAUDE_CODE.md). Its `export-claude` and `run-claude` commands preserve input/response
bindings without putting reference answers in the evaluated session. `claude-doctor` checks the
native CLI and sanitized authentication metadata. This transport limits CLI invocations, not internal
provider calls; its outputs use `imported` provenance and a versioned execution profile. Run each
configuration separately. Do not treat its reported cost estimate as a subscription invoice.

For direct OpenAI API evaluation:

Install the optional OpenAI adapter only for live calls. Set `OPENAI_API_KEY` through your shell or
local secret manager. No `.env` loading is performed. Use the exact available model ID appropriate
to your account. The adapter uses the Responses API, JSON output mode, no tools or browsing,
`store=False`, no automatic retry and a 60-second request timeout. Account/provider data controls
remain separate. The default output cap is 1,200 tokens; incomplete responses are recorded as errors.

Call cap: at most 30 per invocation, covering the selected batch. The original pilot has 9 development
and 21 holdout tasks; full-corpus batches use their own recorded counts. Default context cap: 40,000
characters. Both adapters support explicit long-context opt-in up to 400,000 characters as described
in the full-corpus guide; this is not a guarantee of model token-window fit. Dollar cost is not
calculated; inspect provider pricing before enabling paid calls. The application does not train or fine-tune a model.

Run each model into a new directory. An interrupted run remains partial; score it as partial rather
than deleting failures. Repeating a run creates a new version and incurs additional calls.
The attempt log, response JSONL and run metadata retain the record of what was requested. Both
adapters stop after the first provider error, incomplete output or operator interruption. The CLI
returns a failure status; retained responses can still be scored with remaining tasks marked missing.
OpenAI responses now bind an `openai-responses-v1` profile including output/context caps, format,
timeout and retry policy. Reports from different execution settings must remain separate.

## 4. Imported responses from another provider

One JSONL record per case:

```json
{
  "case_id": "ID_FROM_PREPARED_CASES",
  "case_sha256": "HASH_FROM_PREPARED_CASES",
  "model": "EXACT_PROVIDER_MODEL_ID",
  "prompt_sha256": "HASH_FROM_FREEZE",
  "provenance": "imported",
  "raw_output": "{\"relevant_found\": false, \"quotes\": [], \"summary\": \"No relevant provision found.\", \"needs_human_review\": true}",
  "error": null
}
```

These are placeholders, not model results. Preserve original provider export, timestamp, settings,
request/response IDs and usage next to imported records. Import provenance is declared, not
independently authenticated. Synthetic fixtures must use `synthetic_fixture`. Mixed model/prompt/
provenance/execution-profile/provider reports, different returned OpenAI model IDs, mixed splits or
selection revisions, duplicate IDs, unknown IDs and stale case/prompt hashes are rejected. Legacy
imports without provider/settings metadata remain readable but do not establish configuration parity.

## 5. Score and review

Score with the exact split and frozen protocol used for the run. The CLI checks that the case file
contains the complete frozen selection before selecting the split. Missing/error responses remain
visible. Reports should not be presented as complete where tasks are missing.

Every report creates a blank `human_review.csv`. Fill its four 0–2 rubric dimensions, severity,
disposition, rationale, source reference, actual reviewer name, UTC review timestamp and response
hash. Use the exact source contract and question when reviewing. `validate-review` rejects blank,
incomplete, duplicate, stale or missing review records. It does not authenticate identity, adjudicate
legal interpretation, modify automated metrics, or authorize deployment.

## 6. Compare and hand over

Use the delivery template. Report observed counts by category, all critical/major errors, and paired
examples where models disagree. Keep reference corrections distinct from model errors. A model
comparison with unequal prompts, cases or limits must disclose the difference.

Keep raw contracts, provider responses and client-specific evidence private by default. Before a
public portfolio release review rights, source attribution, sensitive content, provenance and
accuracy of claims. Publish an aggregate summary and selected permitted excerpts after review.
Never publish keys, client names without permission, fabricated results or unsigned expert approvals.

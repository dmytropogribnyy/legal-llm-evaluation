# Validation record

## v0.2.0 — Claude Code transport, 2026-09-26

- 40 offline unit/regression tests passed locally, including an actual Python subprocess standing
  in for the external CLI. This fixture is explicitly not Claude inference.
- Tests cover reference-free export, changed input hashes, unexpected gold fields, manifest path
  traversal, usage/cap/model guards, subscription auth metadata, rejected provider overrides,
  fresh task directories, raw receipt preservation, timeout/error stop behavior and profile mixing.
- CI now defines Ubuntu/Windows with Python 3.11/3.12. Check the commit's actual Actions result
  before claiming any particular matrix job passed.
- Source selection, extraction prompt, legal rubric and metric formulas are unchanged. A separate
  versioned execution profile records the new CLI transport; pooling distinct profiles is rejected.
- **Real Claude Code invocations: 0. Windows native CLI / Pro/Max live acceptance: pending.**
- **Owner legal review and model comparison: pending.** No owner credentials were accessed and no
  API/subscription model usage was consumed while implementing the adapter.

## v0.1.0 — initial foundation

**Date:** 2026-09-26 · **Release:** 0.1.0 technical foundation.

| Check | Actual result |
|---|---|
| Unit/regression suite | 26 tests passed |
| Ruff | Passed |
| Python compilation | Passed |
| Offline evaluator self-check | Four controlled responses processed; injected unsupported quote, missed provision and missing review request detected |
| Source verification | CUAD JSON: 40,128,638 bytes; SHA-256 matches pinned source |
| Source annotation offsets | All selected reference spans match their recorded source offsets |
| Selection reproduction | Exact same manifest on independent second preparation |
| Contract split | 3 development / 7 holdout; zero identical-context overlap |
| Label coverage | Both presence labels in each category/split; at least two of each in holdout |
| Live API calls | **0 performed** |
| Owner legal reviews | **0 recorded; pending** |
| Model comparison / external acceptance | **Not performed** |

## What the tests exercise

Unsupported quotes; omitted reference material; false absence and false presence; invalid JSON;
schema inconsistency; human-review flags; missing/error responses in denominators; duplicate and
unknown response IDs; stale case and prompt hashes; mixed model/provenance rejection; separation of
reference labels from provider input; paid-call guards; sanitized error records; frozen-selection
completeness; review completeness and response binding; deterministic contract splits and source
annotation offsets. Provider transport is mocked in tests, not treated as live acceptance.

The offline demo's numeric scores describe deliberately constructed self-checks. They are not
published as model performance. Run it locally with `python -m legal_eval demo --out runs/self-check`.

Detailed source/selection evidence: [DATA_VALIDATION.json](DATA_VALIDATION.json),
[selection manifest](../data/selection_manifest.json),
[preparation freeze](../data/preparation_freeze.json).

## Next evidence needed

1. Owner review of legal criteria and source-label interpretation.
2. Exact provider/model selection and agreed live-run spending scope.
3. Development runs, final protocol freeze, then comparable holdout runs.
4. Completed legal review of outputs and a dated case study.
5. Deployment-specific applicability assessment before any compliance-related conclusion.

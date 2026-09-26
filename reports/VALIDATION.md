# Initial validation record

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

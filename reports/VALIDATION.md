# Validation record

## v0.3.2 — clean-copy and CLI workflow audit, 2026-09-26

- **70 offline tests passed**, including five new regressions. New tests run actual CLI
  subprocesses in an isolated path containing spaces: cached fetch, preparation, selection,
  freeze, reference-free export, scoring and review-template validation. Fixtures are explicitly
  synthetic; review CSV checks do not represent a human legal review.
- Error paths cover modified source/cases, missing responses, overwrite rejection, unsupported
  Claude CLI versions and undecodable subprocess output. Encoding failures stop the run and
  preserve error/missing-task accounting instead of leaving an unfinished status.
- Claude preflight now requires native CLI 2.1.248+ (the vendor's documented minimum for
  `--restricted`). This does not claim live compatibility with an untested installed version.
- A separate clean archive reproduced the original pilot and complete 509-text corpus from the
  hash-verified cached source; its catalog exactly matched the committed summary. A 12-task
  real-data development batch was selected, frozen and exported without a model call.
- Ruff, compilation and the controlled evaluator self-check passed. The existing CI matrix
  automatically includes the new CLI workflow tests; results are attached to the published commit.
- Dataset, prompts, protocol documents, metric formulas and execution profile IDs are unchanged.
- **Live model calls: 0. Owner legal reviews: 0.** Native Windows subscription acceptance remains
  pending; mock CLI responses and passing offline checks are not model performance evidence.

## v0.3.1 — consistency and operator audit, 2026-09-26

- Fixed acceptance of empty/duplicate case selections at freeze/verification boundaries.
  Duplicate inputs now fail before any provider invocation.
- Bound full-corpus selection-document verification at both freeze and scoring entrypoints,
  in addition to existing prompt/rubric checks. Mixed pilot/full-corpus freezes are rejected.
- Scoring rejects mixed development/holdout, selection revisions, providers and returned
  OpenAI model IDs, preventing incompatible results from entering one report.
- Added OpenAI execution profile `openai-responses-v1`: output/context caps, model, JSON mode,
  timeout, retry policy and store flag. Different configurations cannot be pooled silently.
- OpenAI now stops on the first error/incomplete output/operator interruption, saves final run
  status and preserves attempted/error/missing cases. CLI failures return a nonzero exit status.
- Reports show the split, selection protocol and returned model IDs. Malformed human-review
  CSVs now produce actionable validation errors instead of uncaught missing-cell/header errors.
- **65 offline tests passed**, including 14 new audit regressions. Fake provider receipts are
  controlled fixtures, not real inference. Ruff, compilation and offline self-check passed.
- Full-corpus metadata and the 20,867-task pool remain unchanged. Original pilot prompt,
  both selection documents, rubric and numerical metric formulas are unchanged. Previously
  mixed runs that passed loose validation must be separated and rescored.
- Full-source catalog verified against the committed summary/index, with existing v0.3.0
  batch freezes still valid. CI results are available on the exact published commit.
- Live model calls and owner legal reviews during this audit: **0**.

## v0.3.0 — full CUAD corpus, 2026-09-26

- 51 offline tests passed locally; Ruff, compilation and evaluator self-check passed.
- Complete pinned source processed: 510 records / 509 exact unique texts, 41 categories,
  20,910 source tasks; every answer offset and presence flag validated.
- One duplicate record suppressed from scoring; two conflicting unique category labels
  quarantined, leaving 20,867 eligible tasks. Original annotations remain inspectable.
- 404 development / 105 holdout contracts; all ten pilot assignments preserved, with
  no exact-text overlap. Near-duplicate / issuer-family clustering remains unimplemented.
- Two real-data development pages exported as local cases: 60 tasks covering all 41
  categories without duplicate IDs. First 30 tasks frozen and exported reference-free.
- The longest real contract (338,211 characters) selected, frozen, exported and read
  back intact with explicit long-context opt-in; no model was invoked.
- Regression fix: JSONL parsing now preserves Unicode line separators inside contracts.
  Generated JSON/JSONL/CSV and tracked source line endings are deterministic across OSes.
- Public metadata: [corpus summary](../data/corpus_summary.json),
  [contract index](../data/corpus_index.csv), [validation evidence](CORPUS_VALIDATION.json).
- New selection protocol is `cuad-full-corpus-v1`; original pilot prompt/rubric and
  frozen manifests remain unchanged. Claude execution profiles now record the context cap.
- **Live model calls: 0. Owner legal reviews: 0.** Source preparation and transport
  fixtures do not constitute model benchmark results or customer delivery evidence.

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

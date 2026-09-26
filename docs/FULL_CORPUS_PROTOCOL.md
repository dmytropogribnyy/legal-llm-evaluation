# Full CUAD corpus protocol v1

Selection ID: `cuad-full-corpus-v1`. Introduced in software v0.3.0.
This is a separate selection protocol; it does not replace the frozen 10-contract,
three-category `contract-review-pilot-v1`. The extraction prompt and automated
rubric remain [v1](EVALUATION_PROTOCOL.md); case hashes additionally bind this protocol.
A change to this document requires rebuilding the catalog and new batch freezes.

## Source, normalization and exclusions

Use only the pinned CUAD v1 JSON in `data/source.json`; verify its SHA-256 before
preparation. Catalog every source question and full document context. Validate
all annotated character offsets and presence labels. Store text once per exact
SHA-256 and tasks separately; neither file is published in Git.

There are 510 source document records, 509 unique exact texts, 41 categories and
20,910 source question/contract pairs. These are **not** 20,910 positive clauses.
The two ADURO consulting agreement records share identical text but have different
annotations for Exclusivity and Anti-Assignment. Preserve both originals in the
catalog. Keep the lexicographically first title as the canonical record for runs;
suppress the second record's 41 tasks and quarantine both conflicting categories
from automatic evaluation. This leaves 20,867 deduplicated, unambiguous tasks.
Do not silently choose a winning annotation or claim expert adjudication.
Near-duplicates, amendments, shared templates and issuer families have not been
clustered; exact-text separation alone does not prove independence.

## Development and holdout

Preserve all ten original pilot contract-hash assignments. For remaining unique
texts, assign holdout if `int(SHA256(protocol_id + contract_sha256)[:8], 16) % 5 == 0`,
development otherwise. Every category and duplicate of a contract stays in that
same split. This produces an approximately 80/20 allocation for new contracts,
not an exact ratio or a guarantee of positive/negative balance in every category.
Publish per-category/per-split counts, including zeros. The source is public and
may have appeared in model training: this is a regression benchmark, not proof of
unseen-data generalization. Viewing holdout answers exposes that material; keep
an exposure log and use a new external set for a fresh confirmation after tuning.

## Batch ordering and context

Filter by split, optional category names and an explicit maximum context length.
Remove duplicate and conflicted tasks. Within each category sort by stable case ID;
interleave the alphabetically ordered categories round-robin. Select `[offset:offset+limit]`,
with 1–30 tasks per batch. No reference labels, spans or model outputs influence
ordering. Keep filters fixed when advancing offsets to avoid overlapping selections.
Record selected IDs, catalog/file hashes, filters and pagination in `batch.json`.
A partial page or selected categories must never be reported as full-corpus coverage.
For fewer than 41 tasks, a batch cannot cover all categories; subsequent pages complete
coverage. For targeted work, explicitly select legal risk categories.

All contracts remain complete: no truncation, gold-guided cropping or artificial
negative labels from missing chunks. Default execution cap: 40,000 characters
(293 unique contracts). Explicit opt-in up to 400,000 characters covers all 509
unique texts; the observed maximum is 338,211. This is a character safety cap,
**not a token count or a model-context guarantee**. Operators must check model
context/output budgets and subscription limits before long-context runs. Provider
rejection/timeout stays an error in the report; no hidden fallback to shorter text.

## Freezing, evidence and interpretation

Materialize only the selected batch into the existing case format, hash every case,
then freeze it with the extraction prompt and v1 rubric. Each case includes this
selection protocol's hash. Export only question and contract to the model; gold
annotations and reviewer notes remain local. Claude CLI/OpenAI adapters keep their
explicit usage opt-in and maximum 30 tasks per run. No automatic all-corpus paid loop.

Automated checks measure output schema, source-supported quotations, annotated
presence and lexical overlap. They do not certify legal interpretation, enforceability,
commercial acceptability, or AI Act conformity. Source-supported but irrelevant quotes
can pass grounding; expert review remains necessary. Expanded categories (dates,
parties, names as well as clauses) reuse the extraction task, not a legal-advice rubric.
Run reports show missing/error cases in denominators. Report category metrics and
positive/negative support; do not hide rare categories behind aggregate accuracy.
Full-corpus results require all planned batches, consistent model/prompt/settings,
unique case IDs and a declared scope. Cross-batch aggregation is not automated yet;
do not average batch percentages as if denominators were equal.

Corpus validation is data engineering evidence. Model responses, independent legal
reviews, customer engagements and EU AI Act applicability decisions need separate,
real evidence. This version does not assert those have been completed.

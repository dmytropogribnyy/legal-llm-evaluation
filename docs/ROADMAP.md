# Completion roadmap

## Stage 1 — implemented technical foundation

- Pin and verify real CUAD source data; select complete contracts deterministically.
- Freeze prompt/protocol/case hashes and separate contract-level development/holdout groups.
- Validate output structure, quote support and agreement with source labels.
- Preserve errors and missing tasks; generate reports and response-bound review sheets.
- Provide a bounded optional provider adapter and offline regression checks.
- Provide a Claude Code Pro/Max CLI adapter, reference-free bundles and a VS Code operator guide.
- Draft the engagement brief, human rubric and conditional AI Act evidence mapping.

## Stage 2 — owner legal review

Dmytro reviews the scope, rubric and development reference labels. Record actual decisions and
corrections. Check whether the small selection is useful for the intended commercial service.
If selection or methodology changes, issue a new protocol before model runs. Review the governance
mapping against the current applicable legislation; no signature is pre-filled.

## Stage 3 — measured model pilot

Choose exact model IDs and a bounded API or subscription usage scope. First validate the actual
provider/CLI on the owner's machine; offline tests do not establish live compatibility.
Run development tasks, finalize the prompt,
then evaluate two models against the same holdout. Initial comparison: 42 holdout responses,
plus at least 18 development responses if both models are used there. Repeats cost extra and must
be separately identified. Keep actual output/usage records; inspect incomplete responses.

## Stage 4 — reviewed case study

Review all model responses, adjudicate source-label disagreements, and publish a concise report:
scope, counts, metrics, legal error examples, limitations and practical recommendations. Do not
select examples solely to make a preferred model look good. Update the README status and link
the completed case study from the portfolio and LinkedIn. A completed technical case can then be
described accurately in the Independent Projects section of a CV.

## Stage 5 — optional external pilot

Offer the same bounded workflow to a real legal team or LegalTech provider. Agree the brief,
data permissions, success criteria and delivery. Keep records of the actual engagement and
recipient feedback. A paid or pro bono commission can be described as such once it exists.

## Deliberately deferred

Full RAG retrieval evaluation, model training, OCR, large benchmarks, inter-rater reliability,
production monitoring, comprehensive adversarial testing, conformity assessment and legal advice
on enforceability. Add only when required by a concrete next engagement.

## Delivered in v0.3.0

Full CUAD catalog, 509 unique complete texts / 41 categories, deduplication and
annotation-conflict quarantine, preserved pilot splits, bounded category-filtered
batches, full-text inspection and explicit long-context support. Real-model runs
and owner legal review remain the next evidence milestone. Further source families
(e.g. contract inference rather than clause extraction) require their own adapters
and scoring protocols before their counts can be combined meaningfully.

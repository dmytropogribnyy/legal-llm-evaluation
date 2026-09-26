# Sample engagement brief — Contract review evaluation

**Record:** CR-001 · **Initiated:** 2026-09-26 · **Type:** independent service pilot.
**Service:** project-based Legal AI / LLM evaluation with EU AI Act readiness support.
**Owner:** Dmytro Pogribnyy. No external client is represented by this public pilot.

## Business question

A legal team considering a contract-analysis assistant needs to know what the tool misses,
what it invents, and when a lawyer must intervene. A model's fluent explanation is insufficient
for this decision. The pilot assembles inspectable evidence for a limited contract-review workflow.

## Intended use and scope

- English-language commercial-contract provision identification for a human legal reviewer.
- Liability caps, termination for convenience, and governing law.
- Complete supplied contract text, a defined question, supporting quotes and a brief summary.
- The user remains responsible for legal interpretation and any action on the agreement.
- No determination of enforceability, legal advice to the public, signing, automated negotiation,
  litigation decisions, individual eligibility, employment decisions, or judicial use is evaluated.

These are the pilot's design assumptions, not a conclusion about any future client's actual system.

## Deliverables and acceptance

| Deliverable | Acceptance evidence |
|---|---|
| Dataset and reference scope | Pinned source, text hashes, all annotation offsets valid, disjoint contract groups |
| Evaluation specification | Frozen prompt and protocol hashes before final model runs |
| Technical report | Every expected case accounted for, including missing and failed responses |
| Legal error register | Reviewer rationale and source evidence for each assessed response |
| Model comparison | Separate reports on identical cases; disagreements explained by category |
| Readiness worksheet | Applicability assumptions, evidence gaps, responsible owners and next actions |
| Handover | Reproduction commands, source attribution, limitations and human review record |

Technical completion does not imply a model is acceptable for deployment. Proposed release criteria
must be agreed with a real recipient before a commissioned engagement. For this pilot, a critical
unsupported legal assertion or missed material qualification blocks a positive acceptance recommendation
until investigated. Percentage thresholds are intentionally not invented before legal review.

## Owner contribution

The repository documents technical preparation and assisted drafting of the methodology. Dmytro's
legal review of the reference labels, rubric and model outputs is a pending work item. It will be
recorded with reviewer, date, rationale and evidence; no expert sign-off is inferred from authorship.

## A future external engagement

Record the agreed purpose, allowed data, provider/subprocessor conditions, deliverables, commercial
terms, recipient acceptance and publication permission. Keep identities and confidential material
outside this public repository. Do not describe an independent pilot as completed commissioned work.

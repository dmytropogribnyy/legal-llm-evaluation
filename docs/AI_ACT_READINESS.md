# EU AI Act readiness — applicability and evidence mapping

**Service scope:** preliminary applicability assessment, evidence organization and gap analysis.
**Pilot status:** independent illustrative deployment scenario; no client deployment assessed;
legal owner review pending. This document is not a conformity assessment or certification.
**Source review date:** 2026-09-26. Confirm the current consolidated legislation, amendments,
application dates and relevant guidance at the start of each engagement. This pilot does not
determine obligations from a product label or hardcode a regulatory deadline.

## 1. Establish the actual use case

Complete the following before marking any obligation applicable:

| Question | Pilot assumption / outstanding evidence |
|---|---|
| Intended purpose | Help a legal professional locate and inspect commercial-contract provisions |
| Decision impact | Advisory output; a person reviews the agreement and makes decisions |
| Organization's role | Unresolved for a commissioned deployment: provider, deployer or other role must be established |
| Users and territory | Illustrative EU-based legal team; actual users and deployment territory to confirm |
| High-risk pathway | Screen Article 6 / Annex I and each relevant Annex III use case; do not assume from “Legal AI” |
| Justice or ADR use | Not in this pilot's intended use; a judicial/ADR deployment needs a fresh assessment |
| Transparency duties | Assess the actual interaction and disclosure arrangements under applicable rules |
| Data and providers | Public evaluation data in this pilot; client processing and retention not assessed |

Article 6 and Annex III provide classification criteria. Annex III's justice-related use cases are
specific, including certain judicial-authority and alternative-dispute-resolution uses. The preliminary
inference for this pilot is that the words “contract review” alone do not establish that classification.
Document intended purpose and actual deployment before reaching a conclusion.

Sources: [Article 6](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6),
[Annex III](https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3),
[Commission overview](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai).

## 2. Map controls conditionally

Articles 9–15 below concern high-risk systems. Until classification is resolved, these rows are
**conditional requirement mappings / useful governance practices**, not a statement that all those
obligations apply to this pilot. A code artifact provides limited evidence; it does not satisfy an
entire legal obligation by itself.

| Reference / theme | Evidence available or designed here | Gap to assess in a real deployment |
|---|---|---|
| [Article 9 — risk management](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-9) | Failure categories and risk register | System-wide lifecycle process, ownership, residual-risk acceptance |
| [Article 11 — documentation](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-11) | Brief, data card, protocol, model/run metadata | Complete applicable technical documentation and deployment architecture |
| [Article 12 — record-keeping](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-12) | Local attempt/response records and hashes | Production logging, integrity controls, access and retention policy |
| [Article 14 — human oversight](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-14) | Review rubric, response-bound review sheet, no automatic acceptance verdict | Trained reviewers, effective intervention, escalation and actual operational practice |
| [Article 15 — accuracy and robustness](https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-15) | Narrow output checks and documented evaluation limits | Representative validation, adversarial testing, cybersecurity, ongoing monitoring |

Related checks may include data governance, instructions, transparency, staff competence, supplier
terms and deployer duties. These are open scope questions, not covered by a five-row checklist.
The complete legal text is accessible via [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng).

## 3. Issue an evidence-gap report

For each applicable item record: reference and source version; applicability rationale; control;
artifact path/hash; evidence owner; status (available / partial / missing / not applicable with
reason); remaining action; reviewer and date. Do not issue an overall compliance percentage.

**Current conclusion:** technical preparation supplies some evaluation and traceability artifacts.
There is no live model assessment, reviewed legal evaluation, operational oversight evidence, full
classification decision or conformity conclusion. Those gaps are the next work, not hidden findings.

# Evaluation protocol v1

## Question and unit of analysis

The primary unit is one contract/category task. A contract contributes three correlated tasks;
therefore 30 tasks are not 30 independent contracts. The outcome is support for a human review
decision, not an automated legal opinion.

## Selection and development boundary

Use the hash-pinned CUAD v1 JSON specified in `data/source.json`. Retain one-paragraph contracts of
at most 40,000 characters with all three target categories. Never crop around known answer spans.
Remove exact duplicate contexts and sort by SHA-256 of `contract-review-pilot-v1` plus title. Select
three development contracts greedily to cover at least one positive and one negative label per
category. Select seven holdout contracts from the remainder to cover at least two of each label per
category. At each step maximize uncovered label requirements; break ties by the fixed hash order.
Fail if coverage cannot be met. This uses source annotations only, before any model outcomes.
It is a deliberately stratified pilot, not a representative sample of legal work.

Exact counts are published in `reports/DATA_VALIDATION.json`. Report category-level counts and errors; aggregate
accuracy can conceal a model that mostly predicts absence. Empty reference labels may warrant
expert correction, so absence agreement is not proof that no relevant clause exists.

Review development cases when revising prompts. Before holdout, save a new freeze of case hashes,
prompt and this protocol. Do not alter the protocol or select a winner after inspecting holdout and
then report the same results as a fresh test. Further tuning creates a new exploratory iteration;
confirmation needs another independently selected set. Public CUAD may already be in model training
data. No training-data novelty or unseen-benchmark claim is made.

## Model response

Required JSON fields: `relevant_found` (boolean), `quotes` (list of nonempty verbatim passages),
`summary` (text), and `needs_human_review` (boolean). A positive finding needs at least one quote;
an absent finding needs an empty quote list. References are withheld from the provider input.
The summary must capture material exceptions and avoid claims beyond the supplied agreement.

## Automated metrics

| Metric | Calculation | Interpretation limit |
|---|---|---|
| Schema validity | Valid responses / all expected tasks | Formatting and consistency only |
| Reference presence accuracy | Presence agrees with CUAD / all expected tasks | Annotation agreement, not legal accuracy |
| Verified quote rate | Quotes found in source / all submitted quotes | Whitespace-normalized substring check; no quotes means N/A |
| Positive reference token F1 | Token-multiset overlap over all annotated positive spans, macro-averaged over positive tasks | Diagnostic lexical coverage; no legal-equivalence claim |
| Missing/error counts | Expected tasks without a usable response | Remain in denominators; never silently dropped |

Unsupported quotes receive no lexical overlap credit. A quote from an irrelevant section can still
pass the substring check: a reviewer must assess relevance and reasoning. Repeating a quote or
returning an entire contract is penalized by the lexical precision term, not treated as perfect
extraction. There is no all-purpose composite “legal quality score”. Review false positives,
false negatives and every unflagged response.

## Human rubric

Reviewers work from the original text, the stated question, publisher labels and model response.
Compare model outputs without a model label where practical. Do not use a second LLM as the only
adjudicator. The initial pilot uses one named reviewer; independent agreement is not claimed.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Legal accuracy | Materially incorrect | Partially correct; correction needed | Accurate within supplied scope |
| Material completeness | Misses a decisive condition or exception | Some relevant detail omitted | Material conditions captured |
| Supported reasoning | Material unsupported assertion | Evidence insufficient for part of explanation | Claims supported by source |
| Uncertainty handling | Unjustified certainty or fabricated answer | Limitations only partly explained | Appropriate qualification or absence finding |

Severity is **critical** for a materially wrong conclusion likely to drive a harmful decision;
**major** for a substantial omission requiring correction; **minor** for a nonmaterial issue;
**none** where no issue was identified. Record rationale, source reference, disposition (accept,
revise, reject), reviewer, UTC timestamp and exact response hash. A blank worksheet is not a review.
Reference corrections require a separate adjudication record and dataset version, never silent
editing to favor a model. Report both original-label and adjudicated results if this occurs.

## Comparison and conclusions

Use identical cases, prompt, protocol and output caps for a primary paired comparison. Preserve
requested and returned model IDs, response IDs, timestamps, provider status and token usage.
If settings differ, label that comparison accordingly. Inspect all 21 held-out tasks per model.
Show numerator and denominator with each headline percentage; avoid significance or broad ranking
claims on seven contracts. Repeated runs and contract-level uncertainty estimates are future work.

Cost is unknown unless priced against the relevant model/account tariff. Call and token caps are not
dollar caps. Latency is observed client elapsed time, not a guaranteed service level.

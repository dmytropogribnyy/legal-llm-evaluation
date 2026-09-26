# Legal AI & LLM Evaluation

**Independent evaluation services · Contract review · EU AI Act readiness support**

A Python workflow for testing how reliably an LLM identifies contract provisions and supports its
answers with source evidence. The service combines legal review, automated output validation,
error analysis, and practical evidence mapping for AI governance.

**Available for project-based freelance / B2B engagements.** This public repository presents an
independently initiated service pilot using published commercial-contract data. It does not disclose
client work or represent an external commission.

## Contract evaluation corpus

**Decision supported:** where does a contract-review AI miss material provisions, invent supporting
quotes or require legal review before its output can be relied on?

| Scope | Current implementation |
|---|---|
| Full source catalog | 510 CUAD document records; **509 unique complete contract texts** |
| Coverage | **41 categories; 20,910 source question/contract pairs** |
| Evaluation pool | **20,867 tasks** after exact deduplication and conflicting-annotation exclusions |
| Development / holdout | 404 / 105 unique contracts; original ten pilot assignments preserved |
| Inspection | Full texts, reference offsets, provenance, searchable contract index and category coverage |
| Execution | Reproducible batches of 1–30 tasks; OpenAI API or local Claude Code adapter |
| Long documents | Complete texts up to 338,211 characters; explicit context-limit opt-in |
| Checks and review | JSON validity, source-supported quotes, presence/overlap checks, legal-review templates |
| Governance | Intended-use assessment, applicability worksheet, evidence map and risk register |

**Status — 26 September 2026 · v0.3.0:** full-corpus preparation and offline validation are complete.
The source contains an exact duplicate with conflicting annotations in two categories; both conflicts
are preserved for inspection and excluded from automatic scoring. The original 10-contract / 30-task
pilot remains reproducible under its original protocol.
**Live model comparison and owner legal review have not yet been performed.**
The [validation record](reports/VALIDATION.md) distinguishes data checks from model evidence.

**[Full corpus: inspect, select and run](docs/FULL_CORPUS_GUIDE.md)** ·
[Verified corpus summary](data/corpus_summary.json) · [Contract index](data/corpus_index.csv)

## What an engagement delivers

1. An agreed evaluation brief and acceptance criteria.
2. A versioned dataset with provenance and a documented reference-review process.
3. Reproducible model runs, preserved responses and transparent metrics.
4. A legal error register with supporting passages and recommendations.
5. An EU AI Act applicability and evidence-gap worksheet, scoped to the actual use case.

Start with the [sample engagement brief](docs/ENGAGEMENT_BRIEF.md),
[evaluation protocol](docs/EVALUATION_PROTOCOL.md), and
[AI Act readiness mapping](docs/AI_ACT_READINESS.md).

## Try the evaluator locally

Python 3.11+; no API key or third-party Python package is needed for the offline workflow.
Run commands from the repository root.

```bash
python -m unittest discover -s tests -v
python -m legal_eval demo --out runs/self-check
```

The self-check uses four **controlled fixtures** to demonstrate detection of missing provisions and
unsupported quotes. Its scores describe the evaluator checks, not an LLM's performance. The commands below reproduce the original pilot. For the full corpus, follow the
[full-corpus guide](docs/FULL_CORPUS_GUIDE.md).

```bash
# Downloads approximately 40 MB from the publisher's pinned Hugging Face revision.
python -m legal_eval fetch
python -m legal_eval prepare
python -m legal_eval freeze --out runs/protocol-v1.json
```

The source is hash-verified before use. Contract texts, reference answers, paid runs and review
sheets remain in ignored local directories. The public [selection manifest](data/selection_manifest.json)
contains IDs, source references and hashes, without redistributing the full contracts.

## Use Claude Code in VS Code

Use the official native Claude Code CLI with your existing Pro/Max login. The workflow exports
reference-free input bundles, starts a fresh restricted CLI session for each task, preserves original
responses and feeds them to the same evaluator. It requires an explicit model ID and usage opt-in.

**[Step-by-step PowerShell instructions](docs/CLAUDE_CODE.md)** cover preparation, subscription
preflight, the original nine development tasks, scoring and human review. The
[full-corpus guide](docs/FULL_CORPUS_GUIDE.md) adds larger selections and long documents. No separate Anthropic API key is used.
Account limits and any enabled extra usage still apply. Run inference from an ordinary VS Code
terminal, outside the coding agent's own session. The VS Code **Run Task** menu also includes offline
tests and the no-inference subscription preflight.

This measures a declared Claude Code configuration. Its CLI receipts use `imported` provenance;
they are not labeled as direct API calls. Keep the input/output artifacts under ignored `runs/`.

## Use the OpenAI API

Install the optional adapter and provide `OPENAI_API_KEY` through your local environment.
No key is read from a repository file.

```bash
python -m pip install -e ".[openai]"
python -m legal_eval run-openai --model YOUR_MODEL_ID --split development \
  --frozen runs/protocol-v1.json --max-calls 9 --allow-paid --out runs/model-a-dev
python -m legal_eval score --responses runs/model-a-dev/responses.jsonl \
  --split development --frozen runs/protocol-v1.json --out runs/model-a-dev-report
```

After development, freeze the final prompt/protocol into a **new** file. Evaluate each chosen model
on the same 21 holdout tasks with `--split holdout --max-calls 21`, separate output directories, and
the same frozen protocol. Record exact model IDs; do not mix development and holdout scores.

The adapter is covered with a fake transport; live-provider acceptance is pending. It disables SDK
retries, caps calls and output tokens, requests `store=False`, and preserves errors in the denominator.
Provider retention and account terms still require review before sending non-public material.
There is no automatic dollar-budget calculation. Calls require the explicit `--allow-paid` flag.

Each report contains `REPORT.md`, `metrics.json`, and a blank `human_review.csv` bound to exact
response hashes. Complete the review using the rubric, then check its completeness:

```bash
python -m legal_eval validate-review --report runs/model-a-dev-report/metrics.json \
  --reviews runs/model-a-dev-report/human_review.csv
```

The review validator checks records and bindings; it does not authenticate the reviewer or make a
legal judgment. Other providers can be evaluated using the documented [response format](docs/RUNBOOK.md).

## Interpretation

- A quote appearing in a contract does not establish that the model interpreted it correctly.
- CUAD labels are reference annotations, not a determination of enforceability or an exhaustive legal opinion.
- Corpus size is not evidence of model quality. Scores apply only to the tasks actually run and reviewed.
  Public benchmark exposure during training is unknown; the local holdout is not guaranteed unseen.
- Exact deduplication does not remove near-duplicates, related amendments or issuer-family overlap.
- AI Act mapping starts with intended use and applicability. A contract-review tool is not automatically
  high-risk because it operates in a legal domain. The mapping is readiness support, not certification.

## Documentation

| Document | Use |
|---|---|
| [Engagement brief](docs/ENGAGEMENT_BRIEF.md) | Business question, deliverables and acceptance |
| [Full-corpus guide](docs/FULL_CORPUS_GUIDE.md) | Inspect all contracts and prepare bounded execution batches |
| [Full-corpus protocol](docs/FULL_CORPUS_PROTOCOL.md) | Splits, duplicates, conflicts, context and coverage |
| [Evaluation protocol](docs/EVALUATION_PROTOCOL.md) | Sampling, metrics, rubric and interpretation |
| [Data provenance](docs/DATA_CARD.md) | CUAD attribution, licenses, selection and limitations |
| [Operator runbook](docs/RUNBOOK.md) | Execution, comparison, review and evidence release |
| [Claude Code / VS Code guide](docs/CLAUDE_CODE.md) | Subscription workflow, context separation and PowerShell commands |
| [AI Act readiness](docs/AI_ACT_READINESS.md) | Applicability, controls, evidence and gaps |
| [Risk register](docs/RISK_REGISTER.csv) | Material failure modes and proposed mitigation |
| [Delivery report template](templates/DELIVERY_REPORT.md) | Client-facing report structure |
| [Implementation roadmap](docs/ROADMAP.md) | Small, evidence-led completion stages |

Developed by [Dmytro Pogribnyy](https://dmytropogribnyy.github.io/) — PhD in Business Law,
Senior SDET / QA Automation Engineer, with a focus on Legal AI and LLM evaluation.
Related engineering project: [AI QA Factory](https://github.com/dmytropogribnyy/ai-qa-factory).

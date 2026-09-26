# Use the full contract corpus

Run from the repository root with Python 3.11+. The commands below work in a normal
VS Code terminal, including PowerShell. Preparation, inspection, freezing and export
are offline after the initial source download; they do not invoke a model.

## 1. Download and catalog every source contract

```powershell
python -m legal_eval fetch
python -m legal_eval prepare-corpus
```

`data/prepared/full-cuad/` contains:

| File | Purpose |
|---|---|
| `contract_index.csv` | Searchable list of 509 unique texts: title, hash, split, length |
| `contracts.jsonl` | Full contract texts, stored once, including long documents |
| `tasks.jsonl` | All 20,910 original questions, answer offsets, labels and exclusion flags |
| `catalog.json` | Source/file hashes, all 41 categories, label coverage and annotation conflicts |

The public [summary](../data/corpus_summary.json) and [contract index](../data/corpus_index.csv)
contain metadata, without full contract texts or answer passages. All raw/prepared
material stays local and Git-ignored. CUAD attribution and terms are in the [data card](DATA_CARD.md).
The initial `prepare` command remains available for the original ten-contract pilot.
Use a fresh `--out` directory for a new corpus version; existing catalogs are not overwritten.

## 2. Inspect a complete contract and its source annotations

Choose a hash from `contract_index.csv`, preferably a development contract:

```powershell
python -m legal_eval inspect-contract --contract-sha256 CONTRACT_SHA256 --out runs/inspection-001
```

Open `contract.txt`, `annotations.json` and `provenance.json` in the output directory.
They retain full text and original annotations, including both conflicting source
variants where applicable. Inspecting holdout answers exposes the holdout: record
this before any prompt tuning and do not call it a fresh unseen test afterwards.

## 3. Prepare a practical first batch

Start with 12 development tasks across three commercial-risk categories:

```powershell
python -m legal_eval corpus-batch --category "Cap On Liability" --category "Termination For Convenience" --category "Anti-Assignment" --limit 12 --out runs/legal-risk-dev-001
python -m legal_eval freeze --cases runs/legal-risk-dev-001/cases.jsonl --out runs/legal-risk-dev-001/freeze.json
python -m legal_eval export-claude --cases runs/legal-risk-dev-001/cases.jsonl --frozen runs/legal-risk-dev-001/freeze.json --out runs/legal-risk-dev-001/claude-input
```

To sample all categories, omit the `--category` options. `--offset 0 --limit 30`
selects the first page; the next page uses `--offset 30` and a new output directory.
Keep all filters fixed between pages. `batch.json` records eligible/selected counts,
IDs, hashes and the next offset. A single 30-task page cannot cover all 41 categories.
No labels or answer spans are sent to the model.

## 4. Run only after choosing the model and usage scope

Complete the [Claude Code preflight](CLAUDE_CODE.md), check subscription/extra-usage
settings and replace the model placeholder with your chosen full ID:

```powershell
python -m legal_eval run-claude --bundle runs/legal-risk-dev-001/claude-input --model YOUR_FULL_CLAUDE_MODEL_ID --max-invocations 12 --allow-subscription-usage --out runs/legal-risk-dev-001-output
python -m legal_eval score --cases runs/legal-risk-dev-001/cases.jsonl --frozen runs/legal-risk-dev-001/freeze.json --responses runs/legal-risk-dev-001-output/responses.jsonl --out runs/legal-risk-dev-001-report
```

The run command consumes model usage. The tool never automatically launches the
whole corpus. For the direct OpenAI adapter use the same `--cases` and `--frozen`
with `run-openai`, your explicit model, `--max-calls 12` and `--allow-paid`.
Keep model/prompt/settings constant for comparisons. Complete the report's human
review sheet to assess legal meaning; automated grounding alone is insufficient.

## 5. Long documents and holdout

The default 40,000-character cap covers 293 unique contracts. To allow **all 509**,
add `--max-context-characters 400000` to BOTH `corpus-batch` and `export-claude`
(or `run-openai` for that adapter). The longest source text has 338,211 characters.
Text is never truncated. The exported Claude bundle records and enforces the chosen
limit. Character limits do not guarantee fit within the selected model's token
window; check that window and output budget before running. Timeouts/errors remain
visible, and the Claude wrapper stops after the first failed task.

For confirmation, prepare a separate batch using `--split holdout`, freeze it and
pass `--split holdout` to both export and scoring. Never change the prompt based on
holdout answers and continue to label the same set unseen. The expanded corpus
preserves all ten pilot split assignments; exact duplicates cannot cross splits.

The [full-corpus protocol](FULL_CORPUS_PROTOCOL.md) explains deterministic selection,
deduplication, conflicting annotations, rare-category support and interpretation.
The corpus has been validated; real-model scores and owner legal reviews are pending.

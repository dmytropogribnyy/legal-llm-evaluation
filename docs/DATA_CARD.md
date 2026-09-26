# Data provenance and limitations

**Source:** [Contract Understanding Atticus Dataset (CUAD)](https://www.atticusprojectai.org/cuad/),
curated by The Atticus Project. Dataset publication: Hendrycks, Burns, Chen and Ball,
*CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review*, NeurIPS 2021.
[Paper](https://arxiv.org/abs/2103.06268).

The source contains 510 commercial contracts and annotations across 41 clause types. Contracts were
sourced from public SEC EDGAR filings. This pilot uses the publisher's existing annotations, not
new annotation work attributed to this repository's author.

The pinned dataset revision, URL, byte size and SHA-256 are in [source.json](../data/source.json).
The public [selection manifest](../data/selection_manifest.json) records source question IDs,
contract titles, context hashes, split assignment and reference-presence flags. Contract parties
named in source titles are **dataset subjects, not clients of this service**.

## Rights and storage

CUAD annotations are published under CC BY 4.0. Attribute the dataset and identify modifications.
The publisher separately makes no representation about licenses of the underlying contracts.
See the [publisher README](https://huggingface.co/datasets/theatticusproject/cuad/blob/main/CUAD_v1/CUAD%20v1%20ReadMe%20_%20Datasheet/CUAD_v1_README.txt)
and [legal notices](https://www.atticusprojectai.org/legal/).

Full contracts and derived reference text are fetched locally and excluded from git. This repository
publishes provenance, code, methods and aggregate preparation results. Before publishing excerpts or
model responses containing contract passages, review reuse rights and any sensitive source content.
Client data requires separate authorization, provider assessment and a private workspace.

## Known limitations

- SEC-filed, English-language commercial contracts are not representative of every jurisdiction,
  agreement type, negotiated practice or contract format.
- The 40,000-character limit favors shorter contracts; no claim about long-document retrieval.
- No OCR, scanned-image extraction, RAG retrieval benchmark or current-law correctness test.
- The source labels can be incomplete; local owner legal review is pending.
- Exact-text de-duplication does not exclude all related companies or near-duplicate templates.
- Public data may have been included in model training. The locally held-out split controls our
  prompt-tuning process, not provider training exposure.
- This task evaluates agreement text; EU AI Act governance mapping concerns a proposed European
  deployment context, not the law governing the sampled contracts.

Published preparation checks are reproducible with `python -m legal_eval fetch` and `prepare`.

## Full-corpus expansion — v0.3.0

The original pilot above remains unchanged. `prepare-corpus` now catalogs the complete
pinned source: 510 records, 509 exact unique texts and all 41 categories / 20,910
source tasks. Text is stored once per hash. Every source answer offset and presence
label is checked. The ADURO duplicate has two conflicting categories; original
annotations are retained, duplicates and conflicts excluded from automatic runs.
The resulting evaluation pool is 20,867 tasks.

The generated [summary](../data/corpus_summary.json) publishes per-category positive
and negative counts for the 404 development / 105 holdout contracts. Document Name
has no negative examples; Parties has no holdout negatives. Aggregate scores must
not imply balanced coverage. Full texts remain local, with unchanged source attribution
and redistribution limitations. See the [separate selection protocol](FULL_CORPUS_PROTOCOL.md).

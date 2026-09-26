# Working on this repository

- Preserve the distinction between independent service pilot, controlled evaluator fixtures,
  real provider responses, expert-reviewed results and externally commissioned work.
- Never invent clients, API outcomes, model scores, reviewer approvals, credentials or certification.
- Keep source contracts, provider outputs, client material and secrets out of tracked files by default.
- Preserve source attribution, pinned hashes, contract-level splits and response provenance.
- Do not tune on the holdout and still call the result a fresh confirmation.
- Any change to selection, prompt, rubric or metrics needs a new protocol/version and disclosed impact.
- EU AI Act mappings require intended-use and applicability reasoning. Do not treat all Legal AI
  as high-risk or equate passing checks with conformity.
- Run `python -m unittest discover -s tests -v` and the offline demo after evaluator changes.
- Paid provider calls require explicit scope, model choice and the runner's opt-in/caps.
- Public updates follow the owner's task authorization; preserve unfinished-work status accurately.

# Working on Legal LLM Evaluation in VS Code

Read `AGENTS.md`, `README.md` and `docs/CLAUDE_CODE.md` before changing or running this project.

- This is an independent service pilot. Live model acceptance and owner legal review are pending
  until actual run evidence and signed review records exist.
- Local preparation, tests, fixes and reference-free bundle export are normal development work.
- Run subscription inference only after the owner chooses an available full model ID and approves
  its bounded usage. Show the `run-claude` command for the owner's ordinary VS Code terminal.
- Do not launch the adapter from an active Claude Code Bash session or clear `CLAUDECODE` to force it.
- The evaluated model must receive only the exported question/contract and frozen instructions.
  Never answer benchmark questions using a coding session that has read the reference annotations.
- Do not manufacture provider receipts, CLI metadata, model scores or Dmytro's legal approvals.
- Never publish raw contracts, answers, authentication details or files from `runs/` by default.
- Do not interact with other projects or their running agents. This repository has its own scope.

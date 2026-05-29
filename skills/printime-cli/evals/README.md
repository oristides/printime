# Agent evals

Simulate whether an agent (with **only SKILL.md**) picks and **executes** the exact `printime` command from natural language.

Cases live in [../evals.json](../evals.json) (**20 cases** — English, Portuguese, Spanish).

Coverage: tasks, checklists (large lists + checked items), messages, notes, email, URL vs QR ambiguity, inline markdown, markdown files, `--print`, ASCII.

## Grading

- **Exact match only** — argv must match `expected` token-for-token (after shell parsing).
- **Max 4 command attempts** — harness runs each proposed command; wrong answers get a short follow-up in the **same agent session** (`cursor agent --resume`).
- Agent may read SKILL.md and run `printime --help` within the session before answering.
- **Score** = `1 / attempt_number` on first exact match; **0** with `attempts=4` if never correct.

## Run agent simulation

```bash
printime eval --simulate
printime eval --simulate -v          # verbose: expected command, each run, CLI output
printime eval --simulate --case task-comer-arroz
printime eval --simulate --dry-run   # score expected commands without calling agent
```

## Validate one command parses

```bash
printime eval --validate 'printime task --body "comer arroz hoy"'
```

## Score a transcript manually

```bash
printime eval --case task-comer-arroz --score $'printime checklist --items x
printime task --body "comer arroz hoy"'
```

## Golden reference check

```bash
printime eval
```

Checks every case `expected` command is valid and scores as attempt 1.

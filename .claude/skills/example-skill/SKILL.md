---
name: example-skill
description: Starter template showing the TriAgentLoop skill body standard. Use as a reference when authoring a new skill, or run scripts/new-skill.sh to scaffold one. Not a task skill — it performs no work itself.
---

# Example Skill

This is the reference skill that ships with every TriAgentLoop install. It
exists so the `skills/` directory is tracked by Git (and therefore seeded into
every fresh workspace), and so authors have a complete, copyable example of the
Skill Body Standard from `docs/skill-contract.md`.

Read this file when you want to see how a well-formed skill is structured, then
either copy it or run `scripts/new-skill.sh <slug>` to scaffold a new one.

## When to use

- You are learning the skill format and want a concrete, contract-compliant
  example to read or copy.
- You are about to author a new skill and want the canonical section layout.

## When not to use

- You need real work done (planning, review, debugging, QA). This skill is a
  template and performs no task. Pick or author a task skill instead.
- You want to add a new skill quickly — run `scripts/new-skill.sh <slug>`
  rather than hand-copying this file.

## Repo-native workflow steps

A task skill written from this template should drive the repo's
Planner / Builder / Reviewer protocol:

1. **Planner** frames the goal and acceptance criteria, then writes a `plan`
   record to `$TAL_HARNESS_ROOT/docs/agent-handoffs/<topic>.jsonl` for any
   multi-file or ambiguous work.
2. **Builder** branches with `git checkout -b agent/build/<topic>`, scopes
   changes to the assigned files, and runs the project's local validation
   commands.
3. **Reviewer** reviews the diff and appends a `review` record; an `approve`
   record (with `branch`) is checkpoint-ready.

Keep every step grounded in `AGENTS.md`, isolated Git branches/worktrees, and
the handoff log — never in external runtime hooks, daemons, or hidden state.

## Specialist prompt hints

When a step maps to a focused role, reference a prompt under
`agent/prompts/specialists/` rather than inventing one inline. Name the
specialist explicitly so the operator can paste the right prompt into the right
pane.

## Validation and evidence

- State the exact local validation commands a skill should run (discovered from
  the target project, e.g. `npm run typecheck`, `npm run build`, a test suite).
- Require evidence: command output, a smoke boot, or a manual repro — not just a
  claim that it works. A type check alone does not prove a filesystem-driven or
  runtime path is correct.

## Stop and escalation conditions

- Stop and ask the Planner if assigned files, acceptance criteria, or validation
  commands are missing (unless running in an explicit autopilot mode).
- Stop on a dirty tree, a failed fast-forward merge, or failing validation, and
  report instead of forcing the change through.
- Never bypass pre-commit hooks with `--no-verify`.

## Reporting

End with a compact handoff: append the appropriate record to the topic's
handoff log, then emit 3–5 bullets covering status, branch + log path, the next
agent and action, and any blockers.

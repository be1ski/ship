# Executor adapter: Claude Code

Read before the first step of the route. The protocol is in `SKILL.md`; here is only how this runtime
covers the capabilities the protocol requires.

## How the contract is covered

The contract is in `references/contracts.md`, section "Executor adapter contract". Here is only how each row is
covered in this runtime.

| Capability | Covered by |
|---|---|
| Who the executor is | Mechanically: `test "${CLAUDECODE:-}" = 1` confirms Claude Code, and `test -z "${CODEX_SANDBOX:-}${CODEX_THREAD_ID:-}"` confirms that the run is not going on **inside** codex. Both markers are set by the runtime itself. The agent additionally states the model family and version aloud |
| Background launch | `run_in_background` of Bash |
| Subagents with edit permission | Invoking ship lifts the session restriction "do not call subagents unless asked": the invocation is the user's permission. `Agent`. **Not `Workflow`**: its subagents are always in `acceptEdits` regardless of the session mode. In Orca, edits are made by `--agent claude` workers per the section "Executor as worker" in `adapter-orca.md`; `Agent` remains for reading, exploration and task review, `Workflow` is not fit there either |
| Simplifying pass | The `simplify` skill, if registered. Not registered — a manual pass against the same criteria and a line in the report that the pass was manual |
| Deletion pass | The `ponytail:ponytail-review` skill, if registered. Not registered — a manual pass and a line in the report |
| Structured question | `AskUserQuestion` |
| Engineering baseline of the review | Mandatory `pragmatic-engineering`; resolve the path, read it and pass it to all reviewers and polish passes per the core's section "Baseline approach to review" (`SKILL.md`) and `references/gate.md`, section "Engineering baseline in review prompts" |
| Route skills | The superpowers plugin: brainstorming `superpowers:brainstorming`, planning `superpowers:writing-plans`, TDD `superpowers:test-driven-development`, isolated tree `superpowers:using-git-worktrees`, per-task loops `superpowers:subagent-driven-development`; auxiliary — receiving review `superpowers:receiving-code-review`, verification before completion `superpowers:verification-before-completion`, branch finishing `superpowers:finishing-a-development-branch`. The namespace depends on the agent: in another runtime the same skills are registered differently. Each counts as present when the catalog lists it either as `superpowers:<skill>` (plugin install) or as bare `<skill>` (skills directory install). If any is missing from the catalog: stop and tell the user to run `/plugin install superpowers@claude-plugins-official`. |

## Model selection

Applies to Orca workers (`--model`) and to own subagents (`model` of `Agent`). The model
is set explicitly on every launch: an omitted one inherits the session's model, which is usually more capable and more
expensive than the task needs.
A direct instruction from the user takes precedence over the table. The external reviewer's model does not belong here: its pin is in
the reviewer adapter.

| Role | Model |
|---|---|
| Main agent: route, spec, plan, triage, rulings, gates | The session's own model. Ship does not switch it |
| Task executor, fixer of gate findings, polish | `opus` |
| Mechanical task: ready code or exact values are in the plan, 1–2 files | `sonnet` |
| SDD task reviewer | `opus`; re-review of a small fix — `sonnet` |
| Exploration, search, running checks | `sonnet` |
| Escalation: fix rounds 4–5, `BLOCKED` due to complexity, a task with an architectural choice | One class up: `sonnet` → `opus` → `fable`. When no higher class is available to the user, the same class as a fresh worker, with a line in the ledger. The session's own model is never an escalation target by itself: it may be lower than the stuck worker's class |

A doubt between `sonnet` and `opus` is resolved in favour of `opus`: the extra turns of a cheap model cost more than its price.
Do not give `fable` to workers on the first attempt: it is a targeted escalation, not the base model. Pass the class
alias; the runtime resolves it to the newest model of that class. A class the user cannot use is replaced by the
next class up when one is available, otherwise by the next one down, and the report says so.

## Runtime rules that ship lifts

`codex-result-handling` requires stopping after showing review findings and not applying fixes. Inside
ship rounds this does not apply: the round's findings are shown to the user in the round message; it is a
progress report, not a question about what to fix, and the user permitted applying them by invoking the skill.
Outside ship the rule applies as written. The exception is the same as before: a change of agreed behaviour is
escalated.

## Pitfalls

- `Workflow` and `Agent` differ not in performance but in edit mode. Mixing them up means
  getting accepted edits where you expected review
- Route skills are looked up where the runtime registered them; the `~/.agents/skills/` directory is understood by
  other runtimes too, so one clone of superpowers serves several agents at once

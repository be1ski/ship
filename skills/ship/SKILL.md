---
name: ship
description: Use when work needs independent cross-vendor review through completion in Claude Code or Codex — a spec, a plan, an implementation, or a quick script. Triggers on "/ship", "$ship", "$ship:ship", "прогони через ревью", "пиши спеку, план и реализуй", "доведи до чистого ревью", "до консенсуса с ревьюером", "review until clean", "full ride".
---

# ship — take work to a clean external review

## Orca

If the `ORCA_TERMINAL_HANDLE` environment variable is set and `references/adapter-orca.md` exists
next to this skill, read it now, before preflight, and follow it. It replaces how the reviewer is
called, how the isolated tree is created and who edits code (Orca workers instead of the
executor's own subagents). Either condition false: skip this section silently.

## Shared install and role selection

Relative paths below are relative to the directory of the loaded `SKILL.md`.

The executor is the current main agent, not an arbitrary CLI found in PATH:

| Where ship was invoked | Executor adapter | Reviewer adapter |
|---|---|---|
| Claude Code / Anthropic Claude | `references/adapter-executor-claude-code.md` | `references/adapter-reviewer-codex.md` |
| Codex / OpenAI GPT | `references/adapter-executor-codex.md` | `references/adapter-reviewer-claude-code.md` |

Read the selected pair before the first step; the routes and the protocol below are shared by both pairings.
A missing CLI or missing authorization of the external reviewer is an unfinished gate, not a reason to replace
it with a subagent of the executor. The reviewer only reads and returns findings; all fixes are made by the
executor. The review prompt does not run ship recursively.

The user's instructions, including the repository's own (`CLAUDE.md`, `AGENTS.md`), and the constraints of the current runtime take precedence over this skill and its
dependencies. Decisions and permissions already agreed are kept; do not request them again because of a
transition between stages or agents.

A gate is **not "review until it is clean"**. A gate is one list of findings, driven to closure
by the same reviewer that produced it. The list is compiled once and from then on only shrinks.

The same gate applies to every artifact: to the spec, to the plan, to the code and to the code after
polish.

**Announce at the start**, in the user's language: "Using ship: <route>, reviewer <adapter>". If the runtime has a
todo tool, create one todo per gate of the route.

## Baseline approach to review

**REQUIRED SUB-SKILL: `pragmatic-engineering`.** Before the first step of the route, read
`../pragmatic-engineering/SKILL.md` relative to this skill in full: it is the copy that ships with this version.
If it is not there, find the skill in the current session's skill catalog as `ship:pragmatic-engineering` or
`pragmatic-engineering` and read its `SKILL.md` in full. If neither can be read, name the missing dependency and
stop before the first step of the route.

## Roles and runtime

There are two roles, and they are fundamentally different agents:

- **executor** — the agent in which ship was invoked: writes the spec, the plan, the code and the polish, runs
  the triage of findings;
- **reviewer** — an external agent that the executor calls through the mechanism declared by the adapter, and
  that produces findings.

**The invariant the whole skill rests on: the reviewer is not the executor.** A different model, a different
vendor. An agent reviewing itself or its own model is blind exactly where the generator made the mistake.
The cross-vendor arrangement is load-bearing; do not dilute it — neither with "a second lens for confidence"
nor by substituting a reviewer from the same model family.

The invariant is checked in both directions: name your own family and vendor in the report next to the
reviewer's. If you do not know who you are yourself, the gate is blocked just as with an unknown reviewer.

Which agent takes which role is not fixed. The reviewer is plugged in through an **adapter**: a file in
`references/` that describes how to call this reviewer and how to read its output.

Why the loop diverged without these rules and which measurements they rest on —
`references/rationale.md`.

## Route

| What comes in | Route |
|---|---|
| A feature is requested, or the design was agreed in the conversation after brainstorming | spec → 🚪 → plan → 🚪 → code → 🚪 → polish → 🚪delta |
| **Only** a spec or **only** a plan is requested, without implementation | artifact → 🚪 → stop |
| One-off work or already written code: a script, a single-file fix, a config edit | code → 🚪 → polish → 🚪delta |
| The spec or the plan already exist as files | enter at the first unclosed gate |

The sign of one-off work: a spec would take longer than the work itself. If the route is not obvious —
**one** question to the user. After that, do not ask about the route; this ban does not apply to escalations
and stalls.

A gate over an already existing file counts as closed only if the clean run was over its **current**
content. No proof — the gate is open.

## Gate

**Round 1 — discovery.** A fresh discovery call to the reviewer over the whole scope, with the "exhaustive
sweep" block. It returns a list. The list is frozen into the ledger: it is the gate's contract, and **this is the
only round allowed to open new topics on unchanged code**. Recording the run's thread id is mandatory:
without it verification will not happen.

**Rounds 2+ — verification in the same thread.** A verification call on the same id with a response to every
row of the list. The reviewer keeps its own findings in context, re-reads the current state or
receives an updated delta from the saved base per the adapter's rules, and answers one
line per finding: RESOLVED / NOT RESOLVED / REGRESSED. It may raise a new finding **only**
if it is a defect introduced by a response, that is, one that lives in a line changed after its review.

**Exit condition** — one of two: discovery returned zero findings, or verification returned as its last
line exactly `VERDICT: ALL RESOLVED`. For code and config gates, a run of the checks on the
same state is added to this (the "Checks" section, `references/checks.md`); the spec and the plan have no executable checks.

**A run that did not happen is not a round, and it does not close the gate.** An error, a timeout, empty
output, a killed broker — rerun, up to two times, then escalate. Do not treat the exit code as a signal until
the adapter has proven otherwise: with many reviewers the exit code is the same with findings and without them.
Parse only the content of the output.

**A clean verdict over an empty scope is not a clean gate.** Before counting zero findings,
make sure the reviewed scope is not empty. Git gate: `git diff --stat <gate base> -- <paths>` is not empty, and
untracked files that are part of the work have been added at least via `git add -N`. A wrong base, an already
committed tree or someone else's worktree give "clean" on zero content. A file gate (spec,
plan, file as is) has no diff at all: check that every path named in the prompt
exists and is non-empty — and if the content went into the prompt inline, that the non-empty content of the
right file was sent. A snapshot delta is checked by a non-empty diff, including deletion: the absence of the
current file does not by itself make such a scope empty. Confirm reading and scope coverage in the way of the
selected adapter, not by the presence of an arbitrary text marker.

**After a context compaction or a break**, before continuing: re-read this file, the selected
executor and reviewer adapters, `references/ledger.md`, the route registry `gates.md`, the ledger
and saved state of every gate the registry lists as open (`ledger.md`, `thread-id`, `base-sha` or
snapshots), and the reference file of the current phase from the index below.

<!-- phase-index:start -->
## Phase index

Read the listed file in full at the start of the phase, and again after a context compaction.

| Before | Read |
|---|---|
| The first step of any route: preflight, route details, spec and plan handling | `references/route.md`, `references/ledger.md`, `references/checks.md` |
| Writing or checking an adapter | `references/contracts.md` |
| Opening any gate, calling the reviewer | `references/gate.md`, `references/ledger.md`, `references/prompts.md` |
| Handling a round's findings, parallel fixes | `references/triage.md` |
| Handing a state to a gate, closing a code or config gate | `references/checks.md` |
| Polish after the code gate | `references/polish.md` |
| Every round message and the final report | `references/report.md` |
<!-- phase-index:end -->

## Done

The work is finished when all of the following hold at once:

- the code gate is closed;
- the polish delta from the base of the clean code gate is closed by its own gate; if polish
  did not change a single line — the gate is not run, the absence of a delta is recorded in the registry and the report;
- if the change touched money, access, data deletion or irreversible operations — after these
  stages a fresh confirmation gate over the whole change is closed; it may be the last gate;
- every required gate from the registry is closed by a run verdict — zero discovery findings or
  `VERDICT: ALL RESOLVED` — over a non-empty scope, and there were no new edits after the last gate;
- the checks were run in this same message, with output;
- there are no open lines in any gate ledger of the route, and an explicit outcome is kept for every
  carried-over deferred/parked SDD entry; the final report lists the findings of each gate with their outcome
  (the "Report" section, `references/report.md`), and everything noticed but not done is named in a separate line.

A route that ended at the spec or the plan has no code and polish criteria: it
is finished when all the gates it provides for are closed according to the registry, and the report says that
the route ended there and why.

Merge, PR and branch deletion are a separate decision: the branch-finishing skill.

## Red flags

| Thought | What it really is |
|---|---|
| "I'll run a fresh sweep once more, maybe it comes back clean" | After discovery a fresh sweep is not the same gate but a new one. Verification goes into the thread |
| "It is asking to tighten the check again — I'll add it" | Your own fix: check whether the layer is needed, delete what is unnecessary or fix what is needed per its contract |
| "The findings are minor, a repeat round is not needed" | The gate is closed by a verdict, not by your assessment of the findings |
| "I fixed everything, so it is clean" | Until the list is closed by a verdict, the state is unknown |
| "Polish didn't break anything" | Polish is a code change. It has its own gate over the delta |
| "The reviewer is nitpicking, I'll skip an item" | Skipping is not allowed. Either fix it or reject it with proof in the ledger |
| "Easier to apply it than to argue" | Blindly applying a wrong finding breaks the code. Reject it |
| "It asks to support one more input — I'll add it" | That is scope expansion disguised as a fix. Escalate |
| "The task is small, the gate is overkill" | That is what the one-off route is for. The gate stays |
| "I'll add docstrings, it will look more proper" | A retelling docstring is the same junk. The name does the explaining |
| "While I'm at it I'll tidy up around it / add a guard" | Polish does not expand the scope. A line in the report |
| "I'll ask the user what to do with the findings" | Triage is your job. Only scope, taste and stalls go up |
| "The reviewer found six, all valid, off to fix them" | The user has not seen any of the six. First the round message, then the edits |
| "The review crashed, but before that it was clean" | A run that did not happen is not a round. Rerun |
| "Exit code 0, so it passed" | 0 comes with findings too. Parse the output |
| "There is no reviewer, I'll review it myself" | Reviewer = not the executor. No adapter — say so and stop |
| "It's late already, I'll finish it tomorrow" | An unclosed gate is unfinished work. Report it as such |

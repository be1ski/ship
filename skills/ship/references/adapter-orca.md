# Orca adapter: the reviewer and executors as workers

An optional file. Read from the "Orca" section in `SKILL.md` when the session runs in an Orca terminal.
It changes three things: **how the external reviewer is called, where the isolated tree is created and who edits
code**. Routes, gates, the ledger, triage, the round message format and the "reviewer ≠ executor" invariant
stay as in `SKILL.md` and the reviewer and executor adapters; read them as usual.

Load the `orchestration` skill: it provides this session's CLI and the `skills get orchestration` guide.
It is installed by Orca, not by this plugin. If it is not in the catalog, name it as a missing prerequisite and stop.
Below, `ORCA` is that CLI. Call the reviewer per the table in **all** gates: spec, plan, code, polish,
confirmation pass.

**In Orca only workers edit code**: implementation, the per-task executors and fixers of
subagent-driven-development, fixing code-gate findings, polish — per the section "Executor as
worker". The main agent does not call its own subagents for edits (`Agent`, `spawn_agent`) and does not
edit the implementation tree itself. The main agent keeps: the route, the spec and the plan with their edits,
triage, rulings, the ledgers and the gate registry, round messages, running the checks, commits on behalf of
parallel fixers. SDD task reviewers remain its subagents: they only read.

## Isolated tree

The route's "isolated tree" step is covered by Orca, not by `EnterWorktree` and not by `git worktree add`:
Orca does not show trees in `.claude/worktrees/` in the panel; workers in them are alive but invisible.
The order is the same as before: the spec and the plan are committed, the plan SHA is in the `base-sha` of the future code gate.

```bash
ORCA worktree create --name <topic> --base-branch "$(cat "$SHIP_GATE/base-sha")" --json \
  > "$SHIP_ROOT/worktree.json"          # run from the repository's main checkout
```

- `--base-branch` is the literal plan SHA. Without it Orca takes the repository's default base, and
  the plan commit may not be in the tree.
- From `result.worktree` record in `gates.md` the `path` and the tree selector `id:<id>` (an `id` of the form
  `<repoId>::<path>`). Verify: `git -C <path> rev-parse HEAD` equals `base-sha`, the tree is in
  `ORCA worktree list`. If not — stop, do not change the code gate's base.
- From the isolated-tree skill, step 0 stays (if the session is already in a linked tree, do not create a second
  one), as do the steps for installing dependencies and the clean baseline run, now in the new tree.
- On the full route, when the session is already in a linked tree: work in it — the spec and the plan are written and committed there —
  and record in `gates.md` the path and the selector `path:<absolute path>`. If the tree is not in
  `ORCA worktree list`, tell the user once that the workers are not visible in the panel.
- **Tree selector** — the `--worktree` value for the tree's workers: `id:<id>` for a tree from
  `worktree create`, `path:<absolute path>` for an existing one that was taken over.
- **The route's own tree** — the tree from this section that the route created or took over as its own.
  Committing the task paths depends only on this. Having created or taken it, before the first dispatch record in
  `gates.md` whether `git -C <path> status --porcelain -- . ':!.ship' ':!.superpowers'` is empty: the rollback
  on stop depends on it. A one-off route in the current checkout and files outside git have no own
  tree.
- `--worktree current` of `worker-start` is the workspace of the main agent's terminal: the main
  checkout, or the linked tree the session itself runs in. All workers of a one-off route, executors
  and reviewers, go with it. The workers of the route's own tree always get `--worktree "<tree selector>"`.
- The main agent does not move into the tree: it reads and runs checks via absolute paths and
  `git -C <path>`, and runs SDD scripts as `cd <path> && bash …` in a single command.
- Delete the tree (`ORCA worktree rm`) only together with the merge decision, as in the core.

## Replacing the reviewer call

| Reviewer adapter step | In Orca |
|---|---|
| Who the reviewer is | Claude executor → `--agent codex`. Codex executor → `--agent claude`. The same vendor as the executor — the gate is blocked |
| Model and effort pin | The pair is chosen per the preparation section of the reviewer adapter ("Preparation" or "Preparation and pin") and passed in `--model` and `--effort`. Write `model` and `effort` from the `worker-start` receipt to the ledger |
| Where to run | Spec and plan — `--worktree current`. The code and polish gates and the confirmation pass — where the code lives, because the reviewer reads `git diff` there: `--worktree "<tree selector>"` on the full route, `--worktree current` on a one-off route |
| Discovery | `ORCA orchestration worker-start --spec-file "$R-prompt.md" --task-title "ship <gate> round NN" --worktree <where to run> --agent <agent> --model <id> --effort <level> --json > "$R-receipt.json"` |
| Tab title | Right after the start: `ORCA terminal rename --terminal <terminal from the receipt> --title "ship review: <what is reviewed> · <gate> rNN"`. Without it the tab is called `worker-task_<id>`. A rename error does not break the round |
| Thread | Save the `dispatchId` from the receipt to `$SHIP_GATE/thread-id`. Every follow-up returns a new `dispatchId` — overwrite with it |
| Verification in the same thread | `ORCA orchestration send --to dispatch:$(cat "$SHIP_GATE/thread-id") --subject "ship verify round NN" --body "$(cat "$R-prompt.md")"`. The worker continues the same chat and remembers its findings |
| Waiting | After `worker-start` or `send` **end the turn**: Orca wakes you with a `worker_done` message. This is waiting for the reviewer, not stopping the route — after it continue from the same step. Do not poll and do not write watch scripts |
| Round response | Save the `worker_done` message body to `$R-review.txt` and `last-review.txt` — the `body` field from `ORCA orchestration check --json`, not the printed `check` output, which indents it and appends `payload:` and `To give this worker more work:` lines. The last-line `VERDICT` contract applies to the body. No `VERDICT` line or the text is cut off — read the rest with `ORCA orchestration worker-read --dispatch <id> --source transcript` |
| Prompt mode | Always controlled text, including for a diff: a framework from `prompts.md` with the "What you opened" block (`REVIEWED`, `CONTEXT`) and the `VERDICT` line last. Native `codex exec review` is not used. The reviewer gets the diff the way its adapter declared: Codex runs `git diff <base-sha>` itself; Claude only reads files, so the executor attaches a freshly computed diff to the prompt on discovery and on every verify |
| Read confirmation | The `REVIEWED` and `CONTEXT` lists in the response. There is no `events.jsonl` in this mode |

The frameworks in `prompts.md` stay as they are. In every prompt, discovery and verification, add directly
after the "Engineering baseline" block:

```text
You are a dispatched Orca worker acting only as a reviewer. Put the complete review text, ending
with the VERDICT line, into the worker_done body. Do not create, edit or delete any file.
```

## Executor as worker

**The executor worker's vendor = the main agent's vendor and ≠ the reviewer's vendor.** Otherwise the reviewer
checks its own model. Claude main agent → executors only `--agent claude`, Codex →
only `--agent codex`. If the user named an executor from the reviewer's vendor — say so and
stop; do not substitute silently. The model is set explicitly for each worker via `--model`, per the section
"Model selection" of the executor adapter: invoking ship is the user naming the model in the sense of the
`orchestration` guide, which otherwise adds `--model` only on the user's word. Write `agent` and `model` from the receipt to the SDD ledger.

`$W` is the SDD plan workspace in the tree; for a one-off route — the code-gate scratch. The fixer of a gate
and the polisher write their report files there too.

| SDD or ship step | In Orca |
|---|---|
| Dispatch of the task executor | `ORCA orchestration worker-start --spec-file "$W/task-N-dispatch.md" --task-title "ship impl: task N" --worktree "<tree selector>" --agent <agent> --model <id> --keep-open --json > "$W/task-N-receipt.json"` |
| Tab title | `ORCA terminal rename --terminal <terminal from the receipt> --title "ship impl: <feature> · task N"`. A rename error does not break the task |
| Assignment | The executor template from SDD plus the "Orca executor worker" block from the section below, as a file. The brief and the report file — per the SDD rules; the dispatch also carries the plan's Global Constraints, which the SDD brief script leaves out, and tells the worker to load the TDD skill named in the executor adapter. A one-off route has no SDD task: the assignment is a brief file with the task, the checks and the report path plus the block's variant without git, and the template's commit step does not apply |
| Executor id | The `dispatchId` from the receipt — into the SDD progress ledger. Every `send` returns a new `dispatchId`; keep the latest |
| Waiting | After `worker-start` or `send` **end the turn**: Orca wakes you on `worker_done`. Do not poll. If "Run `ORCA orchestration check --run <id>`" arrives — run that command |
| Executor's question | Arrives as a `question` message: `ORCA orchestration reply --id <message_id> --body "<answer>"` and end the turn again |
| Report | The `worker_done` body is the short SDD status contract; the full report is the `task-N-report.md` file in `$W`. Verify the commits: `git -C <path> log <BASE>..HEAD` |
| Fix rounds 1–3, "resume implementer" | `ORCA orchestration send --to dispatch:<latest dispatchId> --subject "ship fix task N round K" --body "$(cat "$W/task-N-fix-K.md")" --json`. The same chat, the same tab |
| Fix rounds 4–5 | A new `worker-start` on a model one step above the stuck one, per "Model selection". Nothing higher in the same vendor — the same model as a fresh worker, a line in the ledger. Do not wake the stuck one again |
| Fixing gate findings | One fixer worker per gate: the first round — `worker-start` with the title `ship fix: <gate>`, the following rounds of the same gate — `send` to its dispatch. Findings and triage decisions — as a file, one line per finding |
| Polish | One fresh worker: the simplifying pass, the deletion pass, comment cleanup per the core's "Comments" section (`references/polish.md`), checks. The assignment includes the block for `simplify` / `ponytail-review` from the section "Block 'Engineering baseline'" in `prompts.md`, the "Orca executor worker" block from the section below with its exception for agents of the pass itself, and the core's rule "Polish adds nothing" (`references/polish.md`). If the pass is not registered for the worker, it polishes by hand against the same criteria and writes so in the report. From the deletion pass it applies only a deletion that removes nothing the spec, the plan or a check requires; every other candidate is disputed: it lists them in the report without applying, the main agent decides and sends a follow-up `send` |
| The worker did not start | Section "If the worker did not start" |

Polish is done by a worker, not by the main agent: the diff and the output of the passes do not settle in the
context that runs the gates.

## Block "Orca executor worker"

Goes into **every** assignment to a
writing worker: the task executor, the fixer, the polisher. In a follow-up via `send`, repeat it in one
line: `The earlier constraints still apply: no subagents, helpers, other workers or independent reviews.`

```text
You are a dispatched Orca worker acting as the implementer of this one task.
Work only inside <absolute tree path>: edit and commit there and nowhere else. Stay on its
current branch; do not push, merge, rebase or switch branches. Commit only the paths of this task.
Do all of the work yourself. Do not start subagents, helpers or other Orca workers, and do not
start or request an independent review, whatever your worker preamble offers: review is the
coordinator's job after you report. Self-review of your own diff before reporting stays required.
If the brief is unclear or you are blocked, ask the coordinator with `ask` and end your turn
instead of guessing.

Write the full report to <report file>. Put only this short contract into the worker_done body:
Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
Commits: <short SHA + subject>
Tests: <one line>
Concerns: <or none>
Report: <report file path>
```

The contract lines from `<short SHA + subject>` onward are text for the worker; do not substitute them, except
`<report file path>`, which is the same path as `<report file>` above.

The block as is, with the commit and the branch lines, is only for a worker in the route's own tree
(section "Isolated tree"). In all other cases — a one-off route in the
current checkout, files outside git, a parallel fixer — use the variant without git: replace the sentence
`edit and commit there and nowhere else` with
`edit only <its paths>; do not run git add or git commit`, remove
`Stay on its current branch; do not push, merge, rebase or switch branches. Commit only the paths of this task.`,
and replace the `Commits:` line with `Changed: <paths>`.

For the polisher, and only for it, add one sentence after the block:

```text
The only exception: agents that the assigned simplify pass itself launches are part of that pass.
```

## One writing worker per tree

Workers of one tree share the working files and the git index.

- **One** writing worker works in a tree at a time. The next `worker-start` or `send` to an
  executor — only after the previous one's `worker_done`.
- Parallel fixers are allowed only for findings in non-overlapping files and only without git:
  each one's assignment has its paths and the line "do not run git add or git commit". After all the
  `worker_done`, the main agent commits itself, by each fixer's paths — only in the route's own
  tree; nobody commits anywhere else.
- During a review round there are no writing workers in the tree: wait for all `worker_done` before taking the
  `-before` fingerprint and do not `send` to executors until `-after`. The fingerprint from the next section
  applies only to the reviewer: with a live writing worker it proves nothing.

## Stopping at the user's request

Stop **every** writing worker of this tree, not only the named one: with parallel
fixers there are several. Do not save or roll back anything until all of them are stopped.

```bash
ORCA orchestration worker-stop --dispatch <latest dispatchId> --json > "$W/stop-<id>.json"
```

The stop is confirmed only if the response has `state: stopped`, `processAction:
closed_agent_terminal` and `close.ptyKilled: true`. Exit code 1 or `stop_unknown` — not confirmed: `ORCA orchestration
worker-show --dispatch <id>`. If even one is not confirmed — do not touch the tree, tell the user.

All confirmed — save the unfinished work. Rolling back the whole tree is allowed only if it is the route's own
tree (section "Isolated tree") and `gates.md` records that before the first dispatch
it was clean. Then save everything except the scratch and return the tree to the last commit.

```bash
cd <path> && git add -N -- . ':!.ship' ':!.superpowers' \
  && git diff --binary HEAD -- . ':!.ship' ':!.superpowers' > "$W/stopped-<id>.patch" \
  && git reset -q --hard HEAD && git clean -fdq -e .ship -e .superpowers
```

`git add -N` is needed so that new files get into the patch; the pathspec keeps the scratch out of it. Commits
the worker managed to make remain.

In all other cases do not roll back or clean: save only the worker's paths and tell the
user which paths were left unfinished.

```bash
# git: changes to the task paths and its new files; exit code 1 from `git diff --no-index` is normal
cd <path> && { git diff --binary HEAD -- <task paths>
  git ls-files -z --others --exclude-standard -- <task paths> \
    | xargs -0 -r -n1 git diff --no-index --binary /dev/null; } > "$W/stopped-<id>.patch"
# outside git: copies of the files it touched, with relative paths
cd <directory> && rsync -R <task files> "$W/stopped-<id>/"
```

Into the ledger: `Stopped by user: dispatch <id>, patch <path>, tree at <SHA>`; outside git, instead of the patch —
the directory of copies, and `tree at` is not written. Do not wake a stopped worker with `send`: `send` reopens
a closed one. Continuation — with a new worker and only on the user's word.

## What Orca does not provide — cover it yourself

**Read-only is not guaranteed.** The worker's mode comes from Orca's setting for new tabs; for Codex
this may be full access without confirmations. So before `worker-start`/`send` and after
`worker_done` take a fingerprint and compare:

```bash
# git: HEAD, index state and contents, all differences from HEAD and the contents of untracked files, except scratch
{ git rev-parse HEAD; git status --porcelain -- . ':!.ship' ':!.superpowers'; git diff HEAD
  git diff --cached --binary -- . ':!.ship' ':!.superpowers'   # a re-staged file keeps the same status line and the same diff HEAD
  git ls-files -z --others --exclude-standard -- . ':!.ship' ':!.superpowers' | xargs -0 shasum
} 2>&1 | shasum > "$R-tree-before"   # after worker_done the same into -after
# outside git: content and presence of every scope file
shasum <scope files> 2>&1 | shasum > "$R-tree-before"
cmp "$R-tree-before" "$R-tree-after" || echo "REVIEWER TOUCHED THE TREE"
```

In the implementation tree run the commands from inside it (`cd <path> && …`). If the fingerprints differ — the round
does not count: show the user `git status`, do not roll anything back yourself. There must be no writing workers
in the tree at that time (section "One writing worker per tree").

**The Codex tier cannot be set by a flag.** Before the first round with `--agent codex`:

```bash
grep -n '^service_tier' ~/.codex/config.toml
```

If the value is not `default` — tell the user once that the review will run on this tier and the limit
is used up faster; do not change the config.

## If the worker did not start

`worker-start` returned an error or `outcome_unknown` — do not restart it. The error does not prove
that the review did not start: a failed start may own a live worker. Read `failedStage` in the
receipt and act per `ORCA skills get orchestration --reference
references/recovery-and-cleanup.md`. The gate is run with the reviewer adapter's standard command (same vendor, the invariant
intact) only when it is proven that the worker will no longer perform this review: the agent was not
launched, or `worker-stop` returned a confirmed stop. Write about this in the round message.
No proof — the gate is blocked, tell the user. If the worker went silent or an
`escalation` arrived — act per the `orchestration` guide, and do not count the round as clean.

For an executor worker the proof is the same. Only after it does the mechanism from the executor
adapter (its own subagent with edit permission) take over the task, and the report says so. No proof —
the task waits: a second writer in the same tree is worse than idle time.

A `send` that reopens a settled reviewer can fail the same way (seen: `failedStage` `agent_readiness`,
`lastError` "Agent startup blocked: agent-update-prompt" — the Codex CLI waiting on its update prompt).
That is a verification round that did not happen, not a new gate: keep `thread-id` at the last dispatch
that answered, show the user the `lastError`, and repeat the same `send` after they clear it.

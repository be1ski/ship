# Why ship's rules are the way they are

Read when a rule is disputed. Not needed even once while running a gate.

## Why the loop diverged

Measured on a live run (`.ship/ledger.md`): **39 findings over 8 rounds**, 4–6 per round,
the rate does not drop, almost no repeats. But **26 of the 39 lie in code that ship itself added in
previous rounds**: thirteen in a shape check that grew out of a round 1 finding, another thirteen
in a validator lock that grew out of round 2 findings. Round 9 gave 3 out of 3 in round 8 code.

This is not review, it is a ratchet: the reviewer asks to tighten a check → the check is new code → the next
fresh sweep finds gaps **in it**. The diff grew to 1545 insertions on a small script. Both times
the loop broke free, it did so through **deletion**: a removed subprocess boundary (−148 lines of
the shape check) and a lock shrunk from 241 lines to 167.

The rounds were not produced by the reviewer forgetting — they were produced by three things:

1. **Every round was a first round.** A fresh review with the "exhaustive sweep" block opens the whole
   surface again, and after every fix the surface is larger. A manual loop in one thread converges
   in 3–5 rounds precisely because round 2 asks "did you fix what I asked for?", not "what else
   will you find?".
2. **A fix added code by default.** A "tighten the check" finding does not look like scope
   expansion, so it passes triage and lands as a new layer — new surface for round N+1.
3. **A cold start was paid every round.** 32–52 tool calls to re-open the repo;
   a round took 7–14 minutes. Measured on verification in the thread: the same question in a working copy the reviewer
   had already read — **25 seconds** against 125 for a fresh round on the same code.

## What not to do

- **Do not run verification as a fresh review.** A fresh run does not remember what it asked for, and accepts
  a fix that changed the contract. Measured on the same code: the fresh round returned "no material
  correctness issues", while verification in the same thread caught a `REGRESSED` — the fix had quietly replaced
  "zero" with `None`. A fresh reviewer is stricter about the code, the own one is stricter about the fix; verification needs the own one.
- **Resurrect the thread by id, not "the last one".** A "continue the last thread" flag without addressing picks
  up the last thread in the working tree, so any unrelated task of the same reviewer in the same repo
  takes the gate into someone else's context. And resurrection is only for a narrow question: a reviewer kept
  in the conversation and asked to search anew falls apart — it produces more findings and is worse at telling the real ones apart.
- **Do not raise effort when the loop stalls.** Higher reasoning casts a wider net and catches
  less certain findings — with "zero findings" as the exit, that is exactly the mechanism by which the loop
  diverges.
- **Do not change the reviewer in the middle of a gate.** The list belongs to whoever produced it; another adapter is
  a new discovery and a new gate.
- Runtime rules of the kind "showed review findings, stop, do not apply fixes" do not apply inside ship
  rounds: the round message shows the findings as a progress report, not as a question about what to
  fix, and the user permitted applying them by invoking the skill. Outside ship the rule applies as
  written. Which such rules exist in your runtime is stated in the executor adapter.
- **The reviewer's copy of superpowers may lag behind yours.** If it quotes superpowers — it is not making things up,
  it is reading its own.
- The remaining pitfalls of a specific reviewer are in its adapter. Versions drift: if a command from the adapter
  behaved differently, check `--help` before working around it.

## Why in Orca workers write and Orca creates the tree

The main agent's subagents are not visible in Orca: the user can neither look at the executor
nor stop it. A worker is a tab in the panel with an addressable thread (`dispatchId`); SDD's "resume
implementer" maps onto `send` one to one.

A tree created via `EnterWorktree` lands in `.claude/worktrees/`, and Orca does not show it. Measured
2026-11-13 on 1.4.255: `worktree list` does not return such a tree with either `hide` or
`--external-worktree-visibility show`, and `--worktree current` of `worker-start` from it goes to the
main checkout. A tree from `worktree create` is visible right away and becomes a child of the coordinator's workspace.

Model tiers: the coordinator holds the long horizon and the ambiguous decisions (spec, plan, triage)
and runs on the session's model; execution from a ready plan is standard work, the base model is
enough for it, and a cheap one for mechanical work. A strong model for workers is an escalation, when the base one got stuck.

## Why the adapter sets the read confirmation

The requirement "the baseline entry in `CONTEXT`, otherwise the run did not happen" cannot be met in Codex's native diff-review:
`exec review` responds in its own format. Measured on past scratches: of 24 discoveries
with the "What you opened" block in the prompt, the lists reached the output in one. So the text marker
is mandatory only where the prompt sets the response format, and in native mode the output of the reviewer's
commands is checked. This does not change the baseline being mandatory.

Smoke 2026-11-10, codex-cli 0.167.0, a larger model than the default one at `max`, read-only, a toy diff in one
file, the prompt assembled from the diff mode framework, 92 s. In `--json` every command has `status`,
`exit_code` and `aggregated_output`; the whole baseline and `git diff <base SHA>` are in the output of
completed commands. The child review's rollout contains the prompt verbatim and the same outputs; the
parent one has no command outputs. Response: an explanation, a decision line on the known item
(`NOT A DEFECT`) and a finding as a `- [P2]` bullet; no `REVIEWED`/`CONTEXT` lists. The check from the
adapter passes on these events and fails on corrupted variants: an extra baseline line,
a failed command, a non-zero `exit_code`, a path without output, no diff, a diff missing one changed
line, a lone diff header. The first version of the check looked only for the diff header and let the last
variant through; now every line is compared.

The Claude reviewer: discovery and two verifications on 2026-11-10 on 2.1.321 are described below, in "What was checked for the Claude reviewer".

What these runs do not show: whether the baseline changes the number of findings and the share of false ones; how the new
criteria for code and config and the known-items block behave on real gates; the full-text
baseline fallback in native mode and the fallback discovery as controlled text on Codex were not run live.
This is one toy diff and one file gate, not a rerun of the archive.

## Why the check uses the environment and not self-report

The agent's self-report about its own model does not close the invariant: it is not verifiable and breaks exactly
where it matters. Environment markers are set by the runtime, and they survive everything, including the agent's
mistake in identifying itself. Measured: inside a codex run `CODEX_SANDBOX`, `CODEX_THREAD_ID` and
`CODEX_CI` are visible; in Claude Code `CLAUDECODE=1` is visible.

Hence a hard consequence too: **a ship run inside codex with a codex reviewer is caught mechanically** and
blocked, instead of relying on the agent to name itself honestly.

## How checks showed green on broken input

Measured: five checks in a row showed green on input that was known to be broken. The forms in which this
happened:

- a Markdown-escaped `\|` inside a table: ripgrep reads it literally, the regex never
  matches;
- an `except` that swallows parsing: `shlex.split` failed with `ValueError` on a line containing a regex, and
  that line silently dropped out of the check;
- splitting a line on a character that has a different meaning in it: `|` in an `rg` regex is alternation, not
  a pipe, and the line was cut down to nonsense;
- assignment inside a pipe: `fail=1` in `while read` goes into a subshell and is lost. This is about bash and
  sh: in zsh the last element of a pipe runs in the current shell, and there the assignment survives;
- an anchor on a phrase that is not in the text: `rg -q` searched for "only Claude Code", while the text says
  "only to Claude Code".

## What was checked for the Claude reviewer

2026-11-10, Claude Code 2.1.321, the selected model, effort `high`, file mode: discovery and
two verifications through the helper. All three rounds `success`, the `session_id` is the same in `init` and
`result` of every round (`--resume` does not change the id), verdicts `FINDINGS` → `OPEN ITEMS REMAIN` →
`ALL RESOLVED`. Every round has a successful `Read` of the whole baseline file; in discovery it is listed in
`CONTEXT`. Earlier, on 2026-09-17, there was only one discovery on 2.1.274.

Limits: one model, one effort, one gate, file mode. Diff mode with an attached delta and the
full-text baseline fallback were not run live. The measurement does not say whether the baseline changes the number or
the quality of findings.

Sources: [CLI](https://code.claude.com/docs/en/cli-reference),
[headless and resume](https://code.claude.com/docs/en/headless),
[model settings](https://code.claude.com/docs/en/model-config).

## What was checked in Orca

Orca 1.4.248, codex-cli 0.167.2, Claude Code 2.1.323: `--model`/`--effort` reach the worker's
session; `send` to a closed worker continues the same chat for Codex and for Claude; both workers were able to
write a file.

2026-11-13, Orca 1.4.255, codex-cli 0.167.2, Claude Code 2.1.323, a toy repository:

- `worktree create --base-branch <plan SHA>` from the main checkout: the tree's HEAD equals the SHA, the tree is
  visible in `worktree list` and became a child of the coordinator's workspace. A tree in `.claude/worktrees/`
  did not show up in `worktree list` with either `hide` or `show`.
- Executor `--agent claude --model <fable model ID> --keep-open` with `--worktree id:<tree>`:
  the tab is visible in the tree's `terminal list`, the edit and the commit landed on the tree's branch, the main checkout
  was not touched; the report came as the `worker_done` body and as a file. `send` to its dispatch returned a new
  `dispatchId` in the same terminal, the worker made a second commit and reported again.
- Reviewer `--agent codex --model <selected model> --effort max` in the same tree: it ran
  `git diff <SHA>` itself, answered with the `worker_done` body with the `REVIEWED`/`CONTEXT` lists and the line
  `VERDICT: NO FINDINGS`; the tree fingerprint before and after matched.
- `worker-stop` of a running worker: `state: stopped`, `processAction: closed_agent_terminal`,
  `close.ptyKilled: true`. The earlier form of the save-and-rollback command, without a pathspec, saved a patch
  with a new file and returned the tree to HEAD. The current save commands (own tree with a pathspec;
  someone else's checkout without rollback) were checked in a toy git repository outside Orca.
- `--model` with an `opus` and with a `sonnet` model ID reaches the worker; a `sonnet` worker
  committed a mechanical edit.

Not measured: how much controlled-text diff review falls short of native `codex exec review`;
the full ship route with SDD on workers; parallel fixers without git; stopping with parallel
fixers; the outside-git variant (`rsync -R`) in an Orca run; fix rounds 4–5 with a model
change; polish by a worker (`simplify`, `ponytail-review` inside a worker); `question`/`reply` from
an executor; the mirrored pairing with a Codex main agent and `--agent codex` executors; a class alias
such as `opus` in `--model`; the ban on helpers was checked only by the fact that the workers did not start any.

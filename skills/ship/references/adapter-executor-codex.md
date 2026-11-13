# Executor adapter: Codex

The executor is Codex (OpenAI, GPT family), the external reviewer is Claude Code (Anthropic).
Before the first step, read `adapter-reviewer-claude-code.md` next to this file.

## Contract card

| Capability | Covered by |
|---|---|
| Who the executor is | The system context of the current session identifies Codex/OpenAI/GPT; in the local CLI an additional marker is a non-empty `CODEX_THREAD_ID`. Take the model version from the session context; do not guess it from someone else's config |
| External CLI access | Claude needs the network, the existing authorization (including the keychain) and writing session state to `~/.claude`. Check the permissions currently in effect in the runtime; `~/.codex/config.toml` alone does not determine them. If access is already granted, launch right away. If the sandbox actually forbids the needed access, use the permission mechanism the runtime provides for this command only; bypassing the ban or changing the global config is not allowed |
| Long launch | `exec_command` returns the `session_id` of the live process, then `write_stdin` reads the result. In a runtime with `functions.exec`, first wait for the tool call itself; if it returned a `cell_id`, continue via `functions.wait`. These are different IDs, and neither of them is the reviewer's ID |
| Subagents with edit permission | The delegation mechanism available in the current Codex: `collaboration.spawn_agent` or `spawn_agent`. Only non-overlapping files and the current session's permissions. No mechanism — sequential work, note it in the report. In Orca, edits are made by `--agent codex` workers per the section "Executor as worker" in `adapter-orca.md`; the own mechanism remains for reading, exploration and task review |
| Simplifying pass | An available simplification skill; otherwise a manual pass over your own diff: reuse and reduction, noted in the report |
| Deletion pass | `ponytail-review`, if available; otherwise a separate manual "what can be deleted" pass |
| Question to the user | The available `request_user_input_async`; `request_user_input` only in a mode where it is allowed; otherwise a plain text question |
| Engineering baseline of the review | Mandatory `pragmatic-engineering`; resolve the path, read it and pass it to all reviewers and polish passes per the core's section "Baseline approach to review" (`SKILL.md`) and `references/gate.md`, section "Engineering baseline in review prompts" |
| Route skills | `superpowers:brainstorming`, `superpowers:writing-plans`, `superpowers:test-driven-development`, `superpowers:using-git-worktrees`, `superpowers:subagent-driven-development`; auxiliary — `superpowers:receiving-code-review`, `superpowers:verification-before-completion`, `superpowers:finishing-a-development-branch`. Each counts as present when the catalog lists it either as `superpowers:<skill>` (plugin install) or as bare `<skill>` (skills directory install). If any is missing: stop and tell the user to install it with `/plugins`: search for superpowers, install |

## Model selection

For workers and subagents the model is set explicitly, by the SDD tiers: the base working model for
executors and fixers, a cheap one for mechanical work from a ready plan, the strongest one only by escalation
(fix rounds 4–5, `BLOCKED` due to complexity). Take the concrete GPT line IDs from the user's
instructions; if there are none — one question before the first dispatch.

## How to read dependencies

Look the skill up in the current session's catalog of available skills; the registered name may lack
`superpowers:`. If there is no Skill call, reading the full `SKILL.md` at the path given in the catalog
and following its instructions is the standard way of using it. A missing Skill tool does not mean
the skill is missing. If the file itself is missing — name the missing dependency, as the core requires.

The order of stages is set by ship, the repository's requirements by its `AGENTS.md`. Do not repeat a
brainstorm already held and do not create a second worktree if the current session is already isolated. Questions that affect
the product or the scope are asked to the user; technical findings are worked through independently.

## Long review

Launch the helper from the reviewer adapter as a process with the access described in the card above;
with a short yield it keeps running. A sandbox refusal is a launch that did not happen:
first remove the specific restriction in a permitted way, then repeat, without counting the round.
If the runtime does not allow the necessary access, name the restriction and leave the gate open.
Wait via `write_stdin` with empty input and report progress regularly. Do not send Ctrl-C because of
missing output: Claude may return JSON only after the whole round has finished.
Do not launch a second instance of the same round while the first one is alive.

`reviewer.json` and `thread-id` in the scratch store the **Claude session_id**. Only this ID is used
for verification. After compaction, read these files and the ledger; continue the same thread.

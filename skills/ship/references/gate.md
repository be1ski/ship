# ship: gate

## Engineering baseline in review prompts

`pragmatic-engineering` is the basis of **any** review inside ship: of the spec, the plan, the code, individual
tasks, verification of fixes, the polish delta and the confirmation pass. The executor also applies it
during triage and polish, including `simplify`, `ponytail-review` and manual passes. Assess correctness,
implementation complexity and understandability for the owner separately; justify simplification by requirements
and verifiable consequences, keeping useful abstractions and necessary error handling.

Pass every reviewer the "Engineering baseline" block from `references/prompts.md` with the resolved
absolute path to the skill. Do not rely on autoloading or on the executor having read the skill.
The source is context for the criteria, not part of the change under review. The block is mandatory on verify
too; it does not widen the scope and does not permit a repeat sweep. The gate protocol, roles and exit conditions
are set by ship; the engineering criteria by `pragmatic-engineering`, without copying the whole skill into this
file. Proof of reading the baseline and of scope coverage is set by the adapter: `CONTEXT`/`REVIEWED` for modes
with a controlled response text; for native Codex diff-review — an actual successful read via
Read/command execution or the full text in the context of the actual review-child. The absence of a single
text marker does not prove that no read happened; without available proof, do not count the run.
In per-task loops also add this block before the task-review and re-review templates of
subagent-driven-development: this applies to the task-review subagents as well, keeping their response format.

## Gate: discovery once, then verification

**The base is fixed on disk before the first discovery of each git gate.** Resolve the chosen base
to a full SHA with `git rev-parse <base>^{commit}`; if no separate base is given — save the
result of `git rev-parse HEAD`. Do not recompute a base already saved while preparing the route.
Write the SHA to `<gate-scratch>/base-sha` and to the ledger together with the scope
and the working directory. For the full route use the already saved plan SHA, for polish —
the SHA of the clean code gate. In every discovery/verify `<gate base>` means this literal SHA,
not the symbolic `HEAD`; commits made during the gate do not change the base. The diff from it to the working
tree includes staged and committed work. In snapshot mode, instead of a SHA save the snapshots and the mapping of
each snapshot to its original path in the ledger; the deletion rules are in the "Polish" section (`references/polish.md`).

The difference is not in memory — the ledger provides memory anyway. The difference is in the **question**: a
narrow question converges because the list can only shrink, and new items are admitted only inside the small
delta of the fixes.

Not "I fixed everything it wrote", not "only trivia is left", not "the rest is nitpicking". The round counter
by itself is not a reason to stop — the reasons are listed in "Stall" (`references/triage.md`), and they are about content, not about
the number.

**After a gate closes, the next edit requires a new gate** — including polish, renames,
removing comments and editing tests. A new gate means a **new discovery** over its own scope and its own
thread; for polish the scope is the delta (see "Polish", `references/polish.md`), for everything else — the same as before.
Fixes for an already opened next gate are verified in its thread, without opening yet another gate for each fix.

**A fresh confirmation pass after convergence** — not by default, but only when the change touches
money, access, data deletion or irreversible operations. After the code and the polish delta are closed
(or its absence is recorded) — one fresh discovery call over the whole scope. It has a separate scratch
and, in diff/snapshot mode, a copy of the original base/snapshots of the code gate, so that it sees the whole
change; in file mode the whole scope is re-read. Its findings are closed in its own thread and named
separately in the report. This confirmation gate completes the route;
there is no need to repeat the polish gate after it without new polish.

## How to call the reviewer

The commands are in the selected `references/adapter-reviewer-*.md`. Here is only what holds for
any reviewer.

**Branch on the form of the artifact, not on its name.** There is a git diff that can be described in prose
(from a saved SHA to the working tree or a fixed end SHA) — the adapter's diff mode. There is no diff — a spec, a plan, a file outside the
repository, a file that has not changed — file mode. A one-off script and a config edit are split
by the same sign.

**The scope is passed by the mechanism the adapter declared.** In prose it is an instruction to the model, not
a flag: compliance is not guaranteed. One reconciliation for both cases: the paths in the findings must lie
inside the change. If they do not — it is a run that did not happen: rerun with a more explicit scope
description, up to two times, then escalate.

**Discovery — always in the background; if the runtime cannot run in the background — with a timeout above 15 minutes.** Measured:
a round on a 221-line diff took 541 s and did not fit into the runtime's 10-minute timeout, being lost
entirely. A verification round is an order of magnitude cheaper (25–110 s in
measurements), but the background does not hurt it either.

**Pass the prompt as a file, not as a string in argv.** A ledger line that quotes a flag
has every chance of being re-tokenized by a wrapper and parsed as a real flag.

**Keep `.ship/` outside the reviewed scope** — otherwise the gate's service files land in its own
diff and the reviewer reads your own prompt as part of the change. `.ship/` ignores itself (see the ledger);
a scratch placed elsewhere inside the tree is excluded explicitly in the scope description.
Build artifacts go there too: `git rm --cached` will not keep them out, because the next `git add -A` puts them
back into the index.
The session scratchpad, meanwhile, is ephemeral: an acceptance script that lived only there was not
found in any session directory after a restart. A check that must survive until the end of the work goes into
the work's artifact, into the plan or into the repository, not only into `.ship/`.

**What counts as a clean discovery in diff mode is stated in the adapter's card.** Any finding
in the selected adapter's format means an open gate. In file mode the last-line contract
applies; the Claude adapter applies this contract to diff mode as well.

The discovery prompt for file mode, like the others, is in `references/prompts.md`.

## Prompts

The blocks and the full discovery frameworks for files, git diff and snapshots, for verification and the polish
delta are in `references/prompts.md`. Assemble the suitable framework from the indicated blocks, substitute
the values and pick the marked variants; do not retell the text of the blocks in your own words.
**What counts as a clean run and what confirms reading is declared by the adapter**: the last-line contract
and text markers do not work with every reviewer or in every mode.

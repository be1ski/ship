# ship: route

## Preflight

After choosing the route, before its first step: read the selected adapters and the required skills,
check reviewer availability per the adapter, determine the scope, the checks and the route's shared scratch
directory. A missing dependency or an unavailable launch mechanism is a
concrete blocker; preflight does not change permissions and does not require re-approval of work already permitted.

**Utilities.** Run `command -v git python3 jq`. For each one missing, name it and stop; do not
install anything.

**Route skills.** Check that every route skill named in the executor adapter is present in the
session's skill catalog. If one is absent, name it, print the install command for the current
agent from the adapter, and stop.

## Route details

The one-off route is a deliberate exception to the HARD-GATE of the brainstorming skill, which
requires an approved design before any code, including single-file utilities and config edits.
Once the work is classified as one-off, the code starts without a separate design gate: that is the choice
the user makes by invoking ship. If along the way it turns out that the work is not one-off, return to the
full route instead of finishing it in code. Edits already made are neither erased nor hidden:
they stay in the main tree, the worktree is created from HEAD and will not pick them up, and the work in it
is written anew, tests first.

Full route: spec — `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`; if
there is no design yet, the brainstorming skill takes it to an agreed design — **and stops
there**: the spec is written, run through the gate and shown to the user by ship, and the
transition from brainstorming to writing-plans is not performed. The user's approval of the spec is not
cancelled but moved: ship asks for it after a clean gate (see below), not brainstorming before it. Agreeing the design in the conversation stays with brainstorming; only the approval of the written document moves. If the
design is already agreed — write it into this file as is and go straight into the gate, without
running the brainstorming checklist again. Plan — the planning skill, into
`docs/superpowers/plans/YYYY-MM-DD-<feature>.md`; execution — first the isolated-tree skill
(isolated tree), then the per-task loop skill. The one-off route runs in the current
tree: before the first edit, look at what was already dirty in it and describe the gate scope by the paths
of your own work, not by "the working tree" as a whole — otherwise someone else's uncommitted edit ends up in
the gate. Paths separate work only file by file: if the work lands in a file that was already dirty, take a
copy of it before the edit into the code-gate scratch and give the reviewer the delta from that snapshot — by
the same mechanism the polish delta is computed with. For a one-off git gate, before your own edits save the
original HEAD SHA in `base-sha` and in the ledger of the future code gate; the implementation commits must also
fall within its scope. The Execution Handoff from writing-plans is not performed here: the execution method was
already chosen by invoking ship; after a clean plan gate go straight to the worktree and
subagent-driven-development. The spec and the plan are written in the main tree and committed **before** the
worktree is created — as a separate commit and only with their own paths; do not sweep anything else from the
working tree into it: the tree is created from HEAD, and an uncommitted plan simply will not be in it. The line
about the worktree context in writing-plans itself is deliberately overridden here — it is worded differently
in different copies of superpowers; the order is set by ship.

**Before moving to the worktree, save the full SHA of the plan commit** in `base-sha` and the ledger of the
future code gate — this is its base. Scratch and transition data are saved under absolute paths (the
"Ledger" section, `references/ledger.md`); auto-picking the new HEAD must neither pull the spec and the plan into the review nor hide
the code commits.

Code is written tests first: **REQUIRED SUB-SKILL** the TDD skill. Two
boundaries from there that must be read correctly. The Iron Law "wrote code before the test — delete it" is
about new behaviour that you write; **already existing code is not deleted**, tests are written for it,
the TDD skill itself says so. Configs are declared there an "ask your human" exception — in ship
there is no need to ask, invoking the skill is the permission. A red test is not required for a config:
`terraform validate` and its kin pass both before the edit and after it, they cannot be made red. Instead —
the mandatory check from the "Checks" section (`references/checks.md`); without it a config gate does not close. A one-off script is
**not** an exception: that very one runnable check is its test, and it is written red before the code. This is
about a new script. If the code is already written, first run its existing checks or a characterization check
of the intended behaviour; a check goes red only for a demonstrated defect, before the fix. Code that is
already correct needs no invented failing expectation.

The gate closes **before** the artifact goes to the user: otherwise they read a draft that the
reviewer will make you rewrite anyway. After that it differs: a clean spec goes to the user, and ship
waits for confirmation — this is brainstorming's own gate; a clean plan does not block, straight to the
worktree and execution, the plan is visible in the report.

From subagent-driven-development only the per-task loops are performed: implementation, task review,
fixes. Its tail — the final whole-branch review, removal of the plan workspace and the transition to
finishing-a-development-branch — **is not performed**: the whole-branch review is replaced by ship's code gate,
and removal of the tree belongs to the merge decision and comes after polish and the final gate, otherwise
there will be nothing to polish. The code gate sits on top, once, over the whole change.

**Parking from SDD is only a temporary hand-over to the code gate.** Before its discovery, read the SDD progress
ledger, carry all deferred/parked entries with their technical grounds over into the code-gate ledger
and into the "Known task-review items" block from `references/prompts.md` in the discovery prompt. These are
unconfirmed claims: the reviewer must explicitly accept or reject each one with a justification,
and must not treat them as proven. Keep all outcomes, including rejections and scope decisions;
accepted findings are closed by the normal gate loop. Without a decision on every handed-over entry the gate
is not closed. A new discovery does not replace handing over the known facts from the per-task loop.

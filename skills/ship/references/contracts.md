# ship: contracts

## Reviewer adapter contract

The adapter must cover these capabilities. A row without a working fallback is blocking: without it the
reviewer is not fit for ship, and the user is told so rather than having it worked around.

| Capability | Why | Fallback |
|---|---|---|
| Who the reviewer is: vendor, model family, version | Otherwise there is nothing to check the "reviewer ≠ executor" invariant against mechanically | None. Unknown who is answering — blocks |
| A discovery call over a scope described in prose | The gate scope cannot always be expressed with flags: from a saved SHA to the working tree or to a fixed end SHA | Scope flags, if they cover exactly the needed slice. Neither one nor the other — blocks |
| Verification in the **same** thread, addressed by id | The reviewer keeps its own list in context; a narrow question converges, a fresh one does not | None. The adapter must provide a thread in every mode it has declared |
| Distinguishable "clean" / "findings" / "run did not happen" | The gate's exit condition | A last-line contract in the prompt. If it does not hold — blocks |
| "File as is" mode, without a git diff | Spec, plan, file outside the repository, unchanged file | None. A reviewer that cannot read a file by path is not fit for ship |
| The reviewer itself re-reads the current state on verification | Otherwise it judges the fix by the executor's retelling | The delta from the saved base in the prompt; snapshots and deletion — per the rules of "Polish" (`references/polish.md`) |
| Confirmation of reading the baseline and of scope coverage | A clean verdict without the material having been read does not close the gate | Successful reads in the events or the full material in the reviewer's context; without proof the run does not count |
| The run survives a long wait | Measured: a round on a 221-line diff took 541 s, did not fit into a 10-minute timeout and was lost entirely | Background launch, if the runtime supports it; otherwise a timeout above 15 minutes |
| The pin of the model and of all settings that affect the output is visible and recorded | Without it rounds are not comparable with each other | A setting the reviewer does not have (for example reasoning effort) — an explicit `N/A`. An unknown value of an existing setting blocks |

The adapter lives next to the skill and ends with a filled-in contract card. **Read the adapter
before the first reviewer call** — the commands are there, not here.

The adapters are in `references/adapter-reviewer-*.md`; read the needed one before the first reviewer call.

A new adapter is written against the same card: cover every row of the table with a command or a fallback,
check on a live run that discovery returns a list and that verification — in the thread or through the
declared fallback — returns a verdict, and only after that put it into the route.

## Executor adapter contract

The same form as the reviewer's. A row without a working fallback is blocking. Route skills are not replaced
by a manual pass: if the needed one is missing, say which one and stop, as with a missing reviewer adapter.

**The executor runtime is plugged in through a `references/adapter-executor-*.md` file; read it before the
first step of the route.** No adapter for your runtime — write one against the card rather than guessing
from the text; the names of the route skills are there too.

| Capability | Why | Fallback |
|---|---|---|
| Who the executor is: vendor, model family | Otherwise there is nothing to check the "reviewer ≠ executor" invariant against | None. Unknown who is executing — blocks |
| Background launch of a long command | Discovery takes minutes and must not be lost to a timeout | A timeout above 15 minutes |
| Subagents with permission to edit files | Parallel fixing of findings in non-overlapping files | Fix sequentially and say in the report that there was no parallelism |
| A simplifying pass over the diff that applies edits | Polish: reuse and simplification | Go through the diff by hand against the same criteria, say that the pass was manual |
| A "what can be deleted here" pass that lists | Polish: deletion | Same |
| A structured question to the user | Escalation | A plain text question |
| Route skills | Spec, plan, TDD, isolation, per-task loops | None for the skill file itself; for the mechanism the skill asks for — yes |

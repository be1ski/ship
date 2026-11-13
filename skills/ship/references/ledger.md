# ship: ledger

## Ledger

**Each new route gets a new scratch-root**, for example `.ship/<unique-route-id>/`,
or a new directory outside the tree. Inside a git tree, create `.ship/.gitignore` with the single line `*`
if it is missing: the scratch then ignores itself and the repository's own `.gitignore` stays untouched.
Create the root so that creation fails if the name exists; do not reuse a past
route even after it is completed. A continuation of the same route keeps the earlier root.
Inside it each gate gets a separate directory: `spec-01/`, `plan-01/`, `code-01/`, `polish-01/`,
`confirm-01/`. Parallel routes also have different roots.
For recovery in Git, write the absolute path of the scratch-root to the file
`<git-common-dir>/ship-routes/<route-id>.txt`, where `git-common-dir` is obtained with
`git rev-parse --path-format=absolute --git-common-dir` from any worktree. This is a pointer to the registry,
not one more ledger. Outside Git, or when the git directory is not writable for the current runtime (a sandbox that makes `.git` read-only), keep such a pointer in `.ship/routes/` of the original working directory instead; do not ask for a permission only to write the pointer.
After a break, find your route's pointer rather than starting a new registry in the current worktree. Look in both places.
In `<scratch-root>/gates.md` keep the registry: gate, scope, absolute scratch path, state and
proof of closure. Keep there as well the paths of the spec, the plan and the SDD progress ledger for transitions
between stages. When the worktree changes, keep using this registry and the listed directories;
do not overwrite closed gates, add a new gate as a separate row.
A run that did not happen is an attempt of the same gate. If the adapter requires a new scratch for the retry,
keep a reference to the failed attempt and update the active path in the registry, without losing the base and
the ledger.

**A file, not memory:** `<gate-scratch>/ledger.md`, one line per finding — id (your own, running through the gate: `#1`,
`#2`, …) · round · quote · decision
(fixed / rejected + reason / escalated / open) · scope in which it was judged · a **secondary** mark,
if the finding lies in code that a previous round of the same gate added. Conversational memory does not
survive compaction, and the gate cannot be closed while the file has open lines.

The ledger is the source of the "responses to findings" block in the verification prompt: one line for every
**open** ledger line — not only for discovery findings, but also for `REGRESSED` and new ones
raised by verification rounds — its title verbatim and what was done about it.

**Only decisions and technical reasons** go into the ledger. Never "rounds 1–3 already looked, it is clean
here": that is not an argument but suggestion, and it breaks the reviewer.

Next to it lie `base-sha` (for a git gate) or snapshots with a scope description, `thread-id` (the discovery
thread, mandatory), `last-review.txt` (the output of the last round) and the adapter's files. A new gate — a new
id; do not mix the threads of different gates and parallel tasks. After a break, read the registry and the
ledgers, including carried-over SDD entries: readiness and the final report are assembled over the whole route.

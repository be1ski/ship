# ship: polish

## Polish

Only after the code gate has closed. **Fix the base in a separate scratch of the delta gate**:
the full SHA of the clean state in `base-sha` and the ledger, if the work is committed; if not (one-off
route, uncommitted fixes, file outside the repository) — take a copy of the current state of each
affected path and record the mapping of snapshots to paths. The delta is computed from this base.

1. **a simplifying pass** over the diff that applies edits itself;
2. **a "what can be deleted here" pass**, listing only, apply by hand;
3. comment cleanup (rule below);
4. checks.

How these two passes are covered in your runtime is in the executor adapter. If they are not there (a different
runtime, the work runs in a subagent) — do not hang and do not look for workarounds: go through the diff by hand
against the same criteria (reuse and simplification; separately "what can be deleted here") and say in the report
that the pass was manual.

**Polish is one pass, then its own gate over its own delta**, not over the whole change. It is a
full gate: its own discovery, its own thread, its own verification.

The polish prompt is in `references/prompts.md`.

If the base is a snapshot rather than a SHA, give the reviewer the delta explicitly:
`diff -u --label "a/<original-path>" --label "b/<original-path>" <snapshot> <file>` directly in the prompt.
More than one file — snapshot each touched path separately and give a diff for each.
Compare a deleted file with `/dev/null`, keeping its original path in the scope and the header:
`diff -u --label "a/<original-path>" --label /dev/null <snapshot> /dev/null`.
Exit 0 — no differences, 1 — a normal delta, greater than 1 — an error building the diff; it must not be taken
for an empty delta. The headers of the other snapshot diffs must also contain stable original paths,
not changing timestamps. These rules apply to the one-off route too, including outside Git.
Do not snapshot a whole directory: the scratch and everything unrelated lying next to it would end up in the delta.

Plus a **full** run of the checks — the delta review is narrow, and a regression could have slipped past its edge.

**Polish adds nothing.** Only your own change, only deletion and simplification. No new
features, flags, files, `.gitignore`, rewritten tests of others or "tidied up around it while at it" appear.
Whatever is noticed along the way goes as a line in the report, not into the diff.

## Comments

A comment that retells the code — delete it. **A docstring that retells the signature is the same
retelling comment; delete it too.** `"""Return every row of the CSV at path."""` above `read_rows`
adds nothing to the function's name.

Only these may stay:

- **why** it is done this way and not otherwise: an external constraint, an upstream bug, a non-obvious invariant;
- a `TODO`/`FIXME` anchor;
- a `ponytail:` marker with the solution's ceiling named;
- a docstring that says more than the name: contract, units, what it raises — and if docstrings
  are the convention in this repository;
- a header required by tooling or a license.

Everything else moves into the name: a variable, function or type name is stronger than any comment. Do not
bring explanatory comments back when fixing findings — this is the most frequent relapse.

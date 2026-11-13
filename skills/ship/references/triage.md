# ship: triage

## Finding triage

Every finding ends in one of three ways. None may be silently ignored. The user sees the outcome of triage
as the round message (the "Report" section, `references/report.md`) before the first edit.

**First check the premise.** A finding has two layers, the conclusion and the justification, and they diverge.
What has to be checked is the fact it rests on, not only the conclusion. Measured: the reviewer wrote that a
phrase occurs twice and proposed replacing a counting check with three separate ones. The conclusion was right,
the count was not, and the wrong count went into the artifact verbatim, because someone else's justification was
carried over unchecked. The conclusion is right but the justification is false — so fix according to your own
justification.

**Fix.** The finding is correct → edit → check. One at a time
(the receiving-review skill) — except when the findings lie in **non-overlapping
files**: then they may be handed out in parallel (see "Parallelism").

**Reject.** Only with proof: a quote of code, a test, the spec, or a run that showed the number. The run
is given together with the command and the result. Measured: the only rejected finding of a run was settled by
two queries with the same answer, 36; there was nothing to quote there. A rejected finding — a line in the ledger
and a line in the verification prompt.

**Escalate.** In normal triage — exactly two cases: the finding changes the agreed behaviour or scope;
or it is a product/taste decision. Carry a technical dispute yourself — that is what the loop exists for.

An escalated line stays open until the user answers. The answer closes it: agreed — the line
becomes a fix, refused — a rejection, and it goes into the verification prompt in that form. Without
an answer the gate does not close, and the work is reported as unfinished.

Separately, about the most frequent kind: **a finding that asks for new behaviour.** "Add handling for the
header", "support this kind of input" — that is scope expansion arriving disguised as a fix. If the
behaviour was not in the spec — escalate or reject with a reference to the spec, **do not write more code**.

### Ratchet: a finding in code that ship wrote

Before fixing — look at **who wrote the line** the finding points to: by the ledger and by
your own edits in this gate, not by `git blame` — round fixes are not committed yet. If the line was
written by a fix from an earlier round of the same gate, the finding is **secondary**, and a different rule
applies to it:

- **A secondary finding does not by itself justify a new layer.** First check whether the mechanism that gave rise to it is needed.
  Unnecessary — delete it; needed — fix or rewrite it, keeping the contract;
  an incorrect finding — reject it with proof. Per `pragmatic-engineering`, a useful check or
  abstraction does not become unnecessary because it was added in a previous round. If a correct
  fix requires a new mechanism, justify why deletion and a local edit are not enough.
  An ordinary fixable regression remains the executor's technical work; the share of secondary findings
  does not by itself require a decision by the user.
- **A function or module that has collected 3 findings over two or more rounds goes to a layer audit**, not to
  a fourth fix. The audit has one question: what breaks if the layer is removed? Usually nothing, and that is
  the right fix.

Measured, why this rule exists: 26 findings out of 39 in a live run were secondary, and both exits
from the loop were deletions, not fixes. Defensive code written at the reviewer's request is code
that nobody ordered and that the reviewer will check with the same rigour as the real thing.

### Stall

Before each round of fixes, save the exact scoped diff (for files — snapshots and the presence of the paths)
in the current gate's scratch under the round number; record the path and the hash in its ledger. The result of
the fix is compared against it, so the comparison does not depend on memory or on a change of HEAD.

Stop the loop and escalate both positions if:

- the same finding (in substance, regardless of wording) has survived **3 rounds**;
- with open findings remaining, a completed round produced neither an edit nor a justified rejection;
- the number of open findings did not decrease over the last two rounds;
- file edits are claimed, but the exact bytes of the scope did not change after the fix. For git, compare the
  `git diff <gate base> -- <paths>` saved before the fix with the current one (or the hashes of these diffs
  without whitespace normalization); the fixed base includes the index and commits made during the work. For
  file mode compare exact content snapshots and the presence of the paths, for snapshot mode — deltas from the
  same base with stable headers. `patch-id` is not suitable for this: it ignores significant indentation.

The round counter by itself is not a reason to stop. Escalation to the user is a **normal
outcome**, not a failure: what goes up is both positions and the list of what is open, not a "what should I do" request.

## Parallelism

Not everything is parallelized. In Orca the section "One writing worker per tree"
from `references/adapter-orca.md` is added to the rules below.

**Allowed:**
- fixing findings that lie in non-overlapping files — one subagent per finding;
- independent check runs (different test suites, linters, validators);
- exploration and reading before implementation.

**Not allowed:**
- **do not multiply the review itself.** Multi-agent review loses to a single reviewer in measurements, and when
  the exit is "zero findings" every extra lens means extra items that will have to be closed. One
  reviewer, one verdict, one thread;
- fixes in non-overlapping files — yes, in overlapping ones — no, only sequentially;
- subagents on which the runtime imposes auto-accept of edits regardless of the session mode are not fit for
  fixes. Which mechanism in your runtime gives subagents with edit permission, and which
  imposes auto-accept — is in the executor adapter.

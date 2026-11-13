# Prompts

Blocks and frameworks for the external reviewer, task review and polish passes.

A **block** is a piece of text that is inserted into a prompt. A **framework** is a full prompt assembled from
blocks. The English text of blocks and frameworks is copied as is: retelling it in your own words breaks
convergence. Only what is marked changes:

- `<angle brackets>` — substitute a value or the named block;
- "only if …" — the section is either present in full or absent in full;
- "variant" — take exactly one of those listed.

The ending of the prompt and the way to confirm that the reviewer read the baseline and the scope depend on the
reviewer's response mode. Which call runs in which mode is in the reviewer adapter's card.

| Response mode | End of discovery | Read confirmation |
|---|---|---|
| Controlled text: the reviewer answers in free text, the prompt sets the format | `VERDICT: NO FINDINGS` / `VERDICT: FINDINGS` as the last line | The "What you opened" block: the `REVIEWED` and `CONTEXT` lists in the response |
| Native diff-review: the reviewer itself sets the response format | None. Clean or not — per the adapter's card | Actual successful reads in the run's events, per the adapter's card. The "What you opened" block is not included |

No confirmation — the run did not happen. The absence of a text marker in a mode where the adapter does not
promise one does not count as absence of reading, and the baseline is mandatory regardless of the mode.

## Block "Engineering baseline"

Goes at the start of **every** review request: discovery and verify, file and diff mode,
review of individual tasks, the polish delta and the confirmation pass. The executor substitutes the path
after reading the dependency. For the polish passes themselves use the separate block below.

```text
Engineering baseline: pragmatic-engineering.
Read <absolute path to pragmatic-engineering/SKILL.md> in full and apply its engineering
principles to this review. Treat it as the review rubric, not as an artifact to review or
an instruction to implement changes or launch another review.
Assess correctness, implementation complexity and the owner's ability to understand and
maintain the result separately. Ground material findings in requirements, evidence and
concrete consequences; preserve useful abstractions, necessary checks and error handling.
Apply these criteria only within this round's scope. In verification, judge the existing
findings and regressions in the permitted delta; do not start a fresh sweep.
If the baseline cannot be read, report the blocker rather than a clean verdict.
```

If the reviewer reported that it cannot read the baseline, the run did not happen, even with a
`FINDINGS` / `OPEN ITEMS REMAIN` tail: this is not a finding and not a ledger line. For the rerun,
attach the **full text** of the skill the executor has already read between `BEGIN ENGINEERING BASELINE
CONTENT` and `END ENGINEERING BASELINE CONTENT`, separately from the diff. In the block replace the sentence
`Read <absolute path …> in full and apply its engineering principles to this review.` with
`Read the full ENGINEERING BASELINE CONTENT below, apply its engineering principles to this review,
and list it as "CONTEXT: inline ENGINEERING BASELINE CONTENT".`
Apply the adapter's rules for a failed run (for Claude, failed discovery — a new scratch,
failed verify — the same thread) and the common retry limit; a short summary does not replace the dependency.
The `CONTEXT: inline …` entry confirms the full text only in controlled text mode. What
replaces it in native diff-review is stated in the adapter.

The executor checks that the baseline was read in discovery against the mode table above. In controlled text the
reviewer lists the read path in `CONTEXT`, not in `REVIEWED`; for the full text —
`CONTEXT: inline ENGINEERING BASELINE CONTENT`. On verify the block stays before the narrow question about the
findings.

For `simplify` / `ponytail-review`, pass the following block with the same path before their assignment;
if the pass cannot read files, use the full text with the same markers. In manual
polish the executor applies the already read skill itself.

```text
Read <absolute path to pragmatic-engineering/SKILL.md> in full (or the full ENGINEERING
BASELINE CONTENT supplied below). Use its principles as the criteria for this polish pass:
preserve useful abstractions, necessary checks and error handling; justify simplification
by concrete maintenance benefits. Keep the pass's assigned role, editing permissions, scope
and output format. If the baseline is unavailable, report the blocker and do not run the pass.
```

## Block "What counts as a finding"

Goes into **every** discovery prompt, in any mode. Without it the reviewer produces style remarks and
unformatted comments, and triage drowns in things that do not need fixing. The block consists of
one criteria variant and a common tail.

Criteria variant — exactly one, by artifact.

Spec:

```
Judge only what would change the implementation:
- contradictions, and requirements that can be read two ways
- failure and edge-case behaviour the implementer would otherwise have to invent
- unstated assumptions
- success criteria that cannot be checked
```

Plan — the same lines as for the spec, plus one more:

```
- steps that cannot be verified on their own, and tasks that hide more than one outcome
```

Code:

```
Judge only what would change the code:
- behaviour that contradicts the stated scope, the spec or the plan
- wrong results, crashes, data loss or silent failure on inputs this change must handle
- failures reported as success, and error handling that hides the original cause
- checks that cannot fail when the code they guard is broken
New behaviour or defensive code that the stated scope does not require is not a finding.
```

Config:

```
Judge only what would change the configuration:
- values that contradict the stated scope or the service they configure
- settings that fail to load, are silently ignored, or change behaviour outside the scope
- exposure this change introduces: listening addresses, permissions, secrets, destructive defaults
- effects that the stated check does not exercise
```

The polish delta has no variant of its own: its criteria are the paragraph about polish in its framework.

The common tail, after any variant:

```
Ignore cosmetic wording, formatting and style preferences. Material complexity that makes
correct use, diagnosis or maintenance harder is an engineering concern, not a style preference.

Report only material findings: quote the line, say what is wrong, say what change fixes it.
```

Assess material complexity per `pragmatic-engineering` with a concrete consequence, not by the
reviewer's taste.

## Block "What you opened"

Goes into the discovery prompts of **controlled text mode**, file and diff. Without it a clean
run cannot be checked: there are no findings, and therefore no paths that show where the reviewer looked.
In native diff-review the block is not included: the reviewer sets the response format there, and the lists do not
make it into the response; reading is confirmed by the run's events per the adapter.

```
Before the verdict, list what you opened, in two separate lists, and emit both even if you found
nothing:

REVIEWED: <path>   — files that are part of the change under review
CONTEXT: <path>    — anything else you opened to understand it: repository instructions, docs,
                     neighbouring code, configuration

One path per line. REVIEWED must not be empty.
```

Here `<path>` is part of the text for the reviewer; do not substitute it.

Two lists, not one: the reviewer must read the repository instructions and neighbouring code, and a
requirement that "everything opened lies inside the work" would reject an honest run. What is checked is something
else — that `REVIEWED` is non-empty and lies inside the scope. `CONTEXT` paths are not restricted to the scope, but
the entry for the engineering baseline is mandatory.

## Block "Exhaustive sweep"

Into the discovery prompt — this block verbatim. **Only in discovery.** In verification it is poison: it
explicitly asks to open the whole surface again, and after fixes the surface is larger than it was.

```
EXHAUSTIVE SWEEP — this is the important part. Do not report "the top issue" or a sample.
Walk the whole scope line by line — every changed function for a diff, every section for a
document — and enumerate EVERY material finding you can support in one pass. Assume you get
exactly one pass: anything you leave out now ships unfixed.
Before answering, ask yourself explicitly: "if I were asked to review this again tomorrow, what
would I raise then?" — and raise it now instead.
```

Measured: without it the reviewer returns a sample — 1 finding against 6 on the same file, and every finding not
returned becomes a separate round. The flip side: the sweep also raises "what about currency, what about the time
zone". That is not a reason to remove it — that is triage's job, and the line about scale limits it.

## Block "Known task-review items"

Only if the per-task loops left open lines: deferred (`minor (deferred)`) and
parked (`parked`) items from the task ledger. Goes into the discovery of the code gate. The final
review that the per-task loop skill would have handed them to is not performed by ship, so the decision on each
one is made by the gate's reviewer.

```
KNOWN TASK-REVIEW ITEMS. These were raised during per-task review and left open. They are
unverified technical claims, not established defects: each may be wrong, already fixed or out
of scope. Check each one against the current code and decide it yourself.

<one line per item: <id> — <file or location> — <claim>>

For each item, answer on one line:
  <id> — CONFIRMED | NOT A DEFECT | OUT OF SCOPE — one-line reason.
Report a CONFIRMED item as a normal finding as well. These items do not limit the sweep.
```

The lines are substituted into the first angle bracket; the response-format line with `<id>` stays as is.
A claim is carried over together with its technical grounds, as recorded in the task ledger. Do not add
assessments: neither "this is a defect" nor "already looked, it is clean". The executor carries the outcome of
each line into the gate ledger. A line without an answer from the reviewer stays open and goes back into the same
thread as the section from the verification framework.

## Discovery framework: file mode

```
<role lines from the reviewer adapter>

<block "Engineering baseline">

Review <path to the file or list of files>.
This is <a design spec | an implementation plan | a standalone script | a config file | a set of files>, not a diff.

Scope of the work: <one line: what we are building and how big it is>.
Calibrate the bar to that scope.

<block "Exhaustive sweep">

<block "What counts as a finding">

<block "What you opened">

Your last line must be exactly one of:
VERDICT: NO FINDINGS
VERDICT: FINDINGS
```

A clean file discovery is a last line of exactly `VERDICT: NO FINDINGS`; exactly
`VERDICT: FINDINGS` is a run that happened, with an open gate. Any other tail, or none at all — the
run did not happen, rerun.

The line about scale is mandatory. Without it the reviewer demands time zones, schemas and
idempotency from a 15-line spec, and the gate does not converge. For the spec and the plan rounds are cheap and
the list is short, so verification there goes back into the thread by id with the verification framework below.

## Discovery framework: diff mode

The code gate and the confirmation pass. The base is the **saved literal SHA** recorded when the gate
was opened, not `HEAD`: the symbolic ref moves with the very first commit, and the diff from it becomes empty.

```
<role lines from the reviewer adapter>

<block "Engineering baseline">

Review only the changes between <gate base SHA> and <the current working tree | end SHA>.
<only if the scope is narrower than the tree: Only these paths are in scope: <paths>.>
<only if the scratch lies in the working tree: Ignore everything under <gate scratch>.>

Scope of the work: <one line: what we are building and how big it is>.
Calibrate the bar to that scope.

<only if present: block "Known task-review items">

<block "Exhaustive sweep">

<block "What counts as a finding", variant "code" or "config">

<only in controlled text mode: block "What you opened">

<only in controlled text mode:
Your last line must be exactly one of:
VERDICT: NO FINDINGS
VERDICT: FINDINGS>

<only if the reviewer cannot compute the diff itself: a ready-made `git diff <gate base SHA>`>
```

In native diff-review do not require a last line: the response comes in the reviewer's format, and what in it
counts as clean is stated in the adapter's card.

## Discovery framework: polish delta

The same framework as for diff mode, with three differences: the base is the SHA of the delta gate's base, after
the scope lines comes the paragraph about polish, and only the common tail is taken from the "What counts as a finding" block.

```
<role lines from the reviewer adapter>

<block "Engineering baseline">

Review only the changes between <delta gate base SHA> and the current working tree.
<only if the scope is narrower than the tree: Only these paths are in scope: <paths>.>
<only if the scratch lies in the working tree: Ignore everything under <gate scratch>.>
This is a polish pass: simplification, renames and comment removal only. No behaviour was
intended to change. Report anything that changed behaviour, plus any defect introduced by
these edits.

Scope of the work: <one line>.

<block "Exhaustive sweep">

<common tail of the block "What counts as a finding">

<only in controlled text mode: block "What you opened">

<only in controlled text mode:
Your last line must be exactly one of:
VERDICT: NO FINDINGS
VERDICT: FINDINGS>

<only if the reviewer cannot compute the diff itself: a ready-made `git diff <delta gate base SHA>`>
```

If the base of the delta is a snapshot of a file rather than a SHA, take the "snapshot delta" framework below with
two changes. Instead of the criteria variant put the same paragraph about polish, keeping only the common tail of
the "What counts as a finding" block. And replace its opening paragraph, which is about somebody else's
uncommitted work, with:

```
Review the unified diff below and nothing else. It is the delta between the file as it stood when
its review closed and the file as it stands now. Everything outside this diff was already reviewed
and is out of scope.
```

## Discovery framework: snapshot delta

For a file that was dirty **before** the work started: your own change cannot be separated from someone else's in
prose, so the reviewer gets a ready-made delta, not the file. Always controlled text mode.

```
<role lines from the reviewer adapter>

<block "Engineering baseline">

Review the unified diff below and nothing else. It is the delta between the file as it was before
this work started and the file as it stands now. Everything outside this diff is somebody else's
uncommitted work and is out of scope: do not report it, do not fix it, do not mention it.

<ready-made diff from the snapshot; commands with stable headers are in `references/polish.md`>

Scope of the work: <one line>.

<block "Exhaustive sweep">
<block "What counts as a finding">
<block "What you opened">

Your last line must be exactly one of:
VERDICT: NO FINDINGS
VERDICT: FINDINGS
```

Verification in this mode uses its own variant: instead of "re-read the file as it stands" —
"here is the current delta, judge by it", built the same way from the same snapshot. Re-reading the whole file
here would bring someone else's work back into the review.

## Verification framework

Rounds 2+ use this framework. A fresh sweep, an additional "what to pay attention to" list and a
retelling of the scope are not added. Verification always runs as controlled text, including after
native diff-review: the last-line contract is mandatory here.

Besides the mandatory prefix, a block about an edit the reviewer did not raise is allowed. If during the gate
something outside the frozen list had to be changed, that must not be done silently: the reviewer judges by
its own list and will not notice the edit. It is disclosed in a separate block, marked as not raised by
the reviewer, with a request to judge it as well. Accumulating such edits and running them as a separate gate costs
more: on a live task there were four of them, which is four extra runs against three lines in the prompt.

```
<block "Engineering baseline">

You reviewed this change and raised the findings below. I have responded to each.
Re-read the current state yourself — run `git diff <gate base SHA>` — and judge the responses.

<one line per finding: "<finding title>" — fixed like this / rejected because of that>

<only if there was such an edit:
ADDITIONAL EDIT, not raised by you, disclosed so you can judge it: <what and why>>

For each finding you raised, answer on one line:
  <short title> — RESOLVED | NOT RESOLVED | REGRESSED — one-line reason.

<only if there is no decision on known task-review items:
TASK-REVIEW ITEMS still without your decision:
<one line per item: <id> — <file or location> — <claim>>
Answer each on one line: <id> — CONFIRMED | NOT A DEFECT | OUT OF SCOPE — one-line reason.>

Raise a NEW finding only if it is a defect introduced by one of these responses or by a disclosed
additional edit — it must live in a line that changed since your review. Do not re-review code you
already passed, and do not propose hardening for code that already works.

Last line exactly one of:
VERDICT: ALL RESOLVED
VERDICT: OPEN ITEMS REMAIN
```

The response-format lines with `<short title>` and `<id>` are text for the reviewer; do not substitute them. If
discovery produced no findings but there is no decision on a known item, the round consists of the baseline, this
section and the last-line contract.

`<gate base SHA>` is the same saved SHA the gate was opened on; for a gate over the working tree
it is the output of `git rev-parse HEAD` at the moment of opening, recorded literally. Do not substitute either `HEAD` or a bare
`git diff` here: after a commit in the middle of the gate both show an empty or truncated diff,
and the reviewer will judge the fix by it.

If the reviewer cannot compute the diff itself, the sentence with `run git diff` is replaced as stated
in its adapter, and the current diff from the same SHA is attached to the prompt.

In **file mode** only the sentences "You reviewed this change… run `git diff`" change,
and the "Engineering baseline" block is kept: instead of these sentences — "Below are the findings from the
review of `<path>`, with my response to each. Re-read the file as it stands now." The rest of the framework is
the same, including the last-line contract.

A rejection goes into this same framework as a normal line with a technical argument — it needs no separate channel.
Checked: the reviewer withdrew its own finding ("I accept the rejection… the original inconsistency is
resolved without zero-filling") and returned `ALL RESOLVED`. Phrase it technically, without "great
point" and without "you're right".

`REGRESSED` is a finding introduced by a fix. It enters the list on a par with the others, but
is first checked with the ratchet rule from `references/triage.md`: most often the
right answer to it is to roll the fix back, not to build one more layer on top of it.

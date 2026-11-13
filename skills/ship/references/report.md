# ship: report

## Report

The user does not see the reviewer's output or the ledger, and sees the reasoning at best as a retelling. What
the reviewer found and what you are doing about it, they learn only from the text of the message. So every round,
discovery or verification, ends with a **round message**: right after triage and before the first
edit based on its findings. It is a progress report, not a question: write it and carry on, do not
wait for an answer. An answer has to be awaited only for an escalated line, as stated in triage (`references/triage.md`).

**Write every message to the user in the user's language**: the announcement, round messages, questions and
the final report, including table headings and outcome words. The wording below is the English form; translate
it, keep the structure and the limits.

The round message consists of three parts:

1. A bold header: the reviewer, what it looked at, how many findings and what you are doing with them.
2. A table `# | What is wrong | What I do`, a row for **every** finding of the round, with its ledger id in `#`.
   One phrase in plain words per cell. "What is wrong": up to 12 words on what will break and
   where it will show. "What I do": up to 8 words, an edit, "reject: the argument" or "escalate: what the
   question is about". The question itself for an "escalate" row goes under the table.
3. A line `Next: …`.

The table holds only the meaning; line numbers, priority labels, quotes, the thread and the base live in the
gate's ledger and its `last-review.txt`.

A verification in which everything is closed fits into a single header. Otherwise the header says
"closed N of M", the table has only the unclosed, REGRESSED and new findings, and "What is wrong" holds the
reviewer's objection. A discovery without findings is also a single header.

```
**Codex, code review: 2 findings. Fixing 1, rejecting 1**

| # | What is wrong | What I do |
|---|---|---|
| 1 | The report loses the first data row | reject: the header is skipped one line above, a test exists |
| 2 | An empty CSV crashes the script instead of giving an empty report | early exit, test red first |

Next: fix #2, then verification at codex.

**Codex, verification: closed 1 of 2**

| # | What is wrong | What I do |
|---|---|---|
| 2 | A file with only a header still crashes | check after reading the header |

Next: the fix, second verification.

**Codex, verification: all 2 closed.** The code gate is closed.
```

**The final report** brings the findings of all gates from the route registry, including the outcomes of the
handed-over SDD entries, into one table `Gate | What was wrong | How it ended`. Cells follow the same rules as
in the round message: "What was wrong" up to 12 words, "How it ended" up to 8 words, which is "fixed",
"rejected: the argument", "removed together with the layer" or "decided by the user: how". Under the table, in one
line: the reviewer with the model pin and effort, and the executor with its family and vendor: without this
rounds are not comparable with each other, and there is nothing to show the "reviewer ≠ executor" invariant with.

# ship: checks

## Checks

"Tests" — where they exist. Where there are none, the same role is played by an equivalent check: `sing-box check`,
`terraform validate`, `docker compose config`, `shellcheck`, `--dry-run`, a run of the script on live
input. The gate does not close without a run, and a run is not counted from memory
(the verification-before-completion skill).

A check that can be run is always cheaper than a review round: a `set -u` failure, empty input,
a nonexistent key are caught by a smoke run in seconds, and by the reviewer in 6 minutes. Before
handing a state to the gate, run whatever can be run.

**A check that guards exactly this change and can be made red must not be considered
a check until you have seen it red.**
Break what it guards, make sure it fails, restore it, make sure it goes green. The exception
named in `references/route.md` stays: for validators like `terraform validate` the failure condition is not controllable, they
pass both before the edit and after it, and this rule does not concern them.

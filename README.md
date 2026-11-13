# ship

[![CI](https://github.com/be1ski/ship/actions/workflows/test.yml/badge.svg)](https://github.com/be1ski/ship/actions/workflows/test.yml)

Cross-vendor review loop for Claude Code and Codex. One agent writes a spec, a plan and the code; the other vendor's agent reviews each step until it comes back clean.

## Install

Paste into Claude Code or Codex:

```
Install the ship plugin: follow https://github.com/be1ski/ship#readme
```

Or run the commands for your agent yourself. Both CLIs must be logged in; `git`, `python3` and `jq` must exist. Restart the session afterwards.

Claude Code:

```sh
claude plugin marketplace add anthropics/claude-plugins-official
claude plugin marketplace add be1ski/ship
claude plugin install ship@ship
```

Auto-update: set `"autoUpdate": true` on `extraKnownMarketplaces.ship` in `~/.claude/settings.json`.

Codex:

```sh
codex plugin marketplace add be1ski/ship
codex plugin add ship@ship
codex plugin add superpowers@openai-curated-remote
```

## Use

```
/ship add a --dry-run flag to scripts/deploy.sh    # Claude Code
$ship add CSV export to the reports page           # Codex
```

Small tasks go code → review → polish; features go spec → plan → code → polish, each step reviewed. A run starts with `Using ship: <route>, reviewer <adapter>`.

Features commit the spec and plan under `docs/superpowers/` and build in a git worktree; review logs stay in `.ship/`. ship never merges or pushes.

Review rounds take minutes and a feature takes hours, on both accounts' limits. ship stops only for spec approval and for scope or taste decisions.

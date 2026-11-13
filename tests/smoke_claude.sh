#!/usr/bin/env bash
# T1: validate the plugin, install it into an isolated Claude Code profile and assert it loads.
# Usage: bash tests/smoke_claude.sh [<plugin repo dir>]   (default: current directory)
# Needs network and git access to GitHub. The temporary profile is left in place.
set -euo pipefail

fail() { echo "smoke_claude: $*" >&2; exit 1; }

REPO="$(cd "${1:-.}" && pwd)"

# Options review_claude.py passes: an upstream rename must fail here, not in a user's review.
# `claude --help` exits 0 for unknown options, so the help text itself is matched: the option
# must open an option line, alone or after a short alias, so a mention in prose does not count.
HELP="$(claude --help)"
for flag in -p --safe-mode --tools --allowedTools --permission-mode --disable-slash-commands \
            --output-format --verbose --model --effort --session-id --resume; do
  grep -qE -- "^[[:space:]]*(-[A-Za-z], )?$flag([[:space:],=<[]|\$)" <<<"$HELP" \
    || fail "claude --help no longer lists $flag"
done
H="$(mktemp -d)"
export CLAUDE_CONFIG_DIR="$H"

# Not --strict: the manifests omit `version` on purpose (every commit is an update), so the
# "No version specified" warning is the one warning tolerated; errors fail via the exit code.
VALIDATE="$(claude plugin validate "$REPO" --json)" || { printf '%s\n' "$VALIDATE"; fail "claude plugin validate reported errors"; }
printf '%s' "$VALIDATE" \
  | jq -e '[.manifest, (.contents // [])[]] | map(.warnings[]) | all(.message | startswith("No version specified"))' \
  > /dev/null || { printf '%s\n' "$VALIDATE"; fail "claude plugin validate reported unexpected warnings"; }

# The superpowers dependency resolves only from a known marketplace.
claude plugin marketplace add anthropics/claude-plugins-official \
  || fail "adding anthropics/claude-plugins-official failed: this script needs network and git access to GitHub"
claude plugin marketplace add "$REPO"
claude plugin install ship@ship

LIST="$(claude plugin list --json)"
ENTRY="$(printf '%s' "$LIST" | jq '.[] | select(.id == "ship@ship")')"
[ -n "$ENTRY" ] || fail "ship@ship is missing from claude plugin list --json"
ROOT="$(printf '%s' "$ENTRY" | jq -r '.installPath // empty')"
if [ -z "$ROOT" ]; then
  set -- "$H"/plugins/cache/ship/ship/*/
  if [ "$#" -eq 1 ]; then ROOT="$1"; fi
fi
[ -n "$ROOT" ] && [ -d "$ROOT" ] || fail "no plugin root for ship@ship"

for skill in ship pragmatic-engineering; do
  [ -f "$ROOT/skills/$skill/SKILL.md" ] || fail "missing skills/$skill/SKILL.md under $ROOT"
done

# Load state: `enabled` and `errors` as named by `claude plugin list --json` in Claude Code 2.1.
printf '%s\n' "$ENTRY"
printf '%s' "$ENTRY" | jq -e 'has("enabled")' > /dev/null || fail "cannot determine load state"
printf '%s' "$ENTRY" | jq -e '.enabled == true and ((.errors // []) | length == 0)' > /dev/null \
  || fail "ship@ship is not loaded (entry above)"

SUPERPOWERS="$(printf '%s' "$LIST" | jq -r '.[] | select(.id | startswith("superpowers@")) | "\(.id) \(.version)"')"
[ -n "$SUPERPOWERS" ] || fail "no superpowers@ entry in claude plugin list --json: the dependency was not installed"

echo "superpowers: $SUPERPOWERS"
claude --version
echo "smoke_claude: OK"

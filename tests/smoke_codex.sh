#!/usr/bin/env bash
# C7: install the plugin into an isolated Codex profile and assert the skill catalogue.
# Usage: bash tests/smoke_codex.sh [<plugin repo dir>]   (default: current directory)
# SMOKE_EXTRA_SKILL_DIR: a skill directory copied into the isolated ~/.agents/skills first
# (negative control for the isolation assertion). The temporary home is left in place.
set -euo pipefail

REPO="$(cd "${1:-.}" && pwd)"

# Options adapter-reviewer-codex.md passes, per subcommand and as written there: an upstream
# rename must fail here, not in a user's review. The option must open an option line of
# --help, alone or after a short alias, so a mention in prose does not count.
require_flags() {
  local flags="$1" help flag; shift
  help="$("$@" --help)"
  for flag in $flags; do
    grep -qE -- "^[[:space:]]*(-[A-Za-z], )?$flag([[:space:],=<[]|\$)" <<<"$help" \
      || { echo "smoke_codex: '$*' no longer lists $flag" >&2; exit 1; }
  done
}
require_flags "-s -c --skip-git-repo-check --model --json -o" codex exec
require_flags "--model -c --json -o" codex exec review
require_flags "--skip-git-repo-check --model -c -o" codex exec resume
H="$(mktemp -d)"
# CODEX_HOME alone still reads ~/.agents/skills, so HOME is overridden too.
export HOME="$H"
export CODEX_HOME="$H/.codex"
mkdir -p "$CODEX_HOME"

if [ -n "${SMOKE_EXTRA_SKILL_DIR:-}" ]; then
  mkdir -p "$HOME/.agents/skills"
  cp -R "${SMOKE_EXTRA_SKILL_DIR%/}" "$HOME/.agents/skills/"
fi

codex plugin marketplace add "$REPO"
codex plugin add ship@ship
codex debug prompt-input hi > "$H/prompt.txt"

# The catalogue lines sit inside JSON strings with escaped newlines: decode before matching.
python3 - "$H/prompt.txt" <<'PY'
import json
import re
import sys


def strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from strings(value)


raw = open(sys.argv[1], encoding="utf-8").read()
try:
    text = "\n".join(strings(json.loads(raw)))
except ValueError:
    text = raw
for name, pattern, present in [("ship:ship", r"^- ship:ship: ", True),
                               ("ship:pragmatic-engineering", r"^- ship:pragmatic-engineering: ", True),
                               ("no plain ship entry", r"^- ship: ", False)]:
    if bool(re.search(pattern, text, re.MULTILINE)) != present:
        sys.exit("smoke_codex: assertion failed: " + name)
PY

ls "$CODEX_HOME"/plugins/cache/ship/ship/*/skills/ship/SKILL.md \
   "$CODEX_HOME"/plugins/cache/ship/ship/*/skills/pragmatic-engineering/SKILL.md
codex --version
echo "smoke_codex: OK"

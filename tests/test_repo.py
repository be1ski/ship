"""Check the repository tree: manifests, skill sizes, references, denylist."""

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFESTS = [".claude-plugin/plugin.json", ".claude-plugin/marketplace.json",
             ".codex-plugin/plugin.json", ".agents/plugins/marketplace.json"]
MARKETPLACES = [".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"]
SKILLS = ["skills/ship/SKILL.md", "skills/pragmatic-engineering/SKILL.md"]
REFERENCES = "skills/ship/references"
LINE_LIMIT = 500
BYTE_LIMIT = 20000

# Names under references/ that another tool resolves, each with the sentence that shows it.
EXTERNAL_REFERENCES = {
    # adapter-orca.md: "Read `failedStage` in the receipt and act per
    # `ORCA skills get orchestration --reference references/recovery-and-cleanup.md`."
    "recovery-and-cleanup.md",
}
# Bare backticked names of files the skill creates at run time.
RUNTIME_ARTIFACTS = {
    "gates.md",
    "ledger.md",
    # adapter-reviewer-claude-code.md, of the gate scratch: "It holds `round-prompt.md`, `ledger.md`,
    # `reviewer.json`, `thread-id`, `last-review.txt` and the raw responses."
    "round-prompt.md",
}

REFERENCE = re.compile(r"references/([a-z0-9-]+\.md)")
BARE = re.compile(r"`([a-z0-9-]+\.md)`")
DENYLIST = re.compile(r"~/\.agents/skills/ship|be1ski"
                      r"|claude-(?:opus|sonnet|haiku|fable)-[0-9]|gpt-[0-9]")


def has_version(node):
    if isinstance(node, dict):
        return "version" in node or any(has_version(v) for v in node.values())
    if isinstance(node, list):
        return any(has_version(v) for v in node)
    return False


class RepoTest(unittest.TestCase):
    def test_manifests_are_named_ship_and_have_no_version(self):
        problems = []
        for rel in MANIFESTS:
            try:
                data = json.loads((ROOT / rel).read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                problems.append("%s: invalid JSON (%s)" % (rel, error))
                continue
            name = data.get("name") if isinstance(data, dict) else None
            if name != "ship":
                problems.append("%s: name is %r, expected 'ship'" % (rel, name))
            if has_version(data):
                problems.append('%s: has a "version" key' % rel)
            if rel in MARKETPLACES:
                plugins = data.get("plugins") if isinstance(data, dict) else None
                if not (isinstance(plugins, list) and len(plugins) == 1 and isinstance(plugins[0], dict)
                        and plugins[0].get("name") == "ship"):
                    problems.append("%s: plugins must be exactly one entry named 'ship'" % rel)
        self.assertEqual(problems, [])

    def test_skill_cores_fit_the_size_limit(self):
        problems = []
        for rel in SKILLS:
            data = (ROOT / rel).read_bytes()
            lines = len(data.splitlines())
            if lines >= LINE_LIMIT:
                problems.append("%s: %d lines, limit is under %d" % (rel, lines, LINE_LIMIT))
            if len(data) >= BYTE_LIMIT:
                problems.append("%s: %d bytes, limit is under %d" % (rel, len(data), BYTE_LIMIT))
        self.assertEqual(problems, [])

    def test_references_resolve_and_none_is_orphaned(self):
        refs = ROOT / REFERENCES
        files = sorted(path for path in refs.glob("*") if path.is_file())
        problems, texts = [], {}
        for path in [ROOT / SKILLS[0]] + files:
            rel = path.relative_to(ROOT).as_posix()
            try:
                texts[path] = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as error:
                problems.append("%s: not valid UTF-8 at byte %d" % (rel, error.start))
                continue
            for number, line in enumerate(texts[path].splitlines(), 1):
                for name in REFERENCE.findall(line):
                    if not (refs / name).is_file() and name not in EXTERNAL_REFERENCES:
                        problems.append("%s:%d: references/%s does not exist" % (rel, number, name))
                for name in BARE.findall(line):
                    if not (refs / name).is_file() and name not in RUNTIME_ARTIFACTS:
                        problems.append("%s:%d: `%s` is neither a reference file nor a run-time artifact"
                                        % (rel, number, name))
        for path in files:
            tokens = ("references/" + path.name, "`%s`" % path.name)
            if not any(token in text for other, text in texts.items() if other != path for token in tokens):
                problems.append("%s: named by no other scanned file" % path.relative_to(ROOT).as_posix())
        self.assertEqual(problems, [])

    def test_skills_have_no_model_ids_or_author_paths(self):
        problems = []
        for path in sorted((ROOT / "skills").rglob("*")):
            # __pycache__ is git-ignored and its .pyc files embed the local absolute path.
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(ROOT).as_posix()
            text = path.read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), 1):
                for match in DENYLIST.finditer(line):
                    problems.append("%s:%d: %s" % (rel, number, match.group(0)))
        self.assertEqual(problems, [])

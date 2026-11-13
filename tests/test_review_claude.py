"""Exercise the runner boundary without invoking Claude or the network."""

import contextlib
import fcntl
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parent.parent / "skills" / "ship" / "scripts" / "review_claude.py"


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), "the review runner must exist")
        spec = importlib.util.spec_from_file_location("review_claude", SCRIPT)
        self.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.cwd = self.root / "repo"
        self.cwd.mkdir()
        self.scratch = self.root / "gate"
        self.prompt = self.root / "prompt.txt"
        self.prompt.write_text("Review the selected file.\n", encoding="utf-8")

    def invoke(self, mode="discover", payload=None, returncode=0,
               assistant_models=("claude-reviewer-a",),
               init_model="claude-reviewer-a[1m]", during_run=None, **changes):
        args = [mode, "--cwd", str(self.cwd), "--scratch", str(self.scratch),
                "--prompt", str(self.prompt)]
        if mode == "discover":
            args += ["--model", "claude-reviewer-a[1m]", "--effort", "xhigh",
                     "--claude", sys.executable]
        self.calls = []

        def fake_claude(command, **kwargs):
            self.calls.append((command, kwargs))
            if during_run is not None:
                during_run(kwargs)
            session_flag = "--session-id" if mode == "discover" else "--resume"
            session = command[command.index(session_flag) + 1]
            response = {
                "type": "result", "subtype": "success", "is_error": False,
                "session_id": session, "modelUsage": {"claude-reviewer-a": {}},
                "result": "REVIEWED: file.py\nVERDICT: " + (
                    "NO FINDINGS" if mode == "discover" else "ALL RESOLVED"),
                "permission_denials": [],
            }
            response.update(changes)
            events = [{"type": "system", "subtype": "init", "model": init_model,
                       "session_id": session}]
            events.extend({"type": "assistant", "session_id": session,
                           "message": {"role": "assistant", "model": model,
                                       "content": [{"type": "text", "text": "Reviewing."}]}}
                          for model in assistant_models)
            events.append(response)
            raw = payload if payload is not None else "\n".join(json.dumps(event) for event in events) + "\n"
            kwargs["stdout"].write(raw)
            kwargs["stderr"].write("fixture diagnostic\n")
            return subprocess.CompletedProcess(command, returncode)

        output, errors = io.StringIO(), io.StringIO()
        with patch.object(self.runner.subprocess, "run", fake_claude):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = self.runner.main(args)
        self.output, self.errors = output.getvalue(), errors.getvalue()
        return status

    def state(self):
        return json.loads((self.scratch / "reviewer.json").read_text())

    def argv(self, session_flag, session):
        """The whole command: any flag added or dropped must fail a test."""
        return [str(Path(sys.executable).resolve()), "-p", "--safe-mode",
                "--tools", "Read,Glob,Grep", "--allowedTools", "Read,Glob,Grep",
                "--permission-mode", "dontAsk", "--disable-slash-commands",
                "--output-format", "stream-json", "--verbose",
                "--model", "claude-reviewer-a[1m]", "--effort", "xhigh", session_flag, session]

    def test_discovery_pins_identity_and_exposes_only_read_tools(self):
        self.assertEqual(self.invoke(), 0, self.errors)
        state = self.state()
        self.assertEqual(state["vendor"], "Anthropic")
        self.assertEqual(state["family"], "Claude")
        self.assertEqual(state["model"], "claude-reviewer-a[1m]")
        self.assertEqual(state["effort"], "xhigh")
        self.assertEqual(state["cwd"], str(self.cwd))
        self.assertEqual(state["cli"], str(Path(sys.executable).resolve()))
        self.assertEqual(state["actual_models"], ["claude-reviewer-a"])
        self.assertEqual(state["usage_models"], ["claude-reviewer-a"])
        self.assertEqual((self.scratch / "thread-id").read_text().strip(), state["session_id"])
        self.assertEqual((self.scratch / "last-review.txt").read_text(), self.output)
        command, kwargs = self.calls[0]
        self.assertEqual(command, self.argv("--session-id", state["session_id"]))
        self.assertNotIn("shell", kwargs)
        self.assertNotIn("timeout", kwargs)
        self.assertEqual(kwargs["input"], self.prompt.read_text())
        self.assertEqual(kwargs["cwd"], str(self.cwd))
        self.assertTrue((self.scratch / "round-0001" / "stdout.json").is_file())
        self.assertTrue((self.scratch / "round-0001" / "stderr.log").is_file())

    def test_verification_resumes_exact_session_and_retains_pin(self):
        self.assertEqual(self.invoke(), 0, self.errors)
        initial = self.state()
        self.assertEqual(self.invoke("verify"), 0, self.errors)
        self.assertEqual(self.calls[0][0], self.argv("--resume", initial["session_id"]))
        self.assertEqual(self.state(), initial)
        self.assertTrue((self.scratch / "round-0002" / "stdout.json").is_file())

    def test_findings_and_unresolved_items_are_valid_runs(self):
        self.assertEqual(self.invoke(result="A defect.\nVERDICT: FINDINGS"), 0, self.errors)
        self.assertEqual(self.invoke("verify", result="A — NOT RESOLVED\nVERDICT: OPEN ITEMS REMAIN"), 0, self.errors)

    def test_invalid_outputs_fail_and_preserve_successful_review(self):
        self.assertEqual(self.invoke(), 0, self.errors)
        original_state = (self.scratch / "reviewer.json").read_bytes()
        original_review = (self.scratch / "last-review.txt").read_bytes()
        failures = [
            {"payload": "not JSON"}, {"payload": "[]"},
            {"payload": '{"type":"result"}'},
            {"is_error": True}, {"subtype": "error_max_turns"},
            {"result": ""}, {"result": "All resolved"},
            {"result": "VERDICT: NO FINDINGS"},
            {"result": "VERDICT: ALL RESOLVED\ntrailing commentary"},
            {"permission_denials": [{"tool_name": "Read"}]},
            {"permission_denials": None},
            {"session_id": "00000000-0000-0000-0000-000000000000"},
            {"modelUsage": {"claude-other-b": {}}},
            {"modelUsage": {}}, {"modelUsage": None},
            {"assistant_models": []}, {"assistant_models": [None]},
            {"assistant_models": ["claude-reviewer-a", "claude-other-b"]},
            {"init_model": "claude-other-b"},
            {"returncode": 1},
        ]
        for fixture in failures:
            with self.subTest(fixture=fixture):
                self.assertNotEqual(self.invoke("verify", **fixture), 0)
                self.assertEqual((self.scratch / "reviewer.json").read_bytes(), original_state)
                self.assertEqual((self.scratch / "last-review.txt").read_bytes(), original_review)
                self.assertIn("FAILED", self.errors)

    def test_failed_discovery_cannot_be_mistaken_for_a_completed_discovery(self):
        self.assertNotEqual(self.invoke(is_error=True, subtype="error_during_execution"), 0)
        raw = json.loads((self.scratch / "round-0001" / "stdout.json").read_text().splitlines()[-1])
        self.assertTrue(raw["session_id"])
        self.assertFalse((self.scratch / "reviewer.json").exists())
        self.assertFalse((self.scratch / "last-review.txt").exists())
        self.assertNotEqual(self.invoke("verify"), 0)
        self.assertEqual(self.calls, [])

    def test_discovery_interrupted_while_saving_cannot_be_resumed(self):
        real_write = self.runner.atomic_write
        for name in ("thread-id", "last-review.txt"):
            with self.subTest(failed_write=name):
                self.scratch = self.root / ("gate-" + name)

                def failing_write(path, text, name=name):
                    if path.name == name:
                        raise OSError("disk full")
                    real_write(path, text)

                with patch.object(self.runner, "atomic_write", failing_write):
                    self.assertNotEqual(self.invoke(), 0)
                self.assertFalse((self.scratch / "reviewer.json").exists())
                self.assertNotEqual(self.invoke("verify"), 0)
                self.assertEqual(self.calls, [])

    def test_failure_reports_the_reason_claude_gave(self):
        self.assertNotEqual(self.invoke(assistant_models=["<synthetic>"], is_error=True,
                                        result="You've hit your session limit"), 0)
        self.assertIn("session limit", self.errors)
        self.scratch = self.root / "gate-2"
        self.assertNotEqual(self.invoke(payload="error: unknown option", returncode=7), 0)
        self.assertIn("unknown option", self.errors)
        self.assertIn("exit code 7", self.errors)

    def test_discovery_refuses_to_reuse_a_gate(self):
        self.assertEqual(self.invoke(), 0, self.errors)
        self.assertNotEqual(self.invoke(), 0)
        self.assertEqual(self.calls, [])

    def test_discovery_preserves_unrelated_scratch_contents(self):
        self.scratch.mkdir()
        unrelated = self.scratch / "notes.txt"
        unrelated.write_text("keep me")
        self.assertEqual(self.invoke(), 0, self.errors)
        self.assertEqual(unrelated.read_text(), "keep me")

    def test_discovery_refuses_collisions_with_managed_outputs(self):
        self.scratch.mkdir()
        collision = self.scratch / "round-0001"
        collision.mkdir()
        self.assertNotEqual(self.invoke(), 0)
        self.assertTrue(collision.is_dir())
        self.assertEqual(self.calls, [])

    def test_prompt_may_be_prepared_inside_an_otherwise_empty_gate(self):
        self.scratch.mkdir()
        self.prompt = self.scratch / "prompt.txt"
        self.prompt.write_text("Review file.py.")
        self.assertEqual(self.invoke(), 0, self.errors)
        self.assertEqual(self.prompt.read_text(), "Review file.py.")

    def test_verification_refuses_changed_cwd(self):
        self.assertEqual(self.invoke(), 0, self.errors)
        self.cwd = self.root
        self.assertNotEqual(self.invoke("verify"), 0)
        self.assertEqual(self.calls, [])

    def test_discovery_rejects_wrong_actual_model(self):
        self.assertNotEqual(self.invoke(assistant_models=["claude-other-b"]), 0)
        self.assertFalse((self.scratch / "last-review.txt").exists())

    def test_auxiliary_model_usage_does_not_replace_answering_model(self):
        usage = {"claude-reviewer-a": {}, "claude-helper-c": {}}
        self.assertEqual(self.invoke(modelUsage=usage), 0, self.errors)
        self.assertEqual(self.state()["actual_models"], ["claude-reviewer-a"])
        self.assertEqual(self.state()["usage_models"], ["claude-helper-c", "claude-reviewer-a"])
        self.assertEqual(self.invoke("verify"), 0, self.errors)
        record = json.loads((self.scratch / "round-0002" / "run.json").read_text())
        self.assertEqual(record["usage_models"], ["claude-reviewer-a"])

    def test_discovery_creates_nested_scratch_directory(self):
        self.scratch = self.cwd / ".ship" / "code-01"
        self.assertEqual(self.invoke(), 0, self.errors)
        self.assertTrue((self.scratch / "reviewer.json").is_file())

    def test_discovery_refuses_unavailable_claude_executable(self):
        with patch.object(self.runner.shutil, "which", return_value=None):
            self.assertNotEqual(self.invoke(), 0)
        self.assertEqual(self.calls, [])

    def test_inactive_lock_file_does_not_block_verification(self):
        self.assertEqual(self.invoke(), 0, self.errors)
        lock = self.scratch / ".lock"
        lock.write_text("old process has exited\n")
        inode = lock.stat().st_ino
        self.assertEqual(self.invoke("verify"), 0, self.errors)
        self.assertEqual(lock.stat().st_ino, inode)

    def test_active_kernel_lock_blocks_until_released(self):
        self.assertEqual(self.invoke(), 0, self.errors)
        with (self.scratch / ".lock").open("a+") as active:
            fcntl.flock(active, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertNotEqual(self.invoke("verify"), 0)
            self.assertIn("active", self.errors)
            self.assertEqual(self.calls, [])
        self.assertEqual(self.invoke("verify"), 0, self.errors)

    def test_child_inherits_lock_until_it_exits(self):
        children = []

        def spawn_holder(kwargs):
            descriptors = kwargs.get("pass_fds", ())
            self.assertEqual(len(descriptors), 1, "Claude must inherit the gate lock")
            descriptor = descriptors[0]
            self.assertEqual(os.fstat(descriptor).st_ino, (self.scratch / ".lock").stat().st_ino)
            child = subprocess.Popen(
                [sys.executable, "-B", "-c", "import os,sys; os.fstat(int(sys.argv[1])); "
                 "print('ready', flush=True); sys.stdin.read()", str(descriptor)],
                pass_fds=descriptors, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            children.append(child)
            self.assertEqual(child.stdout.readline(), "ready\n")

        try:
            self.assertEqual(self.invoke(during_run=spawn_holder), 0, self.errors)
            # The runner closed its descriptor; its still-running child owns the lock.
            self.assertNotEqual(self.invoke("verify"), 0)
            self.assertIn("active", self.errors)
            self.assertEqual(self.calls, [])
        finally:
            for child in children:
                child.communicate(timeout=5)
        self.assertEqual(children[0].returncode, 0)
        self.assertEqual(self.invoke("verify"), 0, self.errors)


if __name__ == "__main__":
    unittest.main()

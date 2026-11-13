#!/usr/bin/env python3
"""Run a read-only Claude review and resume its pinned session for verification.

Exit 0 means the response is valid, including FINDINGS / OPEN ITEMS REMAIN.
The calling agent, not this runner, decides whether a gate is clean.
Requires POSIX advisory file locks (macOS/Linux).
"""

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid


EFFORTS = ("low", "medium", "high", "xhigh", "max")
OWNER = "ship-claude-review-v1"
MANAGED_NAMES = {"reviewer.json", "thread-id", "last-review.txt", ".lock"}


def absolute_path(value):
    path = Path(value)
    if not path.is_absolute():
        raise argparse.ArgumentTypeError("must be an absolute path")
    return path


def atomic_write(path, text):
    """Replace only a runner-owned file, without exposing a partial state."""
    if path.is_symlink():
        raise ValueError(f"refusing symlink: {path}")
    descriptor, temporary = tempfile.mkstemp(prefix=".ship-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_state(scratch, state):
    atomic_write(scratch / "thread-id", state["session_id"] + "\n")
    # Last: verify accepts a gate by this file, so it must mean a fully saved discovery.
    atomic_write(scratch / "reviewer.json", json.dumps(state, indent=2) + "\n")


def normalized_model(model):
    return re.sub(r"\[[0-9]+[mk]\]$", "", model)


def prepare(args):
    cwd = args.cwd.resolve(strict=True)
    if not cwd.is_dir():
        raise ValueError("cwd must be a directory")
    if args.scratch.is_symlink():
        raise ValueError("scratch must not be a symlink")
    scratch = args.scratch.resolve()
    if scratch == cwd or scratch in cwd.parents or scratch == Path.home().resolve():
        raise ValueError("scratch must be a dedicated directory, not cwd or an ancestor")
    prompt_path = args.prompt.resolve(strict=True)
    prompt = prompt_path.read_text(encoding="utf-8")
    if not prompt.strip():
        raise ValueError("prompt must not be empty")
    if args.mode == "discover":
        if not args.model.startswith("claude-") or any(c.isspace() for c in args.model):
            raise ValueError("model must be an explicit Claude model ID, not an alias")
        executable = shutil.which(args.claude)
        if executable is None:
            raise ValueError(f"Claude executable is unavailable: {args.claude}")
        cli = str(Path(executable).resolve(strict=True))
        if scratch.exists():
            if not scratch.is_dir() or any(
                entry.name in MANAGED_NAMES or re.fullmatch(r"round-[0-9]+", entry.name)
                for entry in scratch.iterdir()
            ):
                raise ValueError("discovery requires a fresh gate with no existing runner outputs")
        else:
            scratch.mkdir(mode=0o700, parents=True)
        state = {
            "owner": OWNER, "vendor": "Anthropic", "family": "Claude",
            "model": args.model, "effort": args.effort, "cwd": str(cwd),
            "session_id": str(uuid.uuid4()), "actual_models": [], "cli": cli,
        }
    else:
        state_path = scratch / "reviewer.json"
        if state_path.is_symlink():
            raise ValueError("reviewer state must not be a symlink")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("owner") != OWNER:
            raise ValueError("scratch does not contain this runner's state")
        if state.get("vendor") != "Anthropic" or state.get("family") != "Claude":
            raise ValueError("reviewer identity changed")
        if state.get("cwd") != str(cwd):
            raise ValueError("cwd differs from the pinned review directory")
        cli = Path(state["cli"])
        if not cli.is_absolute() or not cli.is_file() or not os.access(cli, os.X_OK):
            raise ValueError(f"pinned Claude executable is unavailable: {cli}")
        if not isinstance(state.get("model"), str) or not state["model"].startswith("claude-"):
            raise ValueError("invalid pinned Claude model")
        if state.get("effort") not in EFFORTS:
            raise ValueError("invalid pinned effort")
        uuid.UUID(state["session_id"])
        models = state.get("actual_models")
        if not isinstance(models, list) or (
            models and models != [normalized_model(state["model"])]
        ):
            raise ValueError("invalid pinned actual model")
    return cwd, scratch, prompt, state


def parse_stream(raw, state):
    try:
        events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except ValueError:
        raise ValueError("Claude stdout is not a JSON event stream: %r" % raw.strip()[:200]) from None
    if not events or any(not isinstance(event, dict) for event in events):
        raise ValueError("Claude returned an invalid JSON event stream")
    results = [index for index, event in enumerate(events) if event.get("type") == "result"]
    if results != [len(events) - 1]:
        raise ValueError("Claude did not return exactly one terminal result")
    # Before the model checks: a usage limit or an expired login answers with a synthetic
    # model, and would otherwise be reported as a model mismatch.
    final = events[-1]
    if final.get("subtype") != "success" or final.get("is_error") is not False:
        reason = str(final.get("result") or final.get("subtype"))[:300]
        raise ValueError(f"Claude reported a failed run: {reason}")
    models = set()
    expected = normalized_model(state["model"])
    for event in events:
        if "session_id" in event and event["session_id"] != state["session_id"]:
            raise ValueError("Claude stream belongs to a different session")
        if event.get("type") == "system" and event.get("subtype") == "init":
            model = event.get("model")
            if not isinstance(model, str) or normalized_model(model) != expected:
                raise ValueError("Claude initialized a different model")
        if event.get("type") == "assistant":
            message = event.get("message")
            model = message.get("model") if isinstance(message, dict) else None
            if not isinstance(model, str) or not model:
                raise ValueError("assistant event omits its actual model")
            models.add(normalized_model(model))
    if sorted(models) != [expected]:
        raise ValueError("assistant model is missing or differs from the requested model")
    if state["actual_models"] and sorted(models) != state["actual_models"]:
        raise ValueError("actual assistant model drifted from the pinned reviewer")
    return events[-1], sorted(models)


def validate(response, state, mode, returncode):
    if not isinstance(response, dict) or response.get("type") != "result":
        raise ValueError("Claude did not return one terminal result object")
    if response.get("session_id") != state["session_id"]:
        raise ValueError("Claude returned a different or missing session ID")
    if returncode != 0 or response.get("subtype") != "success" or response.get("is_error") is not False:
        raise ValueError("Claude reported a failed run")
    if response.get("permission_denials") != []:
        raise ValueError("Claude reported permission denials or omitted their status")
    usage = response.get("modelUsage")
    if not isinstance(usage, dict) or normalized_model(state["model"]) not in {
        normalized_model(model) for model in usage
    }:
        raise ValueError("modelUsage is missing or omits the answering model")
    result = response.get("result")
    verdicts = ("NO FINDINGS", "FINDINGS") if mode == "discover" else ("ALL RESOLVED", "OPEN ITEMS REMAIN")
    if not isinstance(result, str) or not result.strip() or result.rstrip().splitlines()[-1] not in {
        "VERDICT: " + verdict for verdict in verdicts
    }:
        raise ValueError("missing or malformed final verdict for this review phase")
    return result, sorted(usage)


def run_review(args):
    cwd, scratch, prompt, state = prepare(args)
    lock = scratch / ".lock"
    lock_stream = lock.open("a+")
    try:
        try:
            fcntl.flock(lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError(f"another review is active in {scratch}") from None
        for number in range(1, 1000000):
            round_dir = scratch / f"round-{number:04d}"
            try:
                round_dir.mkdir(mode=0o700)
                break
            except FileExistsError:
                continue
        else:
            raise ValueError("too many review rounds in this gate")
        (round_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        command = [
            state["cli"], "-p", "--safe-mode", "--tools", "Read,Glob,Grep",
            "--allowedTools", "Read,Glob,Grep", "--permission-mode", "dontAsk",
            "--disable-slash-commands", "--output-format", "stream-json", "--verbose",
            "--model", state["model"], "--effort", state["effort"],
            "--session-id" if args.mode == "discover" else "--resume", state["session_id"],
        ]
        record = {"mode": args.mode, "cwd": str(cwd), "command": command}
        try:
            with (round_dir / "stdout.json").open("x", encoding="utf-8") as raw:
                with (round_dir / "stderr.log").open("x", encoding="utf-8") as log:
                    completed = subprocess.run(
                        command, cwd=str(cwd), input=prompt, text=True, stdout=raw, stderr=log,
                        # An orphan Claude must retain the lock if this runner is killed.
                        pass_fds=(lock_stream.fileno(),),
                    )
            record["returncode"] = completed.returncode
            response, models = parse_stream(
                (round_dir / "stdout.json").read_text(encoding="utf-8"), state
            )
            result, usage_models = validate(response, state, args.mode, completed.returncode)
            record["actual_models"] = models
            record["usage_models"] = usage_models
            atomic_write(scratch / "last-review.txt", result.rstrip() + "\n")
            if not state["actual_models"]:
                state["actual_models"] = models
                state["usage_models"] = usage_models
                write_state(scratch, state)
            record["status"] = "valid"
            print(result.rstrip())
            return 0
        except (OSError, ValueError, KeyError, TypeError) as error:
            record["status"] = "failed"
            record["error"] = str(error)
            code = record.get("returncode")
            exited = f" (claude exit code {code})" if code else ""
            print(f"FAILED: {error}{exited}; inspect {round_dir}", file=sys.stderr)
            return 1
        finally:
            try:
                (round_dir / "run.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            except OSError as error:
                # A diagnostic file must not replace the result of the round itself.
                print(f"could not write {round_dir}/run.json: {error}", file=sys.stderr)
    finally:
        # Keep the inode: unlinking allows concurrent locks on different files.
        lock_stream.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    for mode in ("discover", "verify"):
        command = commands.add_parser(mode)
        command.add_argument("--cwd", type=absolute_path, required=True)
        command.add_argument("--scratch", type=absolute_path, required=True)
        command.add_argument("--prompt", type=Path, required=True)
        if mode == "discover":
            command.add_argument("--claude", default="claude", help="Claude executable name or path")
            command.add_argument("--model", required=True)
            command.add_argument("--effort", choices=EFFORTS, required=True)
    args = parser.parse_args(argv)
    try:
        return run_review(args)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"FAILED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

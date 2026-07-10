"""Regression tests for two hook runtime bugs.

Bug 1 (guard-bash.sh): the .env secret-read guard required whitespace immediately
before `.env`, so every directory-prefixed path — backend/.env, frontend/.env,
./.env, ~/.env — slipped through unblocked. Those are exactly the paths this
project keeps real secrets in (see .gitignore), so the guard had a hole where the
secrets actually live.

Bug 2 (format-changed.sh): this Stop hook re-invokes auto-format.sh per changed
file by piping a `{"tool_input":{"file_path":...}}` JSON on stdin. But it runs with
HOOK_INPUT_JSON already set to the Stop event, and auto-format.sh prefers that env
var over stdin — so the inherited value made every inner call a silent no-op and
Bash-written files (migrations, codegen, scaffolding) were never formatted.

Both hooks are shipped in both runtimes (CLAUDE.md requires them mirrored), so every
case runs against .claude and .codex.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")
RUFF = shutil.which("ruff")

pytestmark = pytest.mark.skipif(
    BASH is None, reason="bash is required to run the hook scripts"
)

RUNTIME_DIRS = [".claude", ".codex"]


def run_guard_bash(runtime_dir: str, command: str) -> dict | None:
    # HOOK_INPUT_JSON must not leak in from the caller's environment; the guard reads
    # stdin only when it is unset.
    env = {k: v for k, v in os.environ.items() if k != "HOOK_INPUT_JSON"}
    proc = subprocess.run(
        [BASH, str(ROOT / runtime_dir / "hooks" / "guard-bash.sh")],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    out = proc.stdout.strip()
    return json.loads(out) if out else None


def is_denied(result: dict | None) -> bool:
    return (
        bool(result)
        and result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
    )


# --- Bug 1: directory-prefixed .env reads must be blocked -------------------------

# The real secret locations for this project, plus the shapes the old space-only
# boundary let through.
BLOCKED_ENV_READS = [
    "cat .env",
    "cat backend/.env",
    "cat frontend/.env",
    "head -5 frontend/.env",
    "less backend/.env",
    "grep SECRET_KEY backend/.env",
    "sed -n 1p ./.env",
    "cat ~/.env",
    "cat /etc/app/.env.local",
]

# Must stay allowed: the tracked secret-free template and ordinary non-secret reads
# (guarding against an over-broad fix that blocks legitimate work).
ALLOWED_READS = [
    "cat .env.example",
    "cat backend/.env.example",
    "cat README.md",
    "grep TODO backend/src/main.py",
    "echo environment ready",
    "sed -n 1p notes.txt",
]


@pytest.mark.parametrize("runtime_dir", RUNTIME_DIRS)
@pytest.mark.parametrize("command", BLOCKED_ENV_READS)
def test_directory_prefixed_env_reads_are_blocked(
    runtime_dir: str, command: str
) -> None:
    result = run_guard_bash(runtime_dir, command)
    assert is_denied(result), (
        f"[{runtime_dir}] reading a secret .env file should be denied: {command!r} -> {result}"
    )


@pytest.mark.parametrize("runtime_dir", RUNTIME_DIRS)
@pytest.mark.parametrize("command", ALLOWED_READS)
def test_env_guard_does_not_overblock(runtime_dir: str, command: str) -> None:
    result = run_guard_bash(runtime_dir, command)
    assert not is_denied(result), (
        f"[{runtime_dir}] a non-secret read must stay allowed: {command!r} -> {result}"
    )


# --- Bug 2: format-changed.sh must actually format Bash-written files -------------


@pytest.mark.skipif(
    RUFF is None, reason="ruff is the .py formatter auto-format.sh invokes"
)
@pytest.mark.parametrize("runtime_dir", RUNTIME_DIRS)
def test_format_changed_formats_bash_written_file_under_stop_env(
    runtime_dir: str, tmp_path: Path
) -> None:
    hooks_src = ROOT / runtime_dir / "hooks"
    hooks_dst = tmp_path / runtime_dir / "hooks"
    hooks_dst.mkdir(parents=True)
    for name in ("format-changed.sh", "auto-format.sh", "hook-json.sh"):
        shutil.copy(hooks_src / name, hooks_dst / name)

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    unformatted = "x=1\ny =2\n"
    target = tmp_path / "mig.py"
    target.write_text(unformatted, encoding="utf-8")

    project_dir_env = (
        "CLAUDE_PROJECT_DIR" if runtime_dir == ".claude" else "CODEX_PROJECT_DIR"
    )
    env = dict(os.environ)
    env[project_dir_env] = str(tmp_path)
    # The exact condition that broke the hook: a Stop event already in HOOK_INPUT_JSON,
    # which has no tool_input.file_path. The fix clears it before the inner call.
    stop_event = (
        '{"hook_event_name":"Stop","stop_hook_active":false,"transcript_path":"/x"}'
    )
    env["HOOK_INPUT_JSON"] = stop_event

    subprocess.run(
        [BASH, str(hooks_dst / "format-changed.sh")],
        input=stop_event,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert target.read_text(encoding="utf-8") != unformatted, (
        f"[{runtime_dir}] format-changed.sh left the Bash-written file unformatted; the inner "
        "auto-format.sh call was a no-op (HOOK_INPUT_JSON inheritance regression)"
    )

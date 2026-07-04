from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="bash is required to run the hook scripts")

# Both runtimes ship their own copy of these hooks (CLAUDE.md requires them to stay
# mirrored); a fix applied to one and not the other is exactly the kind of drift this
# suite should catch, so every case runs against both.
RUNTIME_DIRS = [".claude", ".codex"]


def run_hook(runtime_dir: str, hook: str, payload: dict) -> dict | None:
    proc = subprocess.run(
        [BASH, str(ROOT / runtime_dir / "hooks" / hook)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    out = proc.stdout.strip()
    return json.loads(out) if out else None


def is_denied(result: dict | None) -> bool:
    return bool(result) and result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


# Every payload is exercised with both a forward-slash and a Windows-style backslash
# file_path. A hook that only recognizes forward slashes silently mismatches every
# backslash path — reversing its own deny logic depending on how it's called.
WAITLIST_SLICE_FWD = "C:/Users/dev/repo/memory/feature/waitlist-signup/slice.md"
WAITLIST_SLICE_BS = "C:\\Users\\dev\\repo\\memory\\feature\\waitlist-signup\\slice.md"
BACKEND_FILE_FWD = "C:/Users/dev/repo/backend/src/main.py"
BACKEND_FILE_BS = "C:\\Users\\dev\\repo\\backend\\src\\main.py"


@pytest.mark.parametrize("runtime_dir", RUNTIME_DIRS)
@pytest.mark.parametrize("slice_path", [WAITLIST_SLICE_FWD, WAITLIST_SLICE_BS])
def test_qa_may_write_slice_verdict_regardless_of_separator(runtime_dir: str, slice_path: str) -> None:
    result = run_hook(
        runtime_dir,
        "guard-edits.sh",
        {"tool_input": {"file_path": slice_path}, "agent_type": "qa-checker"},
    )
    assert not is_denied(result), f"[{runtime_dir}] QA writing slice.md was denied for {slice_path!r}: {result}"


@pytest.mark.parametrize("runtime_dir", RUNTIME_DIRS)
@pytest.mark.parametrize("backend_path", [BACKEND_FILE_FWD, BACKEND_FILE_BS])
def test_qa_is_still_denied_outside_its_write_scope(runtime_dir: str, backend_path: str) -> None:
    result = run_hook(
        runtime_dir,
        "guard-edits.sh",
        {"tool_input": {"file_path": backend_path}, "agent_type": "qa-checker"},
    )
    assert is_denied(result), f"[{runtime_dir}] QA writing {backend_path!r} should have been denied: {result}"


@pytest.mark.parametrize("runtime_dir", RUNTIME_DIRS)
def test_implementer_is_denied_reading_agent_infra_regardless_of_separator(runtime_dir: str) -> None:
    infra_fwd = f"C:/Users/dev/repo/{runtime_dir}/hooks/guard-edits.sh"
    infra_bs = f"C:\\Users\\dev\\repo\\{runtime_dir}\\hooks\\guard-edits.sh"
    for infra_path in (infra_fwd, infra_bs):
        result = run_hook(
            runtime_dir,
            "guard-infra-read.sh",
            {"tool_input": {"file_path": infra_path}, "agent_type": "backend-developer"},
        )
        assert is_denied(result), (
            f"[{runtime_dir}] backend-developer reading {infra_path!r} should have been denied: {result}"
        )

"""Regression test for notify-attention.sh's dead agent_type skip.

The launcher (run-hook.py) delivers the hook event via the HOOK_INPUT_JSON env var and
leaves the child hook's stdin at EOF. notify-attention.sh used to read the event only via
`cat` (stdin), so under the launcher INPUT_PEEK was always empty and the "skip when the
event is attributed to a subagent" check never fired. Every other input-consuming hook reads
HOOK_INPUT_JSON first; this one now does too.

The test drives the hook the way the launcher does — event in HOOK_INPUT_JSON, stdin empty —
with a fake `notify-send` on PATH so we can observe whether the desktop notification was
attempted. Linux-only, since that is the branch of notify-attention.sh that shells out to
notify-send.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")

pytestmark = [
    pytest.mark.skipif(BASH is None, reason="bash is required to run the hook scripts"),
    pytest.mark.skipif(
        platform.system() != "Linux",
        reason="test observes the Linux notify-send branch of notify-attention.sh",
    ),
]

RUNTIME_DIRS = [".claude", ".codex"]


def _run(runtime_dir: str, hook_input_json: str, tmp_path: Path) -> bool:
    """Run notify-attention.sh the way the launcher does (event in HOOK_INPUT_JSON, empty
    stdin) with a fake notify-send on PATH. Returns True if the notification was attempted."""
    marker = tmp_path / "notified"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(exist_ok=True)
    fake_notify = fake_bin / "notify-send"
    fake_notify.write_text(f'#!/usr/bin/env bash\ntouch "{marker}"\n', encoding="utf-8")
    fake_notify.chmod(0o755)

    env = {
        "PATH": f"{fake_bin}:/usr/bin:/bin",
        "HOOK_INPUT_JSON": hook_input_json,
    }
    subprocess.run(
        [BASH, str(ROOT / runtime_dir / "hooks" / "notify-attention.sh")],
        input="",  # launcher leaves child stdin empty; the event is only in the env var
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return marker.exists()


@pytest.mark.parametrize("runtime_dir", RUNTIME_DIRS)
def test_subagent_attributed_event_is_suppressed(
    runtime_dir: str, tmp_path: Path
) -> None:
    notified = _run(
        runtime_dir,
        '{"hook_event_name":"Notification","agent_type":"backend-developer"}',
        tmp_path,
    )
    assert not notified, (
        f"[{runtime_dir}] a subagent-attributed Notification should be suppressed, but "
        "notify-send was invoked (agent_type skip is not reading HOOK_INPUT_JSON)"
    )


@pytest.mark.parametrize("runtime_dir", RUNTIME_DIRS)
def test_main_thread_event_still_fires(runtime_dir: str, tmp_path: Path) -> None:
    notified = _run(
        runtime_dir,
        '{"hook_event_name":"Notification"}',
        tmp_path,
    )
    assert notified, (
        f"[{runtime_dir}] a main-thread Notification (no agent_type) should still fire the "
        "desktop notification"
    )

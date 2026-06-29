from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.checks.hook_registration import default_runner, validate_hook_registration


def write_hook_fixture(tmp_path: Path, *, include_guard_mcp: bool = True) -> None:
    for runtime in [".claude", ".codex"]:
        hook_dir = tmp_path / runtime / "hooks"
        hook_dir.mkdir(parents=True)
        for hook in [
            "guard-edits.sh",
            "guard-infra-read.sh",
            "guard-mcp.sh",
            "verify-subagent.sh",
            "auto-format.sh",
            "format-changed.sh",
            "compaction-watch.sh",
            "workflow-watch.sh",
            "notify-stop.sh",
        ]:
            (hook_dir / hook).write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    claude_hooks = [
        "guard-edits.sh",
        "guard-infra-read.sh",
        "verify-subagent.sh",
        "auto-format.sh",
        "format-changed.sh",
        "compaction-watch.sh",
        "workflow-watch.sh",
        "notify-stop.sh",
    ]
    if include_guard_mcp:
        claude_hooks.append("guard-mcp.sh")
    claude_pretool_hooks = []
    if include_guard_mcp:
        claude_pretool_hooks.append(
            {
                "type": "command",
                "command": "python .claude/hooks/run-hook.py .claude/hooks/guard-mcp.sh",
            }
        )
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "mcp__fullstack-guidelines__.*",
                            "hooks": claude_pretool_hooks,
                        }
                    ],
                    "SubagentStop": [
                        {
                            "matcher": "backend-developer|frontend-developer",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": " ".join(f".claude/hooks/{hook}" for hook in claude_hooks),
                                }
                            ],
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / ".codex" / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "mcp__fullstack_guidelines__.*",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": " ".join(
                                        f".codex/hooks/{hook}"
                                        for hook in [
                                            "guard-edits.sh",
                                            "guard-infra-read.sh",
                                            "guard-mcp.sh",
                                            "verify-subagent.sh",
                                            "auto-format.sh",
                                            "format-changed.sh",
                                            "compaction-watch.sh",
                                            "workflow-watch.sh",
                                            "notify-stop.sh",
                                        ]
                                    ),
                                }
                            ],
                        }
                    ],
                    "SubagentStop": [{"matcher": "backend-developer|frontend-developer", "hooks": []}],
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / ".codex" / "config.toml").write_text(
        "hooks = true\n[mcp_servers.fullstack-guidelines]\nenabled = true\n",
        encoding="utf-8",
    )


def test_valid_hook_registration_passes_without_smoke(tmp_path: Path) -> None:
    write_hook_fixture(tmp_path)

    assert validate_hook_registration(tmp_path, smoke=False) == []


def test_missing_hook_registration_is_reported(tmp_path: Path) -> None:
    write_hook_fixture(tmp_path, include_guard_mcp=False)

    findings = validate_hook_registration(tmp_path, smoke=False)

    assert any("missing hook registration for guard-mcp.sh" in f.message for f in findings)


def test_default_smoke_runner_does_not_leak_hook_input_env(monkeypatch) -> None:
    monkeypatch.setenv("HOOK_INPUT_JSON", '{"stop_hook_active": false}')

    result = default_runner(
        [sys.executable, "-c", "import os, sys; sys.exit(0 if 'HOOK_INPUT_JSON' not in os.environ else 1)"],
        "{}",
    )

    assert result.returncode == 0


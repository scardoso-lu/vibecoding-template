from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.services.harness import validate_harness


def _write(path: Path, text: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    else:
        path.chmod(0o644)


def _settings(base: str, matcher: str) -> str:
    return json.dumps(
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": matcher,
                        "hooks": [
                            {
                                "command": f"python {base}/hooks/run-hook.py {base}/hooks/guard-bash.sh"
                            }
                        ],
                    }
                ]
            }
        }
    )


def make_harness(root: Path) -> None:
    """A minimal, fully-consistent two-runtime harness that should validate clean."""
    _write(
        root / ".claude/settings.json",
        _settings(".claude", "mcp__fullstack-guidelines__.*"),
    )
    _write(
        root / ".codex/hooks.json", _settings(".codex", "mcp__fullstack_guidelines__.*")
    )
    for base in (".claude", ".codex"):
        _write(
            root / base / "hooks/guard-bash.sh",
            "#!/usr/bin/env bash\nexit 0\n",
            executable=True,
        )
    _write(root / ".claude/agents/planner.md", "planner\n")
    _write(root / ".codex/agents/planner.toml", "name = 'planner'\n")
    _write(
        root / ".codex/config.toml",
        "hooks = true\n\n[mcp_servers.fullstack-guidelines]\nenabled = true\n",
    )


def test_clean_harness_passes(tmp_path: Path) -> None:
    make_harness(tmp_path)
    assert validate_harness(tmp_path) == []


def test_non_executable_registered_hook_is_reported(tmp_path: Path) -> None:
    make_harness(tmp_path)
    (tmp_path / ".codex/hooks/guard-bash.sh").chmod(0o644)

    findings = validate_harness(tmp_path)

    assert any(
        f.path == ".codex/hooks/guard-bash.sh" and "not executable" in f.message
        for f in findings
    )


def test_missing_registered_hook_script_is_reported(tmp_path: Path) -> None:
    make_harness(tmp_path)
    (tmp_path / ".claude/hooks/guard-bash.sh").unlink()

    findings = validate_harness(tmp_path)

    assert any(
        f.path == ".claude/hooks/guard-bash.sh" and "missing" in f.message
        for f in findings
    )


def test_registration_parity_is_enforced(tmp_path: Path) -> None:
    make_harness(tmp_path)
    # Register an extra hook for Claude only.
    _write(
        tmp_path / ".claude/hooks/guard-mcp.sh",
        "#!/usr/bin/env bash\nexit 0\n",
        executable=True,
    )
    _write(
        tmp_path / ".codex/hooks/guard-mcp.sh",
        "#!/usr/bin/env bash\nexit 0\n",
        executable=True,
    )
    settings = json.loads((tmp_path / ".claude/settings.json").read_text())
    settings["hooks"]["PreToolUse"].append(
        {
            "matcher": "X",
            "hooks": [
                {
                    "command": "python .claude/hooks/run-hook.py .claude/hooks/guard-mcp.sh"
                }
            ],
        }
    )
    (tmp_path / ".claude/settings.json").write_text(
        json.dumps(settings), encoding="utf-8"
    )

    findings = validate_harness(tmp_path)

    assert any("registered for Claude but not Codex" in f.message for f in findings)


def test_hook_file_set_parity_is_enforced(tmp_path: Path) -> None:
    make_harness(tmp_path)
    _write(
        tmp_path / ".claude/hooks/extra-helper.sh",
        "#!/usr/bin/env bash\n",
        executable=True,
    )

    findings = validate_harness(tmp_path)

    assert any(
        f.path == ".codex/hooks/extra-helper.sh" and "missing from Codex" in f.message
        for f in findings
    )


def test_agent_set_parity_is_enforced(tmp_path: Path) -> None:
    make_harness(tmp_path)
    _write(tmp_path / ".claude/agents/challenger.md", "challenger\n")

    findings = validate_harness(tmp_path)

    assert any(
        f.path == ".codex/agents/challenger.toml"
        and "missing Codex mirror" in f.message
        for f in findings
    )


def test_missing_mcp_matcher_is_reported(tmp_path: Path) -> None:
    make_harness(tmp_path)
    _write(tmp_path / ".codex/hooks.json", _settings(".codex", "SomeOtherMatcher"))

    findings = validate_harness(tmp_path)

    assert any("missing guidelines MCP matcher" in f.message for f in findings)


def test_codex_config_must_enable_hooks_and_mcp(tmp_path: Path) -> None:
    make_harness(tmp_path)
    (tmp_path / ".codex/config.toml").write_text("hooks = false\n", encoding="utf-8")

    findings = validate_harness(tmp_path)

    messages = "\n".join(f.message for f in findings)
    assert "hooks feature is not enabled" in messages
    assert "fullstack-guidelines MCP server is not enabled" in messages

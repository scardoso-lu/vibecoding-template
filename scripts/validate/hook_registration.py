from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Callable, Sequence

from scripts.validate.common import Finding, hook_commands, hook_matchers, read_text

Runner = Callable[[Sequence[str], str], subprocess.CompletedProcess[str]]

EXPECTED_HOOKS = [
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


Runner = Callable[[Sequence[str], str], subprocess.CompletedProcess[str]]


def default_runner(command: Sequence[str], stdin: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("HOOK_INPUT_JSON", None)
    return subprocess.run(command, input=stdin, capture_output=True, text=True, check=False, env=env)


def validate_hook_registration(root: Path, *, smoke: bool = True, runner: Runner = default_runner) -> list[Finding]:
    findings: list[Finding] = []
    configs = [
        (".claude/settings.json", ".claude/hooks", "mcp__fullstack-guidelines__.*"),
        (".codex/hooks.json", ".codex/hooks", "mcp__fullstack_guidelines__.*"),
    ]
    for config_rel, hook_dir_rel, mcp_matcher in configs:
        config_path = root / config_rel
        hook_dir = root / hook_dir_rel
        if not config_path.exists():
            findings.append(Finding(config_rel, "missing hook config"))
            continue
        try:
            config = json.loads(read_text(config_path))
        except json.JSONDecodeError as exc:
            findings.append(Finding(config_rel, f"invalid JSON: {exc}"))
            continue
        commands = hook_commands(config)
        matchers = hook_matchers(config)
        for hook in EXPECTED_HOOKS:
            if not (hook_dir / hook).exists():
                findings.append(Finding(f"{hook_dir_rel}/{hook}", "missing expected hook file"))
            if hook not in " ".join(commands):
                findings.append(Finding(config_rel, f"missing hook registration for {hook}"))
        if mcp_matcher not in matchers:
            findings.append(Finding(config_rel, f"missing MCP matcher {mcp_matcher}"))
        if not any("backend-developer|frontend-developer" in matcher for matcher in matchers):
            findings.append(Finding(config_rel, "missing developer SubagentStop matcher"))

    codex_config = root / ".codex/config.toml"
    if codex_config.exists():
        text = read_text(codex_config)
        if "hooks = true" not in text:
            findings.append(Finding(".codex/config.toml", "hooks feature is not enabled"))
        if "[mcp_servers.fullstack-guidelines]" not in text or "enabled = true" not in text:
            findings.append(Finding(".codex/config.toml", "fullstack-guidelines MCP server is not enabled"))
    else:
        findings.append(Finding(".codex/config.toml", "missing Codex config"))

    if smoke and not findings:
        smoke_cases = [
            (
                ["python", ".claude/hooks/run-hook.py", ".claude/hooks/guard-edits.sh"],
                '{"agent_type":"qa","tool_input":{"file_path":"frontend/e2e/new-story.spec.ts"}}',
                False,
                "QA frontend/e2e write should be allowed",
            ),
            (
                ["python", ".claude/hooks/run-hook.py", ".claude/hooks/guard-edits.sh"],
                '{"agent_type":"qa","tool_input":{"file_path":"frontend/src/x.ts"}}',
                True,
                "QA app-code write should be denied",
            ),
            (
                ["python", ".claude/hooks/run-hook.py", ".claude/hooks/guard-mcp.sh"],
                '{"agent_type":"qa"}',
                True,
                "QA MCP call should be denied",
            ),
        ]
        old_cwd = Path.cwd()
        try:
            os.chdir(root)
            for command, stdin, should_deny, message in smoke_cases:
                result = runner(command, stdin)
                denied = '"permissionDecision":"deny"' in result.stdout or '"permissionDecision": "deny"' in result.stdout
                if result.returncode != 0:
                    findings.append(Finding("hook-smoke", f"{message}: command exited {result.returncode}"))
                elif denied != should_deny:
                    findings.append(Finding("hook-smoke", f"{message}: expected denied={should_deny}, got {denied}"))
        finally:
            os.chdir(old_cwd)
    return findings



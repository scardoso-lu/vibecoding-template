#!/usr/bin/env python3
"""Harness parity and integrity validator.

Enforces that the two runtime harnesses (`.claude` and `.codex`) stay correctly
wired and in sync:

- every hook script the runtime registers (`run-hook.py <script>`) exists and is
  executable, so the launcher's `exec` can actually run it;
- both runtimes register the same set of hooks;
- both runtimes ship the same hook files and the same agent set;
- the guidelines MCP matcher is present in both configs;
- the Codex config enables hooks and the guidelines MCP server.

Sourced helpers (`hook-json.sh`) and the Python launcher (`run-hook.py`) are not
`exec`-ed, so they are exempt from the executable-bit check.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from scripts.validate.models import (
    Finding,
    hook_commands,
    hook_matchers,
    read_text,
)

# (name, base dir, hook config, MCP matcher expected in that config)
RUNTIMES = [
    ("claude", ".claude", ".claude/settings.json", "mcp__fullstack-guidelines__.*"),
    ("codex", ".codex", ".codex/hooks.json", "mcp__fullstack_guidelines__.*"),
]


def _registered_hook_paths(commands: list[str]) -> set[str]:
    """Relative paths of hook scripts the runtime `exec`s via run-hook.py."""
    paths: set[str] = set()
    for command in commands:
        for match in re.finditer(r"run-hook\.py\s+(\S+\.sh)", command):
            paths.add(match.group(1).replace("\\", "/"))
    return paths


def _load_config(path: Path) -> tuple[object | None, str | None]:
    try:
        return json.loads(read_text(path)), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def validate_harness(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    registered_basenames: dict[str, set[str]] = {}

    for name, base, config_rel, mcp_matcher in RUNTIMES:
        config_path = root / config_rel
        hooks_dir = root / base / "hooks"
        if not config_path.exists():
            findings.append(Finding(config_rel, "missing hook config"))
            registered_basenames[name] = set()
            continue
        config, error = _load_config(config_path)
        if error is not None:
            findings.append(Finding(config_rel, f"invalid JSON: {error}"))
            registered_basenames[name] = set()
            continue

        registered = _registered_hook_paths(hook_commands(config))
        registered_basenames[name] = {Path(rel).name for rel in registered}

        for rel in sorted(registered):
            script = root / rel
            script_rel = (
                script.relative_to(root).as_posix() if script.is_absolute() else rel
            )
            if not script.exists():
                findings.append(
                    Finding(script_rel, "registered hook script is missing")
                )
            elif not os.access(script, os.X_OK):
                findings.append(
                    Finding(
                        script_rel,
                        "registered hook script is not executable; run-hook.py cannot exec it (chmod +x)",
                    )
                )

        if mcp_matcher not in hook_matchers(config):
            findings.append(
                Finding(config_rel, f"missing guidelines MCP matcher {mcp_matcher}")
            )

    # Registration parity: both runtimes must register the same hook set.
    claude_reg = registered_basenames.get("claude", set())
    codex_reg = registered_basenames.get("codex", set())
    for hook in sorted(claude_reg - codex_reg):
        findings.append(
            Finding(
                ".codex/hooks.json",
                f"hook '{hook}' registered for Claude but not Codex",
            )
        )
    for hook in sorted(codex_reg - claude_reg):
        findings.append(
            Finding(
                ".claude/settings.json",
                f"hook '{hook}' registered for Codex but not Claude",
            )
        )

    # Hook file-set parity: both hook directories must ship the same files.
    claude_hook_files = {
        p.name for p in (root / ".claude/hooks").glob("*") if p.is_file()
    }
    codex_hook_files = {
        p.name for p in (root / ".codex/hooks").glob("*") if p.is_file()
    }
    for hook in sorted(claude_hook_files - codex_hook_files):
        findings.append(
            Finding(
                f".codex/hooks/{hook}",
                "hook file present for Claude but missing from Codex",
            )
        )
    for hook in sorted(codex_hook_files - claude_hook_files):
        findings.append(
            Finding(
                f".claude/hooks/{hook}",
                "hook file present for Codex but missing from Claude",
            )
        )

    # Agent-set parity: every Claude agent has a Codex mirror and vice versa.
    claude_agents = {p.stem for p in (root / ".claude/agents").glob("*.md")}
    codex_agents = {p.stem for p in (root / ".codex/agents").glob("*.toml")}
    for agent in sorted(claude_agents - codex_agents):
        findings.append(
            Finding(
                f".codex/agents/{agent}.toml",
                "agent defined for Claude but missing Codex mirror",
            )
        )
    for agent in sorted(codex_agents - claude_agents):
        findings.append(
            Finding(
                f".claude/agents/{agent}.md",
                "agent defined for Codex but missing Claude mirror",
            )
        )

    # Codex config sanity: hooks + guidelines MCP must be enabled.
    codex_config = root / ".codex/config.toml"
    if codex_config.exists():
        text = read_text(codex_config)
        if "hooks = true" not in text:
            findings.append(
                Finding(
                    ".codex/config.toml", "hooks feature is not enabled (hooks = true)"
                )
            )
        if (
            "[mcp_servers.fullstack-guidelines]" not in text
            or "enabled = true" not in text
        ):
            findings.append(
                Finding(
                    ".codex/config.toml",
                    "fullstack-guidelines MCP server is not enabled",
                )
            )
    elif (root / ".claude").exists():
        findings.append(Finding(".codex/config.toml", "missing Codex config"))

    return findings


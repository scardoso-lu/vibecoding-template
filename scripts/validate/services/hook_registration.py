from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Callable, Sequence

from scripts.validate.models import Finding, hook_commands, hook_matchers, read_text

Runner = Callable[[Sequence[str], str], subprocess.CompletedProcess[str]]

EXPECTED_HOOKS = [
    "guard-edits.sh",
    "guard-infra-read.sh",
    "guard-mcp.sh",
    "verify-subagent.sh",
    "verify-qa.sh",
    "auto-format.sh",
    "format-changed.sh",
    "guard-harness.sh",
    "notify-stop.sh",
]

EXPECTED_PROMPT_MATCHERS = [
    "product-owner|business-challenger",
    "software-architect|technical-challenger",
    "qa-challenger",
]

EXPECTED_START_PROMPT_MATCHERS = [
    "backend-developer|frontend-developer",
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
        hooks_config = config.get("hooks", {}) if isinstance(config, dict) else {}
        subagent_start_entries = hooks_config.get("SubagentStart", []) if isinstance(hooks_config, dict) else []
        for prompt_matcher in EXPECTED_START_PROMPT_MATCHERS:
            matching_entries = [
                entry
                for entry in subagent_start_entries
                if isinstance(entry, dict) and entry.get("matcher") == prompt_matcher
            ]
            if not matching_entries:
                findings.append(Finding(config_rel, f"missing start prompt matcher {prompt_matcher}"))
                continue
            if not any(
                isinstance(hook, dict) and hook.get("type") == "prompt"
                for entry in matching_entries
                for hook in entry.get("hooks", [])
            ):
                findings.append(Finding(config_rel, f"missing start prompt hook for {prompt_matcher}"))

        subagent_entries = hooks_config.get("SubagentStop", []) if isinstance(hooks_config, dict) else []
        for prompt_matcher in EXPECTED_PROMPT_MATCHERS:
            matching_entries = [
                entry
                for entry in subagent_entries
                if isinstance(entry, dict) and entry.get("matcher") == prompt_matcher
            ]
            if not matching_entries:
                findings.append(Finding(config_rel, f"missing planning prompt matcher {prompt_matcher}"))
                continue
            if not any(
                isinstance(hook, dict) and hook.get("type") == "prompt"
                for entry in matching_entries
                for hook in entry.get("hooks", [])
            ):
                findings.append(Finding(config_rel, f"missing prompt hook for {prompt_matcher}"))

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
                '{"agent_type":"qa-checker","tool_input":{"file_path":"frontend/e2e/new-story.spec.ts"}}',
                False,
                "qa-checker frontend/e2e write should be allowed",
            ),
            (
                ["python", ".claude/hooks/run-hook.py", ".claude/hooks/guard-edits.sh"],
                '{"agent_type":"qa-checker","tool_input":{"file_path":"frontend/src/x.ts"}}',
                True,
                "qa-checker app-code write should be denied",
            ),
            (
                ["python", ".claude/hooks/run-hook.py", ".claude/hooks/guard-mcp.sh"],
                '{"agent_type":"qa-checker"}',
                True,
                "qa-checker MCP call should be denied",
            ),
            (
                ["python", ".claude/hooks/run-hook.py", ".claude/hooks/guard-edits.sh"],
                '{"agent_type":"qa-challenger","tool_input":{"file_path":"memory/feature/example/slice.md"}}',
                True,
                "qa-challenger slice.md write should be denied (read-only)",
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




def find_bash() -> str | None:
    import shutil

    candidates: list[str] = []
    env_bash = os.environ.get("GIT_BASH")
    if env_bash:
        candidates.append(env_bash)
    candidates.extend(
        [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files\Git\usr\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\usr\bin\bash.exe",
        ]
    )
    path_bash = shutil.which("bash")
    if path_bash:
        candidates.append(path_bash)
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return None


def _compile_python(path: Path) -> str | None:
    try:
        compile(read_text(path), str(path), "exec")
    except SyntaxError as exc:
        return f"{exc.msg} at line {exc.lineno}"
    return None


def validate_hook_syntax(root: Path) -> list[Finding]:
    """JSON config validity, launcher compile check, and bash -n on hook scripts."""
    findings: list[Finding] = []
    for rel in [".codex/hooks.json", ".claude/settings.json"]:
        path = root / rel
        if not path.exists():
            findings.append(Finding(rel, "missing hook config"))
            continue
        try:
            json.loads(read_text(path))
        except json.JSONDecodeError as exc:
            findings.append(Finding(rel, f"invalid JSON: {exc}"))

    for rel in [".codex/hooks/run-hook.py", ".claude/hooks/run-hook.py"]:
        if not (root / rel).exists():
            findings.append(Finding(rel, "missing hook launcher"))
            continue
        error = _compile_python(root / rel)
        if error is not None:
            findings.append(Finding(rel, f"python compile failed: {error}"))

    hook_scripts = sorted((root / ".codex/hooks").glob("*.sh")) + sorted(
        (root / ".claude/hooks").glob("*.sh")
    )
    bash = find_bash()
    if bash is None:
        if hook_scripts:
            findings.append(Finding("doctor", "bash not found; skipped hook shell syntax checks"))
        return findings
    for script in hook_scripts:
        rel = script.relative_to(root).as_posix()
        result = subprocess.run([bash, "-n", rel], cwd=root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            findings.append(
                Finding(rel, f"bash syntax check failed: {result.stderr.strip() or result.stdout.strip() or 'no output'}")
            )
    return findings

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.checks.common import Finding, repo_root_from
from scripts.validate.checks.hook_registration import validate_hook_registration
from scripts.validate.checks.workflow import run_validators


def run(command: list[str], *, cwd: Path) -> tuple[int, str, str]:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def find_bash() -> str | None:
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
        path = Path(candidate)
        if path.exists():
            return str(path)
    return None


def compile_python(path: Path) -> str | None:
    try:
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
    except SyntaxError as exc:
        return f"{exc.msg} at line {exc.lineno}"
    return None


def validate_hook_syntax(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    bash = find_bash()

    for rel in [".codex/hooks.json", ".claude/settings.json"]:
        path = root / rel
        if not path.exists():
            findings.append(Finding(rel, "missing hook config"))
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            findings.append(Finding(rel, f"invalid JSON: {exc}"))

    for rel in [".codex/hooks/run-hook.py", ".claude/hooks/run-hook.py"]:
        if not (root / rel).exists():
            findings.append(Finding(rel, "missing hook launcher"))
            continue
        error = compile_python(root / rel)
        if error is not None:
            findings.append(Finding(rel, f"python compile failed: {error}"))

    hook_scripts = sorted((root / ".codex/hooks").glob("*.sh")) + sorted((root / ".claude/hooks").glob("*.sh"))
    if bash is None:
        if hook_scripts:
            findings.append(Finding("doctor", "bash not found; skipped hook shell syntax checks"))
        return findings
    for script in hook_scripts:
        rel = script.relative_to(root).as_posix()
        code, stdout, stderr = run([bash, "-n", rel], cwd=root)
        if code != 0:
            findings.append(Finding(rel, f"bash syntax check failed: {stderr or stdout or 'no output'}"))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=repo_root_from())
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--skip-hook-smoke", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    workflow_results = run_validators(root)
    findings = validate_hook_syntax(root)
    findings.extend(validate_hook_registration(root, smoke=not args.skip_hook_smoke))

    if args.json_output:
        print(
            json.dumps(
                {
                    **{name: [finding.__dict__ for finding in result] for name, result in workflow_results.items()},
                    "doctor": [finding.__dict__ for finding in findings],
                },
                indent=2,
            )
        )
    else:
        for validator_name, result in workflow_results.items():
            if result:
                print(f"{validator_name}: {len(result)} finding(s)")
                for finding in result:
                    print(f"  {finding.format()}")
            else:
                print(f"{validator_name}: ok")
        if findings:
            print(f"doctor: {len(findings)} finding(s)")
            for finding in findings:
                print(f"  {finding.format()}")
        else:
            print("doctor: ok")

    return 1 if any(workflow_results.values()) or findings else 0


if __name__ == "__main__":
    raise SystemExit(main())


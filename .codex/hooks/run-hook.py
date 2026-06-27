#!/usr/bin/env python3
"""Cross-platform launcher for repo hook scripts.

Codex hook commands start here, then this script finds a usable Bash and execs
the requested .sh hook with the hook event JSON available as HOOK_INPUT_JSON.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    for key in ("CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        value = os.environ.get(key)
        if value:
            return Path(value).resolve()

    launcher_root = Path(__file__).resolve().parents[2]
    if (launcher_root / ".codex").is_dir() or (launcher_root / ".git").exists():
        return launcher_root

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(result.stdout.strip()).resolve()
    except Exception:
        return Path.cwd().resolve()


def is_usable_bash(path: str | None) -> bool:
    if not path:
        return False

    lowered = path.lower().replace("/", "\\")
    if lowered.endswith("\\windows\\system32\\bash.exe"):
        return False
    if lowered.endswith("\\microsoft\\windowsapps\\bash.exe"):
        return False

    try:
        result = subprocess.run(
            [path, "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False

    return result.returncode == 0 and "GNU bash" in (result.stdout + result.stderr)


def add_candidate(candidates: list[str], value: str | None) -> None:
    if value and value not in candidates:
        candidates.append(value)


def bash_candidates() -> list[str]:
    candidates: list[str] = []
    add_candidate(candidates, os.environ.get("GIT_BASH"))

    found = shutil.which("bash")
    add_candidate(candidates, found)

    if os.name == "nt":
        try:
            result = subprocess.run(
                ["git", "--exec-path"],
                check=True,
                capture_output=True,
                text=True,
            )
            git_root = (Path(result.stdout.strip()) / "../../..").resolve()
            add_candidate(candidates, str(git_root / "bin" / "bash.exe"))
            add_candidate(candidates, str(git_root / "usr" / "bin" / "bash.exe"))
        except Exception:
            pass

        roots = [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("LOCALAPPDATA")
            and str(Path(os.environ["LOCALAPPDATA"]) / "Programs"),
            os.environ.get("ChocolateyInstall")
            and str(Path(os.environ["ChocolateyInstall"]) / "lib" / "git" / "tools" / "git"),
            str(Path.home() / "scoop" / "apps" / "git" / "current"),
            r"C:\msys64",
        ]
        for root in roots:
            if not root:
                continue
            add_candidate(candidates, str(Path(root) / "Git" / "bin" / "bash.exe"))
            add_candidate(candidates, str(Path(root) / "Git" / "usr" / "bin" / "bash.exe"))
            add_candidate(candidates, str(Path(root) / "bin" / "bash.exe"))
            add_candidate(candidates, str(Path(root) / "usr" / "bin" / "bash.exe"))

    return candidates


def resolve_bash() -> str:
    for candidate in bash_candidates():
        if is_usable_bash(candidate):
            return candidate
    raise SystemExit(
        "Could not find a usable Bash. Install Git for Windows, install bash, "
        "or set GIT_BASH to bash.exe."
    )


def add_bash_tool_path(bash_path: str, env: dict[str, str]) -> None:
    if os.name != "nt":
        return

    bash_dir = Path(bash_path).resolve().parent
    git_root = bash_dir.parent
    if git_root.name == "usr":
        git_root = git_root.parent

    paths = [
        bash_dir,
        git_root / "usr" / "bin",
        git_root / "mingw64" / "bin",
        git_root / "bin",
    ]
    existing = [str(path) for path in paths if path.exists()]
    env["PATH"] = os.pathsep.join(existing + [env.get("PATH", "")])


def to_bash_path(path: Path) -> str:
    value = str(path.resolve())
    if os.name == "nt" and len(value) >= 3 and value[1:3] == ":\\":
        drive = value[0].lower()
        rest = value[3:].replace("\\", "/")
        return f"/{drive}/{rest}"
    return value.replace("\\", "/")


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run-hook.py <hook-script.sh>", file=sys.stderr)
        return 64

    root = repo_root()
    script = Path(sys.argv[1])
    if not script.is_absolute():
        script = root / script
    script = script.resolve()
    if not script.exists():
        print(f"Hook script not found: {script}", file=sys.stderr)
        return 0

    env = os.environ.copy()
    env.setdefault("CODEX_PROJECT_DIR", str(root))
    stdin = sys.stdin.read()
    if stdin and "HOOK_INPUT_JSON" not in env:
        env["HOOK_INPUT_JSON"] = stdin

    try:
        bash = resolve_bash()
        add_bash_tool_path(bash, env)
        command = f"exec {shell_quote(to_bash_path(script))}"
        return subprocess.run([bash, "-lc", command], env=env, check=False).returncode
    except Exception as exc:
        print(f"Hook launcher failed open: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

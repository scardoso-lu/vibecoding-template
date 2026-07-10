from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.validate.repository import app_code_state
from scripts.validate.services.gate import run_gate
from scripts.validate.services.verification import (
    parse_verification_rows,
    validate_verification,
)

BASH = shutil.which("bash")
GIT = shutil.which("git")


def write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def messages(findings) -> str:
    return "\n".join(finding.format() for finding in findings)


def slice_text(verification: str, coverage_status: str = "done") -> str:
    return f"""## Status
- State: active
## Acceptance Criteria
- [ ] AC-001: signup works
- [ ] AC-002: signup page renders
## Test Coverage
| Criteria | Test Type | Test Location | Status |
|---|---|---|---|
| AC-001 | backend | `backend/test/test_signup.py` | {coverage_status} |
| AC-002 | frontend-unit | `frontend/src/signup/page.test.tsx` | {coverage_status} |
{verification}
"""


# --- grammar / parsing ---------------------------------------------------


def test_parser_reads_command_covers_and_skip_rows() -> None:
    rows = parse_verification_rows(
        """## Verification
- Run: cd backend && uv run pytest test/test_signup.py -q | covers: AC-001, AC-002
- Run: none [skip-verify: docs-only] | covers: AC-003
"""
    )
    assert rows[0].command == "cd backend && uv run pytest test/test_signup.py -q"
    assert rows[0].covers == {"AC-001", "AC-002"}
    assert not rows[0].skip
    assert rows[1].skip and rows[1].skip_reason == "docs-only"
    assert rows[1].covers == {"AC-003"}


def test_missing_section_and_empty_section_are_findings(tmp_path: Path) -> None:
    write(tmp_path / "memory/feature/a/slice.md", slice_text(""))
    write(
        tmp_path / "memory/feature/b/slice.md",
        slice_text("## Verification\nprose without any rows\n"),
    )

    msgs = messages(validate_verification(tmp_path))

    assert "missing required section ## Verification" in msgs
    assert "must contain at least one `- Run:` row" in msgs


def test_malformed_rows_are_findings(tmp_path: Path) -> None:
    write(
        tmp_path / "memory/feature/a/slice.md",
        slice_text(
            """## Verification
- Run:  | covers: AC-001
- Run: none [skip-verify: ] | covers: AC-002
- Run: pytest backend/test/test_signup.py [skip-verify: but also a command]
"""
        ),
    )

    msgs = messages(validate_verification(tmp_path))

    assert "Run row has no command" in msgs
    assert "skip-verify token must carry a reason" in msgs
    assert "either a command or an explicit skip" in msgs


def test_covers_must_span_every_criterion_and_reject_unknown_ids(
    tmp_path: Path,
) -> None:
    write(
        tmp_path / "memory/feature/a/slice.md",
        slice_text(
            """## Verification
- Run: cd backend && uv run pytest test/test_signup.py -q | covers: AC-001, AC-999
"""
        ),
    )

    msgs = messages(validate_verification(tmp_path))

    assert "covers unknown acceptance criterion AC-999" in msgs
    assert "AC-002 is not covered by any ## Verification Run row" in msgs


def test_vacuous_command_is_rejected_and_suffix_naming_passes(tmp_path: Path) -> None:
    # `Run: true` is formally valid but names no mapped test file - the exact
    # talk-around this contract exists to kill.
    write(
        tmp_path / "memory/feature/a/slice.md",
        slice_text(
            """## Verification
- Run: true | covers: AC-001, AC-002
"""
        ),
    )
    vacuous = messages(validate_verification(tmp_path))
    assert "does not name any test file mapped to its covered criteria" in vacuous

    # A path suffix (`test/test_signup.py`) or full path both satisfy the rule.
    write(
        tmp_path / "memory/feature/a/slice.md",
        slice_text(
            """## Verification
- Run: cd backend && uv run pytest test/test_signup.py -q | covers: AC-001
- Run: npx pnpm --dir frontend test frontend/src/signup/page.test.tsx | covers: AC-002
"""
        ),
    )
    assert "does not name any test file" not in messages(
        validate_verification(tmp_path)
    )


def test_not_started_coverage_rows_exempt_the_path_naming_rule(tmp_path: Path) -> None:
    write(
        tmp_path / "memory/feature/a/slice.md",
        slice_text(
            """## Verification
- Run: echo placeholder until staged dependency lands | covers: AC-001, AC-002
""",
            coverage_status="not-started",
        ),
    )

    assert "does not name any test file" not in messages(
        validate_verification(tmp_path)
    )


def test_focused_playwright_command_must_be_nonempty_and_match_a_run_row(
    tmp_path: Path,
) -> None:
    base = """## Verification
- Run: cd backend && uv run pytest test/test_signup.py -q | covers: AC-001, AC-002

## QA Handoff
- Playwright story tests required: yes
- Focused Playwright command:{focused}
"""
    write(
        tmp_path / "memory/feature/a/slice.md",
        slice_text(base.format(focused="")),
    )
    assert "`Focused Playwright command:` must not be empty" in messages(
        validate_verification(tmp_path)
    )

    write(
        tmp_path / "memory/feature/a/slice.md",
        slice_text(base.format(focused=" pnpm e2e -- signup.spec.ts")),
    )
    assert "must match one of the ## Verification Run rows" in messages(
        validate_verification(tmp_path)
    )

    write(
        tmp_path / "memory/feature/a/slice.md",
        slice_text(
            """## Verification
- Run: cd backend && uv run pytest test/test_signup.py -q | covers: AC-001, AC-002
- Run: cd frontend && pnpm e2e -- signup.spec.ts | covers: AC-002

## QA Handoff
- Playwright story tests required: yes
- Focused Playwright command: pnpm e2e -- signup.spec.ts
"""
        ),
    )
    msgs = messages(validate_verification(tmp_path))
    assert "Focused Playwright command" not in msgs


def test_repo_without_memory_is_clean(tmp_path: Path) -> None:
    assert validate_verification(tmp_path) == []


# --- evidence cross-check ------------------------------------------------

GOOD_VERIFICATION = """## Verification
- Run: cd backend && uv run pytest test/test_signup.py -q | covers: AC-001, AC-002
"""


def evidence(runs: list[dict], code_state: dict | None = None) -> str:
    data: dict = {
        "generated_by": {
            "command": "python scripts/validate/cli.py gate --root . --slice memory/feature/a/slice.md",
            "cwd": ".",
        },
        "runs": runs,
    }
    if code_state is not None:
        data["code_state"] = code_state
    return json.dumps(data)


def run_entry(command: str, exit_code: int = 0) -> dict:
    return {
        "command": command,
        "cwd": ".",
        "exit_code": exit_code,
        "started_at": "2026-07-10T00:00:00Z",
        "finished_at": "2026-07-10T00:00:01Z",
        "output_path": "memory/feature/a/evidence/verify-1.txt",
    }


def test_declared_command_missing_from_evidence_blocks(tmp_path: Path) -> None:
    write(tmp_path / "memory/feature/a/slice.md", slice_text(GOOD_VERIFICATION))
    write(
        tmp_path / "memory/feature/a/qa-evidence.json",
        evidence([run_entry("validate-tools project-layout .")]),
    )

    assert "was never executed by the gate" in messages(validate_verification(tmp_path))


def test_declared_command_that_failed_blocks(tmp_path: Path) -> None:
    write(tmp_path / "memory/feature/a/slice.md", slice_text(GOOD_VERIFICATION))
    write(
        tmp_path / "memory/feature/a/qa-evidence.json",
        evidence(
            [
                run_entry(
                    "cd backend && uv run pytest test/test_signup.py -q", exit_code=1
                )
            ]
        ),
    )

    assert "did not pass" in messages(validate_verification(tmp_path))


def test_matching_passing_run_satisfies_the_cross_check(tmp_path: Path) -> None:
    write(tmp_path / "memory/feature/a/slice.md", slice_text(GOOD_VERIFICATION))
    write(
        tmp_path / "memory/feature/a/qa-evidence.json",
        evidence([run_entry("cd backend && uv run pytest test/test_signup.py -q")]),
    )

    msgs = messages(validate_verification(tmp_path))
    assert "was never executed" not in msgs
    assert "did not pass" not in msgs


def test_skip_rows_require_no_evidence(tmp_path: Path) -> None:
    write(
        tmp_path / "memory/feature/a/slice.md",
        slice_text(
            """## Verification
- Run: none [skip-verify: docs-only, no runtime surface] | covers: AC-001, AC-002
"""
        ),
    )
    write(tmp_path / "memory/feature/a/qa-evidence.json", evidence([run_entry("x")]))

    msgs = messages(validate_verification(tmp_path))
    assert "was never executed" not in msgs


# --- freshness (code_state digest) ----------------------------------------


@pytest.mark.skipif(GIT is None, reason="git is required for code_state fixtures")
class TestFreshness:
    def _git_repo(self, tmp_path: Path) -> None:
        write(tmp_path / "backend/src/main.py", "print('v1')\n")
        write(tmp_path / "memory/feature/a/slice.md", slice_text(GOOD_VERIFICATION))
        subprocess.run([GIT, "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run([GIT, "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            [
                GIT,
                "-c",
                "user.email=t@example.com",
                "-c",
                "user.name=t",
                "commit",
                "-qm",
                "init",
            ],
            cwd=tmp_path,
            check=True,
        )

    def _write_evidence(self, tmp_path: Path) -> None:
        write(
            tmp_path / "memory/feature/a/qa-evidence.json",
            evidence(
                [run_entry("cd backend && uv run pytest test/test_signup.py -q")],
                code_state=app_code_state(tmp_path),
            ),
        )

    def test_fresh_evidence_passes(self, tmp_path: Path) -> None:
        self._git_repo(tmp_path)
        self._write_evidence(tmp_path)

        assert "stale" not in messages(validate_verification(tmp_path))

    def test_app_code_change_after_evidence_blocks(self, tmp_path: Path) -> None:
        self._git_repo(tmp_path)
        self._write_evidence(tmp_path)
        write(tmp_path / "backend/src/main.py", "print('v2 - post-evidence fix')\n")

        assert "stale relative to the app code" in messages(
            validate_verification(tmp_path)
        )

    def test_memory_only_change_does_not_invalidate_evidence(
        self, tmp_path: Path
    ) -> None:
        self._git_repo(tmp_path)
        self._write_evidence(tmp_path)
        write(tmp_path / "memory/rules.md", 'Source: get_guideline("x")\n')

        assert "stale" not in messages(validate_verification(tmp_path))

    def test_missing_code_state_blocks_when_git_is_available(
        self, tmp_path: Path
    ) -> None:
        self._git_repo(tmp_path)
        write(
            tmp_path / "memory/feature/a/qa-evidence.json",
            evidence([run_entry("cd backend && uv run pytest test/test_signup.py -q")]),
        )

        assert "missing code_state" in messages(validate_verification(tmp_path))


# --- gate integration ------------------------------------------------------


def test_gate_executes_declared_run_rows_and_records_them(tmp_path: Path) -> None:
    write(
        tmp_path / "memory/feature/a/slice.md",
        slice_text(
            f"""## Verification
- Run: {shutil.which("python") and "python" or "python3"} -c "print('verified')" | covers: AC-001, AC-002
- Run: none [skip-verify: nothing else to run] | covers: AC-002
"""
        ),
    )

    run_gate(tmp_path, Path("memory/feature/a/slice.md"))

    data = json.loads(
        (tmp_path / "memory/feature/a/qa-evidence.json").read_text(encoding="utf-8")
    )
    verify_runs = [run for run in data["runs"] if "print('verified')" in run["command"]]
    assert verify_runs and verify_runs[0]["exit_code"] == 0
    assert (tmp_path / verify_runs[0]["output_path"]).read_text(
        encoding="utf-8"
    ).strip() == "verified"
    # Skip rows are never executed.
    assert not any("skip-verify" in run["command"] for run in data["runs"])
    assert "code_state" in data


def test_gate_returns_nonzero_when_a_declared_command_fails(tmp_path: Path) -> None:
    write(
        tmp_path / "memory/feature/a/slice.md",
        slice_text(
            """## Verification
- Run: python -c "raise SystemExit(3)" | covers: AC-001, AC-002
"""
        ),
    )

    assert run_gate(tmp_path, Path("memory/feature/a/slice.md")) == 1
    data = json.loads(
        (tmp_path / "memory/feature/a/qa-evidence.json").read_text(encoding="utf-8")
    )
    failed = [run for run in data["runs"] if "SystemExit(3)" in run["command"]]
    assert failed and failed[0]["exit_code"] == 3


# --- CLI exit codes ----------------------------------------------------------


def test_cli_exit_codes_for_clean_and_failing_fixtures(tmp_path: Path) -> None:
    clean = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate/cli.py"),
            "verification",
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert clean.returncode == 0

    write(tmp_path / "memory/feature/a/slice.md", slice_text(""))
    failing = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/validate/cli.py"),
            "verification",
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert failing.returncode == 1
    assert "missing required section ## Verification" in failing.stdout


# --- hook-level smoke (both runtimes) ----------------------------------------


@pytest.mark.skipif(BASH is None, reason="bash is required to run the hook scripts")
@pytest.mark.parametrize("runtime_dir", [".claude", ".codex"])
class TestHookSmoke:
    def run_hook(
        self,
        runtime_dir: str,
        hook: str,
        stdin: str,
        project_dir: Path | None = None,
        path_override: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        import os

        env = os.environ.copy()
        env.pop("HOOK_INPUT_JSON", None)
        var = "CLAUDE_PROJECT_DIR" if runtime_dir == ".claude" else "CODEX_PROJECT_DIR"
        env.pop("CLAUDE_PROJECT_DIR", None)
        env.pop("CODEX_PROJECT_DIR", None)
        if project_dir is not None:
            env[var] = str(project_dir)
        if path_override is not None:
            env["PATH"] = path_override
        return subprocess.run(
            [BASH, str(ROOT / runtime_dir / "hooks" / hook)],
            input=stdin,
            capture_output=True,
            text=True,
            env=env,
            cwd=project_dir or ROOT,
        )

    def test_garbage_stdin_fails_open_silently(self, runtime_dir: str) -> None:
        result = self.run_hook(runtime_dir, "verify-qa.sh", "not json at all")
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_empty_stdin_fails_open_silently(self, runtime_dir: str) -> None:
        result = self.run_hook(runtime_dir, "verify-qa.sh", "")
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_stop_hook_active_short_circuits(self, runtime_dir: str) -> None:
        result = self.run_hook(
            runtime_dir,
            "verify-qa.sh",
            '{"agent_type":"qa-checker","stop_hook_active":true}',
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_other_agent_types_pass_through(self, runtime_dir: str) -> None:
        result = self.run_hook(
            runtime_dir,
            "verify-qa.sh",
            '{"agent_type":"backend-developer","stop_hook_active":false}',
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_qa_checker_is_blocked_on_a_failing_fixture(
        self, runtime_dir: str, tmp_path: Path
    ) -> None:
        # A fixture repo whose slice declares no ## Verification section; the
        # hook must surface the validator finding as a {"decision":"block"}.
        write(tmp_path / "memory/feature/a/slice.md", slice_text(""))
        (tmp_path / "scripts").symlink_to(ROOT / "scripts")
        result = self.run_hook(
            runtime_dir,
            "verify-qa.sh",
            '{"agent_type":"qa-checker","stop_hook_active":false}',
            project_dir=tmp_path,
        )
        assert result.returncode == 0
        assert '"decision":"block"' in result.stdout
        assert "verification" in result.stdout

    def test_developer_gate_fails_closed_on_missing_toolchain(
        self, runtime_dir: str, tmp_path: Path
    ) -> None:
        import os

        write(tmp_path / "backend/pyproject.toml", "[project]\nname='x'\n")
        (tmp_path / "scripts").symlink_to(ROOT / "scripts")
        # A PATH containing only bash + python: ruff/uv/pytest/validate-tools all
        # missing while the backend manifest exists -> the gate must block, not
        # silently skip.
        fakebin = tmp_path / "fakebin"
        fakebin.mkdir()
        for tool in ("bash", "python", "python3", "git", "grep", "dirname", "cat"):
            source = shutil.which(tool)
            if source:
                os.symlink(source, fakebin / tool)
        result = self.run_hook(
            runtime_dir,
            "verify-subagent.sh",
            '{"agent_type":"backend-developer","stop_hook_active":false}',
            project_dir=tmp_path,
            path_override=str(fakebin),
        )
        assert result.returncode == 0
        assert '"decision":"block"' in result.stdout
        assert "fail-closed toolchain policy" in result.stdout

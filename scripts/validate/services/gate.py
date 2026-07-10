"""Gate service: run the deterministic evidence commands and write qa-evidence.json.

Besides the repo-shape commands (compose, backend coverage, frontend
test/build/e2e), the gate executes every non-skip `- Run:` row declared in the
slice's ## Verification section and records it in runs[] verbatim, and stamps the
evidence with the app-code state digest (see repository.app_code_state) so the
verification validator can prove the declared commands ran, passed, and ran
against the code that is actually shipping.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from scripts.validate.repository import app_code_state
from scripts.validate.services.verification import parse_verification_rows


def iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_command(
    root: Path, command: str, cwd: str, output_path: Path
) -> dict[str, object]:
    started_at = iso_now()
    workdir = root / cwd
    result = subprocess.run(
        command, cwd=workdir, shell=True, capture_output=True, text=True, check=False
    )
    finished_at = iso_now()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        result.stdout
        + ("\n" if result.stdout and result.stderr else "")
        + result.stderr,
        encoding="utf-8",
    )
    return {
        "command": command,
        "cwd": cwd,
        "exit_code": result.returncode,
        "started_at": started_at,
        "finished_at": finished_at,
        "output_path": output_path.relative_to(root).as_posix(),
    }


def read_backend_coverage(root: Path) -> float | None:
    path = root / "backend/coverage.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    total = data.get("totals", {})
    value = total.get("percent_covered")
    return float(value) if isinstance(value, (int, float)) else None


def read_frontend_coverage(root: Path) -> float | None:
    path = root / "frontend/coverage/coverage-summary.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    total = data.get("total", {})
    statements = total.get("statements", {})
    value = statements.get("pct")
    return float(value) if isinstance(value, (int, float)) else None


def run_gate(root: Path, slice_arg: Path, coverage_threshold: float = 80.0) -> int:
    root = root.resolve()
    slice_path = (
        (root / slice_arg).resolve()
        if not slice_arg.is_absolute()
        else slice_arg.resolve()
    )
    slice_dir = slice_path.parent
    evidence_dir = slice_dir / "evidence"

    commands: list[tuple[str, str, str]] = [
        ("validate-tools project-layout .", ".", "project-layout.txt"),
    ]
    runtime_smoke_config = slice_dir / "runtime-smoke.json"
    if (root / "docker-compose.yml").exists():
        commands.append(
            ("docker compose up --build --wait", ".", "docker-compose-up.txt")
        )
        if (root / "frontend/package.json").exists():
            commands.append(
                (
                    f"python scripts/validate/cli.py runtime-smoke --config {runtime_smoke_config.relative_to(root).as_posix()}",
                    ".",
                    "runtime-smoke.txt",
                )
            )
    if (root / "backend/pyproject.toml").exists():
        commands.append(
            (
                "uv run pytest --cov=src --cov-report=json:coverage.json --cov-fail-under=80",
                "backend",
                "backend-coverage.txt",
            )
        )
    if (root / "frontend/package.json").exists():
        commands.extend(
            [
                (
                    "npx pnpm@10.16.0 --dir frontend test:coverage",
                    ".",
                    "frontend-coverage.txt",
                ),
                ("npx pnpm@10.16.0 --dir frontend build", ".", "frontend-build.txt"),
                ("npx pnpm@10.16.0 --dir frontend e2e", ".", "e2e.txt"),
            ]
        )
    # Slice-declared verification commands (## Verification `- Run:` rows) run
    # while any compose stack is still up, so focused Playwright rows can reach it.
    slice_text = slice_path.read_text(encoding="utf-8")
    for index, row in enumerate(parse_verification_rows(slice_text), start=1):
        if row.skip or row.malformed or not row.command:
            continue
        commands.append((row.command, ".", f"verify-{index}.txt"))

    if (root / "docker-compose.yml").exists():
        commands.append(
            ("docker compose down --remove-orphans", ".", "docker-compose-down.txt")
        )

    runs = [
        run_command(root, command, cwd, evidence_dir / output_name)
        for command, cwd, output_name in commands
    ]

    unit_coverage: list[dict[str, object]] = []
    backend_coverage = read_backend_coverage(root)
    if backend_coverage is not None:
        unit_coverage.append(
            {
                "surface": "backend",
                "minimum_percent": coverage_threshold,
                "actual_percent": backend_coverage,
                "summary_path": "backend/coverage.json",
            }
        )
    frontend_coverage = read_frontend_coverage(root)
    if frontend_coverage is not None:
        unit_coverage.append(
            {
                "surface": "frontend",
                "minimum_percent": coverage_threshold,
                "actual_percent": frontend_coverage,
                "summary_path": "frontend/coverage/coverage-summary.json",
            }
        )

    e2e_coverage_path = (slice_dir / "e2e-coverage.json").relative_to(root).as_posix()
    evidence = {
        "schema_version": 1,
        "slice": slice_path.relative_to(root).as_posix(),
        "coverage_threshold": coverage_threshold,
        "generated_at": iso_now(),
        "generated_by": {
            "command": f"python scripts/validate/cli.py gate --root . --slice {slice_arg}",
            "cwd": ".",
        },
        "runs": runs,
        "unit_coverage": unit_coverage,
        "e2e_coverage_path": e2e_coverage_path,
        # Computed after every run finished, so the digest reflects any file the
        # commands themselves produced; the verification validator recomputes it
        # and blocks stale evidence.
        "code_state": app_code_state(root),
    }
    (slice_dir / "qa-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    return 1 if any(run["exit_code"] != 0 for run in runs) else 0

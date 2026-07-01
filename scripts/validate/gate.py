#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--slice", type=Path, required=True)
    parser.add_argument("--coverage-threshold", type=float, default=80.0)
    args = parser.parse_args()

    root = args.root.resolve()
    slice_path = (
        (root / args.slice).resolve()
        if not args.slice.is_absolute()
        else args.slice.resolve()
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
                    f"python scripts/validate/runtime-smoke.py --config {runtime_smoke_config.relative_to(root).as_posix()}",
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
                "minimum_percent": args.coverage_threshold,
                "actual_percent": backend_coverage,
                "summary_path": "backend/coverage.json",
            }
        )
    frontend_coverage = read_frontend_coverage(root)
    if frontend_coverage is not None:
        unit_coverage.append(
            {
                "surface": "frontend",
                "minimum_percent": args.coverage_threshold,
                "actual_percent": frontend_coverage,
                "summary_path": "frontend/coverage/coverage-summary.json",
            }
        )

    e2e_coverage_path = (slice_dir / "e2e-coverage.json").relative_to(root).as_posix()
    evidence = {
        "schema_version": 1,
        "slice": slice_path.relative_to(root).as_posix(),
        "coverage_threshold": args.coverage_threshold,
        "generated_at": iso_now(),
        "generated_by": {
            "command": f"python scripts/validate/gate.py --root . --slice {args.slice}",
            "cwd": ".",
        },
        "runs": runs,
        "unit_coverage": unit_coverage,
        "e2e_coverage_path": e2e_coverage_path,
    }
    (slice_dir / "qa-evidence.json").write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
    )
    return 1 if any(run["exit_code"] != 0 for run in runs) else 0


if __name__ == "__main__":
    raise SystemExit(main())

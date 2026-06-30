from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

from scripts.validate.checks.common import Finding, line_number, read_text

def _existing_dirs(root: Path, rel_paths: Sequence[str]) -> list[Finding]:
    return [Finding(rel, "missing required project directory") for rel in rel_paths if not (root / rel).is_dir()]


def _file_contains(path: Path, patterns: Sequence[str]) -> bool:
    if not path.exists():
        return False
    text = read_text(path)
    return all(pattern in text for pattern in patterns)


def validate_project_layout(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    backend_root = root / "backend"
    frontend_root = root / "frontend"
    compose = root / "docker-compose.yml"
    if backend_root.exists():
        for rel in [
            "backend/Dockerfile",
            "backend/Dockerfile.test",
            "backend/.env.example",
            "backend/pyproject.toml",
            "backend/uv.lock",
        ]:
            if not (root / rel).exists():
                findings.append(Finding(rel, "missing expected stack-local backend artifact"))
        dockerfile_test = root / "backend/Dockerfile.test"
        if dockerfile_test.exists() and "COPY test" not in read_text(dockerfile_test):
            findings.append(Finding("backend/Dockerfile.test", "backend test image must copy test/ before running pytest"))
    if frontend_root.exists():
        if (frontend_root / "app").exists() and (frontend_root / "src/app").exists():
            findings.append(
                Finding(
                    "frontend/app",
                    "duplicate Next App Router roots; use frontend/src/app and remove frontend/app",
                )
            )
        if (frontend_root / "pages").exists() and (frontend_root / "src/app").exists():
            findings.append(
                Finding(
                    "frontend/pages",
                    "do not mix legacy frontend/pages router with frontend/src/app",
                )
            )
        for rel in [
            "frontend/Dockerfile",
            "frontend/.env.example",
            "frontend/.npmrc",
            "frontend/package.json",
            "frontend/pnpm-lock.yaml",
            "frontend/pnpm-workspace.yaml",
        ]:
            if not (root / rel).exists():
                findings.append(Finding(rel, "missing expected stack-local frontend artifact"))
        dockerfile = root / "frontend/Dockerfile"
        if dockerfile.exists() and not _file_contains(
            dockerfile,
            [".npmrc", "package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", "pnpm install"],
        ):
            findings.append(Finding("frontend/Dockerfile", "frontend image must copy stack-local pnpm files before install"))
        env_example = root / "frontend/.env.example"
        if compose.exists() and env_example.exists():
            env_text = read_text(env_example)
            if re.search(r"=\s*https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(?:/|$)", env_text):
                findings.append(
                    Finding(
                        "frontend/.env.example",
                        "compose frontend env must not point service URLs at localhost",
                    )
                )
    for rel in ["pnpm-lock.yaml", "pnpm-workspace.yaml"]:
        if (root / rel).exists():
            findings.append(Finding(rel, "stack artifact must live under frontend/, not repo root"))
    if backend_root.exists() and frontend_root.exists() and not compose.exists():
        findings.append(Finding("docker-compose.yml", "fullstack app needs a compose runtime path"))
    if compose.exists():
        text = read_text(compose)
        if backend_root.exists() and "./backend/.env" not in text:
            findings.append(Finding("docker-compose.yml", "backend service must use stack-local env file ./backend/.env"))
        if frontend_root.exists() and "./frontend/.env" not in text:
            findings.append(Finding("docker-compose.yml", "frontend service must use stack-local env file ./frontend/.env"))
    return findings


def validate_database_policy(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    backend_root = root / "backend"
    if not backend_root.exists():
        return findings
    runtime_files = [
        "backend/src/config/settings.py",
        "backend/src/infrastructure/db/engine.py",
        "backend/alembic.ini",
        "backend/alembic/env.py",
    ]
    for rel in runtime_files:
        path = root / rel
        if not path.exists():
            continue
        text = read_text(path)
        if "sqlite:///" in text and "TEST" not in text.upper() and "E2E" not in text.upper():
            findings.append(Finding(rel, "runtime database config must not default to SQLite"))
    env_example = root / "backend/.env.example"
    if env_example.exists():
        text = read_text(env_example)
        if "DATABASE_URL=" not in text:
            findings.append(Finding("backend/.env.example", "DATABASE_URL must be documented"))
        elif "sqlite:///" in text:
            findings.append(Finding("backend/.env.example", "default documented DATABASE_URL must not use SQLite"))
        elif "postgresql" not in text:
            findings.append(Finding("backend/.env.example", "default documented DATABASE_URL should target PostgreSQL"))
    else:
        findings.append(Finding("backend/.env.example", "missing backend database env example"))
    compose = root / "docker-compose.yml"
    if compose.exists():
        text = read_text(compose).lower()
        if "postgres" not in text:
            findings.append(Finding("docker-compose.yml", "compose must define the guideline database service"))
        if "depends_on" not in text:
            findings.append(Finding("docker-compose.yml", "app service must depend on the database service"))
    return findings

def _function_body(text: str, name: str) -> str | None:
    match = re.search(rf"^def\s+{re.escape(name)}\s*\([^)]*\)\s*->?\s*[^:]*:\s*$", text, re.MULTILINE)
    if not match:
        match = re.search(rf"^def\s+{re.escape(name)}\s*\([^)]*\)\s*:\s*$", text, re.MULTILINE)
    if not match:
        return None
    rest = text[match.end() :]
    next_def = re.search(r"^def\s+\w+\s*\(", rest, re.MULTILINE)
    return rest[: next_def.start()] if next_def else rest


def validate_migrations(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    migration_dir = root / "backend/alembic/versions"
    if not migration_dir.exists():
        return findings
    for migration in sorted(migration_dir.glob("*.py")):
        rel = migration.relative_to(root).as_posix()
        text = read_text(migration)
        for function in ["upgrade", "downgrade"]:
            body = _function_body(text, function)
            if body is None:
                findings.append(Finding(rel, f"migration missing {function}()"))
                continue
            stripped = [line.strip() for line in body.splitlines() if line.strip() and not line.strip().startswith("#")]
            if not stripped or stripped == ["pass"]:
                findings.append(Finding(rel, f"migration {function}() must not be empty"))
        if "initial" in migration.name.lower() or "0001" in migration.name:
            if "op.create_table" not in text:
                findings.append(Finding(rel, "initial migration must create schema tables"))
    return findings
def _python_settings_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    text = read_text(path)
    return {match.group(1) for match in re.finditer(r"^\s*([A-Z][A-Z0-9_]+)\s*:", text, re.MULTILINE)}


def validate_backend_contract(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    backend_root = root / "backend"
    if not backend_root.exists():
        return findings

    findings.extend(
        _existing_dirs(
            root,
            [
                "backend/src/domain",
                "backend/src/application",
                "backend/src/infrastructure",
                "backend/src/presentation",
                "backend/alembic",
            ],
        )
    )

    settings_path = root / "backend/src/config/settings.py"
    env_example = root / "backend/.env.example"
    settings_keys = _python_settings_keys(settings_path)
    if settings_keys:
        if not env_example.exists():
            findings.append(Finding("backend/.env.example", "missing env example for backend settings"))
        else:
            env_text = read_text(env_example)
            for key in sorted(settings_keys):
                if not re.search(rf"^{re.escape(key)}=", env_text, re.MULTILINE):
                    findings.append(Finding("backend/.env.example", f"missing setting key {key}"))

    routes_dir = root / "backend/src/presentation/routes"
    tests_dir = root / "backend/test"
    if routes_dir.exists():
        for route in sorted(routes_dir.glob("*.py")):
            if route.name == "__init__.py":
                continue
            expected = tests_dir / f"test_routes_{route.stem}.py"
            if not expected.exists():
                findings.append(
                    Finding(
                        expected.relative_to(root).as_posix(),
                        f"missing API route test for {route.relative_to(root).as_posix()}",
                    )
                )

    entity_dir = root / "backend/src/domain/entities"
    migration_dir = root / "backend/alembic/versions"
    if entity_dir.exists() and any(entity_dir.glob("*.py")) and not any(migration_dir.glob("*.py")):
        findings.append(Finding("backend/alembic/versions", "domain entities exist but no Alembic migration files were found"))

    write_use_cases = root / "backend/src/application/use_cases"
    mutating_prefixes = ("create_", "update_", "delete_", "archive_")
    if write_use_cases.exists():
        for use_case in sorted(write_use_cases.rglob("*.py")):
            if not use_case.name.startswith(mutating_prefixes):
                continue
            text = read_text(use_case)
            if "AuditWriter" not in text or "._audit.emit(" not in text:
                findings.append(
                    Finding(
                        use_case.relative_to(root).as_posix(),
                        "mutating use case must use AuditWriter and emit an audit event",
                    )
                )
    return findings


def validate_frontend_contract(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    frontend_root = root / "frontend"
    if not frontend_root.exists():
        return findings

    if (frontend_root / "app").exists() and (frontend_root / "src/app").exists():
        findings.append(
            Finding(
                "frontend/app",
                "duplicate Next App Router roots; use frontend/src/app and remove frontend/app",
            )
        )
    if (frontend_root / "pages").exists() and (frontend_root / "src/app").exists():
        findings.append(
            Finding(
                "frontend/pages",
                "do not mix legacy frontend/pages router with frontend/src/app",
            )
        )

    findings.extend(
        _existing_dirs(
            root,
            [
                "frontend/src/app",
                "frontend/src/components",
                "frontend/src/services",
                "frontend/src/actions",
                "frontend/e2e",
            ],
        )
    )

    e2e_root = root / "frontend/e2e"
    selector_patterns = [
        (re.compile(r"\bwaitForTimeout\s*\("), "do not use sleeps; rely on Playwright auto-waiting assertions"),
        (re.compile(r"nth-child\s*\("), "do not use nth-child selectors in E2E tests"),
        (re.compile(r"\.locator\(\s*['\"](?:\.|#)"), "prefer role/label/text locators over CSS selectors"),
    ]
    if e2e_root.exists():
        for spec in sorted(e2e_root.rglob("*.ts")):
            text = read_text(spec)
            rel = spec.relative_to(root).as_posix()
            for pattern, message in selector_patterns:
                for match in pattern.finditer(text):
                    findings.append(Finding(rel, message, line_number(text, match.start())))

    actions_dir = root / "frontend/src/actions"
    action_tests_dir = actions_dir / "__tests__"
    if actions_dir.exists():
        for action_file in sorted(actions_dir.glob("*.ts")):
            candidates = [
                action_tests_dir / f"{action_file.stem}.test.ts",
                action_tests_dir / f"{action_file.stem}.test.tsx",
            ]
            if not any(candidate.exists() for candidate in candidates):
                findings.append(
                    Finding(
                        action_tests_dir.relative_to(root).as_posix(),
                        f"missing Server Action test for {action_file.relative_to(root).as_posix()}",
                    )
                )

    components_dir = root / "frontend/src/components"
    if components_dir.exists():
        for form in sorted(components_dir.rglob("*-form.tsx")):
            test_path = form.parent / "__tests__" / f"{form.stem}.test.tsx"
            if not test_path.exists():
                findings.append(
                    Finding(
                        test_path.relative_to(root).as_posix(),
                        f"missing form validation test for {form.relative_to(root).as_posix()}",
                    )
                )

    app_root = root / "frontend/src/app/[lang]/(app)"
    if app_root.exists():
        for page in sorted(app_root.rglob("page.tsx")):
            route_dir = page.parent
            if not any((route_dir / name).exists() for name in ("loading.tsx", "error.tsx", "not-found.tsx")):
                findings.append(
                    Finding(
                        route_dir.relative_to(root).as_posix(),
                        "user-facing route should define loading, error, or not-found state",
                    )
                )
    return findings


"""Runtime smoke service: GET a URL and assert required/forbidden body text."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


DEFAULT_FORBIDDEN_TEXT = [
    "Application error",
    "server-side exception",
    "Digest:",
]


def load_config(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("runtime smoke config must be a JSON object")
    return data


def run_smoke(
    config_path: Path | None = None,
    url: str | None = None,
    must_contain: list[str] | None = None,
    forbid: list[str] | None = None,
) -> int:
    must_contain = must_contain or []
    forbid = forbid or []

    config: dict[str, object] = {}
    if config_path:
        try:
            config = load_config(config_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"invalid runtime smoke config: {exc}", file=sys.stderr)
            return 1

    url = url or config.get("url")
    if not isinstance(url, str) or not url:
        print("runtime smoke requires --url or config.url", file=sys.stderr)
        return 1

    configured_required = config.get("must_contain", [])
    if not isinstance(configured_required, list) or not all(
        isinstance(item, str) for item in configured_required
    ):
        print(
            "runtime smoke config must_contain must be a list of strings",
            file=sys.stderr,
        )
        return 1
    configured_forbidden = config.get("forbid", [])
    if not isinstance(configured_forbidden, list) or not all(
        isinstance(item, str) for item in configured_forbidden
    ):
        print("runtime smoke config forbid must be a list of strings", file=sys.stderr)
        return 1

    required_text = [*configured_required, *must_contain]
    forbidden_text = [*DEFAULT_FORBIDDEN_TEXT, *configured_forbidden, *forbid]

    try:
        request = Request(url, headers={"User-Agent": "runtime-smoke/1.0"})
        with urlopen(request, timeout=15) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
    except URLError as exc:
        print(f"request failed: {exc}", file=sys.stderr)
        return 1

    print(f"GET {url} -> {status}")
    if status < 200 or status >= 300:
        print(f"unexpected HTTP status {status}", file=sys.stderr)
        return 1

    failed = False
    for text in required_text:
        if text not in body:
            print(f"missing expected text: {text}", file=sys.stderr)
            failed = True
    for text in forbidden_text:
        if text in body:
            print(f"forbidden text present: {text}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


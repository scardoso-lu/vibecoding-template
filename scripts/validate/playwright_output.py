from __future__ import annotations

import re

def summarize_playwright_output(text: str) -> list[str]:
    summary: list[str] = []
    patterns = [
        re.compile(r"^\s*\d+\)\s+.+$", re.MULTILINE),
        re.compile(r"^\s*(?:Error|TimeoutError):\s+.+$", re.MULTILINE),
        re.compile(r"^\s+at .+\.(?:spec|test)\.ts:\d+:\d+.*$", re.MULTILINE),
        re.compile(r"^\s*\d+\s+failed\b.*$", re.MULTILINE),
    ]
    for pattern in patterns:
        for match in pattern.finditer(text):
            line = match.group(0).strip()
            if line not in summary:
                summary.append(line)
    return summary


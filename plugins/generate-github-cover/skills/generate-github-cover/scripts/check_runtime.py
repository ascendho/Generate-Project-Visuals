#!/usr/bin/env python3
"""Check that the deterministic image-rendering runtime is ready."""

from __future__ import annotations

import importlib.metadata
import json
import platform
import sys
from typing import Any


MINIMUM_PYTHON = (3, 10)
EXPECTED_PACKAGES = {
    "playwright": "1.61.0",
    "segno": "1.6.6",
}


def _install_commands() -> tuple[str, str]:
    executable = (sys.executable or "python3").replace('"', '\\"')
    python_command = f'"{executable}"'
    return (
        f'{python_command} -m pip install "playwright==1.61.0" "segno==1.6.6"',
        f"{python_command} -m playwright install chromium",
    )


def _package_status(package: str, expected: str) -> dict[str, Any]:
    try:
        installed = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return {
            "expected": expected,
            "installed": None,
            "ok": False,
            "error": "package is not installed",
        }
    return {
        "expected": expected,
        "installed": installed,
        "ok": installed == expected,
        "error": None if installed == expected else "installed version does not match",
    }


def _chromium_status(playwright_ready: bool) -> dict[str, Any]:
    if not playwright_ready:
        return {
            "ok": False,
            "error": "Playwright must be installed at the expected version first",
        }
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
    except Exception as exc:  # Playwright exposes environment-specific exception types.
        message = str(exc).splitlines()[0] or type(exc).__name__
        return {"ok": False, "error": message}
    return {"ok": True, "error": None}


def _remediation(
    python_ok: bool,
    packages: dict[str, dict[str, Any]],
    chromium: dict[str, Any],
) -> list[str]:
    if not python_ok:
        return ["Rerun this check with a Python 3.10+ interpreter."]
    install_packages, install_browser = _install_commands()
    actions = []
    if not all(item["ok"] for item in packages.values()):
        actions.append(install_packages)
    if not chromium["ok"]:
        actions.append(install_browser)
    return actions


def check_runtime() -> dict[str, Any]:
    python_ok = sys.version_info >= MINIMUM_PYTHON
    packages = {
        package: _package_status(package, expected)
        for package, expected in EXPECTED_PACKAGES.items()
    }
    chromium = _chromium_status(packages["playwright"]["ok"])
    ok = python_ok and all(item["ok"] for item in packages.values()) and chromium["ok"]
    return {
        "ok": ok,
        "python": {
            "minimum": ".".join(str(part) for part in MINIMUM_PYTHON),
            "installed": platform.python_version(),
            "ok": python_ok,
        },
        "packages": packages,
        "chromium": chromium,
        "remediation": [] if ok else _remediation(python_ok, packages, chromium),
    }


def main() -> int:
    result = check_runtime()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

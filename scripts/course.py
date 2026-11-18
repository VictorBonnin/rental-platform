#!/usr/bin/env python3
"""Portable commands for the Rental course.

Usage: python scripts/course.py <command>
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JAVA_SERVICE = ROOT / "apps" / "car-rental-service"
PYTHON_SERVICE = ROOT / "apps" / "pricing-service"

# Host ports can be changed (e.g. CAR_RENTAL_PORT=18080) when 8080/8000 are taken;
# docker-compose.yml reads the same variables.
CAR_RENTAL_URL = os.environ.get(
    "CAR_RENTAL_URL", f"http://localhost:{os.environ.get('CAR_RENTAL_PORT', '8080')}"
)
PRICING_URL = os.environ.get(
    "PRICING_URL", f"http://localhost:{os.environ.get('PRICING_PORT', '8000')}"
)


class CommandFailed(Exception):
    """Raised when a step fails; the script then exits with code 1."""


def gradlew() -> str:
    if os.name == "nt":
        return str(JAVA_SERVICE / "gradlew.bat")
    return "./gradlew"


def run(args: list[str], cwd: Path = ROOT) -> None:
    print(f"\n==> {' '.join(args)}  (in {cwd.relative_to(ROOT) or '.'})", flush=True)
    result = subprocess.run(args, cwd=cwd, check=False)
    if result.returncode != 0:
        raise CommandFailed(f"command failed with code {result.returncode}: {' '.join(args)}")


# --- commands --------------------------------------------------------------


def prerequisites() -> None:
    missing = []
    print(f"python: {sys.version.split()[0]} ({sys.executable})")
    for tool in ("java", "docker"):
        path = shutil.which(tool)
        print(f"{tool}: {path or 'NOT FOUND'}")
        if path is None:
            missing.append(tool)
    if missing:
        raise CommandFailed(f"missing prerequisites: {', '.join(missing)}")


def test_java() -> None:
    run([gradlew(), "clean", "test"], cwd=JAVA_SERVICE)


def test_python() -> None:
    run([sys.executable, "-m", "pytest"], cwd=PYTHON_SERVICE)


def test() -> None:
    test_java()
    test_python()


def lint_java() -> None:
    run([gradlew(), "checkstyleMain", "checkstyleTest"], cwd=JAVA_SERVICE)


def lint_python() -> None:
    run([sys.executable, "-m", "ruff", "check", "app", "tests"], cwd=PYTHON_SERVICE)
    run([sys.executable, "-m", "ruff", "format", "--check", "app", "tests"], cwd=PYTHON_SERVICE)


def lint() -> None:
    lint_java()
    lint_python()


def verify() -> None:
    """Local quality gates: tests then linters. Stops at the first failure.

    Docker images, Gitleaks, report publishing and branch protection stay
    the responsibility of the GitHub Actions workflows.
    """
    test()
    lint()


def compose_up() -> None:
    run(["docker", "compose", "up", "--build", "--detach"])


def compose_down() -> None:
    run(["docker", "compose", "down", "--remove-orphans"])


def http_get(url: str):
    with urllib.request.urlopen(url, timeout=5) as response:
        body = response.read().decode("utf-8")
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise CommandFailed(f"{url} did not return JSON (wrong service on this port?)") from error


def wait_for(url: str, timeout_seconds: int = 90) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            http_get(url)
            return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(2)
    raise CommandFailed(f"service not available: {url}")


def smoke() -> None:
    for base in (CAR_RENTAL_URL, PRICING_URL):
        wait_for(f"{base}/health")
        health = http_get(f"{base}/health")
        if health.get("status") != "UP":
            raise CommandFailed(f"{base}/health is not UP: {health}")
        cars = http_get(f"{base}/cars")
        if not cars:
            raise CommandFailed(f"{base}/cars returned no car")
        print(f"OK {base}: health UP, {len(cars)} entries in /cars")

    quote = http_get(f"{CAR_RENTAL_URL}/cars/C2/quote?days=2")
    if quote.get("total") != 120 or quote.get("currency") != "EUR":
        raise CommandFailed(f"unexpected quote for a standard car over 2 days: {quote}")
    print("OK quote: standard car, 2 days = 120 EUR")


COMMANDS = {
    "prerequisites": prerequisites,
    "test-java": test_java,
    "test-python": test_python,
    "test": test,
    "lint-java": lint_java,
    "lint-python": lint_python,
    "lint": lint,
    "verify": verify,
    "compose-up": compose_up,
    "compose-down": compose_down,
    "smoke": smoke,
}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in COMMANDS:
        print(f"usage: python scripts/course.py <{'|'.join(COMMANDS)}>", file=sys.stderr)
        return 2
    try:
        COMMANDS[argv[0]]()
    except CommandFailed as error:
        print(f"\nFAILED: {error}", file=sys.stderr)
        return 1
    print(f"\n{argv[0]}: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

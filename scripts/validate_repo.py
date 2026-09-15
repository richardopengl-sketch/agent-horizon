from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / ".reports"
REPORT_PATH = REPORT_DIR / "validation-report.json"


def run_check(name: str, command: list[str]) -> dict:
    started = time.monotonic()
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    return {
        "name": name,
        "command": command,
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
        "stdout": completed.stdout[-6000:],
        "stderr": completed.stderr[-6000:],
    }


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    checks = [
        run_check("pytest", [sys.executable, "-m", "pytest", "-q"]),
        run_check("ruff", [sys.executable, "-m", "ruff", "check", "."]),
        run_check("mypy", [sys.executable, "-m", "mypy", "core", "scenarios"]),
        run_check("compile", [sys.executable, "-m", "compileall", "-q", "core", "scenarios", "automation", "app.py"]),
        run_check("secret_scan", [sys.executable, "scripts/secret_scan.py"]),
    ]
    report = {
        "schema_version": 1,
        "repository": "agent-horizon",
        "ok": all(check["ok"] for check in checks),
        "checks": checks,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for check in checks:
        status = "PASS" if check["ok"] else "FAIL"
        print(f"[{status}] {check['name']} ({check['duration_seconds']}s)")
        if not check["ok"]:
            if check["stdout"]:
                print(check["stdout"])
            if check["stderr"]:
                print(check["stderr"], file=sys.stderr)
    print(f"report: {REPORT_PATH}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

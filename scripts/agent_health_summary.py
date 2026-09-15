from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / ".reports"
VALIDATION = REPORT_DIR / "validation-report.json"
OUTPUT = REPORT_DIR / "agent-health.json"


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    validation = json.loads(VALIDATION.read_text(encoding="utf-8")) if VALIDATION.exists() else {"ok": False, "checks": [], "error": "validation report missing"}
    failed = [check["name"] for check in validation.get("checks", []) if not check.get("ok", False)]
    summary = {
        "schema_version": 1,
        "ready_for_human_review": bool(validation.get("ok")),
        "failed_checks": failed,
        "next_action": "Request human/code-owner review." if validation.get("ok") else "Repair failing deterministic checks before review.",
    }
    OUTPUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if validation.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

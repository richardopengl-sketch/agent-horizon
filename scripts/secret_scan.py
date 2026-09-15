from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "github_pat": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    "github_classic": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "azure_storage_connection": re.compile(r"DefaultEndpointsProtocol=https?;AccountName=[^;\s]+;AccountKey=[^;\s]+", re.IGNORECASE),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webm", ".mp4", ".mp3", ".pyc"}


def tracked_files() -> list[Path]:
    completed = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [ROOT / item.decode("utf-8") for item in completed.stdout.split(b"\0") if item]


def main() -> int:
    findings: list[tuple[str, str]] = []
    for path in tracked_files():
        if path.suffix.lower() in BINARY_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append((str(path.relative_to(ROOT)), name))
    if findings:
        for path, kind in findings:
            print(f"SECRET_PATTERN {kind}: {path}")
        return 1
    print("secret scan: no recognized secret patterns in tracked text files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

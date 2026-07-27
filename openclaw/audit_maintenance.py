"""
V5.16 Phase 2 — Audit maintenance utilities.

verify_audit_file: Verify seq sequence and file_digest chain in a JSONL audit file.
prune_audit_files: Delete .jsonl files older than retain_days by mtime.

Never reads or returns secret values. Never reads event payload content.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Union


def verify_audit_file(path: Union[str, Path]) -> Dict:
    """
    Verify seq sequence and file_digest chain in a JSONL audit file.

    Returns {"ok": bool, "events_checked": int, "errors": list, "warnings": list}.
    Error string formats: "file_not_found", "invalid_json:line{N}",
    "seq_mismatch:line{N}:expected{E}:got{A}", "digest_mismatch:line{N}".

    Never returns event payload content or secret values.
    """
    path = Path(path)
    if not path.exists():
        return {"ok": False, "events_checked": 0, "errors": ["file_not_found"], "warnings": []}

    errors = []
    warnings = []
    events_checked = 0
    accumulated_bytes = b""

    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line_num, raw_line in enumerate(fh, 1):
                line = raw_line.rstrip("\n")
                if not line.strip():
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"invalid_json:line{line_num}")
                    accumulated_bytes += (line + "\n").encode("utf-8")
                    continue

                expected_seq = events_checked + 1
                actual_seq = event.get("seq")
                if actual_seq != expected_seq:
                    errors.append(
                        f"seq_mismatch:line{line_num}:expected{expected_seq}:got{actual_seq}"
                    )

                expected_digest = (
                    hashlib.sha256(accumulated_bytes).hexdigest() if accumulated_bytes else ""
                )
                actual_digest = event.get("file_digest", "")
                if actual_digest != expected_digest:
                    errors.append(f"digest_mismatch:line{line_num}")

                accumulated_bytes += (line + "\n").encode("utf-8")
                events_checked += 1

    except Exception as exc:
        return {
            "ok": False,
            "events_checked": events_checked,
            "errors": [type(exc).__name__],
            "warnings": warnings,
        }

    return {
        "ok": len(errors) == 0,
        "events_checked": events_checked,
        "errors": errors,
        "warnings": warnings,
    }


def prune_audit_files(root: Union[str, Path], retain_days: int) -> Dict:
    """
    Delete .jsonl files in root whose mtime is older than retain_days.

    Returns {"ok": bool, "deleted_count": int, "kept_count": int, "errors": list}.
    """
    root = Path(root)
    if not root.exists():
        return {"ok": True, "deleted_count": 0, "kept_count": 0, "errors": []}

    cutoff = time.time() - (retain_days * 86400)
    deleted = 0
    kept = 0
    errors = []

    for f in root.glob("*.jsonl"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
            else:
                kept += 1
        except Exception:
            errors.append(f"delete_failed:{f.name}")

    return {"ok": len(errors) == 0, "deleted_count": deleted, "kept_count": kept, "errors": errors}

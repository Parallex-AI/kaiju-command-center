#!/usr/bin/env bash
set -euo pipefail

PYTHON=~/kaiju/.venv/bin/python3
OPENCLAW_DIR=~/kaiju/openclaw
AUDIT_SMOKE_ROOT="/tmp/kaiju-openclaw-audit-smoke"
AUDIT_NOT_DIR="/tmp/kaiju-openclaw-audit-not-dir"

cleanup() {
    rm -rf "$AUDIT_SMOKE_ROOT" 2>/dev/null || true
    rm -f "$AUDIT_NOT_DIR" 2>/dev/null || true
    rm -f /tmp/kaiju_smoke_v3_audit_*.py 2>/dev/null || true
}
trap cleanup EXIT

# Clear any leftover state from a previous run
rm -rf "$AUDIT_SMOKE_ROOT" 2>/dev/null || true
rm -f "$AUDIT_NOT_DIR" 2>/dev/null || true

pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; exit 1; }

py_pass() {
    local label="$1"
    local tmpfile
    tmpfile=$(mktemp /tmp/kaiju_smoke_v3_audit_XXXXXX.py)
    cat > "$tmpfile"
    if (cd "$OPENCLAW_DIR" && $PYTHON "$tmpfile") >/dev/null 2>&1; then
        pass "$label"
    else
        echo "  ✗ $label"
        (cd "$OPENCLAW_DIR" && $PYTHON "$tmpfile") 2>&1 | head -20 || true
        rm -f "$tmpfile"
        exit 1
    fi
    rm -f "$tmpfile"
}

echo "=== Kaiju Command Center V3 OpenClaw Audit Smoke Test ==="
echo ""

# ---------------------------------------------------------------------------
# [1/5] Environment
# ---------------------------------------------------------------------------
echo "[1/5] Checking environment..."

[[ -f "$PYTHON" ]] \
    && pass "Python found at $PYTHON" \
    || fail "Python not found at $PYTHON"

py_pass "openclaw and audit modules importable" <<'PYEOF'
import sys
sys.path.insert(0, '.')
from openclaw import process_request
from audit import is_audit_enabled, get_audit_root, build_audit_event, append_audit_event
PYEOF

# ---------------------------------------------------------------------------
# [2/5] Audit writes
# ---------------------------------------------------------------------------
echo ""
echo "[2/5] Testing audit writes..."

py_pass "process_request writes audit events for summary, invalid request, unsupported agent" <<PYEOF
import os, sys, json
from pathlib import Path

os.environ["OPENCLAW_AUDIT_ROOT"] = "$AUDIT_SMOKE_ROOT"
os.environ["OPENCLAW_AUDIT_ENABLED"] = "true"
sys.path.insert(0, '.')
from openclaw import process_request

r = process_request({"client_id": "audit-smoke-client", "agent": "ads-agent", "request": "summary"})
assert r["ok"] is True, "summary ok not True: %r" % r.get("ok")

r = process_request({"client_id": "audit-smoke-client", "agent": "ads-agent", "request": "invalid"})
assert r["ok"] is False, "invalid ok not False: %r" % r.get("ok")
assert r["errors"][0]["code"] == "unsupported_request", \
    "code mismatch: %s" % r["errors"][0]["code"]

r = process_request({"client_id": "audit-smoke-client", "agent": "analytics-agent", "request": "summary"})
assert r["ok"] is False, "unsupported agent ok not False: %r" % r.get("ok")
assert r["errors"][0]["code"] == "unsupported_agent", \
    "code mismatch: %s" % r["errors"][0]["code"]

files = list(Path("$AUDIT_SMOKE_ROOT").glob("*.jsonl"))
assert len(files) >= 1, "No JSONL audit files found under $AUDIT_SMOKE_ROOT"

entries = []
for f in sorted(files):
    for line in f.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            entries.append(json.loads(line))

assert len(entries) >= 3, "Expected >= 3 audit entries, got %d" % len(entries)
PYEOF

# ---------------------------------------------------------------------------
# [3/5] Validate JSONL content
# ---------------------------------------------------------------------------
echo ""
echo "[3/5] Validating audit JSONL content..."

py_pass "all audit entries contain required fields" <<PYEOF
import os, sys, json
from pathlib import Path

os.environ["OPENCLAW_AUDIT_ROOT"] = "$AUDIT_SMOKE_ROOT"
sys.path.insert(0, '.')

REQUIRED = [
    "timestamp", "request_id", "trace_id", "tenant", "agent",
    "request", "ok", "duration_ms", "error_codes", "warning_count", "source",
]

files = sorted(Path("$AUDIT_SMOKE_ROOT").glob("*.jsonl"))
entries = []
for f in files:
    for line in f.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            entries.append(json.loads(line))

for i, entry in enumerate(entries):
    for field in REQUIRED:
        assert field in entry, "entry %d missing field '%s': %s" % (i, field, entry)
    assert entry["source"] == "openclaw", \
        "entry %d source mismatch: %s" % (i, entry.get("source"))
PYEOF

py_pass "audit entries contain no forbidden fields" <<PYEOF
import os, sys, json
from pathlib import Path

os.environ["OPENCLAW_AUDIT_ROOT"] = "$AUDIT_SMOKE_ROOT"
sys.path.insert(0, '.')

FORBIDDEN = [
    "payload", "router_response", "raw_metrics",
    "recommendations", "executive_summary",
]

files = sorted(Path("$AUDIT_SMOKE_ROOT").glob("*.jsonl"))
for f in files:
    for i, line in enumerate(f.read_text(encoding="utf-8").strip().splitlines()):
        if not line.strip():
            continue
        entry = json.loads(line)
        raw = json.dumps(entry)
        for key in FORBIDDEN:
            assert key not in entry, \
                "entry %d contains forbidden key '%s'" % (i, key)
PYEOF

py_pass "expected event types present: summary ok, unsupported_request, unsupported_agent" <<PYEOF
import os, sys, json
from pathlib import Path

os.environ["OPENCLAW_AUDIT_ROOT"] = "$AUDIT_SMOKE_ROOT"
sys.path.insert(0, '.')

files = sorted(Path("$AUDIT_SMOKE_ROOT").glob("*.jsonl"))
entries = []
for f in files:
    for line in f.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            entries.append(json.loads(line))

ok_summary = any(e["ok"] is True and e.get("request") == "summary" for e in entries)
has_unsupported_req = any(
    "unsupported_request" in (e.get("error_codes") or []) for e in entries
)
has_unsupported_agent = any(
    "unsupported_agent" in (e.get("error_codes") or []) for e in entries
)

assert ok_summary, "No ok=true summary event found"
assert has_unsupported_req, "No unsupported_request event found"
assert has_unsupported_agent, "No unsupported_agent event found"
PYEOF

# ---------------------------------------------------------------------------
# [4/5] Disabled and failure behavior
# ---------------------------------------------------------------------------
echo ""
echo "[4/5] Testing audit disabled and failure behavior..."

py_pass "OPENCLAW_AUDIT_ENABLED=false: ok=true, no crash, no new audit file" <<PYEOF
import os, sys
from pathlib import Path

disabled_root = "/tmp/kaiju-openclaw-audit-smoke-disabled"
os.environ["OPENCLAW_AUDIT_ENABLED"] = "false"
os.environ["OPENCLAW_AUDIT_ROOT"] = disabled_root

sys.path.insert(0, '.')
from openclaw import process_request

r = process_request({
    "client_id": "audit-smoke-client",
    "agent": "ads-agent",
    "request": "summary",
})
assert r["ok"] is True, "ok not True when audit disabled: %r" % r.get("ok")

# Disabled audit must not create the directory
assert not Path(disabled_root).exists(), \
    "audit dir should not be created when OPENCLAW_AUDIT_ENABLED=false"
PYEOF

py_pass "audit write failure is non-fatal: ok=true, audit_write_failed in warnings" <<PYEOF
import os, sys

# Place a regular file where the audit directory would be
not_dir = "/tmp/kaiju-openclaw-audit-not-dir"
with open(not_dir, "w") as fh:
    fh.write("not a directory")

os.environ["OPENCLAW_AUDIT_ENABLED"] = "true"
os.environ["OPENCLAW_AUDIT_ROOT"] = not_dir

sys.path.insert(0, '.')
from openclaw import process_request

r = process_request({
    "client_id": "audit-smoke-client",
    "agent": "ads-agent",
    "request": "summary",
})
assert r["ok"] is True, \
    "ok not True on audit failure: %r" % r.get("ok")

warnings = r.get("warnings") or []
codes = [w.get("code") for w in warnings if isinstance(w, dict)]
assert "audit_write_failed" in codes, \
    "audit_write_failed not in warnings: %s" % codes
PYEOF

# ---------------------------------------------------------------------------
# [5/5] Runtime audit files ignored
# ---------------------------------------------------------------------------
echo ""
echo "[5/5] Verifying runtime audit files remain ignored..."

GIT_STATUS=$(git -C ~/kaiju status --short openclaw/audit 2>/dev/null)
if [ -z "$GIT_STATUS" ]; then
    pass "openclaw/audit/ is ignored by Git (no output from git status)"
else
    echo "  ✗ openclaw/audit/ not ignored — git status output:"
    echo "$GIT_STATUS"
    exit 1
fi

echo ""
echo "=== V3 OpenClaw audit smoke test passed. ==="

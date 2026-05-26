#!/usr/bin/env bash
set -euo pipefail

PYTHON=~/kaiju/.venv/bin/python3
OPENCLAW_DIR=~/kaiju/openclaw
CLIENT_ID="openclaw-smoke-client"

cleanup() {
    rm -f /tmp/kaiju_smoke_v3_*.py 2>/dev/null || true
}
trap cleanup EXIT

pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; exit 1; }

py_pass() {
    local label="$1"
    local tmpfile
    tmpfile=$(mktemp /tmp/kaiju_smoke_v3_XXXXXX.py)
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

echo "=== Kaiju Command Center V3 OpenClaw Smoke Test ==="
echo ""

# ---------------------------------------------------------------------------
# [1/5] Environment
# ---------------------------------------------------------------------------
echo "[1/5] Checking environment..."

[[ -f "$PYTHON" ]] \
    && pass "Python found at $PYTHON" \
    || { echo "  ✗ Python not found at $PYTHON"; exit 1; }

py_pass "openclaw module and process_request importable" <<'PYEOF'
import sys
sys.path.insert(0, '.')
from openclaw import process_request
PYEOF

py_pass "registry module importable" <<'PYEOF'
import sys
sys.path.insert(0, '.')
from registry import get_agent, list_agents, get_supported_agents, get_supported_requests
PYEOF

py_pass "policy module importable" <<'PYEOF'
import sys
sys.path.insert(0, '.')
from policy import validate_request_policy
PYEOF

py_pass "schemas module importable" <<'PYEOF'
import sys
sys.path.insert(0, '.')
from schemas import OPENCLAW_VERSION, generate_request_id, generate_trace_id, make_error, make_openclaw_envelope
PYEOF

py_pass "context module importable" <<'PYEOF'
import sys
sys.path.insert(0, '.')
from context import resolve_context
PYEOF

# ---------------------------------------------------------------------------
# [2/5] Valid OpenClaw requests
# ---------------------------------------------------------------------------
echo ""
echo "[2/5] Testing valid OpenClaw requests..."

for req in summary cpa conversions raw; do
    py_pass "process_request $req: ok + full envelope shape" <<PYEOF
import sys
sys.path.insert(0, '.')
from openclaw import process_request

r = process_request({
    "client_id": "openclaw-smoke-client",
    "agent": "ads-agent",
    "request": "$req",
})

assert r["ok"] is True, \
    "ok is not True for request '$req': got %r" % r.get("ok")
assert r["openclaw"]["version"] == "0.1.0", \
    "version mismatch: %s" % r["openclaw"]["version"]
assert r["openclaw"]["request_id"], \
    "request_id missing or empty"
assert r["openclaw"]["trace_id"], \
    "trace_id missing or empty"
assert r["openclaw"]["tenant"] == "openclaw-smoke-client", \
    "tenant mismatch: %s" % r["openclaw"]["tenant"]
assert r["openclaw"]["agent"] == "ads-agent", \
    "agent mismatch: %s" % r["openclaw"]["agent"]
assert "router_response" in r["data"], \
    "data.router_response missing"
assert r["data"]["router_response"]["ok"] is True, \
    "router_response.ok is not True"
assert r["data"]["router_response"]["execution_mode"] == "graph", \
    "execution_mode mismatch: %s" % r["data"]["router_response"]["execution_mode"]
PYEOF
done

# ---------------------------------------------------------------------------
# [3/5] Error handling
# ---------------------------------------------------------------------------
echo ""
echo "[3/5] Testing OpenClaw error handling..."

py_pass "unsupported request returns ok=False, code=unsupported_request, no traceback" <<'PYEOF'
import sys
sys.path.insert(0, '.')
from openclaw import process_request

r = process_request({
    "client_id": "openclaw-smoke-client",
    "agent": "ads-agent",
    "request": "invalid",
})

assert r["ok"] is False, \
    "ok not False for unsupported request: %r" % r.get("ok")
assert len(r["errors"]) > 0, \
    "errors list empty"
assert r["errors"][0]["code"] == "unsupported_request", \
    "code mismatch: %s" % r["errors"][0]["code"]
assert "traceback" not in r, \
    "traceback field must not be exposed"
PYEOF

py_pass "unsupported agent returns ok=False, code=unsupported_agent, no traceback" <<'PYEOF'
import sys
sys.path.insert(0, '.')
from openclaw import process_request

r = process_request({
    "client_id": "openclaw-smoke-client",
    "agent": "analytics-agent",
    "request": "summary",
})

assert r["ok"] is False, \
    "ok not False for unsupported agent: %r" % r.get("ok")
assert len(r["errors"]) > 0, \
    "errors list empty"
assert r["errors"][0]["code"] == "unsupported_agent", \
    "code mismatch: %s" % r["errors"][0]["code"]
assert "traceback" not in r, \
    "traceback field must not be exposed"
PYEOF

# ---------------------------------------------------------------------------
# [4/5] trace_id propagation
# ---------------------------------------------------------------------------
echo ""
echo "[4/5] Testing trace_id propagation..."

py_pass "trace_id from metadata is propagated to openclaw envelope" <<'PYEOF'
import sys
sys.path.insert(0, '.')
from openclaw import process_request

r = process_request({
    "client_id": "openclaw-smoke-client",
    "agent": "ads-agent",
    "request": "summary",
    "metadata": {"trace_id": "trace-test-123"},
})

assert r["openclaw"]["trace_id"] == "trace-test-123", \
    "trace_id not propagated: got %s" % r["openclaw"]["trace_id"]
PYEOF

# ---------------------------------------------------------------------------
# [5/5] CLI demo
# ---------------------------------------------------------------------------
echo ""
echo "[5/5] Testing CLI demo..."

(cd ~/kaiju/openclaw && $PYTHON run_openclaw_demo.py summary       >/dev/null 2>&1) \
    && pass "run_openclaw_demo.py summary exits cleanly" \
    || { echo "  ✗ run_openclaw_demo.py summary failed"; exit 1; }

(cd ~/kaiju/openclaw && $PYTHON run_openclaw_demo.py invalid       >/dev/null 2>&1) \
    && pass "run_openclaw_demo.py invalid exits cleanly" \
    || { echo "  ✗ run_openclaw_demo.py invalid failed"; exit 1; }

(cd ~/kaiju/openclaw && $PYTHON run_openclaw_demo.py summary analytics-agent >/dev/null 2>&1) \
    && pass "run_openclaw_demo.py summary analytics-agent exits cleanly" \
    || { echo "  ✗ run_openclaw_demo.py summary analytics-agent failed"; exit 1; }

echo ""
echo "=== V3 OpenClaw smoke test passed. ==="

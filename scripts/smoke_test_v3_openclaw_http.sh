#!/usr/bin/env bash
set -euo pipefail

PYTHON=~/kaiju/.venv/bin/python3
OPENCLAW_DIR=~/kaiju/openclaw
PORT=8100
SERVER_PID=""
BASE_URL="http://localhost:${PORT}"

cleanup() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -f /tmp/kaiju_smoke_v3_http_*.py /tmp/openclaw_http_smoke.log 2>/dev/null || true
}
trap cleanup EXIT

pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; exit 1; }

py_http_pass() {
    local label="$1"
    local tmpfile
    tmpfile=$(mktemp /tmp/kaiju_smoke_v3_http_XXXXXX.py)
    cat > "$tmpfile"
    if $PYTHON "$tmpfile" >/dev/null 2>&1; then
        pass "$label"
    else
        echo "  ✗ $label"
        $PYTHON "$tmpfile" 2>&1 | head -20 || true
        rm -f "$tmpfile"
        exit 1
    fi
    rm -f "$tmpfile"
}

echo "=== Kaiju Command Center V3 OpenClaw HTTP Smoke Test ==="
echo ""

# ---------------------------------------------------------------------------
# [1/6] Environment
# ---------------------------------------------------------------------------
echo "[1/6] Checking environment..."

[[ -f "$PYTHON" ]] \
    && pass "Python found at $PYTHON" \
    || fail "Python not found at $PYTHON"

$PYTHON -c "import fastapi, uvicorn, requests" >/dev/null 2>&1 \
    && pass "fastapi, uvicorn, requests importable" \
    || fail "Missing dependency: fastapi, uvicorn, or requests"

if curl -s --max-time 2 "${BASE_URL}/openclaw/health" >/dev/null 2>&1; then
    echo "  Port ${PORT} is already in use. Stop the existing OpenClaw server before running this smoke test."
    exit 1
fi
pass "Port ${PORT} is available"

# ---------------------------------------------------------------------------
# [2/6] Start server
# ---------------------------------------------------------------------------
echo ""
echo "[2/6] Starting OpenClaw HTTP server..."

cd "$OPENCLAW_DIR"
$PYTHON -m uvicorn server:app --host 0.0.0.0 --port "$PORT" --log-level warning \
    > /tmp/openclaw_http_smoke.log 2>&1 &
SERVER_PID=$!
echo "  Server PID: $SERVER_PID"

ELAPSED=0
TIMEOUT=10
echo -n "  Waiting for server"
while true; do
    if curl -s --max-time 1 "${BASE_URL}/openclaw/health" >/dev/null 2>&1; then
        echo ""
        pass "Server healthy (started in ${ELAPSED}s)"
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    echo -n "."
    if [ "$ELAPSED" -ge "$TIMEOUT" ]; then
        echo ""
        echo "  ✗ Server did not become healthy within ${TIMEOUT}s"
        echo "  Server startup log:"
        cat /tmp/openclaw_http_smoke.log 2>/dev/null | head -20 || true
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# [3/6] Metadata and health
# ---------------------------------------------------------------------------
echo ""
echo "[3/6] Testing metadata and health endpoints..."

py_http_pass "GET / returns service metadata" <<'PYEOF'
import requests

r = requests.get("http://localhost:8100/", timeout=10)
d = r.json()
assert d["service"] == "kaiju-openclaw", \
    "service mismatch: %s" % d.get("service")
assert d["status"] == "ok", \
    "status mismatch: %s" % d.get("status")
assert "/openclaw/process" in d["endpoints"], \
    "/openclaw/process missing from endpoints: %s" % d.get("endpoints")
PYEOF

py_http_pass "GET /openclaw/health returns ok=true and healthy" <<'PYEOF'
import requests

r = requests.get("http://localhost:8100/openclaw/health", timeout=10)
d = r.json()
assert d["ok"] is True, \
    "ok not True: %r" % d.get("ok")
assert d["service"] == "kaiju-openclaw", \
    "service mismatch: %s" % d.get("service")
assert d["status"] == "healthy", \
    "status mismatch: %s" % d.get("status")
PYEOF

# ---------------------------------------------------------------------------
# [4/6] Valid process requests
# ---------------------------------------------------------------------------
echo ""
echo "[4/6] Testing valid process requests..."

py_http_pass "POST summary: full envelope, trace_id propagation, router_response" <<'PYEOF'
import requests

r = requests.post(
    "http://localhost:8100/openclaw/process",
    json={
        "client_id": "openclaw-http-smoke-client",
        "agent": "ads-agent",
        "request": "summary",
        "metadata": {"trace_id": "http-smoke-trace-123"},
    },
    timeout=30,
)
d = r.json()
assert d["ok"] is True, \
    "ok not True: %r" % d.get("ok")
assert d["openclaw"]["version"] == "0.1.0", \
    "version mismatch: %s" % d["openclaw"]["version"]
assert d["openclaw"]["trace_id"] == "http-smoke-trace-123", \
    "trace_id not propagated: %s" % d["openclaw"]["trace_id"]
assert d["openclaw"]["tenant"] == "openclaw-http-smoke-client", \
    "tenant mismatch: %s" % d["openclaw"]["tenant"]
assert "router_response" in d["data"], \
    "data.router_response missing"
assert d["data"]["router_response"]["ok"] is True, \
    "router_response.ok not True"
assert d["data"]["router_response"]["execution_mode"] == "graph", \
    "execution_mode mismatch: %s" % d["data"]["router_response"]["execution_mode"]
PYEOF

for req in cpa conversions raw; do
    py_http_pass "POST ${req}: ok=true, router_response.ok=true" <<PYEOF
import requests

r = requests.post(
    "http://localhost:8100/openclaw/process",
    json={
        "client_id": "openclaw-http-smoke-client",
        "agent": "ads-agent",
        "request": "${req}",
    },
    timeout=30,
)
d = r.json()
assert d["ok"] is True, \
    "ok not True for ${req}: %r" % d.get("ok")
assert d["data"]["router_response"]["ok"] is True, \
    "router_response.ok not True for ${req}"
PYEOF
done

# ---------------------------------------------------------------------------
# [5/6] Error handling
# ---------------------------------------------------------------------------
echo ""
echo "[5/6] Testing error handling..."

py_http_pass "POST unsupported request: ok=false, code=unsupported_request" <<'PYEOF'
import requests

r = requests.post(
    "http://localhost:8100/openclaw/process",
    json={"client_id": "openclaw-http-smoke-client", "agent": "ads-agent", "request": "invalid"},
    timeout=10,
)
d = r.json()
assert d["ok"] is False, \
    "ok not False: %r" % d.get("ok")
assert len(d["errors"]) > 0, \
    "errors list empty"
assert d["errors"][0]["code"] == "unsupported_request", \
    "code mismatch: %s" % d["errors"][0]["code"]
PYEOF

py_http_pass "POST unsupported agent: ok=false, code=unsupported_agent" <<'PYEOF'
import requests

r = requests.post(
    "http://localhost:8100/openclaw/process",
    json={"client_id": "openclaw-http-smoke-client", "agent": "analytics-agent", "request": "summary"},
    timeout=10,
)
d = r.json()
assert d["ok"] is False, \
    "ok not False: %r" % d.get("ok")
assert len(d["errors"]) > 0, \
    "errors list empty"
assert d["errors"][0]["code"] == "unsupported_agent", \
    "code mismatch: %s" % d["errors"][0]["code"]
PYEOF

py_http_pass "POST malformed JSON: ok=false, code=invalid_json, no traceback" <<'PYEOF'
import requests

r = requests.post(
    "http://localhost:8100/openclaw/process",
    data=b"{bad json}",
    headers={"Content-Type": "application/json"},
    timeout=10,
)
d = r.json()
assert d["ok"] is False, \
    "ok not False: %r" % d.get("ok")
assert len(d["errors"]) > 0, \
    "errors list empty"
assert d["errors"][0]["code"] == "invalid_json", \
    "code mismatch: %s" % d["errors"][0]["code"]
assert "traceback" not in d, \
    "traceback must not be exposed"
PYEOF

# ---------------------------------------------------------------------------
# [6/6] Cleanup
# ---------------------------------------------------------------------------
echo ""
echo "[6/6] Cleaning up..."
if kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
    pass "OpenClaw HTTP server stopped (PID $SERVER_PID)"
fi
SERVER_PID=""

echo ""
echo "=== V3 OpenClaw HTTP smoke test passed. ==="

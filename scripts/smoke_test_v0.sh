#!/usr/bin/env bash
set -euo pipefail

PYTHON=~/kaiju/.venv/bin/python3
REPO=~/kaiju
ROUTER_URL=http://localhost:8000

SERVER_PID=""
SERVER_STARTED_BY_SCRIPT=false

# ---------------------------------------------------------------------------
# Cleanup: stop server only if this script started it
# ---------------------------------------------------------------------------
cleanup() {
    if [ "$SERVER_STARTED_BY_SCRIPT" = true ] && [ -n "$SERVER_PID" ]; then
        echo ""
        echo "Stopping Router server (PID $SERVER_PID)..."
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
        echo "Router server stopped."
    fi
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; exit 1; }

assert_ok() {
    local label="$1"
    local response="$2"
    if echo "$response" | grep -q '"ok": true\|"ok":true'; then
        pass "$label"
    else
        echo "  ✗ $label — unexpected response:"
        echo "$response"
        exit 1
    fi
}

assert_error() {
    local label="$1"
    local expected_error="$2"
    local response="$3"
    if echo "$response" | grep -q "\"ok\": false\|\"ok\":false" && \
       echo "$response" | grep -q "$expected_error"; then
        pass "$label"
    else
        echo "  ✗ $label — unexpected response:"
        echo "$response"
        exit 1
    fi
}

route_post() {
    local data="$1"
    curl -s -X POST "$ROUTER_URL/route" \
        -H "Content-Type: application/json" \
        -d "$data"
}

# ---------------------------------------------------------------------------
# Section 1: Virtual environment
# ---------------------------------------------------------------------------
echo ""
echo "=== Kaiju Command Center V0 Smoke Test ==="
echo ""
echo "[1/6] Checking virtual environment..."

if [ ! -f "$PYTHON" ]; then
    echo "  Missing virtual environment. Expected: ~/kaiju/.venv/bin/python3"
    exit 1
fi
pass "Python found at $PYTHON"

# ---------------------------------------------------------------------------
# Section 2: Dependencies
# ---------------------------------------------------------------------------
echo ""
echo "[2/6] Checking dependencies..."

$PYTHON -c "import fastapi" 2>/dev/null && pass "fastapi" || fail "fastapi not importable"
$PYTHON -c "import uvicorn"  2>/dev/null && pass "uvicorn"  || fail "uvicorn not importable"
$PYTHON -c "import requests" 2>/dev/null && pass "requests" || fail "requests not importable"

# ---------------------------------------------------------------------------
# Section 3: Router HTTP server
# ---------------------------------------------------------------------------
echo ""
echo "[3/6] Checking Router HTTP server..."

if curl -s --max-time 2 "$ROUTER_URL/health" | grep -q '"ok"'; then
    pass "Router already running at $ROUTER_URL"
else
    echo "  Router not running — starting it..."
    cd "$REPO/agents/router"
    $PYTHON -m uvicorn server:app --host 0.0.0.0 --port 8000 \
        > /tmp/kaiju_uvicorn.log 2>&1 &
    SERVER_PID=$!
    SERVER_STARTED_BY_SCRIPT=true
    echo "  Server PID: $SERVER_PID"

    # Wait up to 8 seconds for it to be ready
    for i in $(seq 1 8); do
        sleep 1
        if curl -s --max-time 2 "$ROUTER_URL/health" | grep -q '"ok"'; then
            pass "Router started and healthy (waited ${i}s)"
            break
        fi
        if [ "$i" -eq 8 ]; then
            echo "  Router did not become healthy after 8s"
            cat /tmp/kaiju_uvicorn.log
            exit 1
        fi
    done
fi

# ---------------------------------------------------------------------------
# Section 4: HTTP route tests
# ---------------------------------------------------------------------------
echo ""
echo "[4/6] Testing HTTP routes..."

# Health
response=$(curl -s --max-time 5 "$ROUTER_URL/health")
assert_ok "GET /health" "$response"

# Metadata
response=$(curl -s --max-time 5 "$ROUTER_URL/")
if echo "$response" | grep -q '"service"'; then
    pass "GET / (metadata)"
else
    fail "GET / — unexpected response: $response"
fi

# Happy paths
assert_ok "POST /route summary" \
    "$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"summary"}')"

assert_ok "POST /route cpa" \
    "$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"cpa"}')"

assert_ok "POST /route conversions" \
    "$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"conversions"}')"

assert_ok "POST /route raw" \
    "$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"raw"}')"

# Error paths
assert_error "POST /route unsupported agent" "unsupported_agent" \
    "$(route_post '{"client_id":"demo-client","agent":"analytics-agent","request":"summary"}')"

assert_error "POST /route unsupported request" "unsupported_request" \
    "$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"invalid"}')"

# ---------------------------------------------------------------------------
# Section 5: Demo Client
# ---------------------------------------------------------------------------
echo ""
echo "[5/6] Testing Demo Client..."

cd "$REPO/projects/demo-client"
for req in summary cpa conversions raw; do
    output=$($PYTHON client.py "$req" 2>&1)
    if echo "$output" | grep -q '"ok": true\|"ok":true'; then
        pass "client.py $req"
    else
        echo "  ✗ client.py $req — unexpected output:"
        echo "$output"
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Section 6: CLI regressions
# ---------------------------------------------------------------------------
echo ""
echo "[6/6] Running CLI regressions..."

echo "  Router demos:"
cd "$REPO/agents/router"
for req in summary cpa conversions raw; do
    output=$($PYTHON run_router_demo.py "$req" 2>&1)
    if echo "$output" | grep -q '"ok": true\|"ok":true'; then
        pass "run_router_demo.py $req"
    else
        echo "  ✗ run_router_demo.py $req — unexpected output:"
        echo "$output"
        exit 1
    fi
done

echo "  Ads Agent n8n demos:"
cd "$REPO/agents/ads-agent"
for req in summary cpa conversions raw; do
    output=$($PYTHON run_n8n_demo.py "$req" 2>&1)
    # n8n demos print formatted text, not JSON — just check for no error lines
    if echo "$output" | grep -iq "error\|traceback\|exception"; then
        echo "  ✗ run_n8n_demo.py $req — output contained error:"
        echo "$output"
        exit 1
    else
        pass "run_n8n_demo.py $req"
    fi
done

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "=== V0 smoke test passed. ==="
echo ""

#!/usr/bin/env bash
set -euo pipefail

PYTHON=~/kaiju/.venv/bin/python3
REPO=~/kaiju
ROUTER_URL=http://localhost:8000

SERVER_PID=""

# ---------------------------------------------------------------------------
# Cleanup: always stop server started by this script
# ---------------------------------------------------------------------------
cleanup() {
    if [ -n "$SERVER_PID" ]; then
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

assert_graph_ok() {
    local label="$1"
    local response="$2"

    local ok=false
    local has_graph=false

    echo "$response" | grep -q '"ok": true\|"ok":true' && ok=true || true
    echo "$response" | grep -q '"execution_mode": "graph"\|"execution_mode":"graph"' && has_graph=true || true

    if [ "$ok" = true ] && [ "$has_graph" = true ]; then
        pass "$label"
    else
        echo "  ✗ $label — expected ok:true and execution_mode:\"graph\":"
        echo "$response"
        exit 1
    fi
}

assert_field() {
    local label="$1"
    local field="$2"
    local response="$3"

    if echo "$response" | grep -q "\"$field\""; then
        pass "$label"
    else
        echo "  ✗ $label — field '$field' not found:"
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
echo "=== Kaiju Command Center V1 Graph Smoke Test ==="
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

$PYTHON -c "import fastapi"   2>/dev/null && pass "fastapi"   || fail "fastapi not importable"
$PYTHON -c "import uvicorn"   2>/dev/null && pass "uvicorn"   || fail "uvicorn not importable"
$PYTHON -c "import requests"  2>/dev/null && pass "requests"  || fail "requests not importable"
$PYTHON -c "import langgraph" 2>/dev/null && pass "langgraph" || fail "langgraph not importable"

# ---------------------------------------------------------------------------
# Section 3: Start Router in graph mode
# ---------------------------------------------------------------------------
echo ""
echo "[3/6] Starting Router in graph mode..."

if curl -s --max-time 2 "$ROUTER_URL/health" | grep -q '"ok"' 2>/dev/null; then
    echo "  Port 8000 is already in use. Stop the existing Router server before running the V1 graph smoke test."
    exit 1
fi

cd "$REPO/agents/router"
ADS_AGENT_EXECUTION_MODE=graph $PYTHON -m uvicorn server:app --host 0.0.0.0 --port 8000 \
    > /tmp/kaiju_v1_uvicorn.log 2>&1 &
SERVER_PID=$!
echo "  Server PID: $SERVER_PID (ADS_AGENT_EXECUTION_MODE=graph)"

for i in $(seq 1 8); do
    sleep 1
    if curl -s --max-time 2 "$ROUTER_URL/health" | grep -q '"ok"' 2>/dev/null; then
        pass "Router started in graph mode (waited ${i}s)"
        break
    fi
    if [ "$i" -eq 8 ]; then
        echo "  Router did not become healthy after 8s:"
        cat /tmp/kaiju_v1_uvicorn.log
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Section 4: HTTP graph route tests
# ---------------------------------------------------------------------------
echo ""
echo "[4/6] Testing HTTP graph routes..."

# Health
response=$(curl -s --max-time 5 "$ROUTER_URL/health")
if echo "$response" | grep -q '"ok"'; then
    pass "GET /health"
else
    fail "GET /health — unexpected: $response"
fi

# summary — ok + execution_mode:graph + analysis + recommendations
response=$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"summary"}')
assert_graph_ok  "POST /route summary — ok + execution_mode:graph" "$response"
assert_field     "POST /route summary — contains analysis"         "analysis"         "$response"
assert_field     "POST /route summary — contains recommendations"  "recommendations"  "$response"

# cpa
response=$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"cpa"}')
assert_graph_ok  "POST /route cpa — ok + execution_mode:graph" "$response"
assert_field     "POST /route cpa — contains cpa field"        "cpa"  "$response"

# conversions
response=$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"conversions"}')
assert_graph_ok  "POST /route conversions — ok + execution_mode:graph"    "$response"
assert_field     "POST /route conversions — contains conversions field"   "conversions"  "$response"

# raw
response=$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"raw"}')
assert_graph_ok  "POST /route raw — ok + execution_mode:graph" "$response"
assert_field     "POST /route raw — contains metrics field"    "metrics"  "$response"

# ---------------------------------------------------------------------------
# Section 5: Demo Client through graph mode
# ---------------------------------------------------------------------------
echo ""
echo "[5/6] Testing Demo Client through graph mode..."

cd "$REPO/projects/demo-client"
for req in summary cpa conversions raw; do
    output=$($PYTHON client.py "$req" 2>&1)
    ok=false
    has_graph=false
    echo "$output" | grep -q '"ok": true\|"ok":true' && ok=true || true
    echo "$output" | grep -q '"execution_mode": "graph"\|"execution_mode":"graph"' && has_graph=true || true
    if [ "$ok" = true ] && [ "$has_graph" = true ]; then
        pass "client.py $req"
    else
        echo "  ✗ client.py $req — expected ok:true and execution_mode:\"graph\":"
        echo "$output"
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Section 6: Direct Ads Graph demos
# ---------------------------------------------------------------------------
echo ""
echo "[6/6] Testing direct Ads Graph demos..."

cd "$REPO/agents/ads-agent"
for req in summary cpa conversions raw; do
    output=$($PYTHON run_graph_demo.py "$req" 2>&1)
    ok=false
    has_graph=false
    echo "$output" | grep -q '"ok": true\|"ok":true' && ok=true || true
    echo "$output" | grep -q '"execution_mode": "graph"\|"execution_mode":"graph"' && has_graph=true || true
    if [ "$ok" = true ] && [ "$has_graph" = true ]; then
        pass "run_graph_demo.py $req"
    else
        echo "  ✗ run_graph_demo.py $req — expected ok:true and execution_mode:\"graph\":"
        echo "$output"
        exit 1
    fi
done

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "=== V1 graph smoke test passed. ==="
echo ""

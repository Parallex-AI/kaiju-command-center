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

assert_legacy_ok() {
    local label="$1"
    local response="$2"

    local ok=false
    local has_legacy=false

    echo "$response" | grep -q '"ok": true\|"ok":true' && ok=true || true
    echo "$response" | grep -q '"execution_mode": "legacy"\|"execution_mode":"legacy"' && has_legacy=true || true

    if [ "$ok" = true ] && [ "$has_legacy" = true ]; then
        pass "$label"
    else
        echo "  ✗ $label — expected ok:true and execution_mode:\"legacy\":"
        echo "$response"
        exit 1
    fi
}

# assert_py: run a block of Python against a JSON response; pass or fail.
# Usage: assert_py "label" "$response" "python_code"
assert_py() {
    local label="$1"
    local response="$2"
    local pycode="$3"

    if echo "$response" | $PYTHON -c "
import json, sys
data = json.load(sys.stdin)
$pycode
" 2>/dev/null; then
        pass "$label"
    else
        echo "  ✗ $label"
        echo "  Response: $(echo "$response" | $PYTHON -m json.tool 2>/dev/null | head -30 || echo "$response" | head -c 300)"
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
echo "[1/7] Checking virtual environment..."

if [ ! -f "$PYTHON" ]; then
    echo "  Missing virtual environment. Expected: ~/kaiju/.venv/bin/python3"
    exit 1
fi
pass "Python found at $PYTHON"

# ---------------------------------------------------------------------------
# Section 2: Dependencies
# ---------------------------------------------------------------------------
echo ""
echo "[2/7] Checking dependencies..."

$PYTHON -c "import fastapi"   2>/dev/null && pass "fastapi"   || fail "fastapi not importable"
$PYTHON -c "import uvicorn"   2>/dev/null && pass "uvicorn"   || fail "uvicorn not importable"
$PYTHON -c "import requests"  2>/dev/null && pass "requests"  || fail "requests not importable"
$PYTHON -c "import langgraph" 2>/dev/null && pass "langgraph" || fail "langgraph not importable"

# ---------------------------------------------------------------------------
# Section 3: Start Router in default graph mode
# ---------------------------------------------------------------------------
echo ""
echo "[3/7] Starting Router in default graph mode (no env var)..."

if curl -s --max-time 2 "$ROUTER_URL/health" | grep -q '"ok"' 2>/dev/null; then
    echo "  Port 8000 is already in use. Stop the existing Router server before running the V1 graph smoke test."
    exit 1
fi

cd "$REPO/agents/router"
$PYTHON -m uvicorn server:app --host 0.0.0.0 --port 8000 \
    > /tmp/kaiju_v1_uvicorn.log 2>&1 &
SERVER_PID=$!
echo "  Server PID: $SERVER_PID (ADS_AGENT_EXECUTION_MODE unset — default graph)"

for i in $(seq 1 8); do
    sleep 1
    if curl -s --max-time 2 "$ROUTER_URL/health" | grep -q '"ok"' 2>/dev/null; then
        pass "Router started in default graph mode (waited ${i}s)"
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
echo "[4/7] Testing HTTP graph routes..."

# Health
response=$(curl -s --max-time 5 "$ROUTER_URL/health")
if echo "$response" | grep -q '"ok"'; then
    pass "GET /health"
else
    fail "GET /health — unexpected: $response"
fi

# ---- summary ----
response=$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"summary"}')

# Routing / envelope
assert_graph_ok "POST /route summary — ok + execution_mode:graph"       "$response"
assert_field    "POST /route summary — contains analysis"               "analysis"        "$response"
assert_field    "POST /route summary — contains recommendations"        "recommendations" "$response"

# V1.4 — derived metrics
assert_py "POST /route summary — metrics has derived fields (ctr, cpc, conversion_rate, cpm)" "$response" \
"m = data['data']['data']['metrics']
assert 'ctr' in m, 'ctr missing'
assert 'cpc' in m, 'cpc missing'
assert 'conversion_rate' in m, 'conversion_rate missing'
assert 'cpm' in m, 'cpm missing'"

# V1.4 — unavailable_metrics
assert_py "POST /route summary — unavailable_metrics declared and contains roas" "$response" \
"m = data['data']['data']['metrics']
um = m['unavailable_metrics']
assert isinstance(um, list), 'unavailable_metrics not a list'
assert 'roas' in um, 'roas not in unavailable_metrics'"

# V1.4 — analysis classification fields
assert_py "POST /route summary — analysis has V1.4 classification fields" "$response" \
"a = data['data']['data']['analysis']
assert 'performance_score' in a, 'performance_score missing'
assert 'cpa_level' in a, 'cpa_level missing'
assert 'ctr_level' in a, 'ctr_level missing'
assert 'conversion_rate_level' in a, 'conversion_rate_level missing'
assert 'spend_efficiency' in a, 'spend_efficiency missing'"

# V1.4 — recommendations list
assert_py "POST /route summary — recommendations is non-empty list" "$response" \
"recs = data['data']['data']['recommendations']
assert isinstance(recs, list), 'recommendations not a list'
assert len(recs) > 0, 'recommendations list is empty for current demo data'"

# V1.4 — recommendation structured schema
assert_py "POST /route summary — recommendation uses full structured schema" "$response" \
"r = data['data']['data']['recommendations'][0]
for field in ('type', 'severity', 'priority', 'area', 'action', 'expected_impact', 'rationale'):
    assert field in r, field + ' missing from recommendation'"

# V1.4 — executive_summary
assert_py "POST /route summary — executive_summary exists" "$response" \
"assert 'executive_summary' in data['data']['data'], 'executive_summary missing'"

assert_py "POST /route summary — executive_summary has all fields" "$response" \
"es = data['data']['data']['executive_summary']
for field in ('headline', 'summary', 'next_best_action', 'confidence'):
    assert field in es, field + ' missing from executive_summary'"

# ---- cpa ----
response=$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"cpa"}')

assert_graph_ok "POST /route cpa — ok + execution_mode:graph" "$response"
assert_field    "POST /route cpa — contains cpa field"        "cpa" "$response"

# V1.4 — cpa assertions
assert_py "POST /route cpa — analysis has performance_score" "$response" \
"assert 'performance_score' in data['data']['data']['analysis'], 'performance_score missing'"

assert_py "POST /route cpa — recommendations exists" "$response" \
"assert 'recommendations' in data['data']['data'], 'recommendations missing'"

assert_py "POST /route cpa — executive_summary exists" "$response" \
"assert 'executive_summary' in data['data']['data'], 'executive_summary missing'"

# ---- conversions ----
response=$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"conversions"}')

assert_graph_ok "POST /route conversions — ok + execution_mode:graph"  "$response"
assert_field    "POST /route conversions — contains conversions field" "conversions" "$response"

# V1.4 — conversions assertions
assert_py "POST /route conversions — conversion_rate field present" "$response" \
"assert 'conversion_rate' in data['data']['data']['metrics'], 'conversion_rate missing'"

assert_py "POST /route conversions — recommendations exists" "$response" \
"assert 'recommendations' in data['data']['data'], 'recommendations missing'"

assert_py "POST /route conversions — executive_summary exists" "$response" \
"assert 'executive_summary' in data['data']['data'], 'executive_summary missing'"

# ---- raw ----
response=$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"raw"}')

assert_graph_ok "POST /route raw — ok + execution_mode:graph" "$response"
assert_field    "POST /route raw — contains metrics field"    "metrics" "$response"

# V1.4 — raw assertion
assert_py "POST /route raw — executive_summary exists" "$response" \
"assert 'executive_summary' in data['data']['data'], 'executive_summary missing'"

# ---------------------------------------------------------------------------
# Section 5: Demo Client through graph mode
# ---------------------------------------------------------------------------
echo ""
echo "[5/7] Testing Demo Client through graph mode..."

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
echo "[6/7] Testing direct Ads Graph demos..."

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
# Section 7: Explicit legacy opt-out check
# ---------------------------------------------------------------------------
echo ""
echo "[7/7] Testing explicit legacy opt-out (ADS_AGENT_EXECUTION_MODE=legacy)..."

# Stop the default-mode server cleanly before starting legacy server
kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true
SERVER_PID=""
echo "  Default graph-mode server stopped."

cd "$REPO/agents/router"
ADS_AGENT_EXECUTION_MODE=legacy $PYTHON -m uvicorn server:app --host 0.0.0.0 --port 8000 \
    > /tmp/kaiju_v1_uvicorn_legacy.log 2>&1 &
SERVER_PID=$!
echo "  Server PID: $SERVER_PID (ADS_AGENT_EXECUTION_MODE=legacy)"

for i in $(seq 1 8); do
    sleep 1
    if curl -s --max-time 2 "$ROUTER_URL/health" | grep -q '"ok"' 2>/dev/null; then
        pass "Legacy Router started (waited ${i}s)"
        break
    fi
    if [ "$i" -eq 8 ]; then
        echo "  Legacy Router did not become healthy after 8s:"
        cat /tmp/kaiju_v1_uvicorn_legacy.log
        exit 1
    fi
done

response=$(route_post '{"client_id":"demo-client","agent":"ads-agent","request":"summary"}')
assert_legacy_ok "POST /route summary — ok + execution_mode:legacy" "$response"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "=== V1 graph smoke test passed. ==="
echo ""

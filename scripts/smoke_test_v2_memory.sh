#!/usr/bin/env bash
set -euo pipefail

PYTHON=~/kaiju/.venv/bin/python3
REPO=~/kaiju
AGENT_DIR="$REPO/agents/ads-agent"
CLIENT_ID="memory-smoke-client"
export SMOKE_CLIENT_ID="$CLIENT_ID"

# ---------------------------------------------------------------------------
# Cleanup temp files on exit
# ---------------------------------------------------------------------------
cleanup() {
    rm -f /tmp/kaiju_smoke_*.py 2>/dev/null || true
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; exit 1; }

# Run Python code from agent dir.  Reads code from stdin (heredoc).
# Usage: py_pass "label" <<'PYEOF' ... PYEOF
py_pass() {
    local label="$1"
    local tmpfile
    tmpfile=$(mktemp /tmp/kaiju_smoke_XXXXXX.py)
    cat > "$tmpfile"
    if (cd "$AGENT_DIR" && $PYTHON "$tmpfile") >/dev/null 2>&1; then
        pass "$label"
    else
        echo "  ✗ $label"
        (cd "$AGENT_DIR" && $PYTHON "$tmpfile") 2>&1 | head -20 || true
        rm -f "$tmpfile"
        exit 1
    fi
    rm -f "$tmpfile"
}

# Same as py_pass but runs with MEMORY_ENABLED=false.
py_pass_mem_off() {
    local label="$1"
    local tmpfile
    tmpfile=$(mktemp /tmp/kaiju_smoke_XXXXXX.py)
    cat > "$tmpfile"
    if (cd "$AGENT_DIR" && MEMORY_ENABLED=false $PYTHON "$tmpfile") >/dev/null 2>&1; then
        pass "$label"
    else
        echo "  ✗ $label"
        (cd "$AGENT_DIR" && MEMORY_ENABLED=false $PYTHON "$tmpfile") 2>&1 | head -20 || true
        rm -f "$tmpfile"
        exit 1
    fi
    rm -f "$tmpfile"
}

# ---------------------------------------------------------------------------
# Section 1: Environment
# ---------------------------------------------------------------------------
echo ""
echo "=== Kaiju Command Center V2 Memory Smoke Test ==="
echo ""
echo "[1/7] Checking environment..."

[ -f "$PYTHON" ] || fail "Python not found at $PYTHON"
pass "Python found at $PYTHON"

$PYTHON -c "import langgraph" 2>/dev/null && pass "langgraph importable" || fail "langgraph not importable"
$PYTHON -c "import requests"  2>/dev/null && pass "requests importable"  || fail "requests not importable"
(cd "$AGENT_DIR" && $PYTHON -c "import mempalace") 2>/dev/null \
    && pass "mempalace importable" || fail "mempalace not importable"
(cd "$AGENT_DIR" && $PYTHON -c "import ads_graph") 2>/dev/null \
    && pass "ads_graph importable"  || fail "ads_graph not importable"

# ---------------------------------------------------------------------------
# Section 2: MemPalace utility functions
# ---------------------------------------------------------------------------
echo ""
echo "[2/7] Testing MemPalace utility functions..."

echo "  Cleaning test client memory: memory/client-memory/$CLIENT_ID"
rm -rf "$REPO/memory/client-memory/$CLIENT_ID"
pass "test client directory cleaned"

py_pass "ensure_client_memory_dirs creates expected dirs" <<'PYEOF'
import os, sys, pathlib
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
result = mempalace.ensure_client_memory_dirs(client_id)
assert result.get('enabled') is True, f"Expected enabled=True, got: {result}"
for key in ('client_dir', 'agent_dir', 'snapshots_dir'):
    assert pathlib.Path(result[key]).exists(), f"{key} not created: {result[key]}"
PYEOF

py_pass "write_profile writes profile.json" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
result = mempalace.write_profile(client_id, mempalace.default_profile(client_id))
assert result.get('ok') is True, f"Expected ok=True, got: {result}"
PYEOF

py_pass "read_profile reads written profile" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
profile = mempalace.read_profile(client_id)
assert isinstance(profile, dict), f"Expected dict, got: {type(profile)}"
assert profile.get('client_id') == client_id, \
    f"client_id mismatch: expected '{client_id}', got '{profile.get('client_id')}'"
PYEOF

py_pass "write_snapshot writes summary snapshot and updates latest_summary" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
snapshot = {
    'metrics': {'spend': 100.0, 'conversions': 5, 'cpa': 20.0},
    'analysis': {'performance_score': 70, 'risk_flags': [], 'notes': []},
    'recommendations': [
        {'type': 'optimization', 'severity': 'medium', 'priority': 'medium',
         'area': 'CPA Optimization', 'action': 'Review targeting.',
         'expected_impact': 'Reduce CPA.', 'rationale': 'CPA above target.'},
    ],
}
result = mempalace.write_snapshot(client_id, snapshot, request_type='summary')
assert result.get('ok') is True, f"Expected ok=True, got: {result}"
assert 'latest_summary_path' in result, f"latest_summary_path missing: {result}"
PYEOF

py_pass "read_latest_summary returns written data" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
latest = mempalace.read_latest_summary(client_id)
assert latest is not None, "Expected read_latest_summary to return a dict, got None"
assert isinstance(latest, dict), f"Expected dict, got: {type(latest)}"
assert 'timestamp' in latest, f"timestamp missing from latest_summary"
PYEOF

py_pass "append_recommendations writes JSONL" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
recs = [
    {'type': 'optimization', 'severity': 'medium', 'priority': 'medium',
     'area': 'CPA Optimization', 'action': 'Review targeting.',
     'expected_impact': 'Reduce CPA.', 'rationale': 'CPA above target.'},
    {'type': 'strategy', 'severity': 'low', 'priority': 'low',
     'area': 'Monitoring', 'action': 'Continue monitoring.',
     'expected_impact': 'Stable performance.', 'rationale': 'No critical issue found.'},
]
result = mempalace.append_recommendations(client_id, recs)
assert result.get('ok') is True, f"Expected ok=True, got: {result}"
assert result.get('written', 0) >= 1, f"Expected written >= 1, got: {result.get('written')}"
PYEOF

py_pass "append_insight writes JSONL" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
result = mempalace.append_insight(client_id, {
    'insight_type': 'trend',
    'summary': 'CPA stable across test runs.',
    'evidence': {'cpa_direction': 'stable'},
})
assert result.get('ok') is True, f"Expected ok=True, got: {result}"
PYEOF

py_pass "read_recent_snapshots returns at least one snapshot" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
snapshots = mempalace.read_recent_snapshots(client_id)
assert isinstance(snapshots, list), f"Expected list, got: {type(snapshots)}"
assert len(snapshots) >= 1, f"Expected at least one snapshot, got: {len(snapshots)}"
assert isinstance(snapshots[0], dict), f"Expected dict snapshot"
assert 'timestamp' in snapshots[0], f"timestamp missing from snapshot"
PYEOF

# ---------------------------------------------------------------------------
# Section 3: Memory disabled utility behavior
# ---------------------------------------------------------------------------
echo ""
echo "[3/7] Testing memory disabled utility behavior..."

py_pass_mem_off "ensure_client_memory_dirs returns enabled=false when disabled" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
result = mempalace.ensure_client_memory_dirs(client_id)
assert result.get('enabled') is False, f"Expected enabled=False, got: {result}"
PYEOF

py_pass_mem_off "read_profile returns default profile with _memory_enabled=false when disabled" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
profile = mempalace.read_profile(client_id)
assert profile.get('_memory_enabled') is False, \
    f"Expected _memory_enabled=False, got: {profile.get('_memory_enabled')}"
PYEOF

py_pass_mem_off "write_profile returns ok=false when disabled" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
result = mempalace.write_profile(client_id, {})
assert result.get('ok') is False, f"Expected ok=False, got: {result}"
PYEOF

py_pass_mem_off "write_snapshot returns ok=false when disabled" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
result = mempalace.write_snapshot(client_id, {}, request_type='summary')
assert result.get('ok') is False, f"Expected ok=False, got: {result}"
PYEOF

py_pass_mem_off "read_latest_summary returns None when disabled" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
result = mempalace.read_latest_summary(client_id)
assert result is None, f"Expected None, got: {result}"
PYEOF

py_pass_mem_off "read_recent_snapshots returns [] when disabled" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
import mempalace
client_id = os.environ['SMOKE_CLIENT_ID']
result = mempalace.read_recent_snapshots(client_id)
assert result == [], f"Expected [], got: {result}"
PYEOF

# ---------------------------------------------------------------------------
# Section 4: Ads Graph memory integration
# ---------------------------------------------------------------------------
echo ""
echo "[4/7] Testing Ads Graph memory integration..."

echo "  Running graph summary run 1 (seeds history)..."
py_pass "graph summary run 1 completes ok with graph execution mode" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
from ads_graph import run_ads_graph
client_id = os.environ['SMOKE_CLIENT_ID']
r = run_ads_graph(client_id, 'summary')
assert r.get('ok') is True, f"Expected ok=True, got: {r.get('ok')}"
assert r.get('execution_mode') == 'graph', \
    f"Expected execution_mode=graph, got: {r.get('execution_mode')}"
assert 'data' in r, "response missing 'data'"
PYEOF

echo "  Running graph summary run 2 (should detect history)..."
py_pass "graph summary run 2 detects history and enriched historical_comparison" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
from ads_graph import run_ads_graph
client_id = os.environ['SMOKE_CLIENT_ID']
r = run_ads_graph(client_id, 'summary')
assert r.get('ok') is True, f"Expected ok=True, got: {r.get('ok')}"

mem = r.get('data', {}).get('memory', {})
assert mem.get('enabled') is True, \
    f"Expected memory.enabled=True, got: {mem.get('enabled')}"
assert mem.get('has_history') is True, \
    f"Expected memory.has_history=True, got: {mem.get('has_history')}"

hc = mem.get('historical_comparison', {})
assert hc.get('has_history') is True, \
    f"Expected historical_comparison.has_history=True, got: {hc.get('has_history')}"
assert hc.get('history_count', 0) >= 1, \
    f"Expected history_count >= 1, got: {hc.get('history_count')}"
assert hc.get('comparison_window', 0) >= 1, \
    f"Expected comparison_window >= 1, got: {hc.get('comparison_window')}"
assert 'cpa_direction' in hc, "cpa_direction missing from historical_comparison"
assert 'conversions_direction' in hc, "conversions_direction missing"
assert 'ctr_direction' in hc, "ctr_direction missing"
assert 'conversion_rate_direction' in hc, "conversion_rate_direction missing"
assert 'performance_score_direction' in hc, "performance_score_direction missing"
assert isinstance(hc.get('recurring_risk_flags'), list), \
    f"recurring_risk_flags not a list: {hc.get('recurring_risk_flags')}"
assert isinstance(hc.get('recurring_recommendation_areas'), list), \
    f"recurring_recommendation_areas not a list: {hc.get('recurring_recommendation_areas')}"

wr = mem.get('write_result', {})
assert wr.get('ok') is True, f"Expected write_result.ok=True, got: {wr}"
PYEOF

# ---------------------------------------------------------------------------
# Section 5: Raw mode memory skip
# ---------------------------------------------------------------------------
echo ""
echo "[5/7] Testing raw mode memory skip..."

py_pass "graph raw mode skips memory write with raw skip reason" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
from ads_graph import run_ads_graph
client_id = os.environ['SMOKE_CLIENT_ID']
r = run_ads_graph(client_id, 'raw')
assert r.get('ok') is True, f"Expected ok=True, got: {r.get('ok')}"
mem = r.get('data', {}).get('memory', {})
wr = mem.get('write_result', {})
assert wr.get('skipped') is True, \
    f"Expected write_result.skipped=True, got: {wr}"
reason = wr.get('reason', '')
assert 'raw' in reason.lower(), \
    f"Expected 'raw' in skip reason, got: '{reason}'"
PYEOF

# ---------------------------------------------------------------------------
# Section 6: Graph memory disabled behavior
# ---------------------------------------------------------------------------
echo ""
echo "[6/7] Testing graph memory disabled behavior..."

py_pass_mem_off "graph with MEMORY_ENABLED=false returns ok=true and memory.enabled=false" <<'PYEOF'
import os, sys
sys.path.insert(0, '.')
from ads_graph import run_ads_graph
client_id = os.environ['SMOKE_CLIENT_ID']
r = run_ads_graph(client_id, 'summary')
assert r.get('ok') is True, f"Expected ok=True, got: {r.get('ok')}"
mem = r.get('data', {}).get('memory', {})
assert mem.get('enabled') is False, \
    f"Expected memory.enabled=False, got: {mem.get('enabled')}"
wr = mem.get('write_result', {})
assert wr.get('skipped') is True, \
    f"Expected write_result.skipped=True, got: {wr}"
PYEOF

# ---------------------------------------------------------------------------
# Section 7: Runtime memory remains ignored
# ---------------------------------------------------------------------------
echo ""
echo "[7/7] Verifying runtime memory remains ignored..."

cd "$REPO"
ignored_output=$(git status --short memory/client-memory 2>/dev/null || true)
if [ -z "$ignored_output" ]; then
    pass "memory/client-memory/ is ignored by Git (no output from git status)"
else
    echo "  ✗ memory/client-memory/ appears in git status — check .gitignore"
    echo "$ignored_output"
    exit 1
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "=== V2 memory smoke test passed. ==="
echo ""

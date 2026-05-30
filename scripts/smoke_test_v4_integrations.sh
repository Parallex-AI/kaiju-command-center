#!/usr/bin/env bash
set -euo pipefail

PYTHON=~/kaiju/.venv/bin/python3
REPO=~/kaiju
AGENT_DIR="$REPO/agents/ads-agent"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
cleanup() {
    rm -f /tmp/kaiju_smoke_v4_*.py 2>/dev/null || true
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; exit 1; }

# Run Python snippet from AGENT_DIR with AGENT_DIR on PYTHONPATH.
# Usage: py_pass "label" <<'PYEOF' ... PYEOF
py_pass() {
    local label="$1"
    local tmpfile
    tmpfile=$(mktemp /tmp/kaiju_smoke_v4_XXXXXX.py)
    cat > "$tmpfile"
    if (cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON "$tmpfile") >/dev/null 2>&1; then
        pass "$label"
    else
        echo "  ✗ $label"
        (cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON "$tmpfile") 2>&1 | head -30 || true
        rm -f "$tmpfile"
        exit 1
    fi
    rm -f "$tmpfile"
}

# Run Python snippet with additional env vars (passed as "VAR=val" strings after label).
# The heredoc is read from stdin.
# Usage: py_pass_env "label" "VAR1=val1" "VAR2=val2" <<'PYEOF' ... PYEOF
py_pass_env() {
    local label="$1"
    shift
    local env_args=("$@")
    local tmpfile
    tmpfile=$(mktemp /tmp/kaiju_smoke_v4_XXXXXX.py)
    cat > "$tmpfile"
    if (cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" env "${env_args[@]}" $PYTHON "$tmpfile") >/dev/null 2>&1; then
        pass "$label"
    else
        echo "  ✗ $label"
        (cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" env "${env_args[@]}" $PYTHON "$tmpfile") 2>&1 | head -30 || true
        rm -f "$tmpfile"
        exit 1
    fi
    rm -f "$tmpfile"
}

# ---------------------------------------------------------------------------
echo "=== Kaiju Command Center V4 Integration Resolver Smoke Test ==="
echo ""
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
echo "[1/6] Checking environment..."
# ---------------------------------------------------------------------------

[ -f "$PYTHON" ] || fail "Python not found at $PYTHON"
pass "Python found at $PYTHON"

(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON -c "from integrations.schemas import get_ads_data_source") \
    2>/dev/null && pass "integrations.schemas importable" || fail "integrations.schemas not importable"

(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON -c "from integrations.resolver import resolve_ads_data") \
    2>/dev/null && pass "integrations.resolver importable" || fail "integrations.resolver not importable"

(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON -c "from integrations.mock_fixture_adapter import load_mock_fixture") \
    2>/dev/null && pass "integrations.mock_fixture_adapter importable" || fail "integrations.mock_fixture_adapter not importable"

(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON -c "from integrations.google_ads_adapter import fetch_google_ads_metrics") \
    2>/dev/null && pass "integrations.google_ads_adapter importable" || fail "integrations.google_ads_adapter not importable"

# ---------------------------------------------------------------------------
echo ""
echo "[2/6] Testing ADS_DATA_SOURCE resolution..."
# ---------------------------------------------------------------------------

py_pass_env "unset ADS_DATA_SOURCE defaults to n8n_demo" \
    "ADS_DATA_SOURCE=" <<'PYEOF'
import importlib, os
import integrations.schemas as s
importlib.reload(s)
assert s.get_ads_data_source() == "n8n_demo", f"got: {s.get_ads_data_source()}"
PYEOF

py_pass_env "ADS_DATA_SOURCE=mock_fixture resolves correctly" \
    "ADS_DATA_SOURCE=mock_fixture" <<'PYEOF'
import importlib
import integrations.schemas as s
importlib.reload(s)
assert s.get_ads_data_source() == "mock_fixture", f"got: {s.get_ads_data_source()}"
PYEOF

py_pass_env "ADS_DATA_SOURCE=google_ads resolves correctly" \
    "ADS_DATA_SOURCE=google_ads" <<'PYEOF'
import importlib
import integrations.schemas as s
importlib.reload(s)
assert s.get_ads_data_source() == "google_ads", f"got: {s.get_ads_data_source()}"
PYEOF

py_pass_env "ADS_DATA_SOURCE=bad falls back to n8n_demo" \
    "ADS_DATA_SOURCE=bad" <<'PYEOF'
import importlib
import integrations.schemas as s
importlib.reload(s)
assert s.get_ads_data_source() == "n8n_demo", f"got: {s.get_ads_data_source()}"
PYEOF

py_pass_env "ADS_DATA_SOURCE whitespace/mixed-case: no crash and valid result" \
    "ADS_DATA_SOURCE= Mock_Fixture " <<'PYEOF'
import importlib
import integrations.schemas as s
importlib.reload(s)
result = s.get_ads_data_source()
assert result in ("mock_fixture", "n8n_demo"), f"unexpected: {result}"
PYEOF

# ---------------------------------------------------------------------------
echo ""
echo "[3/6] Testing canonical metrics normalization..."
# ---------------------------------------------------------------------------

py_pass "normalize_metrics derives cpa, ctr, cpc, conversion_rate" <<'PYEOF'
from integrations.schemas import normalize_metrics

payload = {
    "client": "unit-client",
    "campaign": "Unit Campaign",
    "currency": "ARS",
    "spend": 150000,
    "conversions": 75,
    "clicks": 4200,
    "impressions": 95000,
}
m = normalize_metrics(payload, source="test")

assert m["source"] == "test",          f"source: {m['source']}"
assert m["spend"] == 150000.0,         f"spend: {m['spend']}"
assert m["conversions"] == 75,         f"conversions: {m['conversions']}"
assert m["clicks"] == 4200,            f"clicks: {m['clicks']}"
assert m["impressions"] == 95000,      f"impressions: {m['impressions']}"
assert m["cpa"] == 2000.0,             f"cpa: {m['cpa']}"
assert m["ctr"] is not None and m["ctr"] > 0,               f"ctr: {m['ctr']}"
assert m["cpc"] is not None and m["cpc"] > 0,               f"cpc: {m['cpc']}"
assert m["conversion_rate"] is not None and m["conversion_rate"] > 0, f"cr: {m['conversion_rate']}"
PYEOF

py_pass "normalize_metrics does not crash on empty payload" <<'PYEOF'
from integrations.schemas import normalize_metrics
m = normalize_metrics({}, source="test")
assert m["spend"] == 0
assert m["conversions"] == 0
assert m["cpa"] is None
assert m["ctr"] is None
PYEOF

py_pass "normalize_metrics preserves client and campaign" <<'PYEOF'
from integrations.schemas import normalize_metrics
m = normalize_metrics({"client": "acme", "campaign": "Q2 Launch", "spend": 0, "conversions": 0}, source="test")
assert m["client"] == "acme"
assert m["campaign"] == "Q2 Launch"
PYEOF

py_pass "make_integration_error returns required fields" <<'PYEOF'
from integrations.schemas import make_integration_error
err = make_integration_error("test_code", "test message", recoverable=True, source="test")
assert err["code"] == "test_code"
assert err["message"] == "test message"
assert err["recoverable"] is True
assert err["source"] == "test"
PYEOF

# ---------------------------------------------------------------------------
echo ""
echo "[4/6] Testing mock fixture adapter..."
# ---------------------------------------------------------------------------

py_pass "load_mock_fixture returns ok=true" <<'PYEOF'
from integrations.mock_fixture_adapter import load_mock_fixture
r = load_mock_fixture("integration-smoke-client", "summary")
assert r["ok"] is True, f"ok: {r}"
PYEOF

py_pass "load_mock_fixture data_source=mock_fixture" <<'PYEOF'
from integrations.mock_fixture_adapter import load_mock_fixture
r = load_mock_fixture("integration-smoke-client", "summary")
assert r["data_source"] == "mock_fixture", f"data_source: {r['data_source']}"
PYEOF

py_pass "load_mock_fixture data.source=mock_fixture" <<'PYEOF'
from integrations.mock_fixture_adapter import load_mock_fixture
r = load_mock_fixture("integration-smoke-client", "summary")
assert r["data"]["source"] == "mock_fixture", f"data.source: {r['data']['source']}"
PYEOF

py_pass "load_mock_fixture sets client to provided client_id" <<'PYEOF'
from integrations.mock_fixture_adapter import load_mock_fixture
r = load_mock_fixture("integration-smoke-client", "summary")
assert r["data"]["client"] == "integration-smoke-client", f"client: {r['data']['client']}"
PYEOF

py_pass "load_mock_fixture fixture base metrics correct" <<'PYEOF'
from integrations.mock_fixture_adapter import load_mock_fixture
d = load_mock_fixture("integration-smoke-client", "summary")["data"]
assert d["spend"] == 150000.0,    f"spend: {d['spend']}"
assert d["conversions"] == 75,    f"conversions: {d['conversions']}"
assert d["clicks"] == 4200,       f"clicks: {d['clicks']}"
assert d["impressions"] == 95000, f"impressions: {d['impressions']}"
PYEOF

py_pass "load_mock_fixture derives cpa=2000 and positive ctr/cpc/conversion_rate" <<'PYEOF'
from integrations.mock_fixture_adapter import load_mock_fixture
d = load_mock_fixture("integration-smoke-client", "summary")["data"]
assert d["cpa"] == 2000.0,                                    f"cpa: {d['cpa']}"
assert d["ctr"] is not None and d["ctr"] > 0,                 f"ctr: {d['ctr']}"
assert d["cpc"] is not None and d["cpc"] > 0,                 f"cpc: {d['cpc']}"
assert d["conversion_rate"] is not None and d["conversion_rate"] > 0, f"cr: {d['conversion_rate']}"
PYEOF

# ---------------------------------------------------------------------------
echo ""
echo "[5/6] Testing Google Ads adapter safety gates..."
# ---------------------------------------------------------------------------

py_pass_env "resolver mock_fixture: ok=true, data present" \
    "ADS_DATA_SOURCE=mock_fixture" <<'PYEOF'
import importlib
import integrations.schemas as s; importlib.reload(s)
import integrations.mock_fixture_adapter as mfa; importlib.reload(mfa)
import integrations.resolver as r; importlib.reload(r)
result = r.resolve_ads_data("integration-smoke-client", "summary")
assert result["ok"] is True,                    f"ok: {result}"
assert result["data_source"] == "mock_fixture", f"ds: {result['data_source']}"
assert "data" in result,                        f"no data key: {result}"
assert result["data"]["spend"] == 150000.0,     f"spend: {result['data']['spend']}"
PYEOF

py_pass_env "resolver google_ads LIVE_ENABLED=false: google_ads_live_disabled" \
    "ADS_DATA_SOURCE=google_ads" "GOOGLE_ADS_LIVE_ENABLED=false" <<'PYEOF'
import importlib
import integrations.schemas as s; importlib.reload(s)
import integrations.google_ads_adapter as ga; importlib.reload(ga)
import integrations.resolver as r; importlib.reload(r)
result = r.resolve_ads_data("integration-smoke-client", "summary")
assert result["ok"] is False
assert result["error"]["code"] == "google_ads_live_disabled", f"code: {result['error']['code']}"
PYEOF

py_pass_env "resolver google_ads LIVE_ENABLED unset: google_ads_live_disabled" \
    "ADS_DATA_SOURCE=google_ads" "GOOGLE_ADS_LIVE_ENABLED=" <<'PYEOF'
import importlib
import integrations.schemas as s; importlib.reload(s)
import integrations.google_ads_adapter as ga; importlib.reload(ga)
import integrations.resolver as r; importlib.reload(r)
result = r.resolve_ads_data("integration-smoke-client", "summary")
assert result["ok"] is False
assert result["error"]["code"] == "google_ads_live_disabled", f"code: {result['error']['code']}"
PYEOF

py_pass_env "resolver google_ads LIVE_ENABLED=true no credentials: credentials_missing" \
    "ADS_DATA_SOURCE=google_ads" \
    "GOOGLE_ADS_LIVE_ENABLED=true" \
    "GOOGLE_ADS_DEVELOPER_TOKEN=" \
    "GOOGLE_ADS_CLIENT_ID=" \
    "GOOGLE_ADS_CLIENT_SECRET=" \
    "GOOGLE_ADS_REFRESH_TOKEN=" \
    "GOOGLE_ADS_CUSTOMER_ID=" <<'PYEOF'
import importlib
import integrations.schemas as s; importlib.reload(s)
import integrations.google_ads_adapter as ga; importlib.reload(ga)
import integrations.resolver as r; importlib.reload(r)
result = r.resolve_ads_data("integration-smoke-client", "summary")
assert result["ok"] is False
assert result["error"]["code"] == "credentials_missing", f"code: {result['error']['code']}"
PYEOF

py_pass_env "fake credentials validate offline without live API call" \
    "GOOGLE_ADS_DEVELOPER_TOKEN=fake-dev-token" \
    "GOOGLE_ADS_CLIENT_ID=fake-client-id" \
    "GOOGLE_ADS_CLIENT_SECRET=fake-client-secret" \
    "GOOGLE_ADS_REFRESH_TOKEN=fake-refresh-token" \
    "GOOGLE_ADS_CUSTOMER_ID=1234567890" <<'PYEOF'
import importlib
import integrations.google_ads_adapter as ga; importlib.reload(ga)
# Credential loading and validation — no network call
creds = ga.load_google_ads_credentials()
valid, errors = ga.validate_google_ads_credentials(creds)
assert valid is True, f"validation failed: {errors}"
assert errors == [],  f"unexpected errors: {errors}"
# Redaction: all required fields show configured=True
redacted = ga.redacted_google_ads_credentials(creds)
assert redacted["developer_token"]["configured"] is True, "developer_token not configured"
assert redacted["client_id"]["configured"]        is True, "client_id not configured"
assert redacted["client_secret"]["configured"]    is True, "client_secret not configured"
assert redacted["refresh_token"]["configured"]    is True, "refresh_token not configured"
assert redacted["customer_id"]["configured"]      is True, "customer_id not configured"
# Client config dict has required keys; values are never printed
config = ga.build_google_ads_client_config(creds)
assert "developer_token" in config, "developer_token missing from config"
assert "client_id"        in config, "client_id missing from config"
assert "client_secret"    in config, "client_secret missing from config"
assert "refresh_token"    in config, "refresh_token missing from config"
assert config.get("use_proto_plus") is True, "use_proto_plus must be True"
# Customer ID normalization — offline, no network
assert ga.normalize_customer_id("123-456-7890") == "1234567890"
assert ga.normalize_customer_id("  1234567890  ") == "1234567890"
assert ga.normalize_customer_id("") is None
assert ga.normalize_customer_id(None) is None
PYEOF

# Redaction: fake credential values must not appear in adapter demo output.
# GOOGLE_ADS_LIVE_ENABLED=false — loads/redacts credentials without making any network call.
_DEMO_OUTPUT=$(
    cd "$AGENT_DIR" && \
    PYTHONPATH="$AGENT_DIR" \
    ADS_DATA_SOURCE=google_ads \
    GOOGLE_ADS_LIVE_ENABLED=false \
    GOOGLE_ADS_DEVELOPER_TOKEN=fake-dev-token \
    GOOGLE_ADS_CLIENT_ID=fake-client-id \
    GOOGLE_ADS_CLIENT_SECRET=fake-client-secret \
    GOOGLE_ADS_REFRESH_TOKEN=fake-refresh-token \
    GOOGLE_ADS_CUSTOMER_ID=1234567890 \
    $PYTHON run_google_ads_adapter_demo.py 2>&1
)
for secret in "fake-dev-token" "fake-client-secret" "fake-refresh-token" "fake-client-id"; do
    if echo "$_DEMO_OUTPUT" | grep -qF "$secret"; then
        fail "redaction: '$secret' appeared in adapter demo output"
    else
        pass "redaction: '$secret' not in adapter demo output"
    fi
done

# ---------------------------------------------------------------------------
echo ""
echo "[6/6] Testing graph integration with mock fixture..."
# ---------------------------------------------------------------------------

for rt in summary cpa conversions raw; do
    output=$(cd "$AGENT_DIR" && ADS_DATA_SOURCE=mock_fixture $PYTHON run_graph_demo.py "$rt" 2>&1)
    if echo "$output" | grep -q '"ok": true'; then
        pass "graph mock_fixture $rt: exits cleanly with ok=true"
    else
        echo "  ✗ graph mock_fixture $rt: expected ok=true"
        echo "$output" | head -20 | sed 's/^/      /'
        exit 1
    fi
    if echo "$output" | grep -q "mock_fixture"; then
        pass "graph mock_fixture $rt: data_source=mock_fixture in output"
    else
        fail "graph mock_fixture $rt: mock_fixture not found in output"
    fi
done

_SUMMARY=$(cd "$AGENT_DIR" && ADS_DATA_SOURCE=mock_fixture $PYTHON run_graph_demo.py summary 2>&1)
echo "$_SUMMARY" | grep -q '"performance_score"' \
    && pass "graph mock_fixture summary: performance_score present" \
    || fail "graph mock_fixture summary: performance_score missing"
echo "$_SUMMARY" | grep -q '"executive_summary"' \
    && pass "graph mock_fixture summary: executive_summary present" \
    || fail "graph mock_fixture summary: executive_summary missing"

_CPA=$(cd "$AGENT_DIR" && ADS_DATA_SOURCE=mock_fixture $PYTHON run_graph_demo.py cpa 2>&1)
echo "$_CPA" | grep -q '"cpa_level"' \
    && pass "graph mock_fixture cpa: cpa_level present" \
    || fail "graph mock_fixture cpa: cpa_level missing"

# ---------------------------------------------------------------------------
echo ""
echo "Verifying runtime files not tracked..."
# ---------------------------------------------------------------------------
cd "$REPO"
if git status --porcelain | grep -E "openclaw/audit|memory/client-memory"; then
    fail "runtime audit or memory files appeared in git status"
else
    pass "no runtime audit or memory files in git status"
fi

# ---------------------------------------------------------------------------
echo ""
echo "=== V4 integration resolver smoke test passed. ==="

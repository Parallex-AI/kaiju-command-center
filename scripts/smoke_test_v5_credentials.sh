#!/usr/bin/env bash
set -euo pipefail

PYTHON=~/kaiju/.venv/bin/python3
REPO=~/kaiju
AGENT_DIR="$REPO/agents/ads-agent"
OPENCLAW_DIR="$REPO/openclaw"
PORT=8101
BASE_URL="http://localhost:${PORT}"
SERVER_PID=""
SERVER_PID2=""

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
cleanup() {
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    if [ -n "$SERVER_PID2" ] && kill -0 "$SERVER_PID2" 2>/dev/null; then
        kill "$SERVER_PID2" 2>/dev/null || true
        wait "$SERVER_PID2" 2>/dev/null || true
    fi
    rm -f /tmp/kaiju_smoke_v5_*.py /tmp/kaiju_smoke_v5_*.log /tmp/kaiju_smoke_v5_*.json 2>/dev/null || true
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; exit 1; }

# Run a Python snippet from AGENT_DIR with AGENT_DIR on PYTHONPATH.
py_pass() {
    local label="$1"
    local tmpfile
    tmpfile=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.py)
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

# Run a Python snippet with additional env vars (passed as "VAR=val" strings after label).
py_pass_env() {
    local label="$1"
    shift
    local env_args=("$@")
    local tmpfile
    tmpfile=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.py)
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

# Run a Python HTTP test snippet (no path changes needed).
py_http_pass() {
    local label="$1"
    local tmpfile
    tmpfile=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.py)
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

# Wait for the server health endpoint to respond.
wait_for_server() {
    local url="$1"
    local timeout="${2:-12}"
    local elapsed=0
    echo -n "  Waiting for server"
    while true; do
        if curl -s --max-time 1 "$url" >/dev/null 2>&1; then
            echo ""
            pass "Server healthy (started in ${elapsed}s)"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
        echo -n "."
        if [ "$elapsed" -ge "$timeout" ]; then
            echo ""
            return 1
        fi
    done
}

# ---------------------------------------------------------------------------
echo "=== Kaiju Command Center V5 Credential Chain Smoke Test ==="
echo ""
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
echo "[1/19] Environment and import checks..."
# ---------------------------------------------------------------------------

[ -f "$PYTHON" ] || fail "Python not found at $PYTHON"
pass "Python found at $PYTHON"

for module in \
    "credentials.models" \
    "credentials.store" \
    "credentials.local_file_store" \
    "credentials.resolver" \
    "credentials.secret_store" \
    "credentials.google_ads_provider"
do
    (cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON -c "import $module") >/dev/null 2>&1 \
        && pass "$module importable" \
        || fail "$module not importable"
done

(cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "from admin import get_google_ads_credential_status, upsert_google_ads_credential_reference, write_google_ads_credential_bundle, GOOGLE_ADS_SECRET_FIELDS") \
    >/dev/null 2>&1 \
    && pass "openclaw.admin importable" \
    || fail "openclaw.admin not importable"

# ---------------------------------------------------------------------------
echo ""
echo "[2/19] CredentialReference model demo..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON run_credentials_model_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_credentials_model_demo.py: All assertions passed" \
    || { echo "  ✗ run_credentials_model_demo.py: assertion not found in output"; echo "$_OUT" | tail -5; exit 1; }

# ---------------------------------------------------------------------------
echo ""
echo "[3/19] Credential stores..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON run_credentials_store_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_credentials_store_demo.py: All assertions passed" \
    || { echo "  ✗ run_credentials_store_demo.py: assertion not found"; echo "$_OUT" | tail -5; exit 1; }

_OUT=$(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON run_credentials_local_file_store_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_credentials_local_file_store_demo.py: All assertions passed" \
    || { echo "  ✗ run_credentials_local_file_store_demo.py: assertion not found"; echo "$_OUT" | tail -5; exit 1; }

# ---------------------------------------------------------------------------
echo ""
echo "[4/19] Credential resolver..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON run_credentials_resolver_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_credentials_resolver_demo.py: All assertions passed" \
    || { echo "  ✗ run_credentials_resolver_demo.py: assertion not found"; echo "$_OUT" | tail -5; exit 1; }

# ---------------------------------------------------------------------------
echo ""
echo "[5/19] SecretStore and provider..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON run_secret_store_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_secret_store_demo.py: All assertions passed" \
    || { echo "  ✗ run_secret_store_demo.py: assertion not found"; echo "$_OUT" | tail -5; exit 1; }

_OUT=$(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON run_google_ads_provider_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_google_ads_provider_demo.py: All assertions passed" \
    || { echo "  ✗ run_google_ads_provider_demo.py: assertion not found"; echo "$_OUT" | tail -5; exit 1; }

# ---------------------------------------------------------------------------
echo ""
echo "[6/19] Adapter provider mode — non-live checks..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON run_google_ads_adapter_provider_demo.py 2>&1)
echo "$_OUT" | grep -q "Demo complete" \
    && pass "run_google_ads_adapter_provider_demo.py: completed" \
    || { echo "  ✗ run_google_ads_adapter_provider_demo.py: did not complete"; echo "$_OUT" | tail -10; exit 1; }

# google_ads_live_disabled guard: LIVE_ENABLED=false must not hit API
py_pass_env "GOOGLE_ADS_CREDENTIAL_SOURCE=provider LIVE_ENABLED=false: google_ads_live_disabled" \
    "GOOGLE_ADS_LIVE_ENABLED=false" \
    "GOOGLE_ADS_CREDENTIAL_SOURCE=provider" <<'PYEOF'
import importlib
import integrations.google_ads_adapter as ga
importlib.reload(ga)
result = ga.fetch_google_ads_metrics(
    "smoke-client", "summary",
    tenant_id="smoke-tenant",
)
assert result["ok"] is False, f"expected ok=false: {result}"
assert result["error"]["code"] == "google_ads_live_disabled", \
    f"expected google_ads_live_disabled: {result['error']['code']}"
PYEOF

# Default env source: backward-compatible 2-arg call
py_pass_env "2-arg call (no tenant_id) defaults to env path: google_ads_live_disabled" \
    "GOOGLE_ADS_LIVE_ENABLED=false" \
    "GOOGLE_ADS_CREDENTIAL_SOURCE=" <<'PYEOF'
import importlib
import integrations.google_ads_adapter as ga
importlib.reload(ga)
result = ga.fetch_google_ads_metrics("smoke-client", "summary")
assert result["ok"] is False, f"expected ok=false: {result}"
assert result["error"]["code"] == "google_ads_live_disabled", \
    f"expected google_ads_live_disabled: {result['error']['code']}"
PYEOF

# Provider mode without tenant_id returns tenant_id_required
py_pass_env "provider mode without tenant_id: tenant_id_required" \
    "GOOGLE_ADS_LIVE_ENABLED=true" \
    "GOOGLE_ADS_CREDENTIAL_SOURCE=provider" <<'PYEOF'
import importlib
import integrations.google_ads_adapter as ga
importlib.reload(ga)
result = ga.fetch_google_ads_metrics("smoke-client", "summary")
assert result["ok"] is False, f"expected ok=false: {result}"
assert result["error"]["code"] == "tenant_id_required", \
    f"expected tenant_id_required: {result['error']['code']}"
PYEOF

# Provider compose: in-memory store, no live API call
py_pass "provider path: compose credentials in-memory, no live API call" <<'PYEOF'
import tempfile, os
from credentials.local_file_store import LocalFileCredentialReferenceStore
from credentials.secret_store import InMemorySecretStore
from credentials.models import CredentialStatus, IntegrationType, create_credential_reference
from integrations.google_ads_adapter import (
    load_google_ads_credentials_from_provider,
    redacted_google_ads_credentials,
    validate_google_ads_credentials,
)

with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    store_path = f.name
os.environ["CREDENTIAL_REFERENCE_STORE_PATH"] = store_path

try:
    ref_store = LocalFileCredentialReferenceStore()
    secret_store = InMemorySecretStore()
    integration_type = IntegrationType.GOOGLE_ADS.value

    ref = create_credential_reference(
        tenant_id="smoke-tenant",
        client_id="smoke-client",
        integration_type=integration_type,
        customer_id="9876543210",
        status=CredentialStatus.CONFIGURED.value,
    )
    ref_store.put_reference(ref)
    secret_store.put_secret_bundle(
        credential_ref=ref.credential_ref,
        integration_type=integration_type,
        secrets={
            "developer_token": "smoke-dev-token",
            "client_id": "smoke-client-id",
            "client_secret": "smoke-client-secret",
            "refresh_token": "smoke-refresh-token",
        },
    )

    ok, creds, errors = load_google_ads_credentials_from_provider(
        "smoke-tenant", "smoke-client", secret_store=secret_store,
    )
    assert ok is True, f"expected ok=True: {errors}"
    assert creds is not None, "expected credentials"
    valid, val_errors = validate_google_ads_credentials(creds)
    assert valid is True, f"validation failed: {val_errors}"

    redacted = redacted_google_ads_credentials(creds)
    for field in ("developer_token", "client_id", "client_secret", "refresh_token", "customer_id"):
        assert redacted[field]["configured"] is True, f"{field} not configured in redacted"

    # Verify no raw values in redacted output
    import json
    redacted_str = json.dumps(redacted)
    for val in ("smoke-dev-token", "smoke-client-secret", "smoke-refresh-token"):
        assert val not in redacted_str, f"secret value leaked in redacted output: {val}"
finally:
    os.environ.pop("CREDENTIAL_REFERENCE_STORE_PATH", None)
    try:
        os.unlink(store_path)
    except OSError:
        pass
PYEOF

# ---------------------------------------------------------------------------
echo ""
echo "[7/19] OpenClaw admin credential endpoints..."
# ---------------------------------------------------------------------------

# Set up temp credential reference store to avoid touching any runtime file
CRED_STORE_FILE=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)

# Check port availability
if curl -s --max-time 2 "${BASE_URL}/openclaw/health" >/dev/null 2>&1; then
    fail "Port ${PORT} is already in use. Cannot start smoke test server."
fi
pass "Port ${PORT} is available"

# Start server — auth DISABLED, temp credential store
cd "$OPENCLAW_DIR"
CREDENTIAL_REFERENCE_STORE_PATH="$CRED_STORE_FILE" \
OPENCLAW_API_AUTH_ENABLED=false \
OPENCLAW_AUDIT_ENABLED=false \
PORT="$PORT" \
    $PYTHON -m uvicorn server:app --host 127.0.0.1 --port "$PORT" --log-level warning \
    > /tmp/kaiju_smoke_v5_server.log 2>&1 &
SERVER_PID=$!
cd "$REPO"

if ! wait_for_server "${BASE_URL}/openclaw/health" 12; then
    echo "  ✗ Server did not start within 12s"
    cat /tmp/kaiju_smoke_v5_server.log | head -20 || true
    exit 1
fi

# POST safe CredentialReference
py_http_pass "POST /credentials/google-ads with customer_id: ok=true" <<PYEOF
import requests
r = requests.post(
    "http://localhost:${PORT}/openclaw/admin/tenants/smoke-tenant/clients/smoke-client/credentials/google-ads",
    json={"customer_id": "1234567890"},
    timeout=10,
)
assert r.status_code == 200, f"status: {r.status_code} body: {r.text[:200]}"
d = r.json()
assert d["ok"] is True, f"ok: {d}"
assert d["credential_status"]["status"] in ("configured", "missing", "active"), \
    f"status: {d['credential_status']}"
assert "credential_ref" in d["credential_status"], "missing credential_ref"
PYEOF

# GET status
py_http_pass "GET /credentials/google-ads/status: ok=true" <<PYEOF
import requests
r = requests.get(
    "http://localhost:${PORT}/openclaw/admin/tenants/smoke-tenant/clients/smoke-client/credentials/google-ads/status",
    timeout=10,
)
assert r.status_code == 200, f"status: {r.status_code} body: {r.text[:200]}"
d = r.json()
assert d["ok"] is True, f"ok: {d}"
assert d["tenant_id"] == "smoke-tenant", f"tenant_id: {d}"
assert d["client_id"] == "smoke-client", f"client_id: {d}"
PYEOF

# POST forbidden field (non-secret-bundle field) — must be rejected with secret_material_rejected
# Uses oauth_code which is forbidden in the metadata path and not a known bundle field,
# so it routes to the metadata-only path and is rejected by the forbidden-field guard.
py_http_pass "POST forbidden field with oauth_code: secret_material_rejected" <<PYEOF
import requests
r = requests.post(
    "http://localhost:${PORT}/openclaw/admin/tenants/smoke-tenant/clients/smoke-client/credentials/google-ads",
    json={"customer_id": "1234567890", "oauth_code": "should-be-rejected"},
    timeout=10,
)
assert r.status_code == 400, f"expected 400, got: {r.status_code} body: {r.text[:200]}"
d = r.json()
assert d["ok"] is False, f"ok should be False: {d}"
error_codes = [e["code"] for e in d.get("errors", [])]
assert "secret_material_rejected" in error_codes, \
    f"expected secret_material_rejected in errors: {error_codes}"
PYEOF

# POST malformed JSON — must return invalid_json
py_http_pass "POST malformed JSON: invalid_json error" <<PYEOF
import requests
r = requests.post(
    "http://localhost:${PORT}/openclaw/admin/tenants/smoke-tenant/clients/smoke-client/credentials/google-ads",
    data=b"not-valid-json{{{",
    headers={"Content-Type": "application/json"},
    timeout=10,
)
assert r.status_code == 400, f"expected 400, got: {r.status_code} body: {r.text[:200]}"
d = r.json()
assert d["ok"] is False, f"ok should be False: {d}"
error_codes = [e["code"] for e in d.get("errors", [])]
assert "invalid_json" in error_codes, \
    f"expected invalid_json in errors: {error_codes}"
PYEOF

# Response must not contain secret values (check developer_token key value is absent)
py_http_pass "GET /status response contains no secret values" <<PYEOF
import json, requests
r = requests.get(
    "http://localhost:${PORT}/openclaw/admin/tenants/smoke-tenant/clients/smoke-client/credentials/google-ads/status",
    timeout=10,
)
body = r.text
for forbidden in ("developer_token_value", "client_secret", "refresh_token", "ya29", "sk-"):
    assert forbidden not in body, f"forbidden string '{forbidden}' found in response body"
d = r.json()
assert "credential_status" in d, "credential_status missing from response"
cred = d["credential_status"]
assert "developer_token" not in cred, f"developer_token key present in credential_status: {cred}"
PYEOF

# Stop auth-disabled server
kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true
SERVER_PID=""

# Auth-enabled test: start a new server with OPENCLAW_API_AUTH_ENABLED=true
pass "Stopping auth-disabled server"

sleep 1
if curl -s --max-time 2 "${BASE_URL}/openclaw/health" >/dev/null 2>&1; then
    fail "Auth-disabled server did not stop cleanly"
fi

cd "$OPENCLAW_DIR"
CREDENTIAL_REFERENCE_STORE_PATH="$CRED_STORE_FILE" \
OPENCLAW_API_AUTH_ENABLED=true \
OPENCLAW_ADMIN_KEYS="smoke-test-key" \
OPENCLAW_AUDIT_ENABLED=false \
PORT="$PORT" \
    $PYTHON -m uvicorn server:app --host 127.0.0.1 --port "$PORT" --log-level warning \
    > /tmp/kaiju_smoke_v5_server2.log 2>&1 &
SERVER_PID2=$!
cd "$REPO"

if ! wait_for_server "${BASE_URL}/openclaw/health" 12; then
    echo "  ✗ Auth-enabled server did not start within 12s"
    cat /tmp/kaiju_smoke_v5_server2.log | head -20 || true
    exit 1
fi

# Request without token should return 401
py_http_pass "GET /status without auth token: 401 unauthorized" <<PYEOF
import requests
r = requests.get(
    "http://localhost:${PORT}/openclaw/admin/tenants/smoke-tenant/clients/smoke-client/credentials/google-ads/status",
    timeout=10,
)
assert r.status_code == 401, f"expected 401, got: {r.status_code} body: {r.text[:200]}"
d = r.json()
assert d["ok"] is False, f"ok should be False: {d}"
PYEOF

# Request WITH valid Bearer token should succeed
py_http_pass "GET /status with Bearer smoke-test-key: 200 ok" <<PYEOF
import requests
r = requests.get(
    "http://localhost:${PORT}/openclaw/admin/tenants/smoke-tenant/clients/smoke-client/credentials/google-ads/status",
    headers={"Authorization": "Bearer smoke-test-key"},
    timeout=10,
)
assert r.status_code == 200, f"expected 200, got: {r.status_code} body: {r.text[:200]}"
d = r.json()
assert d["ok"] is True, f"ok should be True: {d}"
PYEOF

# POST with auth token: succeeds
py_http_pass "POST /credentials/google-ads with Bearer token: ok=true" <<PYEOF
import requests
r = requests.post(
    "http://localhost:${PORT}/openclaw/admin/tenants/smoke-tenant/clients/smoke-client/credentials/google-ads",
    json={"customer_id": "9999999999"},
    headers={"Authorization": "Bearer smoke-test-key"},
    timeout=10,
)
assert r.status_code == 200, f"expected 200, got: {r.status_code} body: {r.text[:200]}"
d = r.json()
assert d["ok"] is True, f"ok should be True: {d}"
PYEOF

# Stop auth-enabled server
kill "$SERVER_PID2" 2>/dev/null || true
wait "$SERVER_PID2" 2>/dev/null || true
SERVER_PID2=""
pass "Auth-enabled server stopped cleanly"

rm -f "$CRED_STORE_FILE"

# ---------------------------------------------------------------------------
echo ""
echo "[8/19] Secret-safety and git hygiene..."
# ---------------------------------------------------------------------------

GREP_TARGETS="$REPO/scripts $REPO/docs $REPO/agents $REPO/openclaw $REPO/README.md $REPO/.env.example"

# ya29. — OAuth access token prefix
if grep -R "ya29\." -n $GREP_TARGETS 2>/dev/null | grep -v "_PYEOF\|# ya29\|ya29.*marker\|ya29.*forbidden\|starting with.*ya29\|ya29.*prohibition\|must never be used\|no.*ya29"; then
    fail "ya29 OAuth token prefix found in source files"
else
    pass "no ya29 OAuth token prefix in source files"
fi

# sk- — API key prefix
if grep -R "sk-[A-Za-z0-9]" -n $GREP_TARGETS 2>/dev/null | grep -v "PYEOF\|# sk-\|smoke-test-key\|smoke-client-secret\|smoke-dev-token\|smoke-refresh"; then
    fail "sk- API key prefix found in source files"
else
    pass "no sk- API key prefix in source files"
fi

# Real-looking credential assignments — match var=<alphanumeric start>, exclude known-safe placeholders.
# Using [A-Za-z0-9] (no backslash) avoids matching bash line-continuation backslashes.
for var in GOOGLE_ADS_REFRESH_TOKEN GOOGLE_ADS_CLIENT_SECRET GOOGLE_ADS_DEVELOPER_TOKEN; do
    _HIT=$(grep -Rn "${var}=[A-Za-z0-9]" $GREP_TARGETS 2>/dev/null \
        | grep -v "fake-\|smoke-\|demo-\|your-\|test-\|PYEOF\|placeholder\|REDACTED" \
        || true)
    if [ -n "$_HIT" ]; then
        echo "$_HIT"
        fail "Non-placeholder assignment found for ${var}"
    else
        pass "no real ${var} assignment in source files"
    fi
done

# Runtime credential reference store must not be tracked
cd "$REPO"
if git ls-files --error-unmatch "openclaw/credential_references.json" >/dev/null 2>&1; then
    fail "openclaw/credential_references.json is tracked in git — must be gitignored"
else
    pass "runtime credential store file not tracked"
fi

if git status --porcelain | grep -E "credential_references\.json|memory/client-memory|openclaw/audit/"; then
    fail "runtime files appeared in git status"
else
    pass "no runtime files in git status"
fi

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
echo ""
echo "[9/19] Admin credential bundle write — mocked secret store..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    $PYTHON run_admin_credentials_gcp_write_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_admin_credentials_gcp_write_demo.py: All assertions passed" \
    || { echo "  ✗ run_admin_credentials_gcp_write_demo.py: assertion not found"; echo "$_OUT" | tail -15; exit 1; }

# Verify the demo produced no raw fake secret values in its stdout
for val in "fake-dev-token" "fake-client-secret" "fake-refresh-token"; do
    if echo "$_OUT" | grep -q "$val"; then
        fail "Fake secret value '$val' appeared in demo stdout — possible secret leak"
    fi
done
pass "no fake secret values in demo stdout"

# Verify factory selects in_memory when GCP_SECRET_MANAGER_ENABLED=false
# Runs from AGENT_DIR so credentials package is importable directly
py_pass_env "factory default: GCP_SECRET_MANAGER_ENABLED=false selects in_memory" \
    "GCP_SECRET_MANAGER_ENABLED=false" <<'PYEOF'
from credentials.secret_store_factory import get_secret_store_backend_name
backend = get_secret_store_backend_name()
assert backend == "in_memory", f"Expected in_memory, got: {backend}"
PYEOF

# ---------------------------------------------------------------------------
echo ""
echo "[10/19] Admin credential API write — FastAPI TestClient..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    OPENCLAW_API_AUTH_ENABLED=false \
    $PYTHON run_admin_credentials_api_write_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_admin_credentials_api_write_demo.py: All assertions passed" \
    || { echo "  ✗ run_admin_credentials_api_write_demo.py: assertion not found"; echo "$_OUT" | tail -20; exit 1; }

# Verify no fake secret values leaked into demo stdout
for val in "fake-dev-token" "fake-client-id" "fake-client-secret" "fake-refresh-token" "fake-access-token"; do
    if echo "$_OUT" | grep -q "$val"; then
        fail "Fake secret value '$val' appeared in API demo stdout — possible secret leak"
    fi
done
pass "no fake secret values in API demo stdout"

# Scenario checks in stdout
echo "$_OUT" | grep -q "scenario-A.*PASS\|PASS:.*ok=true.*no secret_status" \
    && pass "scenario A: metadata-only POST accepted, no secret_status" \
    || { echo "  ✗ scenario A marker not found"; echo "$_OUT" | tail -30; exit 1; }

echo "$_OUT" | grep -q "PASS.*secret_status.configured=true" \
    && pass "scenario B: full bundle POST accepted, secret_status.configured=true" \
    || { echo "  ✗ scenario B marker not found"; echo "$_OUT" | tail -30; exit 1; }

echo "$_OUT" | grep -q "secret_bundle_incomplete" \
    && pass "scenario C: incomplete bundle rejected with secret_bundle_incomplete" \
    || { echo "  ✗ scenario C marker not found"; echo "$_OUT" | tail -30; exit 1; }

echo "$_OUT" | grep -q "secret_material_rejected" \
    && pass "scenario D: forbidden field rejected with secret_material_rejected" \
    || { echo "  ✗ scenario D marker not found"; echo "$_OUT" | tail -30; exit 1; }

# ---------------------------------------------------------------------------
echo ""
echo "[11/19] Credential lifecycle audit and validation events..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    $PYTHON run_admin_credentials_lifecycle_demo.py 2>&1)
echo "$_OUT" | grep -q "All credential lifecycle audit assertions passed" \
    && pass "run_admin_credentials_lifecycle_demo.py: All assertions passed" \
    || { echo "  ✗ run_admin_credentials_lifecycle_demo.py: assertion not found"; echo "$_OUT" | tail -20; exit 1; }

# Verify no fake secret values in lifecycle demo stdout
for val in "fake-dev-token-lifecycle" "fake-client-secret-lifecycle" "fake-refresh-token-lifecycle" "fake-oauth-client-id-lifecycle"; do
    if echo "$_OUT" | grep -q "$val"; then
        fail "Fake secret value '$val' appeared in lifecycle demo stdout — possible secret leak"
    fi
done
pass "no fake secret values in lifecycle demo stdout"

# Verify forbidden fields not in lifecycle demo stdout
for key in "credential_ref" "secret_id" "login_customer_id"; do
    if echo "$_OUT" | grep -qE "\"${key}\""; then
        fail "Forbidden key '${key}' appeared in lifecycle demo stdout"
    fi
done
pass "no forbidden audit keys in lifecycle demo stdout"

# Validate scenario checks in lifecycle demo stdout
echo "$_OUT" | grep -q "structurally_complete=true" \
    && pass "lifecycle demo E: structurally_complete=true confirmed" \
    || { echo "  ✗ lifecycle demo E: structurally_complete=true not found"; echo "$_OUT" | tail -20; exit 1; }

echo "$_OUT" | grep -q "credential_not_found" \
    && pass "lifecycle demo F: credential_not_found confirmed" \
    || { echo "  ✗ lifecycle demo F: credential_not_found not found"; echo "$_OUT" | tail -20; exit 1; }

echo "$_OUT" | grep -q "status=validation_failed" \
    && pass "lifecycle demo G: status=validation_failed confirmed" \
    || { echo "  ✗ lifecycle demo G: status=validation_failed not found"; echo "$_OUT" | tail -20; exit 1; }

# Delete/revoke markers (H-K)
echo "$_OUT" | grep -q "delete_not_enabled" \
    && pass "lifecycle demo H: delete_not_enabled gate confirmed" \
    || { echo "  ✗ lifecycle demo H: delete_not_enabled not found"; echo "$_OUT" | tail -20; exit 1; }

echo "$_OUT" | grep -q "status=revoked" \
    && pass "lifecycle demo I: status=revoked confirmed" \
    || { echo "  ✗ lifecycle demo I: status=revoked not found"; echo "$_OUT" | tail -20; exit 1; }

echo "$_OUT" | grep -q "secret_already_absent" \
    && pass "lifecycle demo J: idempotent delete secret_already_absent confirmed" \
    || { echo "  ✗ lifecycle demo J: secret_already_absent not found"; echo "$_OUT" | tail -20; exit 1; }

# ---------------------------------------------------------------------------
echo ""
echo "[12/19] Credential lifecycle validation API (FastAPI TestClient)..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    OPENCLAW_API_AUTH_ENABLED=false \
    $PYTHON run_admin_credentials_lifecycle_api_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_admin_credentials_lifecycle_api_demo.py: All assertions passed" \
    || { echo "  ✗ run_admin_credentials_lifecycle_api_demo.py: assertion not found"; echo "$_OUT" | tail -20; exit 1; }

# Verify no fake secret values in API lifecycle demo stdout
for val in "fake-dev-token" "fake-client-id" "fake-client-secret" "fake-refresh-token"; do
    if echo "$_OUT" | grep -q "\"$val\""; then
        fail "Fake secret value '$val' appeared in API lifecycle demo stdout"
    fi
done
pass "no fake secret values in API lifecycle demo stdout"

# Validate scenario checks in API lifecycle demo stdout
echo "$_OUT" | grep -q "status 404 for missing credential" \
    && pass "API lifecycle Validate B: 404 for missing credential" \
    || { echo "  ✗ API lifecycle Validate B: 404 marker not found"; echo "$_OUT" | tail -30; exit 1; }

echo "$_OUT" | grep -q "structurally_complete=true" \
    && pass "API lifecycle Validate A: structurally_complete=true" \
    || { echo "  ✗ API lifecycle Validate A: structurally_complete=true not found"; echo "$_OUT" | tail -30; exit 1; }

echo "$_OUT" | grep -q "status=validation_failed" \
    && pass "API lifecycle Validate C: status=validation_failed" \
    || { echo "  ✗ API lifecycle Validate C: status=validation_failed not found"; echo "$_OUT" | tail -30; exit 1; }

# Delete scenario markers in API lifecycle demo stdout
echo "$_OUT" | grep -q "status 401 without auth token" \
    && pass "API lifecycle Delete E: 401 auth gate confirmed" \
    || { echo "  ✗ API lifecycle Delete E: 401 marker not found"; echo "$_OUT" | tail -30; exit 1; }

echo "$_OUT" | grep -q "status 403 when delete disabled" \
    && pass "API lifecycle Delete A: 403 delete_not_enabled confirmed" \
    || { echo "  ✗ API lifecycle Delete A: 403 marker not found"; echo "$_OUT" | tail -30; exit 1; }

echo "$_OUT" | grep -q "credential status=revoked" \
    && pass "API lifecycle Delete B: status=revoked confirmed" \
    || { echo "  ✗ API lifecycle Delete B: status=revoked not found"; echo "$_OUT" | tail -30; exit 1; }

echo "$_OUT" | grep -q "warnings includes secret_already_absent" \
    && pass "API lifecycle Delete C: idempotent delete confirmed" \
    || { echo "  ✗ API lifecycle Delete C: secret_already_absent not found"; echo "$_OUT" | tail -30; exit 1; }

# ---------------------------------------------------------------------------
echo ""
echo "[13/19] Validate route — server-level auth checks..."
# ---------------------------------------------------------------------------

CRED_STORE_FILE2=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)

if curl -s --max-time 2 "${BASE_URL}/openclaw/health" >/dev/null 2>&1; then
    fail "Port ${PORT} still in use before validate auth test server"
fi

cd "$OPENCLAW_DIR"
CREDENTIAL_REFERENCE_STORE_PATH="$CRED_STORE_FILE2" \
OPENCLAW_API_AUTH_ENABLED=true \
OPENCLAW_ADMIN_KEYS="smoke-validate-key" \
OPENCLAW_AUDIT_ENABLED=false \
PORT="$PORT" \
    $PYTHON -m uvicorn server:app --host 127.0.0.1 --port "$PORT" --log-level warning \
    > /tmp/kaiju_smoke_v5_validate_server.log 2>&1 &
SERVER_PID=$!
cd "$REPO"

if ! wait_for_server "${BASE_URL}/openclaw/health" 12; then
    echo "  ✗ Validate auth test server did not start within 12s"
    cat /tmp/kaiju_smoke_v5_validate_server.log | head -20 || true
    exit 1
fi

# Validate without auth token → 401
py_http_pass "POST /credentials/google-ads/validate without auth: 401" <<PYEOF
import requests
r = requests.post(
    "http://localhost:${PORT}/openclaw/admin/tenants/smoke-tenant/clients/smoke-client/credentials/google-ads/validate",
    timeout=10,
)
assert r.status_code == 401, f"expected 401, got: {r.status_code} body: {r.text[:200]}"
d = r.json()
assert d["ok"] is False, f"ok should be False: {d}"
PYEOF

# Validate with auth token but no credential → 404
py_http_pass "POST /credentials/google-ads/validate with auth, no ref: 404" <<PYEOF
import requests
r = requests.post(
    "http://localhost:${PORT}/openclaw/admin/tenants/smoke-tenant/clients/smoke-client/credentials/google-ads/validate",
    headers={"Authorization": "Bearer smoke-validate-key"},
    timeout=10,
)
assert r.status_code == 404, f"expected 404, got: {r.status_code} body: {r.text[:200]}"
d = r.json()
assert d["ok"] is False, f"ok should be False: {d}"
error_codes = [e["code"] for e in d.get("errors", [])]
assert "credential_not_found" in error_codes, f"expected credential_not_found: {error_codes}"
PYEOF

kill "$SERVER_PID" 2>/dev/null || true
wait "$SERVER_PID" 2>/dev/null || true
SERVER_PID=""
pass "Validate auth test server stopped cleanly"
rm -f "$CRED_STORE_FILE2"

# ---------------------------------------------------------------------------
echo ""
echo "[14/19] Phase 3 delete/revoke — forbidden behavior and env gate checks..."
# ---------------------------------------------------------------------------

# delete_google_ads_credentials must not call get_secret_bundle (only delete_secret_bundle + get_secret_status)
# Match method call syntax (.get_secret_bundle) to avoid matching docstring references.
if grep -n "\.get_secret_bundle" "$OPENCLAW_DIR/admin.py" 2>/dev/null; then
    fail ".get_secret_bundle() call found in admin.py — delete path must not fetch secrets"
else
    pass "admin.py delete path does not call .get_secret_bundle()"
fi

# GOOGLE_ADS_LIVE_ENABLED must not be true in any demo or script file
if grep -R "GOOGLE_ADS_LIVE_ENABLED=true" \
    "$OPENCLAW_DIR/run_admin_credentials_lifecycle_demo.py" \
    "$OPENCLAW_DIR/run_admin_credentials_lifecycle_api_demo.py" \
    "$OPENCLAW_DIR/run_admin_credentials_gcp_write_demo.py" \
    "$OPENCLAW_DIR/run_admin_credentials_api_write_demo.py" \
    2>/dev/null; then
    fail "GOOGLE_ADS_LIVE_ENABLED=true found in a demo file — must remain false"
else
    pass "GOOGLE_ADS_LIVE_ENABLED=true absent from all demo files"
fi

# GCP_SECRET_MANAGER_ENABLED must not be true in demo files
if grep -R "GCP_SECRET_MANAGER_ENABLED=true" \
    "$OPENCLAW_DIR/run_admin_credentials_lifecycle_demo.py" \
    "$OPENCLAW_DIR/run_admin_credentials_lifecycle_api_demo.py" \
    2>/dev/null; then
    fail "GCP_SECRET_MANAGER_ENABLED=true found in lifecycle demo file"
else
    pass "GCP_SECRET_MANAGER_ENABLED=true absent from lifecycle demo files"
fi

# OPENCLAW_ADMIN_DELETE_ENABLED gate must be read from os.environ (not hardcoded).
# Verify _is_admin_delete_enabled reads from os.environ, not a literal True.
if grep -A 3 "def _is_admin_delete_enabled" "$OPENCLAW_DIR/admin.py" 2>/dev/null \
    | grep -q "os.environ"; then
    pass "_is_admin_delete_enabled reads from os.environ (not hardcoded)"
else
    fail "_is_admin_delete_enabled does not read os.environ — delete gate may be hardcoded"
fi

# Audit events in delete path must not log credential_ref, secret_id, customer_id, or login_customer_id
# Check that build_credential_audit_event does not include any of these fields
for forbidden_field in "credential_ref" "secret_id" "customer_id" "login_customer_id"; do
    if grep -A 30 "def build_credential_audit_event" "$OPENCLAW_DIR/audit.py" 2>/dev/null \
        | grep -q "\"${forbidden_field}\""; then
        fail "Forbidden field '${forbidden_field}' found in build_credential_audit_event body"
    else
        pass "build_credential_audit_event does not emit '${forbidden_field}'"
    fi
done

# No real credential JSON files left in repo
for f in \
    "$OPENCLAW_DIR/credential_references.json" \
    "$REPO/agents/ads-agent/credential_references.json"; do
    if [ -f "$f" ]; then
        if git -C "$REPO" ls-files --error-unmatch "$f" >/dev/null 2>&1; then
            fail "Credential file tracked in git: $f"
        else
            pass "Credential file exists but not tracked: $f (ok — runtime only)"
        fi
    else
        pass "Credential file absent (expected): $(basename $f)"
    fi
done

pass "Phase 3 delete/revoke forbidden behavior checks complete"

# ---------------------------------------------------------------------------
echo ""
echo "[15/19] Admin RBAC scope enforcement..."
# ---------------------------------------------------------------------------

# AdminScope enum importable from auth.py
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from auth import AdminScope
for s in ('READ','WRITE','VALIDATE','ROTATE','DELETE','ADMIN'):
    assert hasattr(AdminScope, s), f'Missing scope: {s}'
" 2>&1); then
    pass "AdminScope enum importable with all six scopes"
else
    fail "AdminScope enum missing or incomplete"
fi

# Config parses OPENCLAW_ADMIN_KEYS and OPENCLAW_READ_KEYS
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    OPENCLAW_ADMIN_KEYS="admin-a,admin-b" OPENCLAW_READ_KEYS="read-x" \
    $PYTHON -c "
from config import get_config
c = get_config()
assert 'admin-a' in c.admin_keys and 'admin-b' in c.admin_keys, 'admin_keys not parsed'
assert 'read-x' in c.read_keys, 'read_keys not parsed'
" 2>&1); then
    pass "config parses OPENCLAW_ADMIN_KEYS and OPENCLAW_READ_KEYS"
else
    fail "config does not parse OPENCLAW_ADMIN_KEYS or OPENCLAW_READ_KEYS"
fi

# resolve_token_scope: admin_key → ADMIN, api_keys → READ, unknown → None
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    OPENCLAW_ADMIN_KEYS="admin-tok" OPENCLAW_READ_KEYS="read-tok" OPENCLAW_API_KEYS="old-tok" \
    $PYTHON -c "
from auth import AdminScope, resolve_token_scope
from config import get_config
c = get_config()
assert resolve_token_scope('admin-tok', c) == AdminScope.ADMIN, 'admin_key should resolve ADMIN'
assert resolve_token_scope('read-tok', c) == AdminScope.READ, 'read_key should resolve READ'
assert resolve_token_scope('old-tok', c) == AdminScope.READ, 'api_key should resolve READ'
assert resolve_token_scope('unknown', c) is None, 'unknown should resolve None'
" 2>&1); then
    pass "resolve_token_scope: ADMIN/READ/fallback/None all correct"
else
    fail "resolve_token_scope returned unexpected scope"
fi

# scope_allows: ADMIN allows all; READ allows READ only; ROTATE requires ADMIN
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from auth import AdminScope, scope_allows
assert scope_allows(AdminScope.ADMIN, AdminScope.READ)
assert scope_allows(AdminScope.ADMIN, AdminScope.WRITE)
assert scope_allows(AdminScope.ADMIN, AdminScope.VALIDATE)
assert scope_allows(AdminScope.ADMIN, AdminScope.ROTATE)
assert scope_allows(AdminScope.ADMIN, AdminScope.DELETE)
assert scope_allows(AdminScope.READ, AdminScope.READ)
assert not scope_allows(AdminScope.READ, AdminScope.WRITE)
assert not scope_allows(AdminScope.READ, AdminScope.VALIDATE)
assert not scope_allows(AdminScope.READ, AdminScope.ROTATE)
assert not scope_allows(AdminScope.READ, AdminScope.DELETE)
" 2>&1); then
    pass "scope_allows: ADMIN grants all; READ grants READ only; ROTATE requires ADMIN"
else
    fail "scope_allows returned unexpected result"
fi

# server.py routes pass required_scope to validate_api_auth
if grep -q "required_scope=AdminScope" "$OPENCLAW_DIR/server.py"; then
    pass "server.py routes pass required_scope to validate_api_auth"
else
    fail "server.py routes do not pass required_scope — RBAC not wired to routes"
fi

# TestClient: READ token on write route → 403 scope_not_granted
RBAC_STORE=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    CREDENTIAL_REFERENCE_STORE_PATH="$RBAC_STORE" \
    OPENCLAW_API_AUTH_ENABLED=true \
    OPENCLAW_READ_KEYS="smoke-read-key" \
    OPENCLAW_AUDIT_ENABLED=false \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    $PYTHON -c "
import sys, os
from fastapi.testclient import TestClient
from server import app
client = TestClient(app)
r = client.post(
    '/openclaw/admin/tenants/rbac-smoke-t/clients/rbac-smoke-c/credentials/google-ads',
    json={'customer_id': '1234', 'developer_token': 'fake-dev-token', 'client_id': 'fake-client-id',
          'client_secret': 'fake-client-secret', 'refresh_token': 'fake-refresh-token'},
    headers={'Authorization': 'Bearer smoke-read-key'},
)
assert r.status_code == 403, f'expected 403, got {r.status_code}: {r.text[:200]}'
codes = [e.get('code') for e in r.json().get('errors', [])]
assert 'scope_not_granted' in codes, f'expected scope_not_granted in {codes}'
" 2>/dev/null); then
    pass "TestClient: READ token on write route → 403 scope_not_granted"
else
    fail "TestClient: READ token on write route did not return 403 scope_not_granted"
fi
rm -f "$RBAC_STORE"

# TestClient: ADMIN token on write route → 200 (scope granted, bundle accepted)
RBAC_STORE2=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    CREDENTIAL_REFERENCE_STORE_PATH="$RBAC_STORE2" \
    OPENCLAW_API_AUTH_ENABLED=true \
    OPENCLAW_ADMIN_KEYS="smoke-admin-key" \
    OPENCLAW_AUDIT_ENABLED=false \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    $PYTHON -c "
from fastapi.testclient import TestClient
from server import app
client = TestClient(app)
r = client.post(
    '/openclaw/admin/tenants/rbac-admin-t/clients/rbac-admin-c/credentials/google-ads',
    json={'customer_id': '9999', 'developer_token': 'fake-dev-token', 'client_id': 'fake-client-id',
          'client_secret': 'fake-client-secret', 'refresh_token': 'fake-refresh-token'},
    headers={'Authorization': 'Bearer smoke-admin-key'},
)
assert r.status_code == 200, f'expected 200, got {r.status_code}: {r.text[:200]}'
assert r.json().get('ok') is True, f'ok not True: {r.json()}'
" 2>/dev/null); then
    pass "TestClient: ADMIN token on write route → 200 ok=true"
else
    fail "TestClient: ADMIN token on write route did not return 200"
fi
rm -f "$RBAC_STORE2"

# OPENCLAW_API_KEYS fallback: read works, write denied
RBAC_STORE3=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    CREDENTIAL_REFERENCE_STORE_PATH="$RBAC_STORE3" \
    OPENCLAW_API_AUTH_ENABLED=true \
    OPENCLAW_API_KEYS="smoke-legacy-key" \
    OPENCLAW_AUDIT_ENABLED=false \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    $PYTHON -c "
from fastapi.testclient import TestClient
from server import app
client = TestClient(app)
# Read allowed
r_read = client.get(
    '/openclaw/admin/tenants/legacy-t/clients/legacy-c/credentials/google-ads/status',
    headers={'Authorization': 'Bearer smoke-legacy-key'},
)
assert r_read.status_code == 200, f'expected 200 for read, got {r_read.status_code}'
# Write denied
r_write = client.post(
    '/openclaw/admin/tenants/legacy-t/clients/legacy-c/credentials/google-ads',
    json={'customer_id': '5555'},
    headers={'Authorization': 'Bearer smoke-legacy-key'},
)
assert r_write.status_code == 403, f'expected 403 for write, got {r_write.status_code}: {r_write.text[:200]}'
codes = [e.get('code') for e in r_write.json().get('errors', [])]
assert 'scope_not_granted' in codes, f'expected scope_not_granted, got {codes}'
" 2>/dev/null); then
    pass "OPENCLAW_API_KEYS fallback: read allowed, write denied (scope_not_granted)"
else
    fail "OPENCLAW_API_KEYS fallback: unexpected scope behavior"
fi
rm -f "$RBAC_STORE3"

pass "Admin RBAC scope enforcement checks complete"

# ---------------------------------------------------------------------------
echo ""
echo "[16/19] Audit seq/digest hardening and maintenance..."
# ---------------------------------------------------------------------------

# audit_maintenance.py importable with both functions
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
import audit_maintenance
assert hasattr(audit_maintenance, 'verify_audit_file'), 'verify_audit_file missing'
assert hasattr(audit_maintenance, 'prune_audit_files'), 'prune_audit_files missing'
" 2>&1); then
    pass "audit_maintenance.py importable with verify_audit_file and prune_audit_files"
else
    fail "audit_maintenance.py not importable or missing functions"
fi

# audit.py has _compute_file_digest and _next_audit_seq
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
import audit
assert hasattr(audit, '_compute_file_digest'), '_compute_file_digest missing from audit'
assert hasattr(audit, '_next_audit_seq'), '_next_audit_seq missing from audit'
" 2>&1); then
    pass "audit.py has _compute_file_digest and _next_audit_seq"
else
    fail "audit.py missing _compute_file_digest or _next_audit_seq"
fi

# Config parses OPENCLAW_AUDIT_RETAIN_DAYS
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    OPENCLAW_AUDIT_RETAIN_DAYS=30 \
    $PYTHON -c "
from config import get_config
c = get_config()
assert c.audit_retain_days == 30, f'Expected 30, got {c.audit_retain_days}'
" 2>&1); then
    pass "config parses OPENCLAW_AUDIT_RETAIN_DAYS=30"
else
    fail "config does not parse OPENCLAW_AUDIT_RETAIN_DAYS"
fi

# Config default audit_retain_days=90
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from config import get_config
c = get_config()
assert c.audit_retain_days == 90, f'Expected default 90, got {c.audit_retain_days}'
" 2>&1); then
    pass "config audit_retain_days default=90"
else
    fail "config audit_retain_days default is not 90"
fi

# prune_audit_files: empty dir returns ok=True with zero counts
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
import tempfile
from pathlib import Path
from audit_maintenance import prune_audit_files
with tempfile.TemporaryDirectory() as tmp:
    result = prune_audit_files(Path(tmp), retain_days=90)
    assert result['ok'] is True, f'Expected ok=True: {result}'
    assert result['deleted_count'] == 0, f'Expected 0 deleted: {result}'
    assert result['kept_count'] == 0, f'Expected 0 kept: {result}'
    assert result['errors'] == [], f'Expected no errors: {result}'
" 2>&1); then
    pass "prune_audit_files: empty dir → ok=True, deleted=0, kept=0"
else
    fail "prune_audit_files: unexpected result for empty dir"
fi

# verify_audit_file: valid 2-event chain passes
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
import json, tempfile, hashlib
from pathlib import Path
from audit_maintenance import verify_audit_file
with tempfile.TemporaryDirectory() as tmp:
    audit_file = Path(tmp) / 'test.jsonl'
    e1 = {'seq': 1, 'file_digest': '', 'op': 'test'}
    line1 = json.dumps(e1) + '\n'
    e2 = {'seq': 2, 'file_digest': hashlib.sha256(line1.encode('utf-8')).hexdigest(), 'op': 'test2'}
    line2 = json.dumps(e2) + '\n'
    audit_file.write_text(line1 + line2, encoding='utf-8')
    result = verify_audit_file(audit_file)
    assert result['ok'] is True, f'Expected ok=True: {result}'
    assert result['events_checked'] == 2, f'Expected 2 events: {result}'
    assert result['errors'] == [], f'Expected no errors: {result}'
" 2>&1); then
    pass "verify_audit_file: valid 2-event file passes"
else
    fail "verify_audit_file: valid file failed verification"
fi

# verify_audit_file: tampered digest detected
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
import json, tempfile, hashlib
from pathlib import Path
from audit_maintenance import verify_audit_file
with tempfile.TemporaryDirectory() as tmp:
    audit_file = Path(tmp) / 'tampered.jsonl'
    e1 = {'seq': 1, 'file_digest': '', 'op': 'test'}
    line1 = json.dumps(e1) + '\n'
    e2_tampered = {'seq': 2, 'file_digest': 'aabbcc', 'op': 'test2'}
    line2 = json.dumps(e2_tampered) + '\n'
    audit_file.write_text(line1 + line2, encoding='utf-8')
    result = verify_audit_file(audit_file)
    assert result['ok'] is False, f'Expected ok=False for tampered file: {result}'
    assert any('digest_mismatch' in e for e in result['errors']), f'Expected digest_mismatch: {result}'
" 2>&1); then
    pass "verify_audit_file: tampered digest detected (digest_mismatch)"
else
    fail "verify_audit_file: tampered file not detected"
fi

# Lifecycle demo includes L/M/N/O sections (lifecycle demo already ran in [11/19])
# Re-run just to capture output for marker checks
_OUT_PHASE2=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    $PYTHON run_admin_credentials_lifecycle_demo.py 2>&1)
echo "$_OUT_PHASE2" | grep -q "verify_audit_file ok=True" \
    && pass "lifecycle demo L: verify_audit_file ok=True confirmed" \
    || { echo "  ✗ lifecycle demo L: verify_audit_file ok=True not found"; echo "$_OUT_PHASE2" | tail -20; exit 1; }

echo "$_OUT_PHASE2" | grep -q "tampered file fails verification" \
    && pass "lifecycle demo M: tamper detection confirmed" \
    || { echo "  ✗ lifecycle demo M: tamper detection not found"; echo "$_OUT_PHASE2" | tail -20; exit 1; }

echo "$_OUT_PHASE2" | grep -q "audit_append_failed" \
    && pass "lifecycle demo N: audit failure warning confirmed" \
    || { echo "  ✗ lifecycle demo N: audit_append_failed not found"; echo "$_OUT_PHASE2" | tail -20; exit 1; }

echo "$_OUT_PHASE2" | grep -q "old file was deleted" \
    && pass "lifecycle demo O: prune deleted old file confirmed" \
    || { echo "  ✗ lifecycle demo O: prune marker not found"; echo "$_OUT_PHASE2" | tail -20; exit 1; }

pass "Audit seq/digest hardening and maintenance checks complete"

# ---------------------------------------------------------------------------
echo ""
echo "[17/19] Rotate credential endpoint..."
# ---------------------------------------------------------------------------

# rotate_google_ads_credentials importable from admin
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "from admin import rotate_google_ads_credentials" 2>&1); then
    pass "rotate_google_ads_credentials importable from admin"
else
    fail "rotate_google_ads_credentials not importable from admin"
fi

# server.py has rotate route
if grep -q "credentials/google-ads/rotate" "$OPENCLAW_DIR/server.py"; then
    pass "server.py has /rotate route"
else
    fail "server.py missing /rotate route"
fi

# rotate route uses AdminScope.ROTATE
if grep -A 30 "credentials/google-ads/rotate" "$OPENCLAW_DIR/server.py" | grep -q "AdminScope.ROTATE"; then
    pass "rotate route uses AdminScope.ROTATE"
else
    fail "rotate route does not use AdminScope.ROTATE"
fi

# rotate_google_ads_credentials must not call get_secret_bundle (match method call syntax)
if grep -A 120 "def rotate_google_ads_credentials" "$OPENCLAW_DIR/admin.py" | grep -q "\.get_secret_bundle"; then
    fail "rotate_google_ads_credentials calls .get_secret_bundle() — must not fetch secrets"
else
    pass "rotate_google_ads_credentials does not call .get_secret_bundle()"
fi

# TestClient: full rotate success → 200, ok=true, status=active
ROTATE_STORE=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    CREDENTIAL_REFERENCE_STORE_PATH="$ROTATE_STORE" \
    OPENCLAW_API_AUTH_ENABLED=false \
    OPENCLAW_AUDIT_ENABLED=false \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    $PYTHON -c "
from fastapi.testclient import TestClient
from server import app
import admin as adm
from credentials.secret_store import InMemorySecretStore
_store = InMemorySecretStore()
adm.create_secret_store = lambda: _store
client = TestClient(app)
_FAKE = {
    'developer_token': 'fake-dt',
    'client_id': 'fake-ci',
    'client_secret': 'fake-cs',
    'refresh_token': 'fake-rt',
}
base = '/openclaw/admin/tenants/smoke-rotate-t/clients/smoke-rotate-c/credentials/google-ads'
r_w = client.post(base, json={'customer_id': '1111111111', **_FAKE})
assert r_w.status_code == 200, f'write failed: {r_w.text[:200]}'
r_rot = client.post(f'{base}/rotate', json=_FAKE)
assert r_rot.status_code == 200, f'rotate failed: {r_rot.status_code} {r_rot.text[:200]}'
d = r_rot.json()
assert d['ok'] is True, f'ok not True: {d}'
rr = d.get('rotation_result') or {}
assert rr['structurally_complete'] is True, f'not complete: {rr}'
cred = d.get('credential_status') or {}
assert cred['status'] == 'active', f'status not active: {cred}'
import json as _json
resp_str = _json.dumps(d)
for v in ('fake-dt', 'fake-ci', 'fake-cs', 'fake-rt'):
    assert v not in resp_str, f'secret value leaked: {v}'
" 2>/dev/null); then
    pass "TestClient: rotate full success → 200, ok=true, status=active"
else
    fail "TestClient: rotate full success failed"
fi
rm -f "$ROTATE_STORE"

# TestClient: rotate missing credential → 404
ROTATE_STORE2=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    CREDENTIAL_REFERENCE_STORE_PATH="$ROTATE_STORE2" \
    OPENCLAW_API_AUTH_ENABLED=false \
    OPENCLAW_AUDIT_ENABLED=false \
    GCP_SECRET_MANAGER_ENABLED=false \
    $PYTHON -c "
from fastapi.testclient import TestClient
from server import app
client = TestClient(app)
_FAKE = {
    'developer_token': 'fake-dt',
    'client_id': 'fake-ci',
    'client_secret': 'fake-cs',
    'refresh_token': 'fake-rt',
}
r = client.post(
    '/openclaw/admin/tenants/smoke-nomatch-t/clients/smoke-nomatch-c/credentials/google-ads/rotate',
    json=_FAKE,
)
assert r.status_code == 404, f'expected 404, got {r.status_code}: {r.text[:200]}'
d = r.json()
assert d['ok'] is False, f'ok not False: {d}'
codes = [e.get('code') for e in d.get('errors', [])]
assert 'credential_not_found' in codes, f'expected credential_not_found: {codes}'
" 2>/dev/null); then
    pass "TestClient: rotate missing credential → 404 credential_not_found"
else
    fail "TestClient: rotate missing credential did not return 404"
fi
rm -f "$ROTATE_STORE2"

# TestClient: rotate revoked → 409
ROTATE_STORE3=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    CREDENTIAL_REFERENCE_STORE_PATH="$ROTATE_STORE3" \
    OPENCLAW_API_AUTH_ENABLED=false \
    OPENCLAW_AUDIT_ENABLED=false \
    OPENCLAW_ADMIN_DELETE_ENABLED=true \
    GCP_SECRET_MANAGER_ENABLED=false \
    $PYTHON -c "
from fastapi.testclient import TestClient
from server import app
import admin as adm
from credentials.secret_store import InMemorySecretStore
_store = InMemorySecretStore()
adm.create_secret_store = lambda: _store
client = TestClient(app)
_FAKE = {
    'developer_token': 'fake-dt',
    'client_id': 'fake-ci',
    'client_secret': 'fake-cs',
    'refresh_token': 'fake-rt',
}
base = '/openclaw/admin/tenants/smoke-revoke-t/clients/smoke-revoke-c/credentials/google-ads'
r_w = client.post(base, json={'customer_id': '2222222222', **_FAKE})
assert r_w.status_code == 200, f'write failed: {r_w.text[:200]}'
r_d = client.delete(base)
assert r_d.status_code == 200, f'delete failed: {r_d.text[:200]}'
r_rot = client.post(f'{base}/rotate', json=_FAKE)
assert r_rot.status_code == 409, f'expected 409, got {r_rot.status_code}: {r_rot.text[:200]}'
d = r_rot.json()
assert d['ok'] is False, f'ok not False: {d}'
codes = [e.get('code') for e in d.get('errors', [])]
assert 'invalid_status_for_rotation' in codes, f'expected invalid_status_for_rotation: {codes}'
" 2>/dev/null); then
    pass "TestClient: rotate revoked → 409 invalid_status_for_rotation"
else
    fail "TestClient: rotate revoked did not return 409"
fi
rm -f "$ROTATE_STORE3"

# TestClient: READ token on rotate route → 403 scope_not_granted
ROTATE_STORE4=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    CREDENTIAL_REFERENCE_STORE_PATH="$ROTATE_STORE4" \
    OPENCLAW_API_AUTH_ENABLED=true \
    OPENCLAW_READ_KEYS="smoke-read-key" \
    OPENCLAW_AUDIT_ENABLED=false \
    GCP_SECRET_MANAGER_ENABLED=false \
    $PYTHON -c "
from fastapi.testclient import TestClient
from server import app
client = TestClient(app)
_FAKE = {
    'developer_token': 'fake-dt',
    'client_id': 'fake-ci',
    'client_secret': 'fake-cs',
    'refresh_token': 'fake-rt',
}
r = client.post(
    '/openclaw/admin/tenants/smoke-rbac-t/clients/smoke-rbac-c/credentials/google-ads/rotate',
    json=_FAKE,
    headers={'Authorization': 'Bearer smoke-read-key'},
)
assert r.status_code == 403, f'expected 403, got {r.status_code}: {r.text[:200]}'
codes = [e.get('code') for e in r.json().get('errors', [])]
assert 'scope_not_granted' in codes, f'expected scope_not_granted: {codes}'
" 2>/dev/null); then
    pass "TestClient: READ token on rotate route → 403 scope_not_granted"
else
    fail "TestClient: READ token on rotate route did not return 403"
fi
rm -f "$ROTATE_STORE4"

# Lifecycle demo P-T markers
_OUT_PHASE3=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    $PYTHON run_admin_credentials_lifecycle_demo.py 2>&1)
echo "$_OUT_PHASE3" | grep -q "rotate returns ok=true" \
    && pass "lifecycle demo P: rotate success confirmed" \
    || { echo "  ✗ lifecycle demo P: rotate success not found"; echo "$_OUT_PHASE3" | tail -20; exit 1; }

echo "$_OUT_PHASE3" | grep -q "rotate from CONFIGURED ok=true" \
    && pass "lifecycle demo Q: rotate from CONFIGURED confirmed" \
    || { echo "  ✗ lifecycle demo Q: rotate from CONFIGURED not found"; echo "$_OUT_PHASE3" | tail -20; exit 1; }

echo "$_OUT_PHASE3" | grep -q "incomplete rotate returns ok=false" \
    && pass "lifecycle demo R: incomplete rotate ok=false confirmed" \
    || { echo "  ✗ lifecycle demo R: incomplete rotate not found"; echo "$_OUT_PHASE3" | tail -20; exit 1; }

echo "$_OUT_PHASE3" | grep -q "invalid_status_for_rotation" \
    && pass "lifecycle demo S: invalid_status_for_rotation confirmed" \
    || { echo "  ✗ lifecycle demo S: invalid_status_for_rotation not found"; echo "$_OUT_PHASE3" | tail -20; exit 1; }

echo "$_OUT_PHASE3" | grep -q "rotate missing credential ok=false" \
    && pass "lifecycle demo T: missing credential rotate confirmed" \
    || { echo "  ✗ lifecycle demo T: missing credential rotate not found"; echo "$_OUT_PHASE3" | tail -20; exit 1; }

# API demo rotate scenarios (run API demo, check rotate markers)
_OUT_ROT_API=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    OPENCLAW_API_AUTH_ENABLED=false \
    $PYTHON run_admin_credentials_lifecycle_api_demo.py 2>&1)
echo "$_OUT_ROT_API" | grep -q "rotate A: status 200" \
    && pass "API demo rotate A: 200 success confirmed" \
    || { echo "  ✗ API demo rotate A: not found"; echo "$_OUT_ROT_API" | tail -20; exit 1; }

echo "$_OUT_ROT_API" | grep -q "rotate B: status 404 for missing credential" \
    && pass "API demo rotate B: 404 not-found confirmed" \
    || { echo "  ✗ API demo rotate B: not found"; echo "$_OUT_ROT_API" | tail -20; exit 1; }

echo "$_OUT_ROT_API" | grep -q "rotate C: status 409 for revoked credential" \
    && pass "API demo rotate C: 409 revoked confirmed" \
    || { echo "  ✗ API demo rotate C: not found"; echo "$_OUT_ROT_API" | tail -20; exit 1; }

echo "$_OUT_ROT_API" | grep -q "rotate E: status 403 for read token" \
    && pass "API demo rotate E: 403 scope_not_granted confirmed" \
    || { echo "  ✗ API demo rotate E: not found"; echo "$_OUT_ROT_API" | tail -20; exit 1; }

pass "Rotate credential endpoint checks complete"

# ---------------------------------------------------------------------------
echo ""
echo "[18/19] Per-tenant token isolation (OPENCLAW_TENANT_KEYS)..."
# ---------------------------------------------------------------------------

# validate_tenant_access importable from auth
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "from auth import validate_tenant_access" 2>&1); then
    pass "validate_tenant_access importable from auth"
else
    fail "validate_tenant_access not importable from auth"
fi

# parse_tenant_keys importable from config
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "from config import parse_tenant_keys" 2>&1); then
    pass "parse_tenant_keys importable from config"
else
    fail "parse_tenant_keys not importable from config"
fi

# parse_tenant_keys: empty/None → {}
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from config import parse_tenant_keys
assert parse_tenant_keys(None) == {}, 'None should return {}'
assert parse_tenant_keys('') == {}, 'empty string should return {}'
assert parse_tenant_keys('   ') == {}, 'whitespace should return {}'
" 2>/dev/null); then
    pass "parse_tenant_keys: empty/None → {}"
else
    fail "parse_tenant_keys: empty/None did not return {}"
fi

# parse_tenant_keys: single pair
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from config import parse_tenant_keys
result = parse_tenant_keys('tok-a:tenant-a')
assert result == {'tok-a': {'tenant-a'}}, f'unexpected: {result}'
" 2>/dev/null); then
    pass "parse_tenant_keys: single pair parsed correctly"
else
    fail "parse_tenant_keys: single pair failed"
fi

# parse_tenant_keys: multi-tenant same token
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from config import parse_tenant_keys
result = parse_tenant_keys('tok-a:tenant-a,tok-a:tenant-b,tok-b:tenant-c')
assert result == {'tok-a': {'tenant-a', 'tenant-b'}, 'tok-b': {'tenant-c'}}, f'unexpected: {result}'
" 2>/dev/null); then
    pass "parse_tenant_keys: multi-tenant same token parsed correctly"
else
    fail "parse_tenant_keys: multi-tenant same token failed"
fi

# validate_tenant_access: no tenant_keys → always allowed
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    OPENCLAW_API_AUTH_ENABLED=false \
    $PYTHON -c "
from auth import validate_tenant_access
from config import OpenClawConfig
cfg = OpenClawConfig(
    env='local', api_auth_enabled=False, api_keys=[], admin_keys=[], read_keys=[],
    allowed_origins=['*'], default_tenant='demo', require_tenant_header=False,
    audit_enabled=False, audit_root='/tmp', memory_enabled=False, memory_root='/tmp',
    n8n_ads_webhook_url=None, n8n_webhook_timeout=15.0, port=8100,
    audit_retain_days=90, tenant_keys={},
    admin_rate_limit_rpm=0, admin_rate_limit_sensitive_rpm=0,
)
ok, errs = validate_tenant_access('any-token', 'any-tenant', cfg)
assert ok is True, f'expected True, got {ok}'
assert errs == [], f'expected [], got {errs}'
ok2, _ = validate_tenant_access(None, 'any-tenant', cfg)
assert ok2 is True, 'None token should be allowed when no map'
" 2>/dev/null); then
    pass "validate_tenant_access: no tenant_keys → always allowed"
else
    fail "validate_tenant_access: no tenant_keys check failed"
fi

# validate_tenant_access: token listed + tenant allowed → True
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from auth import validate_tenant_access
from config import OpenClawConfig
cfg = OpenClawConfig(
    env='local', api_auth_enabled=True, api_keys=[], admin_keys=['tok-x'], read_keys=[],
    allowed_origins=['*'], default_tenant='demo', require_tenant_header=False,
    audit_enabled=False, audit_root='/tmp', memory_enabled=False, memory_root='/tmp',
    n8n_ads_webhook_url=None, n8n_webhook_timeout=15.0, port=8100,
    audit_retain_days=90, tenant_keys={'tok-x': {'tenant-a', 'tenant-b'}},
    admin_rate_limit_rpm=0, admin_rate_limit_sensitive_rpm=0,
)
ok, errs = validate_tenant_access('tok-x', 'tenant-a', cfg)
assert ok is True, f'expected True for allowed tenant, got {ok}'
assert errs == [], f'expected [], got {errs}'
ok2, errs2 = validate_tenant_access('tok-x', 'tenant-b', cfg)
assert ok2 is True, f'expected True for tenant-b, got {ok2}'
" 2>/dev/null); then
    pass "validate_tenant_access: listed token + allowed tenant → True"
else
    fail "validate_tenant_access: listed token + allowed tenant check failed"
fi

# validate_tenant_access: token listed + tenant NOT allowed → False + tenant_access_denied
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from auth import validate_tenant_access
from config import OpenClawConfig
cfg = OpenClawConfig(
    env='local', api_auth_enabled=True, api_keys=[], admin_keys=['tok-x'], read_keys=[],
    allowed_origins=['*'], default_tenant='demo', require_tenant_header=False,
    audit_enabled=False, audit_root='/tmp', memory_enabled=False, memory_root='/tmp',
    n8n_ads_webhook_url=None, n8n_webhook_timeout=15.0, port=8100,
    audit_retain_days=90, tenant_keys={'tok-x': {'tenant-a'}},
    admin_rate_limit_rpm=0, admin_rate_limit_sensitive_rpm=0,
)
ok, errs = validate_tenant_access('tok-x', 'tenant-z', cfg)
assert ok is False, f'expected False for unlisted tenant, got {ok}'
codes = [e.get('code') for e in errs if isinstance(e, dict)]
assert 'tenant_access_denied' in codes, f'expected tenant_access_denied: {codes}'
" 2>/dev/null); then
    pass "validate_tenant_access: listed token + denied tenant → False + tenant_access_denied"
else
    fail "validate_tenant_access: listed token + denied tenant check failed"
fi

# validate_tenant_access: token NOT listed while map is set → global access
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from auth import validate_tenant_access
from config import OpenClawConfig
cfg = OpenClawConfig(
    env='local', api_auth_enabled=True, api_keys=[], admin_keys=['tok-x', 'tok-unlisted'],
    read_keys=[], allowed_origins=['*'], default_tenant='demo', require_tenant_header=False,
    audit_enabled=False, audit_root='/tmp', memory_enabled=False, memory_root='/tmp',
    n8n_ads_webhook_url=None, n8n_webhook_timeout=15.0, port=8100,
    audit_retain_days=90, tenant_keys={'tok-x': {'tenant-a'}},
    admin_rate_limit_rpm=0, admin_rate_limit_sensitive_rpm=0,
)
ok, errs = validate_tenant_access('tok-unlisted', 'any-tenant', cfg)
assert ok is True, f'unlisted token should have global access, got ok={ok}'
assert errs == [], f'expected [], got {errs}'
" 2>/dev/null); then
    pass "validate_tenant_access: unlisted token while map set → global access"
else
    fail "validate_tenant_access: unlisted token global access check failed"
fi

# TestClient: tenant_access_denied returned when token restricted to wrong tenant
TENANT_STORE=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    CREDENTIAL_REFERENCE_STORE_PATH="$TENANT_STORE" \
    OPENCLAW_API_AUTH_ENABLED=true \
    OPENCLAW_ADMIN_KEYS="smoke-admin-tenant-tok" \
    OPENCLAW_TENANT_KEYS="smoke-admin-tenant-tok:allowed-tenant" \
    OPENCLAW_AUDIT_ENABLED=false \
    GCP_SECRET_MANAGER_ENABLED=false \
    $PYTHON -c "
from fastapi.testclient import TestClient
from server import app
client = TestClient(app)
r = client.get(
    '/openclaw/admin/tenants/not-allowed-tenant/clients/smoke-c/credentials/google-ads/status',
    headers={'Authorization': 'Bearer smoke-admin-tenant-tok'},
)
assert r.status_code == 403, f'expected 403, got {r.status_code}: {r.text[:200]}'
codes = [e.get('code') for e in r.json().get('errors', [])]
assert 'tenant_access_denied' in codes, f'expected tenant_access_denied: {codes}'
" 2>/dev/null); then
    pass "TestClient: restricted token on wrong tenant → 403 tenant_access_denied"
else
    fail "TestClient: restricted token on wrong tenant did not return 403 tenant_access_denied"
fi
rm -f "$TENANT_STORE"

# TestClient: allowed tenant passes through with 200
TENANT_STORE2=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    CREDENTIAL_REFERENCE_STORE_PATH="$TENANT_STORE2" \
    OPENCLAW_API_AUTH_ENABLED=true \
    OPENCLAW_ADMIN_KEYS="smoke-admin-tenant-tok" \
    OPENCLAW_TENANT_KEYS="smoke-admin-tenant-tok:allowed-tenant" \
    OPENCLAW_AUDIT_ENABLED=false \
    GCP_SECRET_MANAGER_ENABLED=false \
    $PYTHON -c "
from fastapi.testclient import TestClient
from server import app
client = TestClient(app)
r = client.get(
    '/openclaw/admin/tenants/allowed-tenant/clients/smoke-c/credentials/google-ads/status',
    headers={'Authorization': 'Bearer smoke-admin-tenant-tok'},
)
assert r.status_code == 200, f'expected 200, got {r.status_code}: {r.text[:200]}'
assert r.json().get('ok') is True, f\"ok not True: {r.json()}\"
" 2>/dev/null); then
    pass "TestClient: restricted token on allowed tenant → 200 ok"
else
    fail "TestClient: restricted token on allowed tenant did not return 200"
fi
rm -f "$TENANT_STORE2"

# API demo tenant scenarios confirmed
_OUT_TENANT_API=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    OPENCLAW_API_AUTH_ENABLED=false \
    $PYTHON run_admin_credentials_lifecycle_api_demo.py 2>&1)
echo "$_OUT_TENANT_API" | grep -q "tenant A: no restriction" \
    && pass "API demo tenant A: backward compat confirmed" \
    || { echo "  ✗ API demo tenant A: not found"; echo "$_OUT_TENANT_API" | tail -20; exit 1; }

echo "$_OUT_TENANT_API" | grep -q "tenant B: unlisted tenant → 403" \
    && pass "API demo tenant B: tenant_access_denied confirmed" \
    || { echo "  ✗ API demo tenant B: not found"; echo "$_OUT_TENANT_API" | tail -20; exit 1; }

echo "$_OUT_TENANT_API" | grep -q "tenant E: scope check" \
    && pass "API demo tenant E: scope checked before tenant confirmed" \
    || { echo "  ✗ API demo tenant E: not found"; echo "$_OUT_TENANT_API" | tail -20; exit 1; }

echo "$_OUT_TENANT_API" | grep -q "tenant F: invalid token" \
    && pass "API demo tenant F: 401 for invalid token confirmed" \
    || { echo "  ✗ API demo tenant F: not found"; echo "$_OUT_TENANT_API" | tail -20; exit 1; }

pass "Per-tenant token isolation checks complete"

# ---------------------------------------------------------------------------
echo ""
echo "[19/19] Rate limiting (OPENCLAW_ADMIN_RATE_LIMIT_RPM)..."
# ---------------------------------------------------------------------------

# rate_limit.py importable with all public symbols
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from rate_limit import RateLimiter, RateLimitCategory, get_rate_limiter, check_rate_limit
" 2>&1); then
    pass "rate_limit.py: RateLimiter, RateLimitCategory, get_rate_limiter, check_rate_limit all importable"
else
    fail "rate_limit.py: import failed"
fi

# RateLimitCategory constants
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from rate_limit import RateLimitCategory
assert RateLimitCategory.STANDARD == 'standard'
assert RateLimitCategory.SENSITIVE == 'sensitive'
" 2>/dev/null); then
    pass "RateLimitCategory: STANDARD='standard', SENSITIVE='sensitive'"
else
    fail "RateLimitCategory: unexpected values"
fi

# RateLimiter.check: limit=0 always allowed
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from rate_limit import RateLimiter
rl = RateLimiter()
for i in range(10):
    r = rl.check('test-token', 'standard', 0)
    assert r['allowed'] is True, f'limit=0 should always allow: {r}'
    assert r['remaining'] is None, f'limit=0 remaining should be None: {r}'
" 2>/dev/null); then
    pass "RateLimiter.check: limit=0 always allowed (10 iterations)"
else
    fail "RateLimiter.check: limit=0 check failed"
fi

# RateLimiter.check: limit=2 sliding window enforced
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from rate_limit import RateLimiter
rl = RateLimiter()
r1 = rl.check('tok', 'standard', 2)
assert r1['allowed'] is True and r1['remaining'] == 1
r2 = rl.check('tok', 'standard', 2)
assert r2['allowed'] is True and r2['remaining'] == 0
r3 = rl.check('tok', 'standard', 2)
assert r3['allowed'] is False
assert r3['remaining'] == 0
assert r3['retry_after_seconds'] >= 1
" 2>/dev/null); then
    pass "RateLimiter.check: limit=2 allows 2, denies 3rd with retry_after_seconds"
else
    fail "RateLimiter.check: sliding window enforcement failed"
fi

# Per-token isolation
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from rate_limit import RateLimiter
rl = RateLimiter()
rl.check('token-a', 'standard', 1)
r_a2 = rl.check('token-a', 'standard', 1)
assert r_a2['allowed'] is False, 'token-a should be denied'
r_b1 = rl.check('token-b', 'standard', 1)
assert r_b1['allowed'] is True, 'token-b should be unaffected'
" 2>/dev/null); then
    pass "RateLimiter: per-token isolation (exhausted token-a does not affect token-b)"
else
    fail "RateLimiter: per-token isolation failed"
fi

# Category isolation: standard and sensitive are separate deques
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from rate_limit import RateLimiter
rl = RateLimiter()
rl.check('tok', 'sensitive', 1)
r_s2 = rl.check('tok', 'sensitive', 1)
assert r_s2['allowed'] is False, 'sensitive should be denied'
r_std = rl.check('tok', 'standard', 1)
assert r_std['allowed'] is True, 'standard should still be allowed'
" 2>/dev/null); then
    pass "RateLimiter: standard and sensitive budgets are independent deques"
else
    fail "RateLimiter: category isolation failed"
fi

# check_rate_limit: limit=0 → always (True, [])
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    OPENCLAW_ADMIN_RATE_LIMIT_RPM=0 \
    $PYTHON -c "
from rate_limit import check_rate_limit, RateLimitCategory, get_rate_limiter
get_rate_limiter().reset_for_tests()
from config import get_config
cfg = get_config()
for i in range(5):
    ok, errs = check_rate_limit('test-tok', RateLimitCategory.STANDARD, cfg)
    assert ok is True and errs == []
" 2>/dev/null); then
    pass "check_rate_limit: RPM=0 → always (True, [])"
else
    fail "check_rate_limit: RPM=0 check failed"
fi

# check_rate_limit: limit>0 returns rate_limit_exceeded with retry_after_seconds
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    OPENCLAW_ADMIN_RATE_LIMIT_RPM=1 \
    $PYTHON -c "
from rate_limit import check_rate_limit, RateLimitCategory, get_rate_limiter
from config import get_config
rl = get_rate_limiter()
rl.reset_for_tests()
cfg = get_config()
ok1, _ = check_rate_limit('tok', RateLimitCategory.STANDARD, cfg)
assert ok1 is True, 'first request should be allowed'
ok2, errs2 = check_rate_limit('tok', RateLimitCategory.STANDARD, cfg)
assert ok2 is False, f'second request should be denied: {errs2}'
err = errs2[0]
assert err.get('code') == 'rate_limit_exceeded', f'unexpected code: {err}'
assert err.get('retry_after_seconds', 0) >= 1, f'retry_after should be >= 1: {err}'
assert err.get('recoverable') is True, f'should be recoverable: {err}'
" 2>/dev/null); then
    pass "check_rate_limit: RPM=1 → rate_limit_exceeded error with retry_after_seconds and recoverable=true"
else
    fail "check_rate_limit: RPM=1 enforcement failed"
fi

# Config parses both rate limit env vars
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    OPENCLAW_ADMIN_RATE_LIMIT_RPM=30 \
    OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM=10 \
    $PYTHON -c "
from config import get_config
c = get_config()
assert c.admin_rate_limit_rpm == 30, f'expected 30, got {c.admin_rate_limit_rpm}'
assert c.admin_rate_limit_sensitive_rpm == 10, f'expected 10, got {c.admin_rate_limit_sensitive_rpm}'
" 2>/dev/null); then
    pass "config: OPENCLAW_ADMIN_RATE_LIMIT_RPM=30, OPENCLAW_ADMIN_RATE_LIMIT_SENSITIVE_RPM=10 parsed"
else
    fail "config: rate limit env vars not parsed correctly"
fi

# Config default rate limits are 0 (backward-compatible: disabled)
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from config import get_config
c = get_config()
assert c.admin_rate_limit_rpm == 0, f'default should be 0, got {c.admin_rate_limit_rpm}'
assert c.admin_rate_limit_sensitive_rpm == 0, f'default should be 0, got {c.admin_rate_limit_sensitive_rpm}'
" 2>/dev/null); then
    pass "config: admin_rate_limit_rpm and admin_rate_limit_sensitive_rpm default to 0"
else
    fail "config: rate limit defaults are not 0"
fi

# server.py wires check_rate_limit with 429 response
if grep -q "check_rate_limit" "$OPENCLAW_DIR/server.py" && grep -q "status_code=429" "$OPENCLAW_DIR/server.py"; then
    pass "server.py: check_rate_limit imported and 429 status code wired"
else
    fail "server.py: missing check_rate_limit import or 429 status code"
fi

# API demo: all rate scenarios pass
_OUT_RATE_API=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    OPENCLAW_API_AUTH_ENABLED=false \
    $PYTHON run_admin_credentials_lifecycle_api_demo.py 2>&1)
echo "$_OUT_RATE_API" | grep -q "rate A: request 1 not rate-limited" \
    && pass "API demo rate A: disabled by default confirmed" \
    || { echo "  ✗ API demo rate A: not found"; echo "$_OUT_RATE_API" | tail -20; exit 1; }

echo "$_OUT_RATE_API" | grep -q "rate B: request 3 → 429" \
    && pass "API demo rate B: standard limit enforced (429)" \
    || { echo "  ✗ API demo rate B: not found"; echo "$_OUT_RATE_API" | tail -20; exit 1; }

echo "$_OUT_RATE_API" | grep -q "rate C: second rotate → 429" \
    && pass "API demo rate C: sensitive limit enforced (429)" \
    || { echo "  ✗ API demo rate C: not found"; echo "$_OUT_RATE_API" | tail -20; exit 1; }

echo "$_OUT_RATE_API" | grep -q "rate D: status (standard) → 200 despite sensitive exhausted" \
    && pass "API demo rate D: standard/sensitive budget separation confirmed" \
    || { echo "  ✗ API demo rate D: not found"; echo "$_OUT_RATE_API" | tail -20; exit 1; }

echo "$_OUT_RATE_API" | grep -q "rate E: token-b unaffected → 200" \
    && pass "API demo rate E: per-token isolation confirmed" \
    || { echo "  ✗ API demo rate E: not found"; echo "$_OUT_RATE_API" | tail -20; exit 1; }

echo "$_OUT_RATE_API" | grep -q "rate F: valid request (budget intact) → 200" \
    && pass "API demo rate F: denied requests do not consume rate budget confirmed" \
    || { echo "  ✗ API demo rate F: not found"; echo "$_OUT_RATE_API" | tail -20; exit 1; }

echo "$_OUT_RATE_API" | grep -q "no token values in rate response" \
    && pass "API demo rate G: no token values in rate scenario responses confirmed" \
    || { echo "  ✗ API demo rate G: not found"; echo "$_OUT_RATE_API" | tail -20; exit 1; }

pass "Rate limiting checks complete"

# ---------------------------------------------------------------------------
echo ""
echo "[20/24] Audit file locking (fcntl)..."
# ---------------------------------------------------------------------------

# _HAS_FCNTL constant importable from audit module
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
import audit
assert hasattr(audit, '_HAS_FCNTL'), '_HAS_FCNTL missing from audit module'
" 2>&1); then
    pass "audit.py: _HAS_FCNTL constant present"
else
    fail "audit.py: _HAS_FCNTL not found"
fi

# LOCK_EX wired in audit.py when fcntl available
if grep -q "LOCK_EX" "$OPENCLAW_DIR/audit.py"; then
    pass "audit.py: LOCK_EX present in locking path"
else
    fail "audit.py: LOCK_EX not found"
fi

# append_audit_event returns lock_used field
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
import tempfile, os, shutil
tmp = tempfile.mkdtemp(prefix='kaiju_lock_smoke_')
os.environ['OPENCLAW_AUDIT_ROOT'] = tmp
os.environ['OPENCLAW_AUDIT_ENABLED'] = 'true'
from audit import append_audit_event
ev = {'event_type': 'smoke_test', 'ok': True}
r = append_audit_event(ev)
assert r.get('ok') is True, f'ok not True: {r}'
assert 'lock_used' in r, f'lock_used missing: {r}'
assert r.get('seq') == 1, f'seq != 1: {r}'
shutil.rmtree(tmp, ignore_errors=True)
" 2>&1); then
    pass "append_audit_event: lock_used field present, seq=1 on first append"
else
    fail "append_audit_event: lock_used or seq check failed"
fi

# lifecycle demo Section U passes
_OUT_LOCK=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    $PYTHON run_admin_credentials_lifecycle_demo.py 2>&1)
echo "$_OUT_LOCK" | grep -q "All credential lifecycle audit assertions passed" \
    && pass "lifecycle demo with Section U: All assertions passed" \
    || { echo "  ✗ lifecycle demo Section U: All assertions not found"; echo "$_OUT_LOCK" | tail -25; exit 1; }

echo "$_OUT_LOCK" | grep -q "U: first append ok=true" \
    && pass "lifecycle demo Section U: append ok=true confirmed" \
    || { echo "  ✗ Section U append marker not found"; echo "$_OUT_LOCK" | tail -25; exit 1; }

echo "$_OUT_LOCK" | grep -q "U: seq=1 for first event" \
    && pass "lifecycle demo Section U: seq=1 confirmed" \
    || { echo "  ✗ Section U seq=1 marker not found"; echo "$_OUT_LOCK" | tail -25; exit 1; }

echo "$_OUT_LOCK" | grep -q "U: verify_audit_file ok=true" \
    && pass "lifecycle demo Section U: verify_audit_file ok=true confirmed" \
    || { echo "  ✗ Section U verify_audit_file marker not found"; echo "$_OUT_LOCK" | tail -25; exit 1; }

# No forbidden fields in Section U output
for key in "credential_ref" "secret_id" "login_customer_id"; do
    if echo "$_OUT_LOCK" | grep -A60 "── U:" | grep -qE "\"${key}\""; then
        fail "Forbidden field '${key}' appeared in Section U output"
    fi
done
pass "Section U: no forbidden fields in audit locking output"

pass "Audit file locking checks complete"

# ---------------------------------------------------------------------------
echo ""
echo "[21/24] Live Google Ads readiness gate (live_gate.py)..."
# ---------------------------------------------------------------------------

# live_gate.py importable with all public symbols
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from live_gate import LiveGateInput, LiveGateResult, LiveGateDenialCode, check_live_gate
" 2>&1); then
    pass "live_gate.py: LiveGateInput, LiveGateResult, LiveGateDenialCode, check_live_gate importable"
else
    fail "live_gate.py: import failed"
fi

# LiveGateDenialCode has all 11 constants
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from live_gate import LiveGateDenialCode
codes = [
    LiveGateDenialCode.LIVE_DISABLED,
    LiveGateDenialCode.APPROVAL_MISSING,
    LiveGateDenialCode.APPROVAL_INVALID,
    LiveGateDenialCode.PREFLIGHT_MISSING,
    LiveGateDenialCode.AUDIT_DISABLED,
    LiveGateDenialCode.CREDENTIAL_MISSING,
    LiveGateDenialCode.CREDENTIAL_NOT_ACTIVE,
    LiveGateDenialCode.TENANT_NOT_ALLOWED,
    LiveGateDenialCode.CLIENT_NOT_ALLOWED,
    LiveGateDenialCode.ROLLBACK_PLAN_MISSING,
    LiveGateDenialCode.OPERATOR_CONFIRMATION_MISSING,
]
assert len(codes) == 11
assert all(isinstance(c, str) for c in codes)
" 2>/dev/null); then
    pass "LiveGateDenialCode: all 11 denial codes present and are strings"
else
    fail "LiveGateDenialCode: missing or wrong type for one or more codes"
fi

# check_live_gate: live_disabled is the first gate — fires even if no other condition is met
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from live_gate import LiveGateInput, LiveGateDenialCode, check_live_gate
inp = LiveGateInput(
    live_enabled=False,
    approval_present=False, approval_valid=False, preflight_passed=False,
    audit_enabled=False, credential_configured=False, credential_status='REVOKED',
    tenant_allowed=False, client_allowed=False, rollback_plan_present=False,
    operator_confirmed=False,
)
r = check_live_gate(inp)
assert r.allowed is False, f'allowed should be False: {r}'
assert r.error_code == LiveGateDenialCode.LIVE_DISABLED, f'expected live_disabled: {r.error_code}'
" 2>/dev/null); then
    pass "check_live_gate: live_disabled fires first even when all other conditions fail"
else
    fail "check_live_gate: live_disabled priority check failed"
fi

# check_live_gate: allow path returns allowed=True with error_code=None
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from live_gate import LiveGateInput, check_live_gate
inp = LiveGateInput(
    live_enabled=True,
    approval_present=True, approval_valid=True, preflight_passed=True,
    audit_enabled=True, credential_configured=True, credential_status='ACTIVE',
    tenant_allowed=True, client_allowed=True, rollback_plan_present=True,
    operator_confirmed=True,
)
r = check_live_gate(inp)
assert r.allowed is True, f'expected allowed=True: {r}'
assert r.error_code is None, f'expected error_code=None: {r.error_code}'
assert r.required_actions == [], f'expected no required_actions: {r.required_actions}'
" 2>/dev/null); then
    pass "check_live_gate: allow path → allowed=True, error_code=None, required_actions=[]"
else
    fail "check_live_gate: allow path did not return expected result"
fi

# GOOGLE_ADS_LIVE_ENABLED must not be true in live_gate.py
if grep -q "GOOGLE_ADS_LIVE_ENABLED=true" "$OPENCLAW_DIR/live_gate.py" 2>/dev/null; then
    fail "live_gate.py contains GOOGLE_ADS_LIVE_ENABLED=true — must never be set true in module"
else
    pass "live_gate.py: GOOGLE_ADS_LIVE_ENABLED=true absent"
fi

# live_gate.py must not contain any os.environ reads (pure signal-based, no env coupling)
if grep -q "os.environ" "$OPENCLAW_DIR/live_gate.py" 2>/dev/null; then
    fail "live_gate.py reads os.environ — gate must evaluate pre-supplied signals only"
else
    pass "live_gate.py: no os.environ reads (pure signal evaluation)"
fi

# run_live_gate_demo.py: all 14 assertions pass
_OUT_GATE=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    $PYTHON run_live_gate_demo.py 2>&1)
echo "$_OUT_GATE" | grep -q "All assertions passed." \
    && pass "run_live_gate_demo.py: All assertions passed" \
    || { echo "  ✗ run_live_gate_demo.py: All assertions passed not found"; echo "$_OUT_GATE" | tail -30; exit 1; }

pass "Live Google Ads readiness gate checks complete"

# ---------------------------------------------------------------------------
echo ""
echo "[22/24] Approval record model and local approval store..."
# ---------------------------------------------------------------------------

# approval.py importable with all public symbols
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import (
    ApprovalStatus, ApprovalScope, ApprovalRecord, ApprovalValidationResult,
    LocalFileApprovalStore, create_approval_record, validate_approval_record,
    is_approval_valid, sanitize_approval_record,
)
" 2>&1); then
    pass "approval.py: all public symbols importable"
else
    fail "approval.py: import failed"
fi

# ApprovalStatus and ApprovalScope constants
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope
assert ApprovalStatus.PENDING == 'pending'
assert ApprovalStatus.APPROVED == 'approved'
assert ApprovalStatus.REVOKED == 'revoked'
assert ApprovalStatus.EXPIRED == 'expired'
assert ApprovalStatus.REJECTED == 'rejected'
assert ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION == 'google_ads_live_validation'
assert ApprovalScope.GOOGLE_ADS_CREDENTIAL_ONBOARDING == 'google_ads_credential_onboarding'
assert ApprovalScope.GOOGLE_ADS_CREDENTIAL_ROTATION == 'google_ads_credential_rotation'
assert ApprovalScope.GOOGLE_ADS_CREDENTIAL_REVOKE == 'google_ads_credential_revoke'
" 2>/dev/null); then
    pass "ApprovalStatus and ApprovalScope: all constants correct"
else
    fail "ApprovalStatus or ApprovalScope: missing or wrong value"
fi

# create_approval_record produces a valid approved record
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record, validate_approval_record
rec = create_approval_record(
    tenant_id='smoke-tenant', client_id='smoke-client',
    integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='smoke-operator',
    reason='Smoke test approval',
    rollback_plan='Disable live mode and revoke',
    status=ApprovalStatus.APPROVED,
)
assert rec.approval_id, 'approval_id empty'
assert rec.approved_at, 'approved_at not set for APPROVED'
result = validate_approval_record(rec)
assert result.valid is True, f'valid should be True: {result.error_codes}'
assert result.error_codes == [], f'error_codes should be empty: {result.error_codes}'
" 2>/dev/null); then
    pass "create_approval_record + validate_approval_record: valid approved record passes"
else
    fail "create_approval_record + validate_approval_record: approved record check failed"
fi

# is_approval_valid: correct context → True
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record, is_approval_valid
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='plan',
    status=ApprovalStatus.APPROVED,
)
assert is_approval_valid(rec, ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION, 't1', 'c1', 'google_ads') is True
" 2>/dev/null); then
    pass "is_approval_valid: correct context → True"
else
    fail "is_approval_valid: correct context check failed"
fi

# is_approval_valid: wrong tenant/client/scope → False
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record, is_approval_valid
def make():
    return create_approval_record(
        tenant_id='t1', client_id='c1', integration_type='google_ads',
        scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
        operator_label='op', reason='reason', rollback_plan='plan',
        status=ApprovalStatus.APPROVED,
    )
assert is_approval_valid(make(), ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION, 'wrong-tenant', 'c1', 'google_ads') is False
assert is_approval_valid(make(), ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION, 't1', 'wrong-client', 'google_ads') is False
assert is_approval_valid(make(), ApprovalScope.GOOGLE_ADS_CREDENTIAL_ROTATION, 't1', 'c1', 'google_ads') is False
" 2>/dev/null); then
    pass "is_approval_valid: wrong tenant/client/scope each → False"
else
    fail "is_approval_valid: wrong context mismatch check failed"
fi

# validate_approval_record: expired → approval_expired
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record, validate_approval_record
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='plan',
    status=ApprovalStatus.APPROVED,
    expires_at='2020-01-01T00:00:00Z',
)
result = validate_approval_record(rec)
assert result.valid is False, 'expired record should not be valid'
assert 'approval_expired' in result.error_codes, f'expected approval_expired: {result.error_codes}'
" 2>/dev/null); then
    pass "validate_approval_record: expired approval → approval_expired"
else
    fail "validate_approval_record: expired approval check failed"
fi

# validate_approval_record: revoked → approval_not_approved
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record, validate_approval_record
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='plan',
    status=ApprovalStatus.REVOKED,
)
result = validate_approval_record(rec)
assert result.valid is False
assert any('approval_not_approved' in c for c in result.error_codes), f'expected approval_not_approved: {result.error_codes}'
" 2>/dev/null); then
    pass "validate_approval_record: revoked → approval_not_approved"
else
    fail "validate_approval_record: revoked check failed"
fi

# validate_approval_record: missing rollback_plan → rollback_plan_missing
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record, validate_approval_record
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='   ',
    status=ApprovalStatus.APPROVED,
)
result = validate_approval_record(rec)
assert result.valid is False
assert 'rollback_plan_missing' in result.error_codes, f'expected rollback_plan_missing: {result.error_codes}'
" 2>/dev/null); then
    pass "validate_approval_record: missing rollback_plan → rollback_plan_missing"
else
    fail "validate_approval_record: rollback_plan_missing check failed"
fi

# validate_approval_record: forbidden field name in evidence
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record, validate_approval_record
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='plan',
    status=ApprovalStatus.APPROVED,
    evidence={'credential_ref': 'some-ref'},
)
result = validate_approval_record(rec)
assert result.valid is False
assert 'evidence_metadata_forbidden_field' in result.error_codes, f'expected forbidden_field: {result.error_codes}'
" 2>/dev/null); then
    pass "validate_approval_record: forbidden field name in evidence → evidence_metadata_forbidden_field"
else
    fail "validate_approval_record: forbidden field name check failed"
fi

# validate_approval_record: forbidden value pattern in evidence
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record, validate_approval_record
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='plan',
    status=ApprovalStatus.APPROVED,
    evidence={'notes': 'ya' + '29.some-token-value-here'},
)
result = validate_approval_record(rec)
assert result.valid is False
assert 'evidence_metadata_forbidden_value_pattern' in result.error_codes, f'expected forbidden_value: {result.error_codes}'
" 2>/dev/null); then
    pass "validate_approval_record: forbidden oauth-token-prefix in evidence → evidence_metadata_forbidden_value_pattern"
else
    fail "validate_approval_record: forbidden value pattern check failed"
fi

# validate_approval_record: forbidden value pattern — GCP resource path
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record, validate_approval_record
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='plan',
    status=ApprovalStatus.APPROVED,
    evidence={'ref': 'projects/my-project/secrets/my-secret/versions/1'},
)
result = validate_approval_record(rec)
assert result.valid is False
assert 'evidence_metadata_forbidden_value_pattern' in result.error_codes, f'expected forbidden_value: {result.error_codes}'
" 2>/dev/null); then
    pass "validate_approval_record: GCP resource path in evidence → evidence_metadata_forbidden_value_pattern"
else
    fail "validate_approval_record: GCP resource path forbidden value check failed"
fi

# sanitize_approval_record: forbidden key removed, safe key preserved
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record, sanitize_approval_record
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='plan',
    status=ApprovalStatus.APPROVED,
    evidence={'credential_ref': 'x', 'safe_key': 'safe_value'},
)
s = sanitize_approval_record(rec)
assert 'credential_ref' not in s['evidence'], 'credential_ref should be removed'
assert 'safe_key' in s['evidence'], 'safe_key should be preserved'
assert 'approval_id' in s, 'approval_id should be present'
assert 'tenant_id' in s, 'tenant_id should be present'
" 2>/dev/null); then
    pass "sanitize_approval_record: forbidden field removed, safe field preserved"
else
    fail "sanitize_approval_record: sanitization check failed"
fi

# LocalFileApprovalStore: put / get / list / revoke round-trip
APPROVAL_STORE_TMP=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
import sys
from pathlib import Path
from approval import (
    ApprovalStatus, ApprovalScope, LocalFileApprovalStore,
    create_approval_record, validate_approval_record,
)
store = LocalFileApprovalStore(Path('${APPROVAL_STORE_TMP}'))
rec = create_approval_record(
    tenant_id='store-tenant', client_id='store-client',
    integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='store-op', reason='store test', rollback_plan='revert',
    status=ApprovalStatus.APPROVED,
)
store.put(rec)
fetched = store.get(rec.approval_id)
assert fetched is not None, 'get returned None'
assert fetched.approval_id == rec.approval_id, 'id mismatch'
assert fetched.status == ApprovalStatus.APPROVED
listed = store.list_for_client('store-tenant', 'store-client')
assert len(listed) == 1, f'expected 1, got {len(listed)}'
assert listed[0].approval_id == rec.approval_id
ok = store.revoke(rec.approval_id, reason='smoke test revoke')
assert ok is True, 'revoke should return True'
after = store.get(rec.approval_id)
assert after.status == ApprovalStatus.REVOKED, f'expected REVOKED: {after.status}'
assert after.revoked_at, 'revoked_at should be set'
missing = store.revoke('no-such-id', reason='noop')
assert missing is False, 'revoke nonexistent should return False'
" 2>/dev/null); then
    pass "LocalFileApprovalStore: put/get/list/revoke all correct"
else
    fail "LocalFileApprovalStore: round-trip check failed"
fi
rm -f "$APPROVAL_STORE_TMP"

# run_approval_demo.py: all assertions pass
_OUT_APPROVAL=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    $PYTHON run_approval_demo.py 2>&1)
echo "$_OUT_APPROVAL" | grep -q "All assertions passed." \
    && pass "run_approval_demo.py: All assertions passed" \
    || { echo "  ✗ run_approval_demo.py: All assertions passed not found"; echo "$_OUT_APPROVAL" | tail -30; exit 1; }

# approval.py must not contain GCP imports or os.environ reads
if grep -qE "^(import google|from google|import gcloud)" "$OPENCLAW_DIR/approval.py" 2>/dev/null; then
    fail "approval.py contains GCP imports"
else
    pass "approval.py: no GCP imports"
fi

# No GOOGLE_ADS_LIVE_ENABLED=true in approval.py or run_approval_demo.py
if grep -q "GOOGLE_ADS_LIVE_ENABLED=true" "$OPENCLAW_DIR/approval.py" "$OPENCLAW_DIR/run_approval_demo.py" 2>/dev/null; then
    fail "approval files contain GOOGLE_ADS_LIVE_ENABLED=true"
else
    pass "approval.py and run_approval_demo.py: GOOGLE_ADS_LIVE_ENABLED=true absent"
fi

pass "Approval record model and local approval store checks complete"

# ---------------------------------------------------------------------------
echo "[23/24] Live operation preflight checker (preflight.py)..."
# ---------------------------------------------------------------------------

# preflight.py importable with all public symbols
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from preflight import (
    LiveOperationPreflightInput,
    LiveOperationPreflightResult,
    check_live_operation_preflight,
)
" 2>&1); then
    pass "preflight.py: LiveOperationPreflightInput, LiveOperationPreflightResult, check_live_operation_preflight importable"
else
    fail "preflight.py: import failed"
fi

# LiveOperationPreflightInput and LiveOperationPreflightResult are dataclasses
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
import dataclasses
from preflight import LiveOperationPreflightInput, LiveOperationPreflightResult
assert dataclasses.is_dataclass(LiveOperationPreflightInput)
assert dataclasses.is_dataclass(LiveOperationPreflightResult)
" 2>/dev/null); then
    pass "preflight.py: LiveOperationPreflightInput and LiveOperationPreflightResult are dataclasses"
else
    fail "preflight.py: dataclass check failed"
fi

# check_live_operation_preflight: live_disabled
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record
from live_gate import LiveGateDenialCode
from preflight import LiveOperationPreflightInput, check_live_operation_preflight
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='plan',
    status=ApprovalStatus.APPROVED,
)
inp = LiveOperationPreflightInput(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    operation='fetch', live_enabled=False,
    approval_record=rec,
    required_approval_scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    preflight_passed=True, audit_enabled=True, credential_configured=True,
    credential_status='ACTIVE', tenant_allowed=True, client_allowed=True,
    rollback_plan_present=True, operator_confirmed=True,
)
r = check_live_operation_preflight(inp)
assert r.allowed is False, 'live_disabled should deny'
assert r.error_code == LiveGateDenialCode.LIVE_DISABLED, f'expected live_disabled, got {r.error_code}'
" 2>/dev/null); then
    pass "check_live_operation_preflight: live_disabled → allowed=False"
else
    fail "check_live_operation_preflight: live_disabled check failed"
fi

# check_live_operation_preflight: approval_missing
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalScope
from live_gate import LiveGateDenialCode
from preflight import LiveOperationPreflightInput, check_live_operation_preflight
inp = LiveOperationPreflightInput(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    operation='fetch', live_enabled=True,
    approval_record=None,
    required_approval_scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    preflight_passed=True, audit_enabled=True, credential_configured=True,
    credential_status='ACTIVE', tenant_allowed=True, client_allowed=True,
    rollback_plan_present=True, operator_confirmed=True,
)
r = check_live_operation_preflight(inp)
assert r.allowed is False, 'approval_missing should deny'
assert r.error_code == LiveGateDenialCode.APPROVAL_MISSING, f'expected approval_missing, got {r.error_code}'
assert r.approval_valid is False, 'approval_valid should be False when record is None'
assert r.sanitized_summary['approval_present'] is False, 'summary.approval_present should be False'
" 2>/dev/null); then
    pass "check_live_operation_preflight: approval_missing → allowed=False, approval_valid=False"
else
    fail "check_live_operation_preflight: approval_missing check failed"
fi

# check_live_operation_preflight: expired approval → approval_invalid
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record
from live_gate import LiveGateDenialCode
from preflight import LiveOperationPreflightInput, check_live_operation_preflight
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='plan',
    status=ApprovalStatus.APPROVED,
    expires_at='2020-01-01T00:00:00Z',
)
inp = LiveOperationPreflightInput(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    operation='fetch', live_enabled=True,
    approval_record=rec,
    required_approval_scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    preflight_passed=True, audit_enabled=True, credential_configured=True,
    credential_status='ACTIVE', tenant_allowed=True, client_allowed=True,
    rollback_plan_present=True, operator_confirmed=True,
)
r = check_live_operation_preflight(inp)
assert r.allowed is False, 'expired approval should deny'
assert r.error_code == LiveGateDenialCode.APPROVAL_INVALID, f'expected approval_invalid, got {r.error_code}'
assert r.approval_valid is False, 'approval_valid should be False for expired record'
" 2>/dev/null); then
    pass "check_live_operation_preflight: expired approval → approval_invalid"
else
    fail "check_live_operation_preflight: expired approval check failed"
fi

# check_live_operation_preflight: allow path
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record
from preflight import LiveOperationPreflightInput, check_live_operation_preflight
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='plan',
    status=ApprovalStatus.APPROVED,
)
inp = LiveOperationPreflightInput(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    operation='fetch', live_enabled=True,
    approval_record=rec,
    required_approval_scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    preflight_passed=True, audit_enabled=True, credential_configured=True,
    credential_status='ACTIVE', tenant_allowed=True, client_allowed=True,
    rollback_plan_present=True, operator_confirmed=True,
)
r = check_live_operation_preflight(inp)
assert r.allowed is True, f'all-pass should allow, got error_code={r.error_code}'
assert r.error_code is None, f'error_code should be None, got {r.error_code}'
assert r.approval_valid is True, 'approval_valid should be True'
assert r.live_gate_allowed is True, 'live_gate_allowed should be True'
assert r.required_actions == [], f'required_actions should be empty: {r.required_actions}'
" 2>/dev/null); then
    pass "check_live_operation_preflight: allow path → allowed=True, approval_valid=True"
else
    fail "check_live_operation_preflight: allow path check failed"
fi

# sanitized_summary must not contain tenant_id / client_id / approval_id / credential fields
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record
from preflight import LiveOperationPreflightInput, check_live_operation_preflight
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='plan',
    status=ApprovalStatus.APPROVED,
)
inp = LiveOperationPreflightInput(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    operation='fetch', live_enabled=True,
    approval_record=rec,
    required_approval_scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    preflight_passed=True, audit_enabled=True, credential_configured=True,
    credential_status='ACTIVE', tenant_allowed=True, client_allowed=True,
    rollback_plan_present=True, operator_confirmed=True,
)
r = check_live_operation_preflight(inp)
s = r.sanitized_summary
forbidden_keys = {'tenant_id', 'client_id', 'approval_id', 'refresh_token',
                  'developer_token', 'client_secret', 'access_token'}
found = [k for k in forbidden_keys if k in s]
assert not found, f'forbidden keys in sanitized_summary: {found}'
assert isinstance(s.get('approval_present'), bool), 'approval_present must be bool'
assert isinstance(s.get('approval_valid'), bool), 'approval_valid must be bool'
assert 'operation' in s, 'operation must be in summary'
assert 'integration_type' in s, 'integration_type must be in summary'
" 2>/dev/null); then
    pass "sanitized_summary: no forbidden identifiers; approval_present/approval_valid are bools"
else
    fail "sanitized_summary: forbidden key or type check failed"
fi

# run_preflight_demo.py: all assertions pass
_OUT_PREFLIGHT=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    $PYTHON run_preflight_demo.py 2>&1)
echo "$_OUT_PREFLIGHT" | grep -q "All assertions passed." \
    && pass "run_preflight_demo.py: All assertions passed" \
    || { echo "  ✗ run_preflight_demo.py: All assertions passed not found"; echo "$_OUT_PREFLIGHT" | tail -30; exit 1; }

# preflight.py must not import GCP or Google Ads libraries
if grep -qE "^(import google|from google|import gcloud)" "$OPENCLAW_DIR/preflight.py" 2>/dev/null; then
    fail "preflight.py: contains GCP/Google imports"
else
    pass "preflight.py: no GCP or Google Ads imports"
fi

# preflight.py must not read os.environ directly
if grep -q "os\.environ" "$OPENCLAW_DIR/preflight.py" 2>/dev/null; then
    fail "preflight.py: contains os.environ reads"
else
    pass "preflight.py: no os.environ reads"
fi

# No GOOGLE_ADS_LIVE_ENABLED=true in preflight.py or run_preflight_demo.py
if grep -q "GOOGLE_ADS_LIVE_ENABLED=true" "$OPENCLAW_DIR/preflight.py" "$OPENCLAW_DIR/run_preflight_demo.py" 2>/dev/null; then
    fail "preflight files contain GOOGLE_ADS_LIVE_ENABLED=true"
else
    pass "preflight.py and run_preflight_demo.py: GOOGLE_ADS_LIVE_ENABLED=true absent"
fi

pass "Live operation preflight checker checks complete"

# ---------------------------------------------------------------------------
echo "[24/24] Server live guard (live_guard.py + server route)..."
# ---------------------------------------------------------------------------

# live_guard.py importable with all public symbols
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from live_guard import (
    LIVE_GUARD_INTEGRATION_TYPE,
    LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS,
    build_live_guard_denied_response,
    build_live_guard_allowed_response,
    guard_live_google_ads_operation,
    guard_live_google_ads_from_signals,
    response_has_no_forbidden_keys,
)
" 2>&1); then
    pass "live_guard.py: all public symbols importable"
else
    fail "live_guard.py: import failed"
fi

# LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS contains expected keys
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from live_guard import LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS
required = {'approval_id', 'tenant_id', 'client_id', 'credential_ref',
            'secret_id', 'refresh_token', 'access_token', 'developer_token'}
missing = required - LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS
assert not missing, f'missing forbidden keys: {missing}'
" 2>/dev/null); then
    pass "live_guard.py: LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS contains required keys"
else
    fail "live_guard.py: LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS missing required keys"
fi

# guard_live_google_ads_from_signals: live_disabled
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from live_guard import guard_live_google_ads_from_signals, response_has_no_forbidden_keys
from live_gate import LiveGateDenialCode
result = guard_live_google_ads_from_signals(
    live_enabled=False,
    approval_present=True, approval_valid=True, preflight_passed=True,
    audit_enabled=True, credential_configured=True, credential_status='ACTIVE',
    tenant_allowed=True, client_allowed=True,
    rollback_plan_present=True, operator_confirmed=True,
)
assert result['ok'] is False, 'live_disabled should deny'
assert result['error_code'] == LiveGateDenialCode.LIVE_DISABLED, f'expected live_disabled, got {result[\"error_code\"]}'
assert result['live_api_tested'] is False, 'live_api_tested must be False'
assert response_has_no_forbidden_keys(result), 'forbidden key in response'
" 2>/dev/null); then
    pass "guard_live_google_ads_from_signals: live_disabled → ok=false, live_api_tested=false"
else
    fail "guard_live_google_ads_from_signals: live_disabled check failed"
fi

# guard_live_google_ads_from_signals: approval_missing
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from live_guard import guard_live_google_ads_from_signals
from live_gate import LiveGateDenialCode
result = guard_live_google_ads_from_signals(
    live_enabled=True,
    approval_present=False, approval_valid=False, preflight_passed=True,
    audit_enabled=True, credential_configured=True, credential_status='ACTIVE',
    tenant_allowed=True, client_allowed=True,
    rollback_plan_present=True, operator_confirmed=True,
)
assert result['error_code'] == LiveGateDenialCode.APPROVAL_MISSING, f'expected approval_missing, got {result[\"error_code\"]}'
assert result['live_api_tested'] is False, 'live_api_tested must be False'
" 2>/dev/null); then
    pass "guard_live_google_ads_from_signals: approval_missing → error_code correct"
else
    fail "guard_live_google_ads_from_signals: approval_missing check failed"
fi

# guard_live_google_ads_operation: allow path with full ApprovalRecord
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    $PYTHON -c "
from approval import ApprovalStatus, ApprovalScope, create_approval_record
from preflight import LiveOperationPreflightInput
from live_guard import guard_live_google_ads_operation, response_has_no_forbidden_keys
rec = create_approval_record(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    operator_label='op', reason='reason', rollback_plan='plan',
    status=ApprovalStatus.APPROVED,
)
inp = LiveOperationPreflightInput(
    tenant_id='t1', client_id='c1', integration_type='google_ads',
    operation='fetch', live_enabled=True,
    approval_record=rec,
    required_approval_scope=ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION,
    preflight_passed=True, audit_enabled=True, credential_configured=True,
    credential_status='ACTIVE', tenant_allowed=True, client_allowed=True,
    rollback_plan_present=True, operator_confirmed=True,
)
result = guard_live_google_ads_operation(inp)
assert result['ok'] is True, f'allow path should pass, got error_code={result.get(\"error_code\")}'
assert result['live_allowed'] is True, 'live_allowed must be True'
assert result['live_api_tested'] is False, 'live_api_tested must be False'
assert result['approval_valid'] is True, 'approval_valid must be True'
assert response_has_no_forbidden_keys(result), 'forbidden key in allow response'
" 2>/dev/null); then
    pass "guard_live_google_ads_operation: allow path → ok=true, live_api_tested=false"
else
    fail "guard_live_google_ads_operation: allow path check failed"
fi

# server route: POST /openclaw/admin/live-google-ads/preflight → live_disabled
if (cd "$OPENCLAW_DIR" && PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    OPENCLAW_API_AUTH_ENABLED=false \
    OPENCLAW_AUDIT_ENABLED=false \
    $PYTHON -c "
import os, sys
for mod in list(sys.modules.keys()):
    if mod in ('server', 'admin', 'config', 'auth', 'live_guard', 'live_gate', 'preflight', 'approval'):
        del sys.modules[mod]
from fastapi.testclient import TestClient
from server import app
client = TestClient(app, raise_server_exceptions=True)
r = client.post('/openclaw/admin/live-google-ads/preflight', json={
    'approval_present': True, 'approval_valid': True, 'preflight_passed': True,
    'audit_enabled': True, 'credential_configured': True, 'credential_status': 'ACTIVE',
    'tenant_allowed': True, 'client_allowed': True,
    'rollback_plan_present': True, 'operator_confirmed': True,
})
d = r.json()
assert r.status_code == 403, f'expected 403, got {r.status_code}'
assert d.get('ok') is False, 'ok must be False'
assert d.get('error_code') == 'live_disabled', f'expected live_disabled, got {d.get(\"error_code\")}'
assert d.get('live_allowed') is False, 'live_allowed must be False'
assert d.get('live_api_tested') is False, 'live_api_tested must be False'
forbidden = {'tenant_id','client_id','approval_id','credential_ref','secret_id','refresh_token','access_token'}
found = [k for k in forbidden if k in d]
assert not found, f'forbidden keys in response: {found}'
assert 'request_id' in d, 'request_id must be present'
assert 'trace_id' in d, 'trace_id must be present'
" 2>/dev/null); then
    pass "server route POST /openclaw/admin/live-google-ads/preflight: live_disabled, safe response"
else
    fail "server route: live guard preflight route check failed"
fi

# run_server_live_guard_demo.py: all assertions pass
_OUT_GUARD=$(cd "$OPENCLAW_DIR" && \
    PYTHONPATH="$OPENCLAW_DIR:$AGENT_DIR" \
    GCP_SECRET_MANAGER_ENABLED=false \
    GOOGLE_ADS_LIVE_ENABLED=false \
    OPENCLAW_API_AUTH_ENABLED=false \
    OPENCLAW_AUDIT_ENABLED=false \
    $PYTHON run_server_live_guard_demo.py 2>&1)
echo "$_OUT_GUARD" | grep -q "All assertions passed." \
    && pass "run_server_live_guard_demo.py: All assertions passed" \
    || { echo "  ✗ run_server_live_guard_demo.py: All assertions passed not found"; echo "$_OUT_GUARD" | tail -30; exit 1; }

# live_guard.py must not import GCP or Google Ads libraries
if grep -qE "^(import google|from google|import gcloud)" "$OPENCLAW_DIR/live_guard.py" 2>/dev/null; then
    fail "live_guard.py: contains GCP/Google imports"
else
    pass "live_guard.py: no GCP or Google Ads imports"
fi

# live_guard.py must not read os.environ
if grep -q "os\.environ" "$OPENCLAW_DIR/live_guard.py" 2>/dev/null; then
    fail "live_guard.py: contains os.environ reads"
else
    pass "live_guard.py: no os.environ reads (pure — env read is in route handler only)"
fi

# No GOOGLE_ADS_LIVE_ENABLED=true in live_guard.py or run_server_live_guard_demo.py
if grep -q "GOOGLE_ADS_LIVE_ENABLED=true" "$OPENCLAW_DIR/live_guard.py" "$OPENCLAW_DIR/run_server_live_guard_demo.py" 2>/dev/null; then
    fail "live_guard files contain GOOGLE_ADS_LIVE_ENABLED=true"
else
    pass "live_guard.py and run_server_live_guard_demo.py: GOOGLE_ADS_LIVE_ENABLED=true absent"
fi

pass "Server live guard checks complete"

# ---------------------------------------------------------------------------
echo ""
echo "=== V5 credential chain smoke test passed. ==="

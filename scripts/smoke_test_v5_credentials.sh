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
echo "[1/18] Environment and import checks..."
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
echo "[2/18] CredentialReference model demo..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON run_credentials_model_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_credentials_model_demo.py: All assertions passed" \
    || { echo "  ✗ run_credentials_model_demo.py: assertion not found in output"; echo "$_OUT" | tail -5; exit 1; }

# ---------------------------------------------------------------------------
echo ""
echo "[3/18] Credential stores..."
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
echo "[4/18] Credential resolver..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON run_credentials_resolver_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_credentials_resolver_demo.py: All assertions passed" \
    || { echo "  ✗ run_credentials_resolver_demo.py: assertion not found"; echo "$_OUT" | tail -5; exit 1; }

# ---------------------------------------------------------------------------
echo ""
echo "[5/18] SecretStore and provider..."
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
echo "[6/18] Adapter provider mode — non-live checks..."
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
echo "[7/18] OpenClaw admin credential endpoints..."
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
echo "[8/18] Secret-safety and git hygiene..."
# ---------------------------------------------------------------------------

GREP_TARGETS="$REPO/scripts $REPO/docs $REPO/agents $REPO/openclaw $REPO/README.md $REPO/.env.example"

# ya29. — OAuth access token prefix
if grep -R "ya29\." -n $GREP_TARGETS 2>/dev/null | grep -v "_PYEOF\|# ya29\|ya29.*marker\|ya29.*forbidden\|starting with.*ya29\|ya29.*prohibition\|must never be used"; then
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
echo "[9/18] Admin credential bundle write — mocked secret store..."
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
echo "[10/18] Admin credential API write — FastAPI TestClient..."
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
echo "[11/18] Credential lifecycle audit and validation events..."
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
echo "[12/18] Credential lifecycle validation API (FastAPI TestClient)..."
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
echo "[13/18] Validate route — server-level auth checks..."
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
echo "[14/18] Phase 3 delete/revoke — forbidden behavior and env gate checks..."
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
echo "[15/18] Admin RBAC scope enforcement..."
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
echo "[16/18] Audit seq/digest hardening and maintenance..."
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

# Lifecycle demo includes L/M/N/O sections (lifecycle demo already ran in [11/18])
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
echo "[17/18] Rotate credential endpoint..."
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
echo "[18/18] Per-tenant token isolation (OPENCLAW_TENANT_KEYS)..."
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
echo "=== V5 credential chain smoke test passed. ==="

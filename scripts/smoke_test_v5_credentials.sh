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
echo "[1/13] Environment and import checks..."
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
echo "[2/13] CredentialReference model demo..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON run_credentials_model_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_credentials_model_demo.py: All assertions passed" \
    || { echo "  ✗ run_credentials_model_demo.py: assertion not found in output"; echo "$_OUT" | tail -5; exit 1; }

# ---------------------------------------------------------------------------
echo ""
echo "[3/13] Credential stores..."
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
echo "[4/13] Credential resolver..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$AGENT_DIR" && PYTHONPATH="$AGENT_DIR" $PYTHON run_credentials_resolver_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_credentials_resolver_demo.py: All assertions passed" \
    || { echo "  ✗ run_credentials_resolver_demo.py: assertion not found"; echo "$_OUT" | tail -5; exit 1; }

# ---------------------------------------------------------------------------
echo ""
echo "[5/13] SecretStore and provider..."
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
echo "[6/13] Adapter provider mode — non-live checks..."
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
echo "[7/13] OpenClaw admin credential endpoints..."
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
OPENCLAW_API_KEYS="smoke-test-key" \
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
echo "[8/13] Secret-safety and git hygiene..."
# ---------------------------------------------------------------------------

GREP_TARGETS="$REPO/scripts $REPO/docs $REPO/agents $REPO/openclaw $REPO/README.md $REPO/.env.example"

# ya29. — OAuth access token prefix
if grep -R "ya29\." -n $GREP_TARGETS 2>/dev/null | grep -v "_PYEOF\|# ya29\|ya29.*marker\|ya29.*forbidden"; then
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
echo "[9/13] Admin credential bundle write — mocked secret store..."
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
echo "[10/13] Admin credential API write — FastAPI TestClient..."
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
echo "[11/13] Credential lifecycle audit and validation events..."
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

# ---------------------------------------------------------------------------
echo ""
echo "[12/13] Credential lifecycle validation API (FastAPI TestClient)..."
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

# ---------------------------------------------------------------------------
echo ""
echo "[13/13] Validate route — server-level auth checks..."
# ---------------------------------------------------------------------------

CRED_STORE_FILE2=$(mktemp /tmp/kaiju_smoke_v5_XXXXXX.json)

if curl -s --max-time 2 "${BASE_URL}/openclaw/health" >/dev/null 2>&1; then
    fail "Port ${PORT} still in use before validate auth test server"
fi

cd "$OPENCLAW_DIR"
CREDENTIAL_REFERENCE_STORE_PATH="$CRED_STORE_FILE2" \
OPENCLAW_API_AUTH_ENABLED=true \
OPENCLAW_API_KEYS="smoke-validate-key" \
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
echo "=== V5 credential chain smoke test passed. ==="

#!/usr/bin/env bash
set -euo pipefail

PYTHON=~/kaiju/.venv/bin/python3
REPO=~/kaiju
AGENT_DIR="$REPO/agents/ads-agent"

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
cleanup() {
    rm -f /tmp/kaiju_smoke_v512_*.py /tmp/kaiju_smoke_v512_*.log 2>/dev/null || true
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; exit 1; }

# Run a Python snippet from AGENT_DIR with AGENT_DIR on PYTHONPATH.
# Clears GCP env vars so no test accidentally inherits a live config.
py_pass() {
    local label="$1"
    local tmpfile
    tmpfile=$(mktemp /tmp/kaiju_smoke_v512_XXXXXX.py)
    cat > "$tmpfile"
    if (cd "$AGENT_DIR" && \
        GCP_SECRET_MANAGER_ENABLED=false \
        GCP_PROJECT_ID= \
        GOOGLE_CLOUD_PROJECT= \
        GOOGLE_APPLICATION_CREDENTIALS= \
        PYTHONPATH="$AGENT_DIR" \
        $PYTHON "$tmpfile") >/dev/null 2>&1; then
        pass "$label"
    else
        echo "  ✗ $label"
        (cd "$AGENT_DIR" && \
            GCP_SECRET_MANAGER_ENABLED=false \
            GCP_PROJECT_ID= \
            GOOGLE_CLOUD_PROJECT= \
            GOOGLE_APPLICATION_CREDENTIALS= \
            PYTHONPATH="$AGENT_DIR" \
            $PYTHON "$tmpfile") 2>&1 | head -30 || true
        rm -f "$tmpfile"
        exit 1
    fi
    rm -f "$tmpfile"
}

# Run a Python snippet with explicit env overrides.
py_pass_env() {
    local label="$1"
    shift
    local env_args=("$@")
    local tmpfile
    tmpfile=$(mktemp /tmp/kaiju_smoke_v512_XXXXXX.py)
    cat > "$tmpfile"
    if (cd "$AGENT_DIR" && \
        GOOGLE_APPLICATION_CREDENTIALS= \
        PYTHONPATH="$AGENT_DIR" \
        env "${env_args[@]}" $PYTHON "$tmpfile") >/dev/null 2>&1; then
        pass "$label"
    else
        echo "  ✗ $label"
        (cd "$AGENT_DIR" && \
            GOOGLE_APPLICATION_CREDENTIALS= \
            PYTHONPATH="$AGENT_DIR" \
            env "${env_args[@]}" $PYTHON "$tmpfile") 2>&1 | head -30 || true
        rm -f "$tmpfile"
        exit 1
    fi
    rm -f "$tmpfile"
}

# Run a demo script and check its final pass banner.
demo_pass() {
    local label="$1"
    local script="$2"
    local banner="$3"
    _OUT=$(cd "$AGENT_DIR" && \
        GCP_SECRET_MANAGER_ENABLED=false \
        GCP_PROJECT_ID= \
        GOOGLE_CLOUD_PROJECT= \
        GOOGLE_APPLICATION_CREDENTIALS= \
        PYTHONPATH="$AGENT_DIR" \
        $PYTHON "$script" 2>&1)
    if echo "$_OUT" | grep -q "$banner"; then
        pass "$label"
    else
        echo "  ✗ $label"
        echo "$_OUT" | tail -10
        exit 1
    fi
}

# ---------------------------------------------------------------------------
echo "=== Kaiju Command Center V5.12 GCP Secret Manager Mocked Smoke Test ==="
echo ""
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
echo "[1/8] Environment and import checks..."
# ---------------------------------------------------------------------------

[ -f "$PYTHON" ] || fail "Python not found at $PYTHON"
pass "Python found at $PYTHON"

for module in \
    "credentials.gcp_secret_manager_store" \
    "credentials.secret_store_factory" \
    "credentials.google_ads_provider"
do
    (cd "$AGENT_DIR" && \
        GCP_SECRET_MANAGER_ENABLED=false \
        GOOGLE_APPLICATION_CREDENTIALS= \
        PYTHONPATH="$AGENT_DIR" \
        $PYTHON -c "import $module") >/dev/null 2>&1 \
        && pass "$module importable" \
        || fail "$module not importable"
done

# google-cloud-secret-manager dependency must be installed
(cd "$AGENT_DIR" && \
    GOOGLE_APPLICATION_CREDENTIALS= \
    PYTHONPATH="$AGENT_DIR" \
    $PYTHON -c "from google.cloud import secretmanager; _ = secretmanager.SecretManagerServiceClient") \
    >/dev/null 2>&1 \
    && pass "google-cloud-secret-manager dependency available" \
    || fail "google-cloud-secret-manager not installed (run: pip install google-cloud-secret-manager>=2.20.0)"

# GCP_SECRET_MANAGER_ENABLED must default to false
py_pass "GCP_SECRET_MANAGER_ENABLED defaults to false" <<'PYEOF'
from credentials.gcp_secret_manager_store import get_gcp_secret_manager_enabled
import os
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
assert get_gcp_secret_manager_enabled() is False, "expected false by default"
PYEOF

# Default backend must be in_memory
py_pass "default secret store backend is in_memory" <<'PYEOF'
from credentials.secret_store_factory import get_secret_store_backend_name
import os
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
assert get_secret_store_backend_name() == "in_memory", "expected in_memory"
PYEOF

# ---------------------------------------------------------------------------
echo ""
echo "[2/8] Disabled mode..."
# ---------------------------------------------------------------------------

demo_pass \
    "run_gcp_secret_manager_store_demo.py: disabled mode passed" \
    "run_gcp_secret_manager_store_demo.py" \
    "V5.12.2 GCP Secret Manager store demo passed"

# Inline: disabled GCPSecretManagerStore safe defaults — no GCP calls
py_pass "disabled GCPSecretManagerStore: all methods return safe values" <<'PYEOF'
from credentials.gcp_secret_manager_store import GCPSecretManagerStore
store = GCPSecretManagerStore(enabled=False)
assert store.get_secret_bundle("r", "google_ads") is None
assert store.delete_secret_bundle("r", "google_ads") is False
assert store.list_secret_records() == []
status = store.get_secret_status("r", "google_ads")
assert status["configured"] is False
assert status["metadata"]["backend_status"] == "disabled"
try:
    store.put_secret_bundle("r", "google_ads", {"developer_token": "x"})
    raise AssertionError("expected RuntimeError")
except RuntimeError as e:
    assert "disabled" in str(e).lower()
PYEOF

# ---------------------------------------------------------------------------
echo ""
echo "[3/8] Read/status mock behavior..."
# ---------------------------------------------------------------------------

demo_pass \
    "run_gcp_secret_manager_read_mock_demo.py: read/status passed" \
    "run_gcp_secret_manager_read_mock_demo.py" \
    "V5.12.3 GCP Secret Manager read mock demo passed"

# Inline: helper function formats
py_pass "build_gcp_secret_version_resource_name format correct" <<'PYEOF'
from credentials.gcp_secret_manager_store import build_gcp_secret_version_resource_name
result = build_gcp_secret_version_resource_name("proj", "sec-id", "latest")
assert result == "projects/proj/secrets/sec-id/versions/latest", f"got: {result}"
result2 = build_gcp_secret_version_resource_name("proj", "sec-id", "3")
assert result2 == "projects/proj/secrets/sec-id/versions/3", f"got: {result2}"
PYEOF

py_pass "parse_gcp_secret_payload validates and rejects bad payloads" <<'PYEOF'
import json, os
os.environ.pop("GCP_SECRET_MANAGER_PREFIX", None)
os.environ.pop("GCP_SECRET_MANAGER_ENV", None)
from credentials.gcp_secret_manager_store import parse_gcp_secret_payload

good = {"developer_token": "t", "client_id": "c", "client_secret": "s", "refresh_token": "r"}
result = parse_gcp_secret_payload(json.dumps(good).encode(), "google_ads")
assert set(result.keys()) == set(good.keys())

try:
    parse_gcp_secret_payload(b"not-json", "google_ads")
    raise AssertionError("expected ValueError")
except ValueError:
    pass

try:
    parse_gcp_secret_payload(json.dumps({"access_token": "x"}).encode(), "google_ads")
    raise AssertionError("expected ValueError")
except ValueError:
    pass
PYEOF

# ---------------------------------------------------------------------------
echo ""
echo "[4/8] Write mock behavior..."
# ---------------------------------------------------------------------------

demo_pass \
    "run_gcp_secret_manager_write_mock_demo.py: write passed" \
    "run_gcp_secret_manager_write_mock_demo.py" \
    "V5.12.4 GCP Secret Manager write mock demo passed"

# Inline: build helpers
py_pass "build_gcp_secret_id is deterministic" <<'PYEOF'
import os
os.environ.pop("GCP_SECRET_MANAGER_PREFIX", None)
os.environ.pop("GCP_SECRET_MANAGER_ENV", None)
from credentials.gcp_secret_manager_store import build_gcp_secret_id
a = build_gcp_secret_id("cred_google_ads_abc123", "google_ads")
b = build_gcp_secret_id("cred_google_ads_abc123", "google_ads")
assert a == b, "not deterministic"
assert a == "kaiju-local-google_ads-cred_google_ads_abc123", f"wrong format: {a}"
PYEOF

py_pass "build_gcp_project_resource_name format correct" <<'PYEOF'
from credentials.gcp_secret_manager_store import build_gcp_project_resource_name
assert build_gcp_project_resource_name("my-project") == "projects/my-project"
PYEOF

py_pass "build_gcp_secret_payload validates and rejects bad input" <<'PYEOF'
from credentials.gcp_secret_manager_store import build_gcp_secret_payload
import json

good = {"developer_token": "t", "client_id": "c", "client_secret": "s", "refresh_token": "r"}
payload = build_gcp_secret_payload(good, "google_ads")
assert isinstance(payload, bytes)
parsed = json.loads(payload.decode())
assert set(parsed.keys()) == set(good.keys())

# Deterministic
assert build_gcp_secret_payload(good, "google_ads") == payload

try:
    build_gcp_secret_payload({}, "google_ads")
    raise AssertionError("expected ValueError")
except ValueError:
    pass

try:
    build_gcp_secret_payload({"access_token": "x"}, "google_ads")
    raise AssertionError("expected ValueError")
except ValueError:
    pass
PYEOF

# ---------------------------------------------------------------------------
echo ""
echo "[5/8] Delete/list mock behavior..."
# ---------------------------------------------------------------------------

demo_pass \
    "run_gcp_secret_manager_delete_list_mock_demo.py: delete/list passed" \
    "run_gcp_secret_manager_delete_list_mock_demo.py" \
    "V5.12.5 GCP Secret Manager delete/list mock demo passed"

# Inline: parse_gcp_secret_id
py_pass "parse_gcp_secret_id matches and rejects correctly" <<'PYEOF'
import os
os.environ.pop("GCP_SECRET_MANAGER_PREFIX", None)
os.environ.pop("GCP_SECRET_MANAGER_ENV", None)
from credentials.gcp_secret_manager_store import parse_gcp_secret_id

r = parse_gcp_secret_id("kaiju-local-google_ads-cred_google_ads_abc123")
assert r["matched"] is True
assert r["integration_type"] == "google_ads"
assert r["credential_ref"] == "cred_google_ads_abc123"

for bad in [
    "other-local-google_ads-cred_google_ads_abc123",
    "kaiju-prod-google_ads-cred_google_ads_abc123",
    "kaiju-local-unknown_type-cred",
    "",
]:
    r2 = parse_gcp_secret_id(bad)
    assert r2["matched"] is False, f"expected matched=False for {bad!r}"
PYEOF

# ---------------------------------------------------------------------------
echo ""
echo "[6/8] SecretStoreFactory behavior..."
# ---------------------------------------------------------------------------

demo_pass \
    "run_secret_store_factory_demo.py: factory passed" \
    "run_secret_store_factory_demo.py" \
    "V5.12.6 SecretStoreFactory demo passed"

# Inline: backend selection
py_pass "GCP_SECRET_MANAGER_ENABLED=true selects gcp_secret_manager" <<'PYEOF'
import os
os.environ["GCP_SECRET_MANAGER_ENABLED"] = "true"
from credentials.secret_store_factory import get_secret_store_backend_name
assert get_secret_store_backend_name() == "gcp_secret_manager"
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
PYEOF

py_pass "create_secret_store returns correct types" <<'PYEOF'
import os
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
from credentials.secret_store import InMemorySecretStore
from credentials.gcp_secret_manager_store import GCPSecretManagerStore
from credentials.secret_store_factory import create_secret_store

assert isinstance(create_secret_store(), InMemorySecretStore)
assert isinstance(create_secret_store("in_memory"), InMemorySecretStore)
assert isinstance(create_secret_store("gcp_secret_manager", enabled=False), GCPSecretManagerStore)

try:
    create_secret_store("invalid_backend")
    raise AssertionError("expected ValueError")
except ValueError as e:
    assert "invalid_backend" in str(e)
PYEOF

# Inline: factory status has no secret values
py_pass "secret_store_factory_status contains no secret values" <<'PYEOF'
import os, json
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
from credentials.secret_store_factory import secret_store_factory_status
from credentials.secret_store import assert_no_secret_values_in_payload

status = secret_store_factory_status()
assert "selected_backend" in status
assert "gcp" in status
assert status["selected_backend"] == "in_memory"
assert status["gcp"]["enabled"] is False

ok, offending = assert_no_secret_values_in_payload(status)
assert ok, f"secret markers found in factory status: {offending}"
PYEOF

# ---------------------------------------------------------------------------
echo ""
echo "[7/8] Provider integration with factory..."
# ---------------------------------------------------------------------------

_OUT=$(cd "$AGENT_DIR" && \
    GCP_SECRET_MANAGER_ENABLED=false \
    GCP_PROJECT_ID= \
    GOOGLE_CLOUD_PROJECT= \
    GOOGLE_APPLICATION_CREDENTIALS= \
    PYTHONPATH="$AGENT_DIR" \
    $PYTHON run_google_ads_provider_demo.py 2>&1)
echo "$_OUT" | grep -q "All assertions passed" \
    && pass "run_google_ads_provider_demo.py: All assertions passed" \
    || { echo "  ✗ run_google_ads_provider_demo.py: assertion not found"; echo "$_OUT" | tail -10; exit 1; }

# Explicit InMemorySecretStore injection still bypasses factory
py_pass "explicit secret_store injection bypasses factory" <<'PYEOF'
import os
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
from credentials.secret_store import InMemorySecretStore
from credentials.google_ads_provider import compose_google_ads_credentials

explicit = InMemorySecretStore()
result = compose_google_ads_credentials(
    tenant_id="smoke-tenant",
    client_id="smoke-client",
    secret_store=explicit,
)
# No credential reference → credentials_missing, but no crash = factory bypassed correctly
assert result.ok is False
assert result.errors[0]["code"] in ("credentials_missing", "credential_store_unavailable")
PYEOF

# Factory path (GCP disabled) behaves identically to explicit InMemorySecretStore
py_pass "factory default path (GCP disabled) is safe and consistent" <<'PYEOF'
import os
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
from credentials.secret_store import InMemorySecretStore
from credentials.secret_store_factory import create_secret_store
from credentials.google_ads_provider import compose_google_ads_credentials

# Via factory
r_factory = compose_google_ads_credentials("smoke-tenant", "smoke-client")
# Via explicit store
r_explicit = compose_google_ads_credentials(
    "smoke-tenant", "smoke-client", secret_store=InMemorySecretStore()
)

assert r_factory.ok is False
assert r_explicit.ok is False
assert r_factory.errors[0]["code"] == r_explicit.errors[0]["code"], (
    f"codes differ: {r_factory.errors[0]['code']!r} vs {r_explicit.errors[0]['code']!r}"
)
PYEOF

# No live GCP calls when GCP disabled
py_pass "no live GCP calls made when GCP_SECRET_MANAGER_ENABLED=false" <<'PYEOF'
import os
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
from credentials.gcp_secret_manager_store import GCPSecretManagerStore
from credentials.secret_store_factory import create_secret_store

# auto store is InMemorySecretStore — no GCPSecretManagerStore instantiated
from credentials.secret_store import InMemorySecretStore
store = create_secret_store()
assert isinstance(store, InMemorySecretStore), f"expected InMemorySecretStore: {type(store)}"

# GCPSecretManagerStore disabled never instantiates a real client
gcp_store = GCPSecretManagerStore(enabled=False)
assert gcp_store._client is None, "disabled store must not hold a live client"
PYEOF

# ---------------------------------------------------------------------------
echo ""
echo "[8/8] Secret-safety and git hygiene..."
# ---------------------------------------------------------------------------

GREP_TARGETS="$REPO/scripts $REPO/docs $REPO/agents $REPO/openclaw $REPO/README.md $REPO/.env.example"

# ya29 — OAuth access token prefix (exclude marker constants and docs descriptions)
if grep -R "ya29\." -n $GREP_TARGETS 2>/dev/null \
    | grep -v "_PYEOF\|# ya29\|ya29.*marker\|ya29.*forbidden\|ya29.*prefix"; then
    fail "ya29 OAuth token prefix found in source files"
else
    pass "no ya29 OAuth token prefix in source files"
fi

# sk-[alphanumeric] — API key prefix (exclude known safe marker/test strings)
if grep -R "sk-[A-Za-z0-9]" -n $GREP_TARGETS 2>/dev/null \
    | grep -v "PYEOF\|# sk-\|smoke-test-key\|smoke-client-secret\|smoke-dev-token\|smoke-refresh\|sk-.*marker\|sk-.*prefix"; then
    fail "sk- API key prefix found in source files"
else
    pass "no sk- API key prefix in source files"
fi

# Real-looking credential assignments
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

# No service account JSON files present or tracked
_SA_FILES=$(find "$REPO" \
    \( -name "*service-account*.json" \
    -o -name "*service_account*.json" \
    -o -name "*gcp-credentials*.json" \
    -o -name "*gcp_credentials*.json" \
    -o -name "application_default_credentials.json" \
    \) 2>/dev/null | grep -v ".venv" | grep -v "__pycache__" || true)
if [ -n "$_SA_FILES" ]; then
    echo "$_SA_FILES"
    fail "service account / GCP credential JSON files found in repo"
else
    pass "no service account JSON files present"
fi

# Runtime credential reference store must not be tracked
cd "$REPO"
if git ls-files --error-unmatch "openclaw/credential_references.json" >/dev/null 2>&1; then
    fail "openclaw/credential_references.json is tracked in git — must be gitignored"
else
    pass "runtime credential store file not tracked"
fi

if git status --porcelain | grep -E "credential_references\.json|memory/client-memory|openclaw/audit"; then
    fail "runtime files appeared in git status"
else
    pass "no runtime files in git status"
fi

# ---------------------------------------------------------------------------
echo ""
echo "=== V5.12 GCP Secret Manager mocked smoke test passed. ==="

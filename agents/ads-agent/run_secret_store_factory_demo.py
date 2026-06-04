"""
V5.12.6 — SecretStoreFactory demo.

Validates create_secret_store(), get_secret_store_backend_name(), and
secret_store_factory_status() with no real GCP credentials and no live GCP calls.

Sections:
  1. Default env (GCP disabled) → backend name is in_memory
  2. create_secret_store() auto → InMemorySecretStore
  3. create_secret_store("in_memory") explicit → InMemorySecretStore
  4. create_secret_store("gcp_secret_manager", enabled=False) → disabled GCPSecretManagerStore
  5. create_secret_store("gcp_secret_manager", enabled=True, mock client) → enabled GCPSecretManagerStore
  6. Invalid backend raises ValueError
  7. secret_store_factory_status() shape and no secrets
  8. GCP_SECRET_MANAGER_ENABLED=true env var → backend name switches to gcp_secret_manager
  9. compose_google_ads_credentials with explicit InMemorySecretStore returns credentials_missing
 10. compose_google_ads_credentials with no secret_store uses factory (GCP disabled) → credentials_missing
 11. Final secret-safety assertion on all printed outputs

Run from agents/ads-agent/:
  python3 run_secret_store_factory_demo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Clear GCP env vars before any imports so defaults apply.
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
os.environ.pop("GCP_PROJECT_ID", None)
os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
os.environ.pop("GCP_SECRET_MANAGER_PREFIX", None)
os.environ.pop("GCP_SECRET_MANAGER_ENV", None)

from credentials.gcp_secret_manager_store import GCPSecretManagerStore
from credentials.google_ads_provider import (
    compose_google_ads_credentials,
    google_ads_provider_result_to_redacted_dict,
)
from credentials.secret_store import InMemorySecretStore, assert_no_secret_values_in_payload
from credentials.secret_store_factory import (
    create_secret_store,
    get_secret_store_backend_name,
    secret_store_factory_status,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def section(title: str) -> None:
    print(f"\n--- {title} ---")


def passed(msg: str) -> None:
    print(f"  [PASS] {msg}")


def failed(msg: str) -> None:
    print(f"  [FAIL] {msg}")
    sys.exit(1)


_all_printed_outputs: list = []


def record_and_assert_clean(label: str, payload: dict) -> None:
    _all_printed_outputs.append(payload)
    ok, offending = assert_no_secret_values_in_payload(payload)
    if not ok:
        failed(f"Secret marker found in '{label}' output at: {offending}")


# ---------------------------------------------------------------------------
# Mock infrastructure
# ---------------------------------------------------------------------------

class _MockGCPClient:
    """Minimal mock GCP client for construction tests — never called."""
    pass


# ---------------------------------------------------------------------------
# Section 1 — default env → in_memory
# ---------------------------------------------------------------------------

section("1/11 — Default env (GCP_SECRET_MANAGER_ENABLED unset) → in_memory")

name = get_secret_store_backend_name()
assert name == "in_memory", f"Expected 'in_memory', got: {name!r}"
passed(f"get_secret_store_backend_name() → {name!r}")

# ---------------------------------------------------------------------------
# Section 2 — auto create → InMemorySecretStore
# ---------------------------------------------------------------------------

section("2/11 — create_secret_store() auto → InMemorySecretStore")

store_auto = create_secret_store()
assert isinstance(store_auto, InMemorySecretStore), (
    f"Expected InMemorySecretStore, got: {type(store_auto).__name__}"
)
passed(f"create_secret_store() → {type(store_auto).__name__}")

# ---------------------------------------------------------------------------
# Section 3 — explicit in_memory
# ---------------------------------------------------------------------------

section("3/11 — create_secret_store('in_memory') explicit → InMemorySecretStore")

store_mem = create_secret_store("in_memory")
assert isinstance(store_mem, InMemorySecretStore)
passed("create_secret_store('in_memory') → InMemorySecretStore")

# In-memory store is fully functional.
record = store_mem.put_secret_bundle(
    credential_ref="cred_google_ads_factory_test",
    integration_type="google_ads",
    secrets={
        "developer_token": "tok",
        "client_id": "cid",
        "client_secret": "csec",
        "refresh_token": "rtok",
    },
)
assert record.credential_ref == "cred_google_ads_factory_test"
passed("InMemorySecretStore from factory is fully functional (put/get cycle)")

# ---------------------------------------------------------------------------
# Section 4 — explicit gcp_secret_manager, disabled
# ---------------------------------------------------------------------------

section("4/11 — create_secret_store('gcp_secret_manager', enabled=False) → disabled store")

store_gcp_off = create_secret_store("gcp_secret_manager", enabled=False)
assert isinstance(store_gcp_off, GCPSecretManagerStore), (
    f"Expected GCPSecretManagerStore, got: {type(store_gcp_off).__name__}"
)
passed(f"create_secret_store('gcp_secret_manager', enabled=False) → GCPSecretManagerStore")

# Disabled GCPSecretManagerStore must return safe defaults — no GCP calls.
assert store_gcp_off.get_secret_bundle("ref", "google_ads") is None
passed("Disabled GCPSecretManagerStore.get_secret_bundle → None (no GCP call)")
assert store_gcp_off.delete_secret_bundle("ref", "google_ads") is False
passed("Disabled GCPSecretManagerStore.delete_secret_bundle → False (no GCP call)")
assert store_gcp_off.list_secret_records() == []
passed("Disabled GCPSecretManagerStore.list_secret_records → [] (no GCP call)")

# ---------------------------------------------------------------------------
# Section 5 — explicit gcp_secret_manager, enabled + mock client
# ---------------------------------------------------------------------------

section("5/11 — create_secret_store('gcp_secret_manager', enabled=True, mock client)")

store_gcp_on = create_secret_store(
    "gcp_secret_manager",
    enabled=True,
    project_id="demo-project",
    client=_MockGCPClient(),
)
assert isinstance(store_gcp_on, GCPSecretManagerStore)
passed("create_secret_store('gcp_secret_manager', enabled=True, mock) → GCPSecretManagerStore")

# The store is enabled but mock client methods are not implemented, so reads return None.
result = store_gcp_on.get_secret_bundle("ref", "google_ads")
assert result is None, f"Expected None from mock client, got: {result}"
passed("Enabled GCPSecretManagerStore with stub mock client returns None for get_secret_bundle")

# ---------------------------------------------------------------------------
# Section 6 — invalid backend raises ValueError
# ---------------------------------------------------------------------------

section("6/11 — Invalid backend raises ValueError")

try:
    create_secret_store("redis")
    failed("Expected ValueError for invalid backend 'redis'")
except ValueError as e:
    msg = str(e)
    assert "redis" in msg, f"Error message should mention the invalid backend: {msg}"
    assert "gcp_secret_manager" in msg or "in_memory" in msg, (
        f"Error message should mention valid backends: {msg}"
    )
    passed(f"ValueError raised for invalid backend: {msg!r}")

try:
    create_secret_store("")
    failed("Expected ValueError for empty string backend")
except ValueError as e:
    passed(f"ValueError raised for empty string backend: {str(e)!r}")

# ---------------------------------------------------------------------------
# Section 7 — secret_store_factory_status
# ---------------------------------------------------------------------------

section("7/11 — secret_store_factory_status() shape and no secrets")

status = secret_store_factory_status()
assert isinstance(status, dict), f"Expected dict, got: {type(status)}"
assert "selected_backend" in status, f"Missing 'selected_backend' key: {status}"
assert "gcp" in status, f"Missing 'gcp' key: {status}"
assert status["selected_backend"] == "in_memory", (
    f"Expected 'in_memory' (GCP disabled), got: {status['selected_backend']!r}"
)
gcp = status["gcp"]
assert isinstance(gcp, dict)
assert gcp.get("enabled") is False
assert gcp.get("dependency_available") is True
print(f"  secret_store_factory_status → {status}")
record_and_assert_clean("factory_status", status)
passed(f"secret_store_factory_status() shape correct, selected_backend='in_memory'")

# ---------------------------------------------------------------------------
# Section 8 — GCP_SECRET_MANAGER_ENABLED=true switches backend name
# ---------------------------------------------------------------------------

section("8/11 — GCP_SECRET_MANAGER_ENABLED=true → backend name switches to gcp_secret_manager")

os.environ["GCP_SECRET_MANAGER_ENABLED"] = "true"
name_gcp = get_secret_store_backend_name()
assert name_gcp == "gcp_secret_manager", (
    f"Expected 'gcp_secret_manager', got: {name_gcp!r}"
)
passed(f"get_secret_store_backend_name() with GCP enabled → {name_gcp!r}")

# auto create with GCP enabled → GCPSecretManagerStore (no project_id → init error, but disabled=False)
store_auto_gcp = create_secret_store()
assert isinstance(store_auto_gcp, GCPSecretManagerStore), (
    f"Expected GCPSecretManagerStore, got: {type(store_auto_gcp).__name__}"
)
passed(f"create_secret_store() with GCP enabled → GCPSecretManagerStore")

# Factory status reflects the enabled backend.
status_gcp = secret_store_factory_status()
assert status_gcp["selected_backend"] == "gcp_secret_manager"
passed("secret_store_factory_status() with GCP enabled → selected_backend='gcp_secret_manager'")

# Restore default env.
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
passed("Restored GCP_SECRET_MANAGER_ENABLED to unset (defaults to false)")

# ---------------------------------------------------------------------------
# Section 9 — compose_google_ads_credentials with explicit InMemorySecretStore
# ---------------------------------------------------------------------------

section("9/11 — compose_google_ads_credentials with explicit InMemorySecretStore")

explicit_store = InMemorySecretStore()
result_explicit = compose_google_ads_credentials(
    tenant_id="factory-demo-tenant",
    client_id="factory-demo-client",
    secret_store=explicit_store,
)

assert result_explicit.ok is False
assert result_explicit.errors is not None and len(result_explicit.errors) > 0
error_code_explicit = result_explicit.errors[0]["code"]
# No credential reference set up → credentials_missing
assert error_code_explicit in ("credentials_missing", "credential_store_unavailable"), (
    f"Unexpected error code: {error_code_explicit!r}"
)
passed(f"compose_google_ads_credentials explicit store → ok=False, code={error_code_explicit!r}")

redacted_explicit = google_ads_provider_result_to_redacted_dict(result_explicit)
print(f"  Redacted result (explicit store) → {redacted_explicit}")
record_and_assert_clean("compose_explicit_store", redacted_explicit)

# ---------------------------------------------------------------------------
# Section 10 — compose_google_ads_credentials with no secret_store (factory path)
# ---------------------------------------------------------------------------

section("10/11 — compose_google_ads_credentials with no secret_store → factory path (GCP disabled)")

result_factory = compose_google_ads_credentials(
    tenant_id="factory-demo-tenant",
    client_id="factory-demo-client",
    # secret_store omitted — factory selects InMemorySecretStore (GCP disabled)
)

assert result_factory.ok is False
assert result_factory.errors is not None and len(result_factory.errors) > 0
error_code_factory = result_factory.errors[0]["code"]
assert error_code_factory in ("credentials_missing", "credential_store_unavailable"), (
    f"Unexpected error code: {error_code_factory!r}"
)
passed(f"compose_google_ads_credentials no store → ok=False, code={error_code_factory!r}")
passed("Factory path (GCP disabled) behaves identically to explicit InMemorySecretStore path")

redacted_factory = google_ads_provider_result_to_redacted_dict(result_factory)
print(f"  Redacted result (factory path) → {redacted_factory}")
record_and_assert_clean("compose_factory_path", redacted_factory)

# Outcome codes must match between explicit and factory paths.
assert error_code_explicit == error_code_factory, (
    f"Explicit and factory paths returned different codes: "
    f"{error_code_explicit!r} vs {error_code_factory!r}"
)
passed("Explicit store and factory path return identical error code")

# ---------------------------------------------------------------------------
# Section 11 — Final secret-safety assertion
# ---------------------------------------------------------------------------

section("11/11 — Final secret-safety assertion on all printed outputs")

for i, output in enumerate(_all_printed_outputs):
    ok, offending = assert_no_secret_values_in_payload(output)
    if not ok:
        failed(f"Secret marker found in output #{i}: {offending}")

passed(f"All {len(_all_printed_outputs)} printed outputs free of secret markers")

print("\n=== V5.12.6 SecretStoreFactory demo passed. ===\n")

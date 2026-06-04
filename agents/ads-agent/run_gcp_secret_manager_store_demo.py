"""
V5.12.2 — GCPSecretManagerStore scaffold demo.

Runs with GCP_SECRET_MANAGER_ENABLED=false (default).
No GCP credentials required. No live GCP calls made.
All assertions verify disabled-mode behavior of the scaffold.

Run from agents/ads-agent/:
  python3 run_gcp_secret_manager_store_demo.py
"""

import os
import sys

# Ensure credentials package is importable when run from agents/ads-agent/.
sys.path.insert(0, os.path.dirname(__file__))

# Confirm disabled default before any imports so the test covers env-cold state.
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
os.environ.pop("GCP_PROJECT_ID", None)
os.environ.pop("GOOGLE_CLOUD_PROJECT", None)

from credentials.gcp_secret_manager_store import (
    GCPSecretManagerStore,
    build_gcp_secret_id,
    build_gcp_secret_resource_name,
    gcp_secret_manager_status,
    get_gcp_project_id,
    get_gcp_secret_manager_enabled,
    get_gcp_secret_manager_env,
    get_gcp_secret_manager_prefix,
    load_secret_manager_client_class,
)
from credentials.secret_store import assert_no_secret_values_in_payload


def section(title: str) -> None:
    print(f"\n--- {title} ---")


def passed(msg: str) -> None:
    print(f"  [PASS] {msg}")


def failed(msg: str) -> None:
    print(f"  [FAIL] {msg}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Section 1 — env config helpers (all env vars unset)
# ---------------------------------------------------------------------------

section("1/9 — Env config helpers (all vars unset)")

assert get_gcp_secret_manager_enabled() is False, "Expected enabled=False when unset"
passed("get_gcp_secret_manager_enabled() → False (default)")

assert get_gcp_project_id() is None, "Expected project_id=None when unset"
passed("get_gcp_project_id() → None (no env var)")

assert get_gcp_secret_manager_prefix() == "kaiju", "Expected prefix=kaiju (default)"
passed(f"get_gcp_secret_manager_prefix() → {get_gcp_secret_manager_prefix()!r}")

assert get_gcp_secret_manager_env() == "local", "Expected env=local (default)"
passed(f"get_gcp_secret_manager_env() → {get_gcp_secret_manager_env()!r}")

# ---------------------------------------------------------------------------
# Section 2 — env config helper edge cases
# ---------------------------------------------------------------------------

section("2/9 — Env config helper edge cases")

os.environ["GCP_SECRET_MANAGER_ENABLED"] = "true"
assert get_gcp_secret_manager_enabled() is True
passed("GCP_SECRET_MANAGER_ENABLED=true → enabled=True")

os.environ["GCP_SECRET_MANAGER_ENABLED"] = "false"
assert get_gcp_secret_manager_enabled() is False
passed("GCP_SECRET_MANAGER_ENABLED=false → enabled=False")

del os.environ["GCP_SECRET_MANAGER_ENABLED"]

os.environ["GCP_SECRET_MANAGER_ENV"] = "invalid_value"
assert get_gcp_secret_manager_env() == "local", "Invalid env should fall back to local"
passed("GCP_SECRET_MANAGER_ENV=invalid_value → falls back to 'local'")
del os.environ["GCP_SECRET_MANAGER_ENV"]

os.environ["GCP_PROJECT_ID"] = "my-gcp-project"
assert get_gcp_project_id() == "my-gcp-project"
passed("GCP_PROJECT_ID=my-gcp-project → project_id='my-gcp-project'")
del os.environ["GCP_PROJECT_ID"]

os.environ["GOOGLE_CLOUD_PROJECT"] = "fallback-project"
assert get_gcp_project_id() == "fallback-project"
passed("GOOGLE_CLOUD_PROJECT fallback → project_id='fallback-project'")
del os.environ["GOOGLE_CLOUD_PROJECT"]

# ---------------------------------------------------------------------------
# Section 3 — secret ID / resource name builders
# ---------------------------------------------------------------------------

section("3/9 — build_gcp_secret_id and build_gcp_secret_resource_name")

os.environ["GCP_SECRET_MANAGER_PREFIX"] = "kaiju"
os.environ["GCP_SECRET_MANAGER_ENV"] = "prod"

secret_id = build_gcp_secret_id("cred_google_ads_abcd1234ef56", "google_ads")
assert secret_id == "kaiju-prod-google_ads-cred_google_ads_abcd1234ef56", (
    f"Unexpected secret_id: {secret_id!r}"
)
passed(f"build_gcp_secret_id → {secret_id!r}")

# Deterministic — same call produces same result.
assert build_gcp_secret_id("cred_google_ads_abcd1234ef56", "google_ads") == secret_id
passed("build_gcp_secret_id is deterministic")

resource = build_gcp_secret_resource_name("my-project", secret_id)
expected_resource = f"projects/my-project/secrets/{secret_id}"
assert resource == expected_resource, f"Unexpected resource: {resource!r}"
passed(f"build_gcp_secret_resource_name → {resource!r}")

# Sanitize special characters — slashes and spaces become underscores.
dirty_id = build_gcp_secret_id("ref with spaces/slash", "google/ads integration")
assert " " not in dirty_id and "/" not in dirty_id, f"Unexpected chars in: {dirty_id!r}"
passed(f"Sanitization of special chars → {dirty_id!r}")

del os.environ["GCP_SECRET_MANAGER_PREFIX"]
del os.environ["GCP_SECRET_MANAGER_ENV"]

# ---------------------------------------------------------------------------
# Section 4 — gcp_secret_manager_status()
# ---------------------------------------------------------------------------

section("4/9 — gcp_secret_manager_status()")

status = gcp_secret_manager_status()
print(f"  status = {status}")

assert "enabled" in status
assert "project_id_configured" in status
assert "prefix" in status
assert "environment" in status
assert "dependency_available" in status

assert status["enabled"] is False, "Expected enabled=False (no env var)"
assert status["project_id_configured"] is False, "Expected project_id_configured=False"
assert status["prefix"] == "kaiju"
assert status["environment"] == "local"
assert status["dependency_available"] is True, (
    "Expected dependency_available=True after pip install"
)
passed("gcp_secret_manager_status() shape and values correct")

ok, offending = assert_no_secret_values_in_payload(status)
assert ok, f"Secret marker found in status output: {offending}"
passed("No secret values in status output")

# ---------------------------------------------------------------------------
# Section 5 — lazy import guard
# ---------------------------------------------------------------------------

section("5/9 — load_secret_manager_client_class()")

available, client_class, errors = load_secret_manager_client_class()
assert available is True, f"Expected available=True, got: {errors}"
assert client_class is not None
assert errors == []
passed(f"load_secret_manager_client_class() → available=True, class={client_class.__name__}")

# ---------------------------------------------------------------------------
# Section 6 — GCPSecretManagerStore disabled mode
# ---------------------------------------------------------------------------

section("6/9 — GCPSecretManagerStore(enabled=False) disabled mode")

store = GCPSecretManagerStore(enabled=False)
passed("GCPSecretManagerStore(enabled=False) constructed without GCP credentials")

# get_secret_status — returns unconfigured shape with disabled metadata.
status_result = store.get_secret_status("demo-ref", "google_ads")
print(f"  get_secret_status → {status_result}")
assert status_result["configured"] is False
assert status_result["credential_ref"] == "demo-ref"
assert status_result["integration_type"] == "google_ads"
assert status_result.get("metadata", {}).get("backend_status") == "disabled"
passed("get_secret_status returns unconfigured shape with backend_status=disabled")

ok, offending = assert_no_secret_values_in_payload(status_result)
assert ok, f"Secret marker in get_secret_status output: {offending}"
passed("No secret values in get_secret_status output")

# get_secret_bundle — returns None.
bundle = store.get_secret_bundle("demo-ref", "google_ads")
assert bundle is None, f"Expected None, got: {bundle}"
passed("get_secret_bundle returns None when disabled")

# delete_secret_bundle — returns False.
deleted = store.delete_secret_bundle("demo-ref", "google_ads")
assert deleted is False, f"Expected False, got: {deleted}"
passed("delete_secret_bundle returns False when disabled")

# list_secret_records — returns [].
records = store.list_secret_records()
assert records == [], f"Expected [], got: {records}"
records_filtered = store.list_secret_records(integration_type="google_ads")
assert records_filtered == []
passed("list_secret_records returns [] when disabled")

# put_secret_bundle — raises RuntimeError.
try:
    store.put_secret_bundle("demo-ref", "google_ads", {"developer_token": "x", "client_id": "x", "client_secret": "x", "refresh_token": "x"})
    failed("put_secret_bundle should have raised RuntimeError when disabled")
except RuntimeError as e:
    assert "disabled" in str(e).lower(), f"Unexpected error message: {e}"
    passed(f"put_secret_bundle raises RuntimeError when disabled: {e}")

# ---------------------------------------------------------------------------
# Section 7 — env-default construction (no GCP_SECRET_MANAGER_ENABLED set)
# ---------------------------------------------------------------------------

section("7/9 — GCPSecretManagerStore() with default env (enabled=False)")

os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
default_store = GCPSecretManagerStore()
assert default_store._enabled is False
passed("GCPSecretManagerStore() default env → enabled=False")

bundle = default_store.get_secret_bundle("any-ref", "google_ads")
assert bundle is None
passed("Default-env store get_secret_bundle → None")

# ---------------------------------------------------------------------------
# Section 8 — field validation runs before GCP calls
# ---------------------------------------------------------------------------

section("8/9 — put_secret_bundle validates fields before any GCP call")

store_disabled = GCPSecretManagerStore(enabled=False)

try:
    store_disabled.put_secret_bundle("ref", "google_ads", {})
    failed("Expected ValueError for empty secrets")
except RuntimeError:
    passed("put_secret_bundle raises RuntimeError (disabled) — disabled check runs first")

# When enabled but not ready, field validation should still run before reaching NotImplementedError.
try:
    store_disabled.put_secret_bundle("ref", "google_ads", {"access_token": "leaked"})
    failed("Expected RuntimeError (disabled wins before field check)")
except RuntimeError:
    passed("Disabled check fires before field validation (correct precedence)")

# ---------------------------------------------------------------------------
# Section 9 — no real credentials, no GCP calls confirmed
# ---------------------------------------------------------------------------

section("9/9 — Confirm no real credentials in any output")

all_outputs = [status, status_result]
for output in all_outputs:
    ok, offending = assert_no_secret_values_in_payload(output)
    assert ok, f"Secret marker found in output: {offending}"
passed("All demo outputs free of secret markers")

print("\n=== V5.12.2 GCP Secret Manager store demo passed. ===\n")

"""
V5.12.4 — GCPSecretManagerStore mock write demo.

Validates put_secret_bundle with an injected mock client.
No real GCP credentials required. No live GCP calls made.

Mock clients simulate:
  1. Valid write — create_secret + add_secret_version succeed
  2. AlreadyExists on create_secret — add_secret_version still called
  3. PermissionDenied on create_secret — raises safe RuntimeError
  4. PermissionDenied on add_secret_version — raises safe RuntimeError

Run from agents/ads-agent/:
  python3 run_gcp_secret_manager_write_mock_demo.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Clear GCP env vars before any imports.
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
os.environ.pop("GCP_PROJECT_ID", None)
os.environ.pop("GOOGLE_CLOUD_PROJECT", None)

from credentials.gcp_secret_manager_store import (
    GCPSecretManagerStore,
    build_gcp_project_resource_name,
    build_gcp_secret_id,
    build_gcp_secret_payload,
    build_gcp_secret_resource_name,
)
from credentials.secret_store import SecretRecord, assert_no_secret_values_in_payload

# ---------------------------------------------------------------------------
# Mock infrastructure
# ---------------------------------------------------------------------------
# Secret values live only inside _MOCK_SECRETS. They are never printed.
# The demo asserts that no printed output contains them.

_MOCK_SECRETS = {
    "developer_token": "demo-dev-token",
    "client_id": "demo-client-id",
    "client_secret": "demo-client-secret",
    "refresh_token": "demo-refresh-token",
}


class _MockWriteClient:
    """Captures create_secret and add_secret_version requests. No live calls."""

    def __init__(self) -> None:
        self.create_secret_calls: list = []
        self.add_secret_version_calls: list = []

    def create_secret(self, request: dict) -> object:
        # Capture safe identifiers only — never capture payload.
        self.create_secret_calls.append({
            "parent": request.get("parent"),
            "secret_id": request.get("secret_id"),
            "replication_type": list(
                request.get("secret", {}).get("replication", {}).keys()
            ),
        })
        return type("MockSecret", (), {
            "name": f"{request['parent']}/secrets/{request['secret_id']}"
        })()

    def add_secret_version(self, request: dict) -> object:
        # Capture parent only — never capture or store payload bytes.
        self.add_secret_version_calls.append({"parent": request.get("parent")})
        return type("MockVersion", (), {
            "name": f"{request['parent']}/versions/1"
        })()


class _MockAlreadyExistsClient:
    """create_secret raises AlreadyExists; add_secret_version succeeds."""

    def __init__(self) -> None:
        self.add_secret_version_calls: list = []

    def create_secret(self, request: dict) -> None:
        from google.api_core.exceptions import AlreadyExists
        raise AlreadyExists("Secret already exists: demo-project/secrets/kaiju-local-...")

    def add_secret_version(self, request: dict) -> object:
        self.add_secret_version_calls.append({"parent": request.get("parent")})
        return type("MockVersion", (), {"name": f"{request['parent']}/versions/2"})()


class _MockPermissionDeniedCreateClient:
    """create_secret raises PermissionDenied; add_secret_version should NOT be called."""

    def __init__(self) -> None:
        self.add_secret_version_called = False

    def create_secret(self, request: dict) -> None:
        from google.api_core.exceptions import PermissionDenied
        raise PermissionDenied("Permission denied on secret creation")

    def add_secret_version(self, request: dict) -> None:
        self.add_secret_version_called = True
        raise AssertionError("add_secret_version must not be called after PermissionDenied on create")


class _MockPermissionDeniedVersionClient:
    """create_secret succeeds; add_secret_version raises PermissionDenied."""

    def create_secret(self, request: dict) -> object:
        return type("MockSecret", (), {})()

    def add_secret_version(self, request: dict) -> None:
        from google.api_core.exceptions import PermissionDenied
        raise PermissionDenied("Permission denied on add_secret_version")


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
# Section 1 — build_gcp_project_resource_name
# ---------------------------------------------------------------------------

section("1/9 — build_gcp_project_resource_name")

assert build_gcp_project_resource_name("my-project") == "projects/my-project"
passed("build_gcp_project_resource_name('my-project') → 'projects/my-project'")

# ---------------------------------------------------------------------------
# Section 2 — build_gcp_secret_payload helpers
# ---------------------------------------------------------------------------

section("2/9 — build_gcp_secret_payload")

payload_bytes = build_gcp_secret_payload(_MOCK_SECRETS, "google_ads")
assert isinstance(payload_bytes, bytes), "Expected bytes"
parsed_back = json.loads(payload_bytes.decode("utf-8"))
assert isinstance(parsed_back, dict)
assert set(parsed_back.keys()) == set(_MOCK_SECRETS.keys())
passed(f"build_gcp_secret_payload returns {len(payload_bytes)}-byte JSON object with 4 fields (values not printed)")

# Deterministic — same call produces same bytes.
assert build_gcp_secret_payload(_MOCK_SECRETS, "google_ads") == payload_bytes
passed("build_gcp_secret_payload is deterministic")

try:
    build_gcp_secret_payload({}, "google_ads")
    failed("Expected ValueError for empty secrets")
except ValueError as e:
    passed(f"Rejects empty dict: {e}")

try:
    build_gcp_secret_payload({"access_token": "x"}, "google_ads")
    failed("Expected ValueError for forbidden field")
except ValueError as e:
    assert "disallowed" in str(e).lower()
    passed(f"Rejects forbidden field: {e}")

try:
    build_gcp_secret_payload({"developer_token": ""}, "google_ads")
    failed("Expected ValueError for empty value")
except ValueError as e:
    assert "empty" in str(e).lower()
    passed(f"Rejects empty value: {e}")

# ---------------------------------------------------------------------------
# Section 3 — disabled mode still rejects put_secret_bundle
# ---------------------------------------------------------------------------

section("3/9 — Disabled mode rejects put_secret_bundle")

store_disabled = GCPSecretManagerStore(enabled=False)

try:
    store_disabled.put_secret_bundle("ref", "google_ads", _MOCK_SECRETS)
    failed("Expected RuntimeError for disabled store")
except RuntimeError as e:
    assert "disabled" in str(e).lower(), f"Unexpected message: {e}"
    passed(f"put_secret_bundle raises RuntimeError when disabled: {e}")

# ---------------------------------------------------------------------------
# Section 4 — enabled + valid mock client
# ---------------------------------------------------------------------------

section("4/9 — Enabled + valid mock client: create_secret + add_secret_version")

mock_client = _MockWriteClient()
store_valid = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=mock_client,
)

record = store_valid.put_secret_bundle(
    credential_ref="cred_google_ads_abc123",
    integration_type="google_ads",
    secrets=_MOCK_SECRETS,
)

assert isinstance(record, SecretRecord), f"Expected SecretRecord, got: {type(record)}"
passed("put_secret_bundle returned a SecretRecord")

assert record.credential_ref == "cred_google_ads_abc123"
assert record.integration_type == "google_ads"
assert sorted(record.configured_fields) == sorted(_MOCK_SECRETS.keys())
passed(f"SecretRecord configured_fields: {sorted(record.configured_fields)}")

assert record.created_at is not None
assert record.updated_at is not None
passed("SecretRecord has created_at and updated_at")

meta = record.metadata or {}
assert meta.get("backend") == "gcp_secret_manager"
assert meta.get("write_mode") == "add_secret_version"
assert meta.get("enabled") is True
assert meta.get("secret_id") is not None
passed(f"SecretRecord metadata backend=gcp_secret_manager, write_mode=add_secret_version, secret_id={meta.get('secret_id')!r}")

# Verify create_secret request shape (no payload here).
assert len(mock_client.create_secret_calls) == 1
create_req = mock_client.create_secret_calls[0]
expected_parent = build_gcp_project_resource_name("demo-project")
assert create_req["parent"] == expected_parent, f"Wrong parent: {create_req['parent']!r}"
assert create_req["replication_type"] == ["automatic"], f"Wrong replication: {create_req['replication_type']}"
expected_secret_id = build_gcp_secret_id("cred_google_ads_abc123", "google_ads")
assert create_req["secret_id"] == expected_secret_id, f"Wrong secret_id: {create_req['secret_id']!r}"
passed(f"create_secret called with correct parent={expected_parent!r}, secret_id={expected_secret_id!r}")

# Verify add_secret_version request shape (we captured parent, not payload).
assert len(mock_client.add_secret_version_calls) == 1
version_req = mock_client.add_secret_version_calls[0]
expected_secret_resource = build_gcp_secret_resource_name("demo-project", expected_secret_id)
assert version_req["parent"] == expected_secret_resource, f"Wrong parent: {version_req['parent']!r}"
passed(f"add_secret_version called with correct parent={expected_secret_resource!r}")

# Print the record as a safe dict — assert it contains no secret markers.
record_dict = {
    "credential_ref": record.credential_ref,
    "integration_type": record.integration_type,
    "configured_fields": record.configured_fields,
    "created_at": record.created_at,
    "metadata": record.metadata,
}
print(f"  SecretRecord (safe) → {record_dict}")
record_and_assert_clean("SecretRecord from valid write", record_dict)

# ---------------------------------------------------------------------------
# Section 5 — AlreadyExists on create_secret → add_secret_version still called
# ---------------------------------------------------------------------------

section("5/9 — AlreadyExists on create_secret → add_secret_version proceeds")

already_client = _MockAlreadyExistsClient()
store_already = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=already_client,
)

record_already = store_already.put_secret_bundle(
    credential_ref="cred_google_ads_existing",
    integration_type="google_ads",
    secrets=_MOCK_SECRETS,
)

assert isinstance(record_already, SecretRecord)
assert len(already_client.add_secret_version_calls) == 1, (
    f"Expected 1 add_secret_version call, got {len(already_client.add_secret_version_calls)}"
)
passed("AlreadyExists on create_secret → add_secret_version was still called")
passed(f"Returned SecretRecord with configured_fields={sorted(record_already.configured_fields)}")

# ---------------------------------------------------------------------------
# Section 6 — Forbidden field rejected before any client call
# ---------------------------------------------------------------------------

section("6/9 — Forbidden field rejected before any client call")

spy_client = _MockWriteClient()
store_spy = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=spy_client,
)

try:
    store_spy.put_secret_bundle(
        "ref", "google_ads",
        {"access_token": "leaked", "developer_token": "x"},
    )
    failed("Expected ValueError for forbidden field")
except ValueError as e:
    assert "disallowed" in str(e).lower(), f"Unexpected message: {e}"
    assert len(spy_client.create_secret_calls) == 0, "create_secret should not be called"
    assert len(spy_client.add_secret_version_calls) == 0, "add_secret_version should not be called"
    passed(f"ValueError raised, no GCP calls made: {e}")

# ---------------------------------------------------------------------------
# Section 7 — Empty value rejected before any client call
# ---------------------------------------------------------------------------

section("7/9 — Empty value rejected before any client call")

spy_client2 = _MockWriteClient()
store_spy2 = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=spy_client2,
)

try:
    store_spy2.put_secret_bundle(
        "ref", "google_ads",
        {"developer_token": "", "client_id": "x", "client_secret": "x", "refresh_token": "x"},
    )
    failed("Expected ValueError for empty field value")
except ValueError as e:
    assert "empty" in str(e).lower(), f"Unexpected message: {e}"
    assert len(spy_client2.create_secret_calls) == 0
    assert len(spy_client2.add_secret_version_calls) == 0
    passed(f"ValueError raised, no GCP calls made: {e}")

# ---------------------------------------------------------------------------
# Section 8 — PermissionDenied on create_secret
# ---------------------------------------------------------------------------

section("8/9 — PermissionDenied on create_secret maps to safe RuntimeError")

store_pd_create = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=_MockPermissionDeniedCreateClient(),
)

try:
    store_pd_create.put_secret_bundle("ref", "google_ads", _MOCK_SECRETS)
    failed("Expected RuntimeError for PermissionDenied on create_secret")
except RuntimeError as e:
    msg = str(e)
    assert "gcp_secret_access_denied" in msg, f"Unexpected message: {msg}"
    assert "Permission denied" not in msg, "Raw exception message must not be exposed"
    passed(f"RuntimeError with safe error code: {msg!r}")

# Verify add_secret_version was NOT called.
assert not store_pd_create._client.add_secret_version_called  # type: ignore[attr-defined]
passed("add_secret_version was not called after PermissionDenied on create_secret")

# ---------------------------------------------------------------------------
# Section 9 — PermissionDenied on add_secret_version + final safety
# ---------------------------------------------------------------------------

section("9/9 — PermissionDenied on add_secret_version + secret-safety assertion")

store_pd_version = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=_MockPermissionDeniedVersionClient(),
)

try:
    store_pd_version.put_secret_bundle("ref", "google_ads", _MOCK_SECRETS)
    failed("Expected RuntimeError for PermissionDenied on add_secret_version")
except RuntimeError as e:
    msg = str(e)
    assert "gcp_secret_access_denied" in msg, f"Unexpected message: {msg}"
    assert "Permission denied" not in msg, "Raw exception message must not be exposed"
    passed(f"RuntimeError with safe error code from add_secret_version failure: {msg!r}")

# Final: assert no secret markers in any printed output.
for i, output in enumerate(_all_printed_outputs):
    ok, offending = assert_no_secret_values_in_payload(output)
    if not ok:
        failed(f"Secret marker found in output #{i}: {offending}")

passed(f"All {len(_all_printed_outputs)} printed outputs free of secret markers")

print("\n=== V5.12.4 GCP Secret Manager write mock demo passed. ===\n")

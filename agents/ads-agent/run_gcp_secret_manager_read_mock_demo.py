"""
V5.12.3 — GCPSecretManagerStore mock read/status demo.

Validates get_secret_bundle and get_secret_status with an injected mock client.
No real GCP credentials required. No live GCP calls made.

The mock client simulates four cases:
  1. Valid bundle — all 4 required fields present
  2. Secret not found — GCP NotFound exception
  3. Invalid JSON payload — bytes that are not valid JSON
  4. Disallowed field in payload — JSON with a forbidden key

Run from agents/ads-agent/:
  python3 run_gcp_secret_manager_read_mock_demo.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Ensure no GCP env vars leak into the test from the calling shell.
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
os.environ.pop("GCP_PROJECT_ID", None)
os.environ.pop("GOOGLE_CLOUD_PROJECT", None)

from credentials.gcp_secret_manager_store import (
    GCPSecretManagerStore,
    build_gcp_secret_version_resource_name,
    parse_gcp_secret_payload,
)
from credentials.secret_store import assert_no_secret_values_in_payload

# ---------------------------------------------------------------------------
# Mock infrastructure
# ---------------------------------------------------------------------------
# Secret values live only inside the mock client's data bytes.
# They are never printed. The demo asserts the status output contains none.

_MOCK_VALID_FIELDS = ("developer_token", "client_id", "client_secret", "refresh_token")
_MOCK_VALID_BUNDLE_JSON: bytes = json.dumps({
    "developer_token": "demo-dev-token",
    "client_id": "demo-client-id",
    "client_secret": "demo-client-secret",
    "refresh_token": "demo-refresh-token",
}).encode()


class _MockPayload:
    def __init__(self, data: bytes) -> None:
        self.data = data


class _MockAccessResponse:
    def __init__(self, data: bytes) -> None:
        self.payload = _MockPayload(data)


class _MockValidClient:
    """Returns a complete, valid secret bundle."""
    def access_secret_version(self, request: dict) -> _MockAccessResponse:
        return _MockAccessResponse(_MOCK_VALID_BUNDLE_JSON)


class _MockNotFoundClient:
    """Raises google.api_core.exceptions.NotFound."""
    def access_secret_version(self, request: dict) -> None:
        from google.api_core.exceptions import NotFound
        raise NotFound("404 Secret not found")


class _MockInvalidJsonClient:
    """Returns bytes that are not valid JSON."""
    def access_secret_version(self, request: dict) -> _MockAccessResponse:
        return _MockAccessResponse(b"this-is-not-json")


class _MockForbiddenFieldClient:
    """Returns valid JSON but with a forbidden field (access_token)."""
    def access_secret_version(self, request: dict) -> _MockAccessResponse:
        data = json.dumps({"access_token": "some-token"}).encode()
        return _MockAccessResponse(data)


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
    """Record a printed output dict and assert it contains no secret markers."""
    _all_printed_outputs.append(payload)
    ok, offending = assert_no_secret_values_in_payload(payload)
    if not ok:
        failed(f"Secret marker found in '{label}' output at: {offending}")


# ---------------------------------------------------------------------------
# Section 1 — parse_gcp_secret_payload helpers (unit-style)
# ---------------------------------------------------------------------------

section("1/8 — parse_gcp_secret_payload — valid input")

bundle = parse_gcp_secret_payload(_MOCK_VALID_BUNDLE_JSON, "google_ads")
assert isinstance(bundle, dict), "Expected dict"
assert set(bundle.keys()) == set(_MOCK_VALID_FIELDS), f"Unexpected keys: {set(bundle.keys())}"
passed("parse_gcp_secret_payload returns dict with all 4 fields")

bundle_from_str = parse_gcp_secret_payload(
    _MOCK_VALID_BUNDLE_JSON.decode("utf-8"), "google_ads"
)
assert isinstance(bundle_from_str, dict)
passed("parse_gcp_secret_payload accepts str input as well as bytes")

section("2/8 — parse_gcp_secret_payload — rejection cases")

try:
    parse_gcp_secret_payload(b"not-json", "google_ads")
    failed("Expected ValueError for invalid JSON")
except ValueError as e:
    assert "valid JSON" in str(e), f"Unexpected message: {e}"
    passed(f"Rejects invalid JSON: {e}")

try:
    parse_gcp_secret_payload(b"[1,2,3]", "google_ads")
    failed("Expected ValueError for non-dict JSON")
except ValueError as e:
    assert "object" in str(e).lower(), f"Unexpected message: {e}"
    passed(f"Rejects non-dict JSON (array): {e}")

try:
    parse_gcp_secret_payload(b"{}", "google_ads")
    failed("Expected ValueError for empty dict")
except ValueError as e:
    assert "empty" in str(e).lower(), f"Unexpected message: {e}"
    passed(f"Rejects empty dict: {e}")

try:
    forbidden_payload = json.dumps({"access_token": "x"}).encode()
    parse_gcp_secret_payload(forbidden_payload, "google_ads")
    failed("Expected ValueError for forbidden field")
except ValueError as e:
    assert "disallowed" in str(e).lower(), f"Unexpected message: {e}"
    passed(f"Rejects forbidden field (access_token): {e}")

try:
    empty_val_payload = json.dumps({"developer_token": ""}).encode()
    parse_gcp_secret_payload(empty_val_payload, "google_ads")
    failed("Expected ValueError for empty value")
except ValueError as e:
    assert "empty" in str(e).lower(), f"Unexpected message: {e}"
    passed(f"Rejects empty field value: {e}")

# ---------------------------------------------------------------------------
# Section 3 — build_gcp_secret_version_resource_name
# ---------------------------------------------------------------------------

section("3/8 — build_gcp_secret_version_resource_name")

resource = build_gcp_secret_version_resource_name("my-project", "kaiju-prod-google_ads-ref123")
assert resource == "projects/my-project/secrets/kaiju-prod-google_ads-ref123/versions/latest"
passed(f"default version=latest → {resource!r}")

resource_v2 = build_gcp_secret_version_resource_name("my-project", "kaiju-prod-google_ads-ref123", version="2")
assert resource_v2.endswith("/versions/2")
passed(f"explicit version=2 → {resource_v2!r}")

# ---------------------------------------------------------------------------
# Section 4 — enabled + valid mock client
# ---------------------------------------------------------------------------

section("4/8 — GCPSecretManagerStore(enabled=True, valid mock client)")

store_valid = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=_MockValidClient(),
)
assert store_valid._enabled is True
assert store_valid._init_errors == []
assert store_valid._client is not None
passed("Store constructed: enabled=True, mock client injected")

bundle = store_valid.get_secret_bundle("cred_google_ads_abc123", "google_ads")
assert bundle is not None, "Expected bundle, got None"
assert isinstance(bundle, dict)
assert set(bundle.keys()) == set(_MOCK_VALID_FIELDS), f"Unexpected keys: {set(bundle.keys())}"
# Values exist — assert but never print them.
for field in _MOCK_VALID_FIELDS:
    assert field in bundle and bundle[field], f"Field '{field}' missing or empty"
passed(f"get_secret_bundle returned bundle with {set(bundle.keys())} (values not printed)")

status = store_valid.get_secret_status("cred_google_ads_abc123", "google_ads")
print(f"  get_secret_status (valid) → {status}")
assert status["configured"] is True, f"Expected configured=True, got: {status['configured']}"
assert status["credential_ref"] == "cred_google_ads_abc123"
assert status.get("metadata", {}).get("available") is True
assert status.get("metadata", {}).get("backend") == "gcp_secret_manager"
passed("get_secret_status returns configured=True with available=True metadata")
record_and_assert_clean("get_secret_status valid", status)

# ---------------------------------------------------------------------------
# Section 5 — enabled + NotFound mock client
# ---------------------------------------------------------------------------

section("5/8 — GCPSecretManagerStore — secret not found")

store_notfound = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=_MockNotFoundClient(),
)

bundle_missing = store_notfound.get_secret_bundle("nonexistent-ref", "google_ads")
assert bundle_missing is None, f"Expected None for missing secret, got: {bundle_missing}"
passed("get_secret_bundle returns None when secret not found")

status_notfound = store_notfound.get_secret_status("nonexistent-ref", "google_ads")
print(f"  get_secret_status (not found) → {status_notfound}")
assert status_notfound["configured"] is False
assert status_notfound.get("metadata", {}).get("available") is False
assert status_notfound.get("metadata", {}).get("error_code") == "gcp_secret_not_found"
passed("get_secret_status returns configured=False with error_code=gcp_secret_not_found")
record_and_assert_clean("get_secret_status notfound", status_notfound)

# ---------------------------------------------------------------------------
# Section 6 — enabled + invalid JSON payload
# ---------------------------------------------------------------------------

section("6/8 — GCPSecretManagerStore — invalid JSON payload")

store_invalid_json = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=_MockInvalidJsonClient(),
)

bundle_invalid = store_invalid_json.get_secret_bundle("some-ref", "google_ads")
assert bundle_invalid is None, f"Expected None for invalid JSON, got: {bundle_invalid}"
passed("get_secret_bundle returns None when payload is invalid JSON")

status_invalid_json = store_invalid_json.get_secret_status("some-ref", "google_ads")
print(f"  get_secret_status (invalid JSON) → {status_invalid_json}")
assert status_invalid_json["configured"] is False
assert status_invalid_json.get("metadata", {}).get("error_code") == "gcp_secret_payload_invalid"
passed("get_secret_status returns configured=False with error_code=gcp_secret_payload_invalid")
record_and_assert_clean("get_secret_status invalid json", status_invalid_json)

# ---------------------------------------------------------------------------
# Section 7 — enabled + forbidden field in payload
# ---------------------------------------------------------------------------

section("7/8 — GCPSecretManagerStore — forbidden field in payload")

store_forbidden = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=_MockForbiddenFieldClient(),
)

bundle_forbidden = store_forbidden.get_secret_bundle("some-ref", "google_ads")
assert bundle_forbidden is None, f"Expected None for forbidden field payload, got: {bundle_forbidden}"
passed("get_secret_bundle returns None when payload has forbidden field")

status_forbidden = store_forbidden.get_secret_status("some-ref", "google_ads")
print(f"  get_secret_status (forbidden field) → {status_forbidden}")
assert status_forbidden["configured"] is False
assert status_forbidden.get("metadata", {}).get("error_code") == "gcp_secret_payload_invalid"
passed("get_secret_status returns configured=False with error_code=gcp_secret_payload_invalid")
record_and_assert_clean("get_secret_status forbidden", status_forbidden)

# ---------------------------------------------------------------------------
# Section 8 — enabled + missing project_id (init error path)
# ---------------------------------------------------------------------------

section("8/8 — GCPSecretManagerStore — enabled without project_id (init error)")

store_no_project = GCPSecretManagerStore(enabled=True, project_id=None)
# env vars are cleared at top of file
assert store_no_project._init_errors, "Expected init_errors when project_id is missing"
assert store_no_project._init_errors[0]["code"] == "gcp_project_id_missing"
passed("Init error recorded when project_id is missing")

bundle_no_project = store_no_project.get_secret_bundle("some-ref", "google_ads")
assert bundle_no_project is None
passed("get_secret_bundle returns None when init errors present")

status_no_project = store_no_project.get_secret_status("some-ref", "google_ads")
print(f"  get_secret_status (no project_id) → {status_no_project}")
assert status_no_project["configured"] is False
assert "gcp_project_id_missing" in status_no_project.get("metadata", {}).get("error_codes", [])
passed("get_secret_status returns init_error shape when project_id missing")
record_and_assert_clean("get_secret_status no project", status_no_project)

# ---------------------------------------------------------------------------
# Final: assert no secret markers in any printed output
# ---------------------------------------------------------------------------

print("\n--- Final: secret-safety assertion on all printed outputs ---")

for i, output in enumerate(_all_printed_outputs):
    ok, offending = assert_no_secret_values_in_payload(output)
    if not ok:
        failed(f"Secret marker found in output #{i}: {offending}")

passed(f"All {len(_all_printed_outputs)} printed outputs free of secret markers")

print("\n=== V5.12.3 GCP Secret Manager read mock demo passed. ===\n")

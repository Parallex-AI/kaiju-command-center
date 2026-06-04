"""
V5.12.5 — GCPSecretManagerStore mock delete/list demo.

Validates delete_secret_bundle and list_secret_records with injected mock clients.
No real GCP credentials required. No live GCP calls made.

Mock clients simulate:
  Delete:
    1. Disabled store returns False without any GCP call.
    2. Enabled store calls delete_secret with correct resource name → True.
    3. NotFound on delete_secret → False.
    4. PermissionDenied on delete_secret → False.
  List:
    5. Disabled store returns [].
    6. Enabled store calls list_secrets with correct parent.
    7. list_secrets returns matching and non-matching secrets — only matching are included.
    8. Returned objects are SecretRecord descriptors (no payload access).
    9. access_secret_version is never called.
   10. parse_gcp_secret_id handles valid and invalid IDs.
   11. No secret values appear in any output.

Run from agents/ads-agent/:
  python3 run_gcp_secret_manager_delete_list_mock_demo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Clear GCP env vars before any imports so defaults (kaiju / local) apply.
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
os.environ.pop("GCP_PROJECT_ID", None)
os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
os.environ.pop("GCP_SECRET_MANAGER_PREFIX", None)
os.environ.pop("GCP_SECRET_MANAGER_ENV", None)

from credentials.gcp_secret_manager_store import (
    GCPSecretManagerStore,
    build_gcp_secret_id,
    build_gcp_secret_resource_name,
    parse_gcp_secret_id,
)
from credentials.secret_store import SecretRecord, assert_no_secret_values_in_payload

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

class _MockDeleteSuccessClient:
    """delete_secret succeeds. Records calls by resource name (no secret values)."""

    def __init__(self) -> None:
        self.delete_secret_calls: list = []
        self.access_secret_version_called: bool = False

    def delete_secret(self, request: dict) -> None:
        self.delete_secret_calls.append({"name": request.get("name")})

    def access_secret_version(self, request: dict) -> None:
        self.access_secret_version_called = True
        raise AssertionError("access_secret_version must not be called during delete")


class _MockDeleteNotFoundClient:
    """delete_secret raises NotFound."""

    def delete_secret(self, request: dict) -> None:
        from google.api_core.exceptions import NotFound
        raise NotFound("Secret not found: demo-project/secrets/kaiju-local-...")


class _MockDeletePermissionDeniedClient:
    """delete_secret raises PermissionDenied."""

    def delete_secret(self, request: dict) -> None:
        from google.api_core.exceptions import PermissionDenied
        raise PermissionDenied("Permission denied on delete")


class _MockSecret:
    """Minimal mock of a GCP Secret Manager Secret object."""

    def __init__(self, name: str) -> None:
        self.name = name


class _MockListClient:
    """
    list_secrets returns a fixed iterable of mock secret objects.

    Contains both matching (kaiju-local-*) and non-matching (other prefix/env) names.
    access_secret_version must never be called.
    """

    def __init__(self) -> None:
        self.list_secrets_calls: list = []
        self.access_secret_version_called: bool = False

        # Matching secrets (kaiju-local prefix — matches default env vars).
        self._secrets = [
            _MockSecret("projects/demo-project/secrets/kaiju-local-google_ads-cred_google_ads_abc123"),
            _MockSecret("projects/demo-project/secrets/kaiju-local-google_ads-cred_google_ads_xyz789"),
            # Non-matching: different prefix.
            _MockSecret("projects/demo-project/secrets/other-local-google_ads-cred_google_ads_abc123"),
            # Non-matching: different env.
            _MockSecret("projects/demo-project/secrets/kaiju-prod-google_ads-cred_google_ads_abc123"),
            # Non-matching: incomplete format.
            _MockSecret("projects/demo-project/secrets/kaiju-local-orphan"),
        ]

    def list_secrets(self, request: dict) -> list:
        self.list_secrets_calls.append({"parent": request.get("parent")})
        return self._secrets

    def access_secret_version(self, request: dict) -> None:
        self.access_secret_version_called = True
        raise AssertionError("access_secret_version must not be called during list")


class _MockListEmptyClient:
    """list_secrets returns an empty iterable."""

    def list_secrets(self, request: dict) -> list:
        return []

    def access_secret_version(self, request: dict) -> None:
        raise AssertionError("access_secret_version must not be called during list")


class _MockListErrorClient:
    """list_secrets raises PermissionDenied."""

    def list_secrets(self, request: dict) -> None:
        from google.api_core.exceptions import PermissionDenied
        raise PermissionDenied("Permission denied on list")

    def access_secret_version(self, request: dict) -> None:
        raise AssertionError("access_secret_version must not be called")


# ---------------------------------------------------------------------------
# Section 1 — parse_gcp_secret_id: valid IDs
# ---------------------------------------------------------------------------

section("1/11 — parse_gcp_secret_id: valid IDs match prefix/env")

# Default prefix=kaiju, env=local (env vars cleared above).
valid_id = "kaiju-local-google_ads-cred_google_ads_abc123"
result = parse_gcp_secret_id(valid_id)
assert result["matched"] is True, f"Expected matched=True, got: {result}"
assert result["integration_type"] == "google_ads", f"Wrong integration_type: {result}"
assert result["credential_ref"] == "cred_google_ads_abc123", f"Wrong credential_ref: {result}"
passed(f"parse_gcp_secret_id('{valid_id}') → matched=True, itype=google_ads, ref=cred_google_ads_abc123")

valid_id2 = "kaiju-local-google_ads-cred_google_ads_xyz789"
result2 = parse_gcp_secret_id(valid_id2)
assert result2["matched"] is True
assert result2["credential_ref"] == "cred_google_ads_xyz789"
passed(f"parse_gcp_secret_id('{valid_id2}') → matched=True")

# ---------------------------------------------------------------------------
# Section 2 — parse_gcp_secret_id: non-matching IDs
# ---------------------------------------------------------------------------

section("2/11 — parse_gcp_secret_id: non-matching IDs return matched=False")

for bad_id in [
    "other-local-google_ads-cred_google_ads_abc123",   # wrong prefix
    "kaiju-prod-google_ads-cred_google_ads_abc123",    # wrong env
    "kaiju-local-unknown_type-cred_google_ads_abc123", # unknown integration_type
    "kaiju-local-orphan",                               # missing integration_type segment
    "",                                                 # empty string
    "kaiju-local-google_ads-",                         # empty credential_ref
]:
    r = parse_gcp_secret_id(bad_id)
    assert r["matched"] is False, f"Expected matched=False for {bad_id!r}, got: {r}"
    assert r["integration_type"] is None
    assert r["credential_ref"] is None
    passed(f"parse_gcp_secret_id({bad_id!r}) → matched=False")

# ---------------------------------------------------------------------------
# Section 3 — Disabled delete returns False, no GCP call
# ---------------------------------------------------------------------------

section("3/11 — Disabled store: delete_secret_bundle returns False")

store_disabled = GCPSecretManagerStore(enabled=False)
result_del = store_disabled.delete_secret_bundle("cred_google_ads_abc123", "google_ads")
assert result_del is False, f"Expected False, got: {result_del}"
passed("delete_secret_bundle on disabled store → False (no GCP call)")

# ---------------------------------------------------------------------------
# Section 4 — Disabled list returns []
# ---------------------------------------------------------------------------

section("4/11 — Disabled store: list_secret_records returns []")

result_list = store_disabled.list_secret_records()
assert result_list == [], f"Expected [], got: {result_list}"
passed("list_secret_records on disabled store → []")

result_list_filtered = store_disabled.list_secret_records(integration_type="google_ads")
assert result_list_filtered == []
passed("list_secret_records(integration_type='google_ads') on disabled store → []")

# ---------------------------------------------------------------------------
# Section 5 — Enabled delete success
# ---------------------------------------------------------------------------

section("5/11 — Enabled delete success: calls delete_secret with correct resource name")

delete_client = _MockDeleteSuccessClient()
store_del = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=delete_client,
)

ok = store_del.delete_secret_bundle("cred_google_ads_abc123", "google_ads")
assert ok is True, f"Expected True, got: {ok}"
passed("delete_secret_bundle returned True")

assert len(delete_client.delete_secret_calls) == 1
call = delete_client.delete_secret_calls[0]
expected_secret_id = build_gcp_secret_id("cred_google_ads_abc123", "google_ads")
expected_resource = build_gcp_secret_resource_name("demo-project", expected_secret_id)
assert call["name"] == expected_resource, f"Wrong name: {call['name']!r}, expected: {expected_resource!r}"
passed(f"delete_secret called with correct name={expected_resource!r}")

assert not delete_client.access_secret_version_called
passed("access_secret_version was NOT called during delete")

# ---------------------------------------------------------------------------
# Section 6 — Enabled delete NotFound returns False
# ---------------------------------------------------------------------------

section("6/11 — Enabled delete NotFound: returns False")

store_nf = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=_MockDeleteNotFoundClient(),
)
ok_nf = store_nf.delete_secret_bundle("cred_google_ads_abc123", "google_ads")
assert ok_nf is False, f"Expected False on NotFound, got: {ok_nf}"
passed("delete_secret_bundle returns False on NotFound")

# ---------------------------------------------------------------------------
# Section 7 — Enabled delete PermissionDenied returns False
# ---------------------------------------------------------------------------

section("7/11 — Enabled delete PermissionDenied: returns False")

store_pd = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=_MockDeletePermissionDeniedClient(),
)
ok_pd = store_pd.delete_secret_bundle("cred_google_ads_abc123", "google_ads")
assert ok_pd is False, f"Expected False on PermissionDenied, got: {ok_pd}"
passed("delete_secret_bundle returns False on PermissionDenied")

# ---------------------------------------------------------------------------
# Section 8 — Enabled list calls list_secrets with correct parent
# ---------------------------------------------------------------------------

section("8/11 — Enabled list: calls list_secrets with correct parent")

list_client = _MockListClient()
store_list = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=list_client,
)

records = store_list.list_secret_records()

assert len(list_client.list_secrets_calls) == 1
list_call = list_client.list_secrets_calls[0]
assert list_call["parent"] == "projects/demo-project", (
    f"Wrong parent: {list_call['parent']!r}"
)
passed("list_secrets called with parent='projects/demo-project'")

# ---------------------------------------------------------------------------
# Section 9 — List filters non-matching secrets, returns only matching
# ---------------------------------------------------------------------------

section("9/11 — List filters by prefix/env, returns only matching SecretRecord descriptors")

# 5 secrets in mock: 2 match kaiju-local-google_ads-*, 3 do not.
assert len(records) == 2, f"Expected 2 matching records, got {len(records)}: {records}"
passed(f"list_secret_records returned {len(records)} matching records (3 filtered out)")

for rec in records:
    assert isinstance(rec, SecretRecord), f"Expected SecretRecord, got: {type(rec)}"
    assert rec.integration_type == "google_ads"
    assert rec.configured_fields == [], f"Expected [] for configured_fields, got: {rec.configured_fields}"
    meta = rec.metadata or {}
    assert meta.get("backend") == "gcp_secret_manager"
    assert meta.get("listed") is True
    assert meta.get("secret_id") is not None
    assert "listed" in (meta or {})
    # Print safe descriptor — no secret values.
    rec_dict = {
        "credential_ref": rec.credential_ref,
        "integration_type": rec.integration_type,
        "configured_fields": rec.configured_fields,
        "metadata": rec.metadata,
    }
    print(f"  SecretRecord (safe) → {rec_dict}")
    record_and_assert_clean(f"SecretRecord list item {rec.credential_ref}", rec_dict)
    passed(f"SecretRecord: credential_ref={rec.credential_ref!r}, configured_fields=[]")

assert not list_client.access_secret_version_called
passed("access_secret_version was NOT called during list")

# ---------------------------------------------------------------------------
# Section 10 — List integration_type filter
# ---------------------------------------------------------------------------

section("10/11 — List with integration_type filter")

# Reset client for a second call.
list_client2 = _MockListClient()
store_list2 = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=list_client2,
)

records_filtered = store_list2.list_secret_records(integration_type="google_ads")
assert len(records_filtered) == 2
passed(f"list_secret_records(integration_type='google_ads') → {len(records_filtered)} records")

# Filter for a non-existent integration type.
list_client3 = _MockListClient()
store_list3 = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=list_client3,
)
records_none = store_list3.list_secret_records(integration_type="stripe")
assert records_none == [], f"Expected [] for unknown integration_type, got: {records_none}"
passed("list_secret_records(integration_type='stripe') → [] (no match)")

# Empty client.
store_empty = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=_MockListEmptyClient(),
)
records_empty = store_empty.list_secret_records()
assert records_empty == []
passed("list_secret_records with empty list_secrets response → []")

# PermissionDenied on list_secrets.
store_list_err = GCPSecretManagerStore(
    enabled=True,
    project_id="demo-project",
    client=_MockListErrorClient(),
)
records_err = store_list_err.list_secret_records()
assert records_err == [], f"Expected [] on PermissionDenied, got: {records_err}"
passed("list_secret_records returns [] on PermissionDenied from list_secrets")

# ---------------------------------------------------------------------------
# Section 11 — Secret-safety final check
# ---------------------------------------------------------------------------

section("11/11 — Final secret-safety assertion on all printed outputs")

for i, output in enumerate(_all_printed_outputs):
    ok, offending = assert_no_secret_values_in_payload(output)
    if not ok:
        failed(f"Secret marker found in output #{i}: {offending}")

passed(f"All {len(_all_printed_outputs)} printed outputs free of secret markers")

print("\n=== V5.12.5 GCP Secret Manager delete/list mock demo passed. ===\n")

"""
V5.8 — SecretStore demo (no HTTP server, no disk writes, no real secrets).

Exercises InMemorySecretStore across the full lifecycle: put, status, internal
retrieval, delete, forbidden field rejection, and value-safety assertion.

IMPORTANT: Raw bundle values (developer_token, client_secret, etc.) are
asserted internally but are NEVER printed. All printed output is redacted.
The fake fixture values below are test stand-ins only — they are not real
credentials and are never written to disk or logged.

Usage:
    cd ~/kaiju/agents/ads-agent
    ~/kaiju/.venv/bin/python3 run_secret_store_demo.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from credentials.secret_store import (
    GOOGLE_ADS_SECRET_FIELDS,
    InMemorySecretStore,
    SecretRecord,
    assert_allowed_secret_fields,
    assert_no_secret_values_in_payload,
    make_secret_store_key,
    redact_secret_status,
)

_SEP = "-" * 60

# Fake fixture values for demo/test only. Not real credentials.
_FAKE_BUNDLE = {
    "developer_token": "fake-dev-token",
    "client_id": "fake-client-id",
    "client_secret": "fake-client-secret",
    "refresh_token": "fake-refresh-token",
}
_CRED_REF = "cred_google_ads_demo_abc123"
_INTEGRATION = "google_ads"


def section(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def main() -> None:
    print("V5.8 — SecretStore Demo")

    store = InMemorySecretStore()

    # Collect all printed dicts for final secret-value safety assertion
    printed_outputs = []

    # ------------------------------------------------------------------
    # 1. Status before any bundle is stored
    # ------------------------------------------------------------------
    section("1. get_secret_status — before put (unconfigured)")
    status_before = store.get_secret_status(_CRED_REF, _INTEGRATION)
    print(json.dumps(status_before, indent=2))
    printed_outputs.append(status_before)

    assert status_before["configured"] is False
    assert all(v is False for v in status_before["configured_fields"].values())
    assert status_before["credential_ref"] == _CRED_REF
    print("PASS: configured=false, all fields false before put")

    # ------------------------------------------------------------------
    # 2. Put full bundle — returns SecretRecord only
    # ------------------------------------------------------------------
    section("2. put_secret_bundle — full bundle")
    record = store.put_secret_bundle(_CRED_REF, _INTEGRATION, _FAKE_BUNDLE)
    record_safe = {
        "credential_ref": record.credential_ref,
        "integration_type": record.integration_type,
        "configured_fields": record.configured_fields,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
    print(json.dumps(record_safe, indent=2))
    printed_outputs.append(record_safe)

    assert isinstance(record, SecretRecord)
    assert record.credential_ref == _CRED_REF
    assert record.integration_type == _INTEGRATION
    assert sorted(record.configured_fields) == sorted(GOOGLE_ADS_SECRET_FIELDS)
    assert record.created_at is not None
    print(f"PASS: SecretRecord returned with configured_fields={record.configured_fields}")

    # ------------------------------------------------------------------
    # 3. Get redacted status after put
    # ------------------------------------------------------------------
    section("3. get_secret_status — after put (configured)")
    status_after = store.get_secret_status(_CRED_REF, _INTEGRATION)
    print(json.dumps(status_after, indent=2))
    printed_outputs.append(status_after)

    assert status_after["configured"] is True
    assert all(v is True for v in status_after["configured_fields"].values())
    print("PASS: configured=true, all fields true after put")

    # ------------------------------------------------------------------
    # 4. Internal raw bundle retrieval — assert values, DO NOT print
    # ------------------------------------------------------------------
    section("4. get_secret_bundle — internal retrieval (values not printed)")
    bundle = store.get_secret_bundle(_CRED_REF, _INTEGRATION)
    assert bundle is not None, "Expected bundle to be present"
    assert bundle["developer_token"] == _FAKE_BUNDLE["developer_token"]
    assert bundle["client_id"] == _FAKE_BUNDLE["client_id"]
    assert bundle["client_secret"] == _FAKE_BUNDLE["client_secret"]
    assert bundle["refresh_token"] == _FAKE_BUNDLE["refresh_token"]
    # Deep copy isolation: mutating the returned bundle does not affect the store
    bundle["developer_token"] = "mutated"
    bundle2 = store.get_secret_bundle(_CRED_REF, _INTEGRATION)
    assert bundle2["developer_token"] == _FAKE_BUNDLE["developer_token"], (
        "store must return isolated copies"
    )
    print("PASS: raw bundle retrieved internally (4 fields confirmed, values not printed)")
    print("PASS: deep-copy isolation verified")

    # ------------------------------------------------------------------
    # 5. list_secret_records — SecretRecord only, no values
    # ------------------------------------------------------------------
    section("5. list_secret_records — SecretRecord list")
    records = store.list_secret_records()
    assert len(records) == 1
    r = records[0]
    records_safe = [{
        "credential_ref": r.credential_ref,
        "integration_type": r.integration_type,
        "configured_fields": r.configured_fields,
    }]
    print(json.dumps(records_safe, indent=2))
    printed_outputs.append(records_safe[0])

    assert r.credential_ref == _CRED_REF
    assert r.integration_type == _INTEGRATION
    print(f"PASS: list_secret_records returned 1 record with configured_fields={r.configured_fields}")

    # ------------------------------------------------------------------
    # 6. Delete bundle
    # ------------------------------------------------------------------
    section("6. delete_secret_bundle")
    deleted = store.delete_secret_bundle(_CRED_REF, _INTEGRATION)
    assert deleted is True, "Expected delete to return True"
    print(f"deleted: {deleted}")

    deleted_again = store.delete_secret_bundle(_CRED_REF, _INTEGRATION)
    assert deleted_again is False, "Expected second delete to return False"
    print(f"deleted again: {deleted_again}")
    print("PASS: delete returns True on first call, False on second")

    # ------------------------------------------------------------------
    # 7. Status after delete — unconfigured again
    # ------------------------------------------------------------------
    section("7. get_secret_status — after delete (unconfigured)")
    status_deleted = store.get_secret_status(_CRED_REF, _INTEGRATION)
    print(json.dumps(status_deleted, indent=2))
    printed_outputs.append(status_deleted)

    assert status_deleted["configured"] is False
    assert store.get_secret_bundle(_CRED_REF, _INTEGRATION) is None
    print("PASS: configured=false after delete, get_secret_bundle returns None")

    # ------------------------------------------------------------------
    # 8. Reject forbidden fields
    # ------------------------------------------------------------------
    section("8. put_secret_bundle — reject forbidden fields")
    forbidden_cases = [
        {"developer_token": "x", "access_token": "should-fail"},
        {"developer_token": "x", "oauth_code": "should-fail"},
        {"developer_token": "x", "password": "should-fail"},
        {"developer_token": "x", "authorization": "should-fail"},
        {"developer_token": "x", "auth_header": "should-fail"},
        {"developer_token": "x", "arbitrary_field": "should-fail"},
    ]
    for bad in forbidden_cases:
        try:
            store.put_secret_bundle(_CRED_REF, _INTEGRATION, bad)
            assert False, f"Expected ValueError for: {list(bad.keys())}"
        except ValueError as e:
            err_str = str(e)
            assert "disallowed" in err_str.lower() or "rejected" in err_str.lower() or "disallowed" in err_str.lower(), (
                f"Unexpected error message: {err_str}"
            )
    print(f"PASS: all {len(forbidden_cases)} forbidden field cases raised ValueError")

    # ------------------------------------------------------------------
    # 9. Reject empty values
    # ------------------------------------------------------------------
    section("9. put_secret_bundle — reject empty values")
    empty_cases = [
        {"developer_token": "", "client_id": "x", "client_secret": "x", "refresh_token": "x"},
        {"developer_token": "x", "client_id": "   ", "client_secret": "x", "refresh_token": "x"},
    ]
    for bad in empty_cases:
        try:
            store.put_secret_bundle(_CRED_REF, _INTEGRATION, bad)
            assert False, f"Expected ValueError for empty value in: {list(bad.keys())}"
        except ValueError as e:
            assert "empty" in str(e).lower()
    print(f"PASS: all {len(empty_cases)} empty-value cases raised ValueError")

    # ------------------------------------------------------------------
    # 10. assert_allowed_secret_fields helper
    # ------------------------------------------------------------------
    section("10. assert_allowed_secret_fields — standalone check")
    ok, rejected = assert_allowed_secret_fields(
        {"developer_token": "x", "client_id": "x", "client_secret": "x", "refresh_token": "x"},
        "google_ads",
    )
    assert ok is True and rejected == []
    print(f"PASS: all 4 allowed fields accepted: {ok}, rejected={rejected}")

    ok2, rejected2 = assert_allowed_secret_fields(
        {"developer_token": "x", "access_token": "bad"},
        "google_ads",
    )
    assert ok2 is False and "access_token" in rejected2
    print(f"PASS: forbidden field rejected: ok={ok2}, rejected={rejected2}")

    # ------------------------------------------------------------------
    # 11. redact_secret_status helper — standalone
    # ------------------------------------------------------------------
    section("11. redact_secret_status — standalone")
    partial_status = redact_secret_status(
        "cred_ref_test", "google_ads",
        configured_fields=["developer_token", "client_id"],
    )
    print(json.dumps(partial_status, indent=2))
    printed_outputs.append(partial_status)

    assert partial_status["configured"] is False, "partial bundle must not be configured=true"
    assert partial_status["configured_fields"]["developer_token"] is True
    assert partial_status["configured_fields"]["client_secret"] is False
    print("PASS: partial bundle configured=false, present fields=true, missing fields=false")

    # ------------------------------------------------------------------
    # 12. make_secret_store_key helper
    # ------------------------------------------------------------------
    section("12. make_secret_store_key")
    key = make_secret_store_key("cred_google_ads_abc123", "google_ads")
    print(f"key: {key}")
    assert key == "cred_google_ads_abc123/google_ads"
    print("PASS: key format is credential_ref/integration_type")

    # ------------------------------------------------------------------
    # 13. assert_no_secret_values_in_payload — clean outputs
    # ------------------------------------------------------------------
    section("13. assert_no_secret_values_in_payload — all printed outputs clean")
    for i, output in enumerate(printed_outputs):
        clean, offending = assert_no_secret_values_in_payload(output)
        assert clean, f"Output #{i} contains secret-like value at: {offending}"
    print(f"PASS: all {len(printed_outputs)} printed output dicts contain no secret-like values")

    # ------------------------------------------------------------------
    # 14. assert_no_secret_values_in_payload — detects dirty payload
    # ------------------------------------------------------------------
    section("14. assert_no_secret_values_in_payload — detects dirty payload")
    dirty = {"some_field": "fake-dev-token", "nested": {"token": "fake-client-secret"}}
    clean, offending = assert_no_secret_values_in_payload(dirty)
    assert not clean
    assert "some_field" in offending
    assert "nested.token" in offending
    print(f"PASS: detected secret-like values at: {offending}")

    print(f"\n{_SEP}")
    print("  All assertions passed.")
    print(_SEP)


if __name__ == "__main__":
    main()

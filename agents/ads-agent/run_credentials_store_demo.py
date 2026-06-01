"""
V5.3 — InMemoryCredentialStore demo.

Demonstrates:
- put_reference: store a valid CredentialReference
- get_reference: retrieve it
- get_status: redacted status dict (configured: false for status=missing)
- update_status: status transition to active (configured: true)
- list_references: enumerate stored refs
- delete_reference: remove from store
- missing_credential_status: redacted shape after delete
- secret-metadata rejection: put_reference raises ValueError for unsafe keys
- assert_no_secret_material: direct check including nested dicts
- Unit-style checks for all store operations

No secret values are printed at any point.

Usage:
    cd ~/kaiju/agents/ads-agent
    ~/kaiju/.venv/bin/python3 run_credentials_store_demo.py
"""

import json
import sys
from dataclasses import replace as dc_replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from credentials.models import (
    CredentialStatus,
    IntegrationType,
    create_credential_reference,
    credential_reference_to_redacted_response,
    now_utc_iso,
)
from credentials.store import (
    InMemoryCredentialStore,
    assert_no_secret_material,
    make_store_key,
    missing_credential_status,
)

_SEP = "-" * 60
TENANT = "demo-tenant"
CLIENT = "demo-client"
INTEGRATION = IntegrationType.GOOGLE_ADS.value


def section(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def main() -> None:
    print("V5.3 — InMemoryCredentialStore Demo")

    all_outputs: list = []

    # ------------------------------------------------------------------
    # 1. Create store
    # ------------------------------------------------------------------
    section("1. Create InMemoryCredentialStore")
    store = InMemoryCredentialStore()
    print(f"store type : {type(store).__name__}")
    print("PASS: store created")

    # ------------------------------------------------------------------
    # 2. Create a CredentialReference
    # ------------------------------------------------------------------
    section("2. Create CredentialReference")
    ref = create_credential_reference(
        tenant_id=TENANT,
        client_id=CLIENT,
        integration_type=INTEGRATION,
        customer_id="1234567890",
        metadata={
            "onboarded_by": "admin@kaiju.digital",
            "environment": "staging",
        },
    )
    print(f"tenant_id       : {ref.tenant_id}")
    print(f"client_id       : {ref.client_id}")
    print(f"integration_type: {ref.integration_type}")
    print(f"credential_ref  : {ref.credential_ref}")
    print(f"status          : {ref.status}")
    print(f"customer_id     : {ref.customer_id}")
    assert ref.status == CredentialStatus.MISSING.value
    print("PASS: CredentialReference created with status=missing")

    # ------------------------------------------------------------------
    # 3. put_reference
    # ------------------------------------------------------------------
    section("3. put_reference")
    stored_ref = store.put_reference(ref)
    print(json.dumps(credential_reference_to_redacted_response(stored_ref), indent=2))
    all_outputs.append(credential_reference_to_redacted_response(stored_ref))
    assert stored_ref.tenant_id == ref.tenant_id
    assert stored_ref.credential_ref == ref.credential_ref
    print("PASS: reference stored and returned")

    # ------------------------------------------------------------------
    # 4. get_reference
    # ------------------------------------------------------------------
    section("4. get_reference")
    fetched = store.get_reference(TENANT, CLIENT, INTEGRATION)
    assert fetched is not None
    assert fetched.credential_ref == ref.credential_ref
    assert fetched is not stored_ref, "must return a copy, not the same object"
    print(f"credential_ref  : {fetched.credential_ref}")
    print(f"status          : {fetched.status}")
    print("PASS: get_reference returns a copy with correct values")

    # ------------------------------------------------------------------
    # 5. get_status (status=missing → configured: false)
    # ------------------------------------------------------------------
    section("5. get_status — status=missing, configured: false")
    status_dict = store.get_status(TENANT, CLIENT, INTEGRATION)
    print(json.dumps(status_dict, indent=2))
    all_outputs.append(status_dict)
    assert status_dict["status"] == "missing"
    assert status_dict["configured"] is False
    assert status_dict["credential_ref"] is not None, "stored ref should appear"
    print("PASS: status=missing yields configured: false")

    # ------------------------------------------------------------------
    # 6. update_status → configured
    # ------------------------------------------------------------------
    section("6. update_status → configured")
    updated = store.update_status(TENANT, CLIENT, INTEGRATION, CredentialStatus.CONFIGURED.value)
    assert updated is not None
    assert updated.status == "configured"
    status_after = store.get_status(TENANT, CLIENT, INTEGRATION)
    assert status_after["configured"] is True
    print(f"status     : {updated.status}")
    print(f"configured : {status_after['configured']}")
    print("PASS: configured status yields configured: true")

    # ------------------------------------------------------------------
    # 7. update_status → active with last_validated_at
    # ------------------------------------------------------------------
    section("7. update_status → active")
    validated_at = now_utc_iso()
    active = store.update_status(
        TENANT, CLIENT, INTEGRATION,
        CredentialStatus.ACTIVE.value,
        last_validated_at=validated_at,
    )
    assert active is not None
    status_active = store.get_status(TENANT, CLIENT, INTEGRATION)
    print(json.dumps(status_active, indent=2))
    all_outputs.append(status_active)
    assert active.status == "active"
    assert status_active["configured"] is True
    assert status_active["last_validated_at"] == validated_at
    print("PASS: active status yields configured: true with last_validated_at")

    # ------------------------------------------------------------------
    # 8. list_references
    # ------------------------------------------------------------------
    section("8. list_references")
    refs = store.list_references()
    print(f"count : {len(refs)}")
    assert len(refs) == 1
    print(f"tenant_id : {refs[0].tenant_id}")
    assert refs[0].tenant_id == TENANT

    refs_filtered = store.list_references(tenant_id=TENANT)
    assert len(refs_filtered) == 1

    refs_other = store.list_references(tenant_id="other-tenant")
    assert len(refs_other) == 0

    print("PASS: list_references returns correct count; tenant filter works")

    # ------------------------------------------------------------------
    # 9. delete_reference
    # ------------------------------------------------------------------
    section("9. delete_reference")
    deleted = store.delete_reference(TENANT, CLIENT, INTEGRATION)
    assert deleted is True
    after_delete = store.get_reference(TENANT, CLIENT, INTEGRATION)
    assert after_delete is None
    print(f"deleted : {deleted}")
    print("PASS: delete_reference returns True; get_reference returns None after delete")

    # ------------------------------------------------------------------
    # 10. missing_credential_status after delete
    # ------------------------------------------------------------------
    section("10. get_status after delete — missing")
    missing = store.get_status(TENANT, CLIENT, INTEGRATION)
    print(json.dumps(missing, indent=2))
    all_outputs.append(missing)
    assert missing["status"] == "missing"
    assert missing["configured"] is False
    assert missing["credential_ref"] is None
    assert missing["created_at"] is None
    print("PASS: get_status returns missing_credential_status shape after delete")

    # ------------------------------------------------------------------
    # 11. delete non-existent → False
    # ------------------------------------------------------------------
    section("11. delete_reference — not found")
    not_found = store.delete_reference(TENANT, CLIENT, INTEGRATION)
    assert not_found is False
    print(f"returned : {not_found}")
    print("PASS: delete_reference returns False when not found")

    # ------------------------------------------------------------------
    # 12. put_reference rejects unsafe metadata (refresh_token / client_secret)
    # ------------------------------------------------------------------
    section("12. put_reference — rejects secret-like metadata keys")

    clean_ref = create_credential_reference(
        tenant_id=TENANT,
        client_id=CLIENT,
        integration_type=INTEGRATION,
    )

    bad_meta_ref = dc_replace(
        clean_ref,
        metadata={"refresh_token": "PLACEHOLDER", "client_secret": "PLACEHOLDER"},
    )
    try:
        store.put_reference(bad_meta_ref)
        print("FAIL: should have raised ValueError")
        sys.exit(1)
    except ValueError as exc:
        print(f"Raised ValueError as expected")
        print(f"  message (safe): {str(exc)[:120]}")
        assert "PLACEHOLDER" not in str(exc), "error message must not echo secret values"
        print("PASS: put_reference rejects ref with refresh_token/client_secret in metadata")

    # Confirm the bad ref was NOT stored
    assert store.get_reference(TENANT, CLIENT, INTEGRATION) is None
    print("PASS: store is unmodified after rejected put")

    # ------------------------------------------------------------------
    # 13. assert_no_secret_material — flat and nested detection
    # ------------------------------------------------------------------
    section("13. assert_no_secret_material — flat and nested")

    clean_payload = {"onboarded_by": "admin", "environment": "staging", "region": "us-east-1"}
    clean, offending = assert_no_secret_material(clean_payload)
    assert clean is True
    assert offending == []
    print(f"clean payload   → clean={clean}, offending={offending}")
    print("PASS: clean payload passes")

    flat_payload = {"refresh_token": "PLACEHOLDER", "client_secret": "PLACEHOLDER"}
    clean2, offending2 = assert_no_secret_material(flat_payload)
    assert clean2 is False
    assert "refresh_token" in offending2
    assert "client_secret" in offending2
    print(f"flat secrets    → clean={clean2}, offending={offending2}")
    print("PASS: flat secret keys detected")

    nested_payload = {
        "config": {
            "refresh_token": "PLACEHOLDER",
            "client_secret": "PLACEHOLDER",
        },
        "label": "test",
    }
    clean3, offending3 = assert_no_secret_material(nested_payload)
    assert clean3 is False
    assert "config.refresh_token" in offending3
    assert "config.client_secret" in offending3
    print(f"nested secrets  → clean={clean3}, offending={offending3}")
    print("PASS: nested secret keys detected with full path")

    # ------------------------------------------------------------------
    # 14. Unit-style checks
    # ------------------------------------------------------------------
    section("14. Unit-Style Checks")

    # make_store_key is deterministic
    k1 = make_store_key("t1", "c1", "google_ads")
    k2 = make_store_key("t1", "c1", "google_ads")
    assert k1 == k2
    assert k1 == "t1/c1/google_ads"
    print("PASS: make_store_key is deterministic")

    # Different inputs produce different keys
    k3 = make_store_key("t2", "c1", "google_ads")
    assert k1 != k3
    print("PASS: make_store_key distinguishes different tenant_ids")

    # get_reference on empty store returns None
    empty_store = InMemoryCredentialStore()
    assert empty_store.get_reference("x", "y", "google_ads") is None
    print("PASS: get_reference on empty store returns None")

    # get_status on empty store returns missing shape
    missing_shape = empty_store.get_status("x", "y", "google_ads")
    assert missing_shape["status"] == "missing"
    assert missing_shape["configured"] is False
    assert missing_shape["credential_ref"] is None
    print("PASS: get_status on empty store returns missing shape with configured: false")

    # update_status on non-existent returns None
    assert empty_store.update_status("x", "y", "google_ads", "active") is None
    print("PASS: update_status on non-existent returns None")

    # put and get round-trip
    r = create_credential_reference(tenant_id="t1", client_id="c1", integration_type="google_ads")
    empty_store.put_reference(r)
    got = empty_store.get_reference("t1", "c1", "google_ads")
    assert got is not None
    assert got.credential_ref == r.credential_ref
    print("PASS: put_reference stores; get_reference retrieves correct ref")

    # get_status after put with status=missing → configured: false
    s = empty_store.get_status("t1", "c1", "google_ads")
    assert s["status"] == "missing"
    assert s["configured"] is False
    print("PASS: get_status after put with status=missing returns configured: false")

    # update_status → active → configured: true
    empty_store.update_status("t1", "c1", "google_ads", "active")
    s2 = empty_store.get_status("t1", "c1", "google_ads")
    assert s2["configured"] is True
    assert s2["status"] == "active"
    print("PASS: update_status to active → configured: true")

    # list_references
    ls = empty_store.list_references()
    assert len(ls) == 1
    ls_filtered = empty_store.list_references(tenant_id="t1")
    assert len(ls_filtered) == 1
    ls_none = empty_store.list_references(tenant_id="nobody")
    assert len(ls_none) == 0
    print("PASS: list_references returns correct refs and respects tenant filter")

    # delete_reference → True, then False
    assert empty_store.delete_reference("t1", "c1", "google_ads") is True
    assert empty_store.delete_reference("t1", "c1", "google_ads") is False
    print("PASS: delete_reference returns True then False on repeat")

    # assert_no_secret_material detects nested keys
    nested_test = {"outer": {"refresh_token": "P", "client_secret": "P"}}
    ok_flag, paths = assert_no_secret_material(nested_test)
    assert ok_flag is False
    assert any("refresh_token" in p for p in paths)
    assert any("client_secret" in p for p in paths)
    print("PASS: assert_no_secret_material detects nested refresh_token/client_secret")

    # put_reference rejects unsafe metadata
    base = create_credential_reference(tenant_id="t2", client_id="c2", integration_type="google_ads")
    unsafe = dc_replace(base, metadata={"refresh_token": "PLACEHOLDER"})
    fresh_store = InMemoryCredentialStore()
    try:
        fresh_store.put_reference(unsafe)
        print("FAIL: should have raised ValueError")
        sys.exit(1)
    except ValueError:
        pass
    assert fresh_store.get_reference("t2", "c2", "google_ads") is None
    print("PASS: put_reference rejects unsafe metadata and leaves store unmodified")

    # ------------------------------------------------------------------
    # 15. Secret-safety assertion — no secret values in any output
    # ------------------------------------------------------------------
    section("15. Secret-Safety Assertion")
    combined = json.dumps(all_outputs)
    forbidden_values = [
        "PLACEHOLDER",
        "this-should-be-filtered",
        "also-filtered",
    ]
    for val in forbidden_values:
        assert val not in combined, f"Secret-like value leaked into output: {val}"
    print("PASS: no secret-like values present in any collected output")

    print(f"\n{_SEP}")
    print("  All assertions passed.")
    print(_SEP)


if __name__ == "__main__":
    main()

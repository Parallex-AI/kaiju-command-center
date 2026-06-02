"""
V5.4 — LocalFileCredentialReferenceStore demo.

Demonstrates:
- put_reference: persist a CredentialReference to a JSON file
- get_reference: read it back
- get_status: redacted status dict (configured: false for status=missing)
- update_status: transition to active (configured: true)
- list_references: enumerate with tenant filter
- delete_reference: remove from file
- missing_credential_status: redacted shape after delete
- file existence and content verification (no secret-like keys in JSON)
- unsafe-metadata rejection via ValueError
- unit-style checks for all operations
- cleanup: temp file removed at end

No secret values are printed at any point.

Usage:
    cd ~/kaiju/agents/ads-agent
    ~/kaiju/.venv/bin/python3 run_credentials_local_file_store_demo.py
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
from credentials.local_file_store import (
    LocalFileCredentialReferenceStore,
    dict_to_credential_reference,
    get_default_credential_reference_store_path,
    load_reference_store_file,
    write_reference_store_file,
)
from credentials.store import assert_no_secret_material, missing_credential_status

_SEP = "-" * 60
TENANT = "demo-tenant"
CLIENT = "demo-client"
INTEGRATION = IntegrationType.GOOGLE_ADS.value
DEMO_PATH = Path("/tmp/kaiju-credential-reference-store-demo.json")


def section(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def main() -> None:
    # Remove any leftover from a previous run
    if DEMO_PATH.exists():
        DEMO_PATH.unlink()

    print("V5.4 — LocalFileCredentialReferenceStore Demo")
    print(f"Store path: {DEMO_PATH}")

    all_outputs: list = []

    # ------------------------------------------------------------------
    # 1. Create store
    # ------------------------------------------------------------------
    section("1. Create LocalFileCredentialReferenceStore")
    store = LocalFileCredentialReferenceStore(path=DEMO_PATH)
    print(f"store type  : {type(store).__name__}")
    print(f"store path  : {store.store_path}")
    assert not DEMO_PATH.exists(), "file must not exist before first write"
    print("PASS: store created; file does not yet exist")

    # ------------------------------------------------------------------
    # 2. Create CredentialReference
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
    assert ref.status == CredentialStatus.MISSING.value
    print("PASS: CredentialReference created with status=missing")

    # ------------------------------------------------------------------
    # 3. put_reference — file is created
    # ------------------------------------------------------------------
    section("3. put_reference — persists to file")
    stored = store.put_reference(ref)
    assert DEMO_PATH.exists(), "file must exist after first put"
    print(f"file exists : {DEMO_PATH.exists()}")
    print(json.dumps(credential_reference_to_redacted_response(stored), indent=2))
    all_outputs.append(credential_reference_to_redacted_response(stored))
    assert stored.credential_ref == ref.credential_ref
    print("PASS: reference persisted; file created")

    # ------------------------------------------------------------------
    # 4. Verify JSON file structure and no secret-like keys
    # ------------------------------------------------------------------
    section("4. Verify JSON file — structure and no secret-like keys")
    raw_data = json.loads(DEMO_PATH.read_text())
    print(f"version     : {raw_data.get('version')}")
    print(f"ref count   : {len(raw_data.get('references', {}))}")
    assert raw_data["version"] == 1
    assert len(raw_data["references"]) == 1

    for ref_dict in raw_data["references"].values():
        clean, offending = assert_no_secret_material(ref_dict)
        assert clean, f"Secret-like keys found in stored JSON: {offending}"
        print(f"ref keys    : {sorted(ref_dict.keys())}")

    print("PASS: JSON file has correct structure; no secret-like keys in stored reference")

    # ------------------------------------------------------------------
    # 5. get_reference — survives process restart simulation
    # ------------------------------------------------------------------
    section("5. get_reference — reads from file")
    fresh_store = LocalFileCredentialReferenceStore(path=DEMO_PATH)
    fetched = fresh_store.get_reference(TENANT, CLIENT, INTEGRATION)
    assert fetched is not None
    assert fetched.credential_ref == ref.credential_ref
    assert fetched.tenant_id == TENANT
    print(f"credential_ref  : {fetched.credential_ref}")
    print(f"status          : {fetched.status}")
    print("PASS: get_reference reads correct value from file")

    # ------------------------------------------------------------------
    # 6. get_status (configured: false for status=missing)
    # ------------------------------------------------------------------
    section("6. get_status — status=missing, configured: false")
    status = store.get_status(TENANT, CLIENT, INTEGRATION)
    print(json.dumps(status, indent=2))
    all_outputs.append(status)
    assert status["status"] == "missing"
    assert status["configured"] is False
    assert status["credential_ref"] is not None
    print("PASS: status=missing yields configured: false")

    # ------------------------------------------------------------------
    # 7. update_status → active
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

    # Confirm the update is persisted in the file
    reloaded = fresh_store.get_reference(TENANT, CLIENT, INTEGRATION)
    assert reloaded is not None
    assert reloaded.status == "active"
    print("PASS: active status persisted; fresh store read confirms update")

    # ------------------------------------------------------------------
    # 8. list_references
    # ------------------------------------------------------------------
    section("8. list_references")
    refs = store.list_references()
    assert len(refs) == 1
    refs_by_tenant = store.list_references(tenant_id=TENANT)
    assert len(refs_by_tenant) == 1
    refs_other = store.list_references(tenant_id="other-tenant")
    assert len(refs_other) == 0
    print(f"total refs      : {len(refs)}")
    print(f"by tenant       : {len(refs_by_tenant)}")
    print(f"by other tenant : {len(refs_other)}")
    print("PASS: list_references returns correct counts; tenant filter works")

    # ------------------------------------------------------------------
    # 9. delete_reference
    # ------------------------------------------------------------------
    section("9. delete_reference")
    deleted = store.delete_reference(TENANT, CLIENT, INTEGRATION)
    assert deleted is True
    after = store.get_reference(TENANT, CLIENT, INTEGRATION)
    assert after is None
    print(f"deleted  : {deleted}")
    print("PASS: delete_reference returns True; get_reference returns None")

    # ------------------------------------------------------------------
    # 10. get_status after delete — missing shape
    # ------------------------------------------------------------------
    section("10. get_status after delete — missing")
    missing = store.get_status(TENANT, CLIENT, INTEGRATION)
    print(json.dumps(missing, indent=2))
    all_outputs.append(missing)
    assert missing["status"] == "missing"
    assert missing["configured"] is False
    assert missing["credential_ref"] is None
    assert missing["created_at"] is None
    print("PASS: missing_credential_status shape returned after delete")

    # ------------------------------------------------------------------
    # 11. put_reference rejects secret-like metadata
    # ------------------------------------------------------------------
    section("11. put_reference — rejects secret-like metadata keys")
    clean_ref = create_credential_reference(
        tenant_id=TENANT, client_id=CLIENT, integration_type=INTEGRATION,
    )
    bad_ref = dc_replace(
        clean_ref,
        metadata={"refresh_token": "PLACEHOLDER", "client_secret": "PLACEHOLDER"},
    )
    try:
        store.put_reference(bad_ref)
        print("FAIL: should have raised ValueError")
        sys.exit(1)
    except ValueError as exc:
        print(f"Raised ValueError as expected")
        assert "PLACEHOLDER" not in str(exc)
        print("PASS: put_reference rejects ref with secret-like metadata keys")
    assert store.get_reference(TENANT, CLIENT, INTEGRATION) is None
    print("PASS: store is unmodified after rejected put")

    # ------------------------------------------------------------------
    # 12. Unit-style checks
    # ------------------------------------------------------------------
    section("12. Unit-Style Checks")

    # Missing file returns empty store
    missing_path = Path("/tmp/kaiju-crs-missing-file-test.json")
    if missing_path.exists():
        missing_path.unlink()
    empty = load_reference_store_file(missing_path)
    assert empty == {"version": 1, "references": {}}
    print("PASS: missing file returns empty store structure")

    # Invalid JSON raises safe ValueError
    bad_json_path = Path("/tmp/kaiju-crs-bad-json.json")
    bad_json_path.write_text("{not valid json", encoding="utf-8")
    try:
        load_reference_store_file(bad_json_path)
        print("FAIL: should have raised ValueError")
        sys.exit(1)
    except ValueError as exc:
        assert "invalid JSON" in str(exc) or "Credential reference store" in str(exc)
        print(f"PASS: invalid JSON raises ValueError: {str(exc)[:80]}")
    finally:
        bad_json_path.unlink(missing_ok=True)

    # put/get round-trip on fresh store
    fresh_path = Path("/tmp/kaiju-crs-unit-test.json")
    if fresh_path.exists():
        fresh_path.unlink()
    unit_store = LocalFileCredentialReferenceStore(path=fresh_path)
    r = create_credential_reference(tenant_id="t1", client_id="c1", integration_type="google_ads")
    unit_store.put_reference(r)
    got = unit_store.get_reference("t1", "c1", "google_ads")
    assert got is not None
    assert got.credential_ref == r.credential_ref
    print("PASS: put/get round-trip works on fresh file")

    # update_status active → configured: true
    unit_store.update_status("t1", "c1", "google_ads", "active")
    s = unit_store.get_status("t1", "c1", "google_ads")
    assert s["status"] == "active"
    assert s["configured"] is True
    print("PASS: update_status to active → configured: true")

    # list by tenant filter
    r2 = create_credential_reference(tenant_id="t2", client_id="c2", integration_type="google_ads")
    unit_store.put_reference(r2)
    all_refs = unit_store.list_references()
    assert len(all_refs) == 2
    t1_refs = unit_store.list_references(tenant_id="t1")
    assert len(t1_refs) == 1
    t2_refs = unit_store.list_references(tenant_id="t2")
    assert len(t2_refs) == 1
    print("PASS: list_references tenant filter works with multiple tenants")

    # delete works
    assert unit_store.delete_reference("t1", "c1", "google_ads") is True
    assert unit_store.delete_reference("t1", "c1", "google_ads") is False
    assert unit_store.get_reference("t1", "c1", "google_ads") is None
    print("PASS: delete_reference returns True then False; reference gone from file")

    # Persisted JSON contains no forbidden key substrings in reference dicts
    raw = json.loads(fresh_path.read_text())
    for ref_dict in raw["references"].values():
        clean_flag, offending_paths = assert_no_secret_material(ref_dict)
        assert clean_flag, f"Secret-like keys in persisted JSON: {offending_paths}"
    print("PASS: persisted JSON reference dicts contain no forbidden key substrings")

    # unsafe metadata rejected on unit store
    unsafe = dc_replace(r2, metadata={"client_secret": "PLACEHOLDER"})
    try:
        unit_store.put_reference(unsafe)
        print("FAIL: should have raised ValueError")
        sys.exit(1)
    except ValueError:
        pass
    print("PASS: unsafe metadata rejected on LocalFileCredentialReferenceStore")

    # Clean up unit-test file
    fresh_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # 13. get_default_credential_reference_store_path
    # ------------------------------------------------------------------
    section("13. get_default_credential_reference_store_path")
    import os as _os
    _os.environ.pop("CREDENTIAL_REFERENCE_STORE_PATH", None)
    default_path = get_default_credential_reference_store_path()
    print(f"default path : {default_path}")
    assert "runtime" in str(default_path)
    assert "credential-references" in str(default_path)
    assert default_path.name == "credential_references.json"
    print("PASS: default path contains expected components")

    env_path = Path("/tmp/kaiju-env-override-test.json")
    _os.environ["CREDENTIAL_REFERENCE_STORE_PATH"] = str(env_path)
    env_result = get_default_credential_reference_store_path()
    assert env_result == env_path
    _os.environ.pop("CREDENTIAL_REFERENCE_STORE_PATH", None)
    print("PASS: CREDENTIAL_REFERENCE_STORE_PATH env var override works")

    # ------------------------------------------------------------------
    # 14. Secret-safety assertion — no secret values in any output
    # ------------------------------------------------------------------
    section("14. Secret-Safety Assertion")
    combined = json.dumps(all_outputs)
    forbidden_values = ["PLACEHOLDER", "this-should-be-filtered"]
    for val in forbidden_values:
        assert val not in combined, f"Secret-like value leaked into output: {val}"
    print("PASS: no secret-like values in any collected output")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    section("Cleanup")
    DEMO_PATH.unlink(missing_ok=True)
    assert not DEMO_PATH.exists()
    print(f"Removed demo file: {DEMO_PATH}")
    print("PASS: temp file cleaned up")

    print(f"\n{_SEP}")
    print("  All assertions passed.")
    print(_SEP)


if __name__ == "__main__":
    main()

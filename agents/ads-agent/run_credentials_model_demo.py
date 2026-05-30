"""
V5.2 — CredentialReference model demo.

Demonstrates:
- Creating a CredentialReference for a tenant/client pair
- Metadata filtering (unsafe keys are silently dropped)
- Full safe dict output
- Redacted API response shape
- Validation result
- Status update to 'active' (configured: true)
- Invalid status and integration_type rejection
- No secret values are printed at any point

Usage:
    cd ~/kaiju/agents/ads-agent
    ~/kaiju/.venv/bin/python3 run_credentials_model_demo.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from credentials.models import (
    CredentialStatus,
    IntegrationType,
    create_credential_reference,
    credential_reference_to_dict,
    credential_reference_to_redacted_response,
    filter_safe_metadata,
    update_credential_status,
    validate_credential_reference,
)

_SEP = "-" * 60


def section(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def main() -> None:
    print("V5.2 — CredentialReference Model Demo")

    # ------------------------------------------------------------------
    # 1. Create a CredentialReference with mixed safe/unsafe metadata
    # ------------------------------------------------------------------
    section("1. Create CredentialReference")

    mixed_metadata = {
        "onboarded_by": "admin@kaiju.digital",
        "notes": "Internal beta client",
        "refresh_token": "this-should-be-filtered",
        "client_secret": "also-filtered",
        "authorization": "Bearer also-filtered",
        "oauth_code": "filtered-too",
        "environment": "staging",
        "region": "us-east-1",
        "access_level": "filtered-because-access",
    }

    ref = create_credential_reference(
        tenant_id="Demo Tenant",
        client_id="Demo Client",
        integration_type=IntegrationType.GOOGLE_ADS.value,
        customer_id="1234567890",
        login_customer_id=None,
        status=CredentialStatus.MISSING.value,
        metadata=mixed_metadata,
    )

    print(f"tenant_id       : {ref.tenant_id}")
    print(f"client_id       : {ref.client_id}")
    print(f"integration_type: {ref.integration_type}")
    print(f"credential_ref  : {ref.credential_ref}")
    print(f"customer_id     : {ref.customer_id}")
    print(f"status          : {ref.status}")
    print(f"created_at      : {ref.created_at}")

    # ------------------------------------------------------------------
    # 2. Show metadata filtering
    # ------------------------------------------------------------------
    section("2. Metadata Filtering")

    print("Input keys :", sorted(mixed_metadata.keys()))
    print("Safe keys  :", sorted(ref.metadata.keys()) if ref.metadata else [])

    unsafe_keys_filtered = [
        k for k in mixed_metadata if k not in (ref.metadata or {})
    ]
    print("Filtered   :", sorted(unsafe_keys_filtered))

    assert "refresh_token" not in (ref.metadata or {}), "refresh_token must be filtered"
    assert "client_secret" not in (ref.metadata or {}), "client_secret must be filtered"
    assert "authorization" not in (ref.metadata or {}), "authorization must be filtered"
    assert "oauth_code" not in (ref.metadata or {}), "oauth_code must be filtered"
    assert "access_level" not in (ref.metadata or {}), "access_level must be filtered"
    assert "onboarded_by" in (ref.metadata or {}), "safe key must be preserved"
    assert "environment" in (ref.metadata or {}), "safe key must be preserved"
    print("PASS: all unsafe keys filtered, safe keys preserved")

    # ------------------------------------------------------------------
    # 3. Full safe dict
    # ------------------------------------------------------------------
    section("3. Full Safe Dict")
    safe_dict = credential_reference_to_dict(ref)
    print(json.dumps(safe_dict, indent=2))

    # ------------------------------------------------------------------
    # 4. Redacted API response (status=missing → configured: false)
    # ------------------------------------------------------------------
    section("4. Redacted API Response (status=missing)")
    response = credential_reference_to_redacted_response(ref)
    print(json.dumps(response, indent=2))

    assert response["configured"] is False, "missing status must yield configured: false"
    print("PASS: configured is false for status=missing")

    # ------------------------------------------------------------------
    # 5. Validation — valid ref
    # ------------------------------------------------------------------
    section("5. Validation — Valid Reference")
    ok, errors = validate_credential_reference(ref)
    print(f"valid  : {ok}")
    print(f"errors : {errors}")
    assert ok is True, "valid ref must pass validation"
    assert errors == [], "no errors expected"
    print("PASS: valid CredentialReference passes validation")

    # ------------------------------------------------------------------
    # 6. Update status to active → configured: true
    # ------------------------------------------------------------------
    section("6. Update Status → active")
    from credentials.models import now_utc_iso
    validated_at = now_utc_iso()
    active_ref = update_credential_status(
        ref,
        status=CredentialStatus.ACTIVE.value,
        last_validated_at=validated_at,
    )
    active_response = credential_reference_to_redacted_response(active_ref)
    print(f"status          : {active_ref.status}")
    print(f"configured      : {active_response['configured']}")
    print(f"last_validated_at: {active_ref.last_validated_at}")
    assert active_ref.status == "active", "status must be active"
    assert active_response["configured"] is True, "active status must yield configured: true"
    print("PASS: status=active yields configured: true")

    # ------------------------------------------------------------------
    # 7. Validation — invalid status
    # ------------------------------------------------------------------
    section("7. Validation — Invalid Status")
    from dataclasses import replace as dc_replace
    bad_status_ref = dc_replace(ref, status="flying")
    ok2, errors2 = validate_credential_reference(bad_status_ref)
    print(f"valid  : {ok2}")
    print(f"errors : {json.dumps(errors2, indent=2)}")
    assert ok2 is False, "invalid status must fail validation"
    assert any(e["field"] == "status" for e in errors2), "error must reference status field"
    print("PASS: invalid status fails validation")

    # ------------------------------------------------------------------
    # 8. Validation — invalid integration_type
    # ------------------------------------------------------------------
    section("8. Validation — Invalid Integration Type")
    bad_type_ref = dc_replace(ref, integration_type="fax_machine")
    ok3, errors3 = validate_credential_reference(bad_type_ref)
    print(f"valid  : {ok3}")
    print(f"errors : {json.dumps(errors3, indent=2)}")
    assert ok3 is False, "invalid integration_type must fail validation"
    assert any(e["field"] == "integration_type" for e in errors3)
    print("PASS: invalid integration_type fails validation")

    # ------------------------------------------------------------------
    # 9. update_credential_status rejects invalid status
    # ------------------------------------------------------------------
    section("9. update_credential_status — Invalid Status Rejected")
    try:
        update_credential_status(ref, status="launched")
        print("FAIL: should have raised ValueError")
        sys.exit(1)
    except ValueError as exc:
        print(f"Raised ValueError as expected: {exc}")
        print("PASS")

    # ------------------------------------------------------------------
    # 10. Secret-safety assertion — no secret values in any output
    # ------------------------------------------------------------------
    section("10. Secret-Safety Assertion")
    all_output = json.dumps(safe_dict) + json.dumps(response) + json.dumps(active_response)
    secret_values = [
        "this-should-be-filtered",
        "also-filtered",
        "Bearer also-filtered",
        "filtered-too",
        "filtered-because-access",
    ]
    for val in secret_values:
        assert val not in all_output, f"Secret value leaked into output: {val}"
    print("PASS: no secret values present in any output dict")

    print(f"\n{_SEP}")
    print("  All assertions passed.")
    print(_SEP)


if __name__ == "__main__":
    main()

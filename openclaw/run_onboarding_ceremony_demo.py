"""
V5.20 Phase 3 — Onboarding approval ceremony validator demo/test script.

Verifies validate_onboarding_ceremony() across all 36 test cases:
valid pass, individual field failures, forbidden field/value detection,
sanitized_summary exclusions, multi-failure, and required_actions contract.

Pure local logic — no GCP, no Google Ads API, no real credentials,
no env var reads, no network, no filesystem I/O.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in sys.path:
    sys.path.insert(0, _OPENCLAW_DIR)

from onboarding_ceremony import (
    ChecklistDecision,
    ChecklistFailureCode,
    OnboardingCeremonyInput,
    validate_onboarding_ceremony,
)

_PASS = "[PASS]"
_FAIL = "[FAIL]"
_failures: list = []


def _assert(condition: bool, label: str) -> bool:
    tag = _PASS if condition else _FAIL
    print(f"  {tag} {label}")
    if not condition:
        _failures.append(label)
    return condition


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_FUTURE = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
_PAST = "2020-01-01T00:00:00Z"


def _valid(**overrides) -> OnboardingCeremonyInput:
    base = dict(
        operator_label="demo-operator",
        tenant_id="demo-tenant",
        client_id="demo-client",
        integration_type="google_ads",
        intended_operation="credential_onboarding",
        approval_scope="read-only live validation for demo-tenant/demo-client",
        risk_acknowledgement="Operator acknowledges real credentials will enter the system",
        rollback_plan_present=True,
        emergency_revoke_plan_present=True,
        evidence_location="ticket-KAIJU-001",
        approved_at="2026-08-20T10:00:00Z",
        expires_at=_FUTURE,
        approval_status="APPROVED",
        audit_enabled=True,
        smoke_tests_passed=True,
        preflight_available=True,
        live_gate_available=True,
        revoke_path_available=True,
        credential_intake_boundary_confirmed=True,
        oauth_boundary_design_only=True,
        live_flag_false_confirmed=True,
        real_credentials_present=False,
        google_ads_api_called=False,
        gcp_commands_used=False,
        evidence={"safe_note": "preflight PASS, rollback rehearsed"},
        metadata={"smoke_result": "26/26 PASS"},
    )
    base.update(overrides)
    return OnboardingCeremonyInput(**base)


# ---------------------------------------------------------------------------
# Test 1 — valid ceremony passes
# ---------------------------------------------------------------------------
print("\n── Test 1: valid ceremony passes")
result = validate_onboarding_ceremony(_valid())
_assert(result.ok is True, "valid: ok=True")
_assert(result.decision == ChecklistDecision.PASS, "valid: decision=PASS")
_assert(result.failure_codes == [], "valid: no failure_codes")
_assert(result.required_actions == [], "valid: required_actions empty on pass")

# ---------------------------------------------------------------------------
# Test 2 — missing operator_label fails
# ---------------------------------------------------------------------------
print("\n── Test 2: missing operator_label fails")
result = validate_onboarding_ceremony(_valid(operator_label="  "))
_assert(result.ok is False, "no-operator: ok=False")
_assert(ChecklistFailureCode.OPERATOR_LABEL_MISSING in result.failure_codes,
        "no-operator: operator_label_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 3 — missing tenant fails
# ---------------------------------------------------------------------------
print("\n── Test 3: missing tenant fails")
result = validate_onboarding_ceremony(_valid(tenant_id=""))
_assert(result.ok is False, "no-tenant: ok=False")
_assert(ChecklistFailureCode.TENANT_MISSING in result.failure_codes,
        "no-tenant: tenant_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 4 — missing client fails
# ---------------------------------------------------------------------------
print("\n── Test 4: missing client fails")
result = validate_onboarding_ceremony(_valid(client_id=""))
_assert(result.ok is False, "no-client: ok=False")
_assert(ChecklistFailureCode.CLIENT_MISSING in result.failure_codes,
        "no-client: client_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 5 — invalid integration fails
# ---------------------------------------------------------------------------
print("\n── Test 5: invalid integration fails")
result = validate_onboarding_ceremony(_valid(integration_type="facebook_ads"))
_assert(result.ok is False, "bad-integration: ok=False")
_assert(ChecklistFailureCode.INTEGRATION_INVALID in result.failure_codes,
        "bad-integration: integration_invalid in failure_codes")

# ---------------------------------------------------------------------------
# Test 6 — invalid operation fails
# ---------------------------------------------------------------------------
print("\n── Test 6: invalid operation fails")
result = validate_onboarding_ceremony(_valid(intended_operation="delete_everything"))
_assert(result.ok is False, "bad-operation: ok=False")
_assert(ChecklistFailureCode.OPERATION_INVALID in result.failure_codes,
        "bad-operation: operation_invalid in failure_codes")

# ---------------------------------------------------------------------------
# Test 7 — missing approval_scope fails
# ---------------------------------------------------------------------------
print("\n── Test 7: missing approval_scope fails")
result = validate_onboarding_ceremony(_valid(approval_scope=""))
_assert(result.ok is False, "no-scope: ok=False")
_assert(ChecklistFailureCode.APPROVAL_SCOPE_MISSING in result.failure_codes,
        "no-scope: approval_scope_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 8 — missing risk_acknowledgement fails
# ---------------------------------------------------------------------------
print("\n── Test 8: missing risk_acknowledgement fails")
result = validate_onboarding_ceremony(_valid(risk_acknowledgement="   "))
_assert(result.ok is False, "no-ack-field: ok=False")
_assert(ChecklistFailureCode.RISK_ACKNOWLEDGEMENT_MISSING in result.failure_codes,
        "no-ack-field: risk_acknowledgement_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 9 — missing rollback plan fails
# ---------------------------------------------------------------------------
print("\n── Test 9: missing rollback plan fails")
result = validate_onboarding_ceremony(_valid(rollback_plan_present=False))
_assert(result.ok is False, "no-rollback: ok=False")
_assert(ChecklistFailureCode.ROLLBACK_PLAN_MISSING in result.failure_codes,
        "no-rollback: rollback_plan_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 10 — missing emergency revoke plan fails
# ---------------------------------------------------------------------------
print("\n── Test 10: missing emergency revoke plan fails")
result = validate_onboarding_ceremony(_valid(emergency_revoke_plan_present=False))
_assert(result.ok is False, "no-emergency-revoke: ok=False")
_assert(ChecklistFailureCode.EMERGENCY_REVOKE_PLAN_MISSING in result.failure_codes,
        "no-emergency-revoke: emergency_revoke_plan_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 11 — missing evidence location fails
# ---------------------------------------------------------------------------
print("\n── Test 11: missing evidence location fails")
result = validate_onboarding_ceremony(_valid(evidence_location=""))
_assert(result.ok is False, "no-evidence-loc: ok=False")
_assert(ChecklistFailureCode.EVIDENCE_LOCATION_MISSING in result.failure_codes,
        "no-evidence-loc: evidence_location_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 12 — missing approved_at fails
# ---------------------------------------------------------------------------
print("\n── Test 12: missing approved_at fails")
result = validate_onboarding_ceremony(_valid(approved_at=None))
_assert(result.ok is False, "no-approved-at: ok=False")
_assert(ChecklistFailureCode.APPROVED_AT_MISSING in result.failure_codes,
        "no-approved-at: approved_at_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 13 — missing expires_at fails
# ---------------------------------------------------------------------------
print("\n── Test 13: missing expires_at fails")
result = validate_onboarding_ceremony(_valid(expires_at=None))
_assert(result.ok is False, "no-expires-at: ok=False")
_assert(ChecklistFailureCode.EXPIRES_AT_MISSING in result.failure_codes,
        "no-expires-at: expires_at_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 14 — approval_status PENDING fails
# ---------------------------------------------------------------------------
print("\n── Test 14: approval_status PENDING fails")
result = validate_onboarding_ceremony(_valid(approval_status="PENDING"))
_assert(result.ok is False, "PENDING: ok=False")
_assert(ChecklistFailureCode.APPROVAL_NOT_APPROVED in result.failure_codes,
        "PENDING: approval_not_approved in failure_codes")

# ---------------------------------------------------------------------------
# Test 15 — approval_status REVOKED fails
# ---------------------------------------------------------------------------
print("\n── Test 15: approval_status REVOKED fails")
result = validate_onboarding_ceremony(_valid(approval_status="REVOKED"))
_assert(result.ok is False, "REVOKED: ok=False")
_assert(ChecklistFailureCode.APPROVAL_NOT_APPROVED in result.failure_codes,
        "REVOKED: approval_not_approved in failure_codes")

# ---------------------------------------------------------------------------
# Test 16 — expired approval fails
# ---------------------------------------------------------------------------
print("\n── Test 16: expired approval fails")
result = validate_onboarding_ceremony(
    _valid(expires_at=_PAST),
    now="2026-08-20T12:00:00Z",
)
_assert(result.ok is False, "expired: ok=False")
_assert(ChecklistFailureCode.APPROVAL_EXPIRED in result.failure_codes,
        f"expired: approval_expired in failure_codes (got {result.failure_codes})")

# ---------------------------------------------------------------------------
# Test 17 — audit disabled fails
# ---------------------------------------------------------------------------
print("\n── Test 17: audit disabled fails")
result = validate_onboarding_ceremony(_valid(audit_enabled=False))
_assert(result.ok is False, "no-audit: ok=False")
_assert(ChecklistFailureCode.AUDIT_NOT_ENABLED in result.failure_codes,
        "no-audit: audit_not_enabled in failure_codes")

# ---------------------------------------------------------------------------
# Test 18 — smoke tests missing fails
# ---------------------------------------------------------------------------
print("\n── Test 18: smoke tests missing fails")
result = validate_onboarding_ceremony(_valid(smoke_tests_passed=False))
_assert(result.ok is False, "no-smoke: ok=False")
_assert(ChecklistFailureCode.SMOKE_TESTS_MISSING in result.failure_codes,
        "no-smoke: smoke_tests_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 19 — preflight missing fails
# ---------------------------------------------------------------------------
print("\n── Test 19: preflight missing fails")
result = validate_onboarding_ceremony(_valid(preflight_available=False))
_assert(result.ok is False, "no-preflight: ok=False")
_assert(ChecklistFailureCode.PREFLIGHT_MISSING in result.failure_codes,
        "no-preflight: preflight_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 20 — live gate missing fails
# ---------------------------------------------------------------------------
print("\n── Test 20: live gate missing fails")
result = validate_onboarding_ceremony(_valid(live_gate_available=False))
_assert(result.ok is False, "no-live-gate: ok=False")
_assert(ChecklistFailureCode.LIVE_GATE_MISSING in result.failure_codes,
        "no-live-gate: live_gate_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 21 — revoke path missing fails
# ---------------------------------------------------------------------------
print("\n── Test 21: revoke path missing fails")
result = validate_onboarding_ceremony(_valid(revoke_path_available=False))
_assert(result.ok is False, "no-revoke-path: ok=False")
_assert(ChecklistFailureCode.REVOKE_PATH_MISSING in result.failure_codes,
        "no-revoke-path: revoke_path_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 22 — credential intake boundary missing fails
# ---------------------------------------------------------------------------
print("\n── Test 22: credential intake boundary missing fails")
result = validate_onboarding_ceremony(_valid(credential_intake_boundary_confirmed=False))
_assert(result.ok is False, "no-intake-boundary: ok=False")
_assert(ChecklistFailureCode.CREDENTIAL_INTAKE_BOUNDARY_MISSING in result.failure_codes,
        "no-intake-boundary: credential_intake_boundary_missing in failure_codes")

# ---------------------------------------------------------------------------
# Test 23 — oauth_boundary_design_only false fails
# ---------------------------------------------------------------------------
print("\n── Test 23: oauth_boundary_design_only false fails")
result = validate_onboarding_ceremony(_valid(oauth_boundary_design_only=False))
_assert(result.ok is False, "oauth-not-design-only: ok=False")
_assert(ChecklistFailureCode.OAUTH_BOUNDARY_NOT_DESIGN_ONLY in result.failure_codes,
        "oauth-not-design-only: oauth_boundary_not_design_only in failure_codes")

# ---------------------------------------------------------------------------
# Test 24 — live_flag_false_confirmed false fails
# ---------------------------------------------------------------------------
print("\n── Test 24: live_flag_false_confirmed false fails")
result = validate_onboarding_ceremony(_valid(live_flag_false_confirmed=False))
_assert(result.ok is False, "live-flag-not-false: ok=False")
_assert(ChecklistFailureCode.LIVE_FLAG_NOT_FALSE in result.failure_codes,
        "live-flag-not-false: live_flag_not_false in failure_codes")

# ---------------------------------------------------------------------------
# Test 25 — real_credentials_present true fails
# ---------------------------------------------------------------------------
print("\n── Test 25: real_credentials_present true fails")
result = validate_onboarding_ceremony(_valid(real_credentials_present=True))
_assert(result.ok is False, "real-creds: ok=False")
_assert(ChecklistFailureCode.REAL_CREDENTIALS_PRESENT in result.failure_codes,
        "real-creds: real_credentials_present in failure_codes")

# ---------------------------------------------------------------------------
# Test 26 — google_ads_api_called true fails
# ---------------------------------------------------------------------------
print("\n── Test 26: google_ads_api_called true fails")
result = validate_onboarding_ceremony(_valid(google_ads_api_called=True))
_assert(result.ok is False, "api-called: ok=False")
_assert(ChecklistFailureCode.GOOGLE_ADS_API_CALLED in result.failure_codes,
        "api-called: google_ads_api_called in failure_codes")

# ---------------------------------------------------------------------------
# Test 27 — gcp_commands_used true fails
# ---------------------------------------------------------------------------
print("\n── Test 27: gcp_commands_used true fails")
result = validate_onboarding_ceremony(_valid(gcp_commands_used=True))
_assert(result.ok is False, "gcp-used: ok=False")
_assert(ChecklistFailureCode.GCP_COMMANDS_USED in result.failure_codes,
        "gcp-used: gcp_commands_used in failure_codes")

# ---------------------------------------------------------------------------
# Test 28 — forbidden field in evidence fails
# ---------------------------------------------------------------------------
print("\n── Test 28: forbidden field in evidence fails")
result = validate_onboarding_ceremony(_valid(evidence={"credential_ref": "some-opaque-ref"}))
_assert(result.ok is False, "forbidden-evidence-field: ok=False")
_assert(ChecklistFailureCode.FORBIDDEN_FIELD_PRESENT in result.failure_codes,
        "forbidden-evidence-field: forbidden_field_present in failure_codes")

# ---------------------------------------------------------------------------
# Test 29 — forbidden field in metadata fails
# ---------------------------------------------------------------------------
print("\n── Test 29: forbidden field in metadata fails")
result = validate_onboarding_ceremony(_valid(metadata={"secret_id": "some-opaque-id"}))
_assert(result.ok is False, "forbidden-metadata-field: ok=False")
_assert(ChecklistFailureCode.FORBIDDEN_FIELD_PRESENT in result.failure_codes,
        "forbidden-metadata-field: forbidden_field_present in failure_codes")

# ---------------------------------------------------------------------------
# Test 30 — forbidden value in evidence fails
#   String split at concatenation boundary to avoid literal appearing in source.
# ---------------------------------------------------------------------------
print("\n── Test 30: forbidden value in evidence fails (OAuth token pattern)")
_token = "ya" + "29.SomeOAuthAccessTokenValue"  # ya29 forbidden value — split to avoid literal in source
result = validate_onboarding_ceremony(_valid(evidence={"note": _token}))
_assert(result.ok is False, "forbidden-evidence-value: ok=False")
_assert(ChecklistFailureCode.FORBIDDEN_VALUE_PRESENT in result.failure_codes,
        "forbidden-evidence-value: forbidden_value_present in failure_codes")

# ---------------------------------------------------------------------------
# Test 31 — forbidden value in metadata fails
# ---------------------------------------------------------------------------
print("\n── Test 31: forbidden value in metadata fails (GCP resource path)")
_path = "projects/" + "my-project/secrets/cred-ref"  # GCP path — split to avoid literal in source
result = validate_onboarding_ceremony(_valid(metadata={"context": _path}))
_assert(result.ok is False, "forbidden-metadata-value: ok=False")
_assert(ChecklistFailureCode.FORBIDDEN_VALUE_PRESENT in result.failure_codes,
        "forbidden-metadata-value: forbidden_value_present in failure_codes")

# ---------------------------------------------------------------------------
# Test 32 — sanitized_summary excludes tenant/client/operator/evidence fields
# ---------------------------------------------------------------------------
print("\n── Test 32: sanitized_summary excludes identity and evidence fields")
result = validate_onboarding_ceremony(_valid())
ss = result.sanitized_summary
for excluded in ("tenant_id", "client_id", "operator_label", "evidence_location",
                 "approved_at", "expires_at", "evidence", "metadata"):
    _assert(excluded not in ss, f"sanitized: '{excluded}' not in sanitized_summary")

# ---------------------------------------------------------------------------
# Test 33 — sanitized_summary excludes forbidden values
# ---------------------------------------------------------------------------
print("\n── Test 33: sanitized_summary contains no forbidden field names or raw values")
result = validate_onboarding_ceremony(_valid())
ss_str = str(result.sanitized_summary)
for forbidden_key in ("credential_ref", "secret_id", "customer_id",
                      "developer_token", "refresh_token"):
    _assert(forbidden_key not in ss_str,
            f"sanitized: '{forbidden_key}' absent from sanitized_summary string")

# ---------------------------------------------------------------------------
# Test 34 — multiple failures return multiple failure_codes
# ---------------------------------------------------------------------------
print("\n── Test 34: multiple failures return multiple failure_codes")
result = validate_onboarding_ceremony(_valid(
    operator_label="",
    tenant_id="",
    audit_enabled=False,
    real_credentials_present=True,
))
_assert(len(result.failure_codes) >= 4,
        f"multi-fail: >=4 failure_codes (got {len(result.failure_codes)})")
_assert(ChecklistFailureCode.OPERATOR_LABEL_MISSING in result.failure_codes,
        "multi-fail: operator_label_missing present")
_assert(ChecklistFailureCode.TENANT_MISSING in result.failure_codes,
        "multi-fail: tenant_missing present")
_assert(ChecklistFailureCode.AUDIT_NOT_ENABLED in result.failure_codes,
        "multi-fail: audit_not_enabled present")
_assert(ChecklistFailureCode.REAL_CREDENTIALS_PRESENT in result.failure_codes,
        "multi-fail: real_credentials_present present")

# ---------------------------------------------------------------------------
# Test 35 — required_actions non-empty on failure
# ---------------------------------------------------------------------------
print("\n── Test 35: required_actions non-empty on failure")
result = validate_onboarding_ceremony(_valid(audit_enabled=False))
_assert(len(result.required_actions) > 0,
        "required-actions: non-empty on failure")
_assert(result.decision == ChecklistDecision.FAIL,
        "required-actions: decision=FAIL on failure")

# ---------------------------------------------------------------------------
# Test 36 — required_actions empty on pass
# ---------------------------------------------------------------------------
print("\n── Test 36: required_actions empty on pass")
result = validate_onboarding_ceremony(_valid())
_assert(result.required_actions == [],
        "required-actions: empty on pass")
_assert(result.decision == ChecklistDecision.PASS,
        "required-actions: decision=PASS on pass")

# ---------------------------------------------------------------------------
# Final result
# ---------------------------------------------------------------------------
print()
if _failures:
    print(f"[FAIL] {len(_failures)} assertion(s) failed:")
    for f in _failures:
        print(f"  - {f}")
    sys.exit(1)

print("All assertions passed.")

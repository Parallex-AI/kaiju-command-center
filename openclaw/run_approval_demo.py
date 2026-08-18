"""
V5.19 Phase 3 — Approval record model and store demo/test script.

Verifies approval record creation, validation, store round-trip, and all
denial conditions. Pure local logic — no GCP, no Google Ads API, no real
credentials, no real env vars.
"""

import sys
import tempfile
from pathlib import Path

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
_ADS_AGENT_DIR = str(Path(__file__).resolve().parents[1] / "agents" / "ads-agent")
for _p in (_OPENCLAW_DIR, _ADS_AGENT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from approval import (
    ApprovalRecord,
    ApprovalScope,
    ApprovalStatus,
    ApprovalValidationResult,
    LocalFileApprovalStore,
    create_approval_record,
    is_approval_valid,
    sanitize_approval_record,
    validate_approval_record,
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


_TENANT = "demo-tenant"
_CLIENT = "demo-client"
_INTEGRATION = "google_ads"
_SCOPE = ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION
_OPERATOR = "demo-operator"
_REASON = "Controlled local testing of approval model"
_ROLLBACK = "Disable GOOGLE_ADS_LIVE_ENABLED and revoke approval record"


def _base_approved(**overrides) -> ApprovalRecord:
    base = dict(
        tenant_id=_TENANT,
        client_id=_CLIENT,
        integration_type=_INTEGRATION,
        scope=_SCOPE,
        operator_label=_OPERATOR,
        reason=_REASON,
        rollback_plan=_ROLLBACK,
        status=ApprovalStatus.APPROVED,
    )
    base.update(overrides)
    return create_approval_record(**base)


# ---------------------------------------------------------------------------
# Test 1 — create_approval_record produces expected fields
# ---------------------------------------------------------------------------
print("\n── Test 1: create_approval_record")
rec = _base_approved()
_assert(bool(rec.approval_id), "create: approval_id non-empty")
_assert(bool(rec.created_at), "create: created_at non-empty")
_assert(rec.status == ApprovalStatus.APPROVED, "create: status=APPROVED")
_assert(bool(rec.approved_at), "create: approved_at populated for APPROVED status")
_assert(rec.tenant_id == _TENANT, "create: tenant_id matches")
_assert(rec.client_id == _CLIENT, "create: client_id matches")
_assert(rec.scope == _SCOPE, "create: scope matches")
_assert(rec.rollback_plan == _ROLLBACK, "create: rollback_plan present")

# ---------------------------------------------------------------------------
# Test 2 — validate_approval_record: valid approved record
# ---------------------------------------------------------------------------
print("\n── Test 2: validate_approval_record — valid record")
result = validate_approval_record(rec)
_assert(result.valid is True, "validate: valid=True for approved record")
_assert(result.error_codes == [], "validate: no error_codes")

# ---------------------------------------------------------------------------
# Test 3 — is_approval_valid: correct context → True
# ---------------------------------------------------------------------------
print("\n── Test 3: is_approval_valid — correct context")
ok = is_approval_valid(rec, _SCOPE, _TENANT, _CLIENT, _INTEGRATION)
_assert(ok is True, "is_approval_valid: correct tenant/client/scope/integration → True")

# ---------------------------------------------------------------------------
# Test 4 — LocalFileApprovalStore: put and get round-trip
# ---------------------------------------------------------------------------
print("\n── Test 4: LocalFileApprovalStore put/get")
with tempfile.TemporaryDirectory(prefix="kaiju_approval_demo_") as tmp:
    store_path = Path(tmp) / "approvals.json"
    store = LocalFileApprovalStore(store_path)
    store.put(rec)
    fetched = store.get(rec.approval_id)
    _assert(fetched is not None, "store.get: returns record after put")
    _assert(fetched.approval_id == rec.approval_id, "store.get: approval_id matches")
    _assert(fetched.tenant_id == _TENANT, "store.get: tenant_id preserved")
    _assert(fetched.status == ApprovalStatus.APPROVED, "store.get: status=APPROVED")
    _assert(fetched.rollback_plan == _ROLLBACK, "store.get: rollback_plan preserved")

# ---------------------------------------------------------------------------
# Test 5 — LocalFileApprovalStore: list_for_client
# ---------------------------------------------------------------------------
print("\n── Test 5: LocalFileApprovalStore list_for_client")
with tempfile.TemporaryDirectory(prefix="kaiju_approval_demo_") as tmp:
    store = LocalFileApprovalStore(Path(tmp) / "approvals.json")
    rec_a = _base_approved()
    rec_b = _base_approved()
    rec_other = create_approval_record(
        tenant_id="other-tenant",
        client_id="other-client",
        integration_type=_INTEGRATION,
        scope=_SCOPE,
        operator_label=_OPERATOR,
        reason=_REASON,
        rollback_plan=_ROLLBACK,
        status=ApprovalStatus.APPROVED,
    )
    store.put(rec_a)
    store.put(rec_b)
    store.put(rec_other)
    listed = store.list_for_client(_TENANT, _CLIENT)
    _assert(len(listed) == 2, f"list_for_client: returns 2 for tenant/client (got {len(listed)})")
    ids = {r.approval_id for r in listed}
    _assert(rec_a.approval_id in ids, "list_for_client: rec_a present")
    _assert(rec_b.approval_id in ids, "list_for_client: rec_b present")
    _assert(rec_other.approval_id not in ids, "list_for_client: other-tenant not included")

# ---------------------------------------------------------------------------
# Test 6 — LocalFileApprovalStore: revoke
# ---------------------------------------------------------------------------
print("\n── Test 6: LocalFileApprovalStore revoke")
with tempfile.TemporaryDirectory(prefix="kaiju_approval_demo_") as tmp:
    store = LocalFileApprovalStore(Path(tmp) / "approvals.json")
    rec = _base_approved()
    store.put(rec)
    result = store.revoke(rec.approval_id, reason="demo revocation")
    _assert(result is True, "store.revoke: returns True for existing record")
    revoked = store.get(rec.approval_id)
    _assert(revoked is not None, "store.get after revoke: record present")
    _assert(revoked.status == ApprovalStatus.REVOKED, "store.revoke: status=REVOKED")
    _assert(bool(revoked.revoked_at), "store.revoke: revoked_at populated")
    result_missing = store.revoke("nonexistent-id", reason="no-op")
    _assert(result_missing is False, "store.revoke: returns False for nonexistent id")

# ---------------------------------------------------------------------------
# Test 7 — is_approval_valid: wrong tenant → False
# ---------------------------------------------------------------------------
print("\n── Test 7: is_approval_valid — wrong tenant")
rec = _base_approved()
ok = is_approval_valid(rec, _SCOPE, "wrong-tenant", _CLIENT, _INTEGRATION)
_assert(ok is False, "is_approval_valid: wrong tenant → False")

# ---------------------------------------------------------------------------
# Test 8 — is_approval_valid: wrong client → False
# ---------------------------------------------------------------------------
print("\n── Test 8: is_approval_valid — wrong client")
rec = _base_approved()
ok = is_approval_valid(rec, _SCOPE, _TENANT, "wrong-client", _INTEGRATION)
_assert(ok is False, "is_approval_valid: wrong client → False")

# ---------------------------------------------------------------------------
# Test 9 — is_approval_valid: wrong scope → False
# ---------------------------------------------------------------------------
print("\n── Test 9: is_approval_valid — wrong scope")
rec = _base_approved()
ok = is_approval_valid(rec, ApprovalScope.GOOGLE_ADS_CREDENTIAL_ROTATION, _TENANT, _CLIENT, _INTEGRATION)
_assert(ok is False, "is_approval_valid: wrong scope → False")

# ---------------------------------------------------------------------------
# Test 10 — validate_approval_record: expired approval
# ---------------------------------------------------------------------------
print("\n── Test 10: validate_approval_record — expired approval")
rec = _base_approved(expires_at="2020-01-01T00:00:00Z")
result = validate_approval_record(rec)
_assert(result.valid is False, "expired: valid=False")
_assert("approval_expired" in result.error_codes, f"expired: approval_expired in error_codes (got {result.error_codes})")

# ---------------------------------------------------------------------------
# Test 11 — validate_approval_record: revoked approval
# ---------------------------------------------------------------------------
print("\n── Test 11: validate_approval_record — revoked approval")
rec = create_approval_record(
    tenant_id=_TENANT, client_id=_CLIENT, integration_type=_INTEGRATION,
    scope=_SCOPE, operator_label=_OPERATOR, reason=_REASON,
    rollback_plan=_ROLLBACK, status=ApprovalStatus.REVOKED,
)
result = validate_approval_record(rec)
_assert(result.valid is False, "revoked: valid=False")
_assert(
    any("approval_not_approved" in c for c in result.error_codes),
    f"revoked: approval_not_approved in error_codes (got {result.error_codes})",
)

# ---------------------------------------------------------------------------
# Test 12 — validate_approval_record: missing rollback_plan
# ---------------------------------------------------------------------------
print("\n── Test 12: validate_approval_record — missing rollback_plan")
rec = _base_approved(rollback_plan="   ")
result = validate_approval_record(rec)
_assert(result.valid is False, "no-rollback: valid=False")
_assert("rollback_plan_missing" in result.error_codes, f"no-rollback: rollback_plan_missing in error_codes (got {result.error_codes})")

# ---------------------------------------------------------------------------
# Test 13 — validate_approval_record: forbidden field name in evidence
# ---------------------------------------------------------------------------
print("\n── Test 13: validate_approval_record — forbidden field name in evidence")
rec = _base_approved()
rec.evidence["credential_ref"] = "some-opaque-ref"
result = validate_approval_record(rec)
_assert(result.valid is False, "forbidden-field: valid=False")
_assert(
    "evidence_metadata_forbidden_field" in result.error_codes,
    f"forbidden-field: evidence_metadata_forbidden_field in error_codes (got {result.error_codes})",
)

# ---------------------------------------------------------------------------
# Test 14 — validate_approval_record: forbidden value pattern in evidence
# ---------------------------------------------------------------------------
print("\n── Test 14: validate_approval_record — forbidden value pattern in evidence")
rec = _base_approved()
rec.evidence["notes"] = "ya" + "29.some-token-value-here"
result = validate_approval_record(rec)
_assert(result.valid is False, "forbidden-value: valid=False")
_assert(
    "evidence_metadata_forbidden_value_pattern" in result.error_codes,
    f"forbidden-value: evidence_metadata_forbidden_value_pattern in error_codes (got {result.error_codes})",
)

# ---------------------------------------------------------------------------
# Test 15 — sanitize_approval_record: forbidden field key removed
# ---------------------------------------------------------------------------
print("\n── Test 15: sanitize_approval_record — forbidden field key removed")
rec = _base_approved()
rec.evidence["credential_ref"] = "some-ref"
rec.evidence["safe_note"] = "this is fine"
sanitized = sanitize_approval_record(rec)
_assert("credential_ref" not in sanitized["evidence"], "sanitize: credential_ref not in sanitized evidence")
_assert("safe_note" in sanitized["evidence"], "sanitize: safe_note preserved in sanitized evidence")

# ---------------------------------------------------------------------------
# Test 16 — validate_approval_record: missing operator_label
# ---------------------------------------------------------------------------
print("\n── Test 16: validate_approval_record — missing operator_label")
rec = _base_approved(operator_label="  ")
result = validate_approval_record(rec)
_assert(result.valid is False, "no-operator: valid=False")
_assert("operator_label_missing" in result.error_codes, f"no-operator: operator_label_missing in error_codes (got {result.error_codes})")

# ---------------------------------------------------------------------------
# Test 17 — validate_approval_record: PENDING status denies
# ---------------------------------------------------------------------------
print("\n── Test 17: validate_approval_record — PENDING status denies")
rec = _base_approved(status=ApprovalStatus.PENDING)
result = validate_approval_record(rec)
_assert(result.valid is False, "PENDING: valid=False")
_assert(
    any("approval_not_approved" in c for c in result.error_codes),
    f"PENDING: approval_not_approved in error_codes (got {result.error_codes})",
)

# ---------------------------------------------------------------------------
# Test 18 — validate_approval_record: REJECTED status denies
# ---------------------------------------------------------------------------
print("\n── Test 18: validate_approval_record — REJECTED status denies")
rec = _base_approved(status=ApprovalStatus.REJECTED)
result = validate_approval_record(rec)
_assert(result.valid is False, "REJECTED: valid=False")
_assert(
    any("approval_not_approved" in c for c in result.error_codes),
    f"REJECTED: approval_not_approved in error_codes (got {result.error_codes})",
)

# ---------------------------------------------------------------------------
# Test 19 — validate_approval_record: EXPIRED status denies
# ---------------------------------------------------------------------------
print("\n── Test 19: validate_approval_record — EXPIRED status denies")
rec = _base_approved(status=ApprovalStatus.EXPIRED)
result = validate_approval_record(rec)
_assert(result.valid is False, "EXPIRED: valid=False")
_assert(
    any("approval_not_approved" in c for c in result.error_codes),
    f"EXPIRED: approval_not_approved in error_codes (got {result.error_codes})",
)

# ---------------------------------------------------------------------------
# Test 20 — validate_approval_record: missing reason denies
# ---------------------------------------------------------------------------
print("\n── Test 20: validate_approval_record — missing reason")
rec = _base_approved(reason="   ")
result = validate_approval_record(rec)
_assert(result.valid is False, "missing-reason: valid=False")
_assert(
    "reason_missing" in result.error_codes,
    f"missing-reason: reason_missing in error_codes (got {result.error_codes})",
)

# ---------------------------------------------------------------------------
# Test 21 — validate_approval_record: future expires_at allows
# ---------------------------------------------------------------------------
print("\n── Test 21: validate_approval_record — future expires_at allows")
from datetime import datetime, timezone, timedelta
_future_expiry = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
rec = _base_approved(expires_at=_future_expiry)
result = validate_approval_record(rec)
_assert(result.valid is True, "future expiry: valid=True")

# ---------------------------------------------------------------------------
# Test 22 — is_approval_valid: wrong integration_type → False
# ---------------------------------------------------------------------------
print("\n── Test 22: is_approval_valid — wrong integration_type → False")
rec = _base_approved()
ok = is_approval_valid(rec, _SCOPE, _TENANT, _CLIENT, "facebook_ads")
_assert(ok is False, "wrong integration_type: is_approval_valid=False")

# ---------------------------------------------------------------------------
# Test 23 — validate_approval_record: forbidden field name in metadata
# ---------------------------------------------------------------------------
print("\n── Test 23: validate_approval_record — forbidden field name in metadata")
rec = _base_approved()
rec.metadata["secret_id"] = "some-opaque-ref"
result = validate_approval_record(rec)
_assert(result.valid is False, "forbidden-metadata-field: valid=False")
_assert(
    "evidence_metadata_forbidden_field" in result.error_codes,
    f"forbidden-metadata-field: evidence_metadata_forbidden_field in error_codes (got {result.error_codes})",
)

# ---------------------------------------------------------------------------
# Test 24 — validate_approval_record: forbidden value pattern in metadata
# ---------------------------------------------------------------------------
print("\n── Test 24: validate_approval_record — forbidden value pattern in metadata")
rec = _base_approved()
rec.metadata["context"] = "projects/" + "my-project/secrets/cred-ref"
result = validate_approval_record(rec)
_assert(result.valid is False, "forbidden-metadata-value: valid=False")
_assert(
    "evidence_metadata_forbidden_value_pattern" in result.error_codes,
    f"forbidden-metadata-value: evidence_metadata_forbidden_value_pattern in error_codes (got {result.error_codes})",
)

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

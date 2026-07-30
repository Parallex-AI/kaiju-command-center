"""
V5.5 / V5.6 / V5.14 / V5.15 / V5.16 — OpenClaw admin helper for credential reference operations.

V5.5:  get_google_ads_credential_status — read-only status lookup
V5.6:  upsert_google_ads_credential_reference — create/update CredentialReference (no secrets)
V5.14: write_google_ads_credential_bundle — write full credential bundle (metadata →
  LocalFileCredentialReferenceStore, secrets → SecretStore). Routes to
  GCPSecretManagerStore or InMemorySecretStore based on GCP_SECRET_MANAGER_ENABLED.
V5.15: validate_google_ads_credentials — structural validation via SecretStore.get_secret_status().
  No secret values fetched. Updates CredentialReference status and last_validated_at.
  Emits audit event operation="validate".
  delete_google_ads_credentials — delete credential bundle and mark CredentialReference REVOKED.
  Requires OPENCLAW_ADMIN_DELETE_ENABLED=true. Idempotent on already-absent secrets.
  Emits audit event operation="delete".
V5.16: rotate_google_ads_credentials — replace secret bundle for an existing CredentialReference.
  Requires AdminScope.ROTATE (only ADMIN tokens satisfy this). Allowed current statuses:
  ACTIVE, CONFIGURED, VALIDATION_FAILED. REVOKED credentials are rejected with
  invalid_status_for_rotation. Uses put_secret_bundle() only — no get_secret_bundle().
  Validates structurally via get_secret_status(). Emits audit event operation="rotate".

No secret values are returned by any function in this module.
"""

import os
import sys
from dataclasses import replace as dc_replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add agents/ads-agent/ to sys.path so the credentials package is importable
_ADS_AGENT_DIR = str(Path(__file__).resolve().parents[1] / "agents" / "ads-agent")
if _ADS_AGENT_DIR not in sys.path:
    sys.path.insert(0, _ADS_AGENT_DIR)

from credentials.local_file_store import LocalFileCredentialReferenceStore
from credentials.models import (
    CredentialStatus,
    create_credential_reference,
    filter_safe_metadata,
    now_utc_iso,
    update_credential_status,
)
from credentials.secret_store import (
    SecretStore,
    GOOGLE_ADS_SECRET_FIELDS,
    assert_allowed_secret_fields,
)
from credentials.secret_store_factory import create_secret_store
from audit import build_credential_audit_event, append_audit_event

_INTEGRATION_TYPE = "google_ads"
_VALID_STATUSES = frozenset(s.value for s in CredentialStatus)
_GOOGLE_ADS_SECRET_FIELD_SET: frozenset = frozenset(GOOGLE_ADS_SECRET_FIELDS)
_BUNDLE_METADATA_KEYS: frozenset = frozenset({"customer_id", "login_customer_id", "status", "metadata"})

# Forbidden key substrings for write payload validation.
# Superset of store.py's list — includes 'auth_header'.
_WRITE_FORBIDDEN_SUBSTRINGS: Tuple[str, ...] = (
    "token",
    "secret",
    "password",
    "authorization",
    "auth_header",
    "oauth_code",
    "refresh",
    "access",
)


def _emit_credential_audit_event(
    tenant_id: str,
    client_id: str,
    operation: str,
    ok: bool,
    request_id: str = "",
    trace_id: str = "",
    error_codes: Optional[List[str]] = None,
) -> Dict:
    """Emit a credential audit event. Never raises — never affects operation outcome."""
    try:
        event = build_credential_audit_event(
            tenant_id=tenant_id,
            client_id=client_id,
            integration_type=_INTEGRATION_TYPE,
            operation=operation,
            ok=ok,
            request_id=request_id,
            trace_id=trace_id,
            error_codes=error_codes,
        )
        return append_audit_event(event)
    except Exception:
        return {"ok": False, "error": "audit_append_failed"}


def _check_no_forbidden_write_fields(
    payload: dict,
    _path: str = "",
) -> Tuple[bool, List[str]]:
    """
    Recursively scan dict keys for forbidden secret-like substrings.

    Returns (True, []) if clean.
    Returns (False, [offending key paths]) if any forbidden substrings are found.
    Values are not inspected — key names are sufficient.
    """
    offending: List[str] = []
    for key, value in payload.items():
        full_path = f"{_path}.{key}" if _path else str(key)
        if any(sub in str(key).lower() for sub in _WRITE_FORBIDDEN_SUBSTRINGS):
            offending.append(full_path)
        if isinstance(value, dict):
            _, child = _check_no_forbidden_write_fields(value, _path=full_path)
            offending.extend(child)
    return (len(offending) == 0, offending)


def _make_admin_error(
    tenant_id: str,
    client_id: str,
    code: str,
    message: str,
    recoverable: bool = False,
) -> Dict[str, Any]:
    return {
        "ok": False,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "integration_type": _INTEGRATION_TYPE,
        "credential_status": None,
        "errors": [
            {
                "code": code,
                "message": message,
                "recoverable": recoverable,
                "source": "openclaw_admin",
            }
        ],
    }


def get_google_ads_credential_status(
    tenant_id: str,
    client_id: str,
) -> Dict[str, Any]:
    """
    Return a safe redacted credential status envelope for a tenant/client pair.

    Uses LocalFileCredentialReferenceStore.get_status(), which returns a
    missing_credential_status shape when no reference has been stored yet.
    Never returns secret values (developer_token, client_secret, refresh_token, etc.).

    On store failure, returns ok=false with a safe error envelope. The original
    exception is not propagated — its message may contain file paths or other
    internal details that should not surface to callers.
    """
    try:
        store = LocalFileCredentialReferenceStore()
        credential_status = store.get_status(tenant_id, client_id, _INTEGRATION_TYPE)
        return {
            "ok": True,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "integration_type": _INTEGRATION_TYPE,
            "credential_status": credential_status,
            "errors": [],
        }
    except Exception:
        return _make_admin_error(
            tenant_id, client_id,
            "credential_status_failed",
            "Failed to retrieve credential status. Check CREDENTIAL_REFERENCE_STORE_PATH configuration.",
            recoverable=True,
        )


def upsert_google_ads_credential_reference(
    tenant_id: str,
    client_id: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create or update a CredentialReference for a tenant/client Google Ads integration.

    Accepts only safe metadata fields: customer_id, login_customer_id, status, metadata.
    Rejects any payload containing secret-like key names (recursive check).
    Never stores developer_token, client_secret, refresh_token, access_token, or OAuth codes.

    Upsert semantics:
    - If a reference already exists: updates provided fields, preserves created_at and
      credential_ref, updates updated_at.
    - If no reference exists: creates a new CredentialReference.

    Returns redacted credential status on success.
    On any error, returns ok=false with a safe message — no secret values in errors.
    """
    # 1. Reject empty/None payload
    if not payload:
        return _make_admin_error(
            tenant_id, client_id,
            "invalid_request",
            "Request body is required. Provide customer_id at minimum.",
        )

    # 2. Reject any forbidden secret-like key names (top-level and nested)
    clean, offending = _check_no_forbidden_write_fields(payload)
    if not clean:
        # Do not echo offending field values — key names are omitted from message too
        return _make_admin_error(
            tenant_id, client_id,
            "secret_material_rejected",
            "Request contains forbidden secret-like fields.",
        )

    # 3. Validate status if provided
    if "status" in payload:
        status_value: Optional[str] = payload["status"]
        if status_value not in _VALID_STATUSES:
            return _make_admin_error(
                tenant_id, client_id,
                "invalid_status",
                f"status must be one of: {sorted(_VALID_STATUSES)}",
            )
    else:
        status_value = None  # preserve existing on update; use default on create

    # 4. Extract allowed fields
    customer_id: Optional[str] = payload.get("customer_id") or None
    login_customer_id: Optional[str] = payload.get("login_customer_id") or None
    metadata_raw = payload.get("metadata")

    try:
        store = LocalFileCredentialReferenceStore()
        existing = store.get_reference(tenant_id, client_id, _INTEGRATION_TYPE)

        if existing is not None:
            # Upsert: update only the fields present in the payload;
            # preserve created_at and credential_ref.
            update_kwargs: Dict[str, Any] = {"updated_at": now_utc_iso()}
            if "customer_id" in payload:
                update_kwargs["customer_id"] = customer_id
            if "login_customer_id" in payload:
                update_kwargs["login_customer_id"] = login_customer_id
            if status_value is not None:
                update_kwargs["status"] = status_value
            if "metadata" in payload:
                update_kwargs["metadata"] = filter_safe_metadata(metadata_raw) or None
            ref = dc_replace(existing, **update_kwargs)
        else:
            # Create: use provided fields; default status to "configured"
            ref = create_credential_reference(
                tenant_id=tenant_id,
                client_id=client_id,
                integration_type=_INTEGRATION_TYPE,
                customer_id=customer_id,
                login_customer_id=login_customer_id,
                status=status_value or CredentialStatus.CONFIGURED.value,
                metadata=metadata_raw,
            )

        store.put_reference(ref)
        credential_status = store.get_status(tenant_id, client_id, _INTEGRATION_TYPE)
        _ar = _emit_credential_audit_event(tenant_id, client_id, operation="metadata_upsert", ok=True)
        result = {
            "ok": True,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "integration_type": _INTEGRATION_TYPE,
            "credential_status": credential_status,
            "errors": [],
        }
        if not _ar.get("ok") and not _ar.get("skipped"):
            result["warnings"] = ["audit_append_failed"]
        return result

    except ValueError:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="metadata_upsert",
            ok=False,
            error_codes=["invalid_credential_reference"],
        )
        err = _make_admin_error(
            tenant_id, client_id,
            "invalid_credential_reference",
            "Credential reference is invalid. Check field values.",
        )
        if not _ar.get("ok") and not _ar.get("skipped"):
            err["warnings"] = ["audit_append_failed"]
        return err
    except Exception:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="metadata_upsert",
            ok=False,
            error_codes=["credential_write_failed"],
        )
        err = _make_admin_error(
            tenant_id, client_id,
            "credential_write_failed",
            "Failed to write credential reference. Check store configuration.",
            recoverable=True,
        )
        if not _ar.get("ok") and not _ar.get("skipped"):
            err["warnings"] = ["audit_append_failed"]
        return err


def write_google_ads_credential_bundle(
    tenant_id: str,
    client_id: str,
    payload: Optional[Dict[str, Any]] = None,
    secret_store: Optional[SecretStore] = None,
) -> Dict[str, Any]:
    """
    Write a complete Google Ads credential bundle.

    Metadata fields (customer_id, login_customer_id, status, metadata) are written
    to LocalFileCredentialReferenceStore via upsert_google_ads_credential_reference().
    Secret fields (developer_token, client_id as OAuth credential, client_secret,
    refresh_token) are written to SecretStore via put_secret_bundle().

    When secret_store is None, uses create_secret_store() which auto-selects
    InMemorySecretStore (default) or GCPSecretManagerStore (when
    GCP_SECRET_MANAGER_ENABLED=true).

    Note on naming: the client_id parameter here is the OpenClaw client ID (route
    identifier). The Google Ads OAuth client_id arrives as payload["client_id"] and
    is secret material — it is never returned in any response field.

    All four secret fields are required. Partial bundles are rejected with
    secret_bundle_incomplete. Unknown or globally-forbidden fields (access_token,
    oauth_code) in the secret position are rejected with secret_material_rejected.
    Secret values never appear in any return value, error message, or log line.
    """
    # 1. Reject empty/None payload
    if not payload:
        err = _make_admin_error(
            tenant_id, client_id,
            "invalid_request",
            "Request body is required.",
        )
        err["secret_status"] = None
        return err

    # 2. Partition payload: known Google Ads secret fields vs everything else
    secret_payload: Dict[str, Any] = {
        k: payload[k] for k in _GOOGLE_ADS_SECRET_FIELD_SET if k in payload
    }
    other_payload: Dict[str, Any] = {
        k: v for k, v in payload.items() if k not in _GOOGLE_ADS_SECRET_FIELD_SET
    }

    # 3. Run existing forbidden-field guard only on non-secret fields
    clean, _offending = _check_no_forbidden_write_fields(other_payload)
    if not clean:
        err = _make_admin_error(
            tenant_id, client_id,
            "secret_material_rejected",
            "Request contains forbidden secret-like fields.",
        )
        err["secret_status"] = None
        return err

    # 4. Require all four secret fields — partial bundles are rejected
    missing_fields = [
        f for f in GOOGLE_ADS_SECRET_FIELDS
        if not payload.get(f) or not str(payload[f]).strip()
    ]
    if missing_fields:
        err = _make_admin_error(
            tenant_id, client_id,
            "secret_bundle_incomplete",
            f"Missing or empty required secret fields: {sorted(missing_fields)}",
        )
        err["secret_status"] = None
        return err

    # 5. Validate secret fields via SecretStore registry (rejects access_token, etc.)
    allowed, _rejected = assert_allowed_secret_fields(secret_payload, _INTEGRATION_TYPE)
    if not allowed:
        err = _make_admin_error(
            tenant_id, client_id,
            "secret_material_rejected",
            "Secret bundle contains disallowed fields.",
        )
        err["secret_status"] = None
        return err

    # 6. Build metadata payload for CredentialReference upsert (no secrets)
    metadata_payload: Dict[str, Any] = {
        k: payload[k] for k in _BUNDLE_METADATA_KEYS if k in payload
    }
    if not metadata_payload:
        # No metadata fields supplied — use minimum viable payload to create the reference
        metadata_payload = {"status": CredentialStatus.CONFIGURED.value}

    # 7. Upsert CredentialReference (metadata only — secrets are never passed here)
    ref_result = upsert_google_ads_credential_reference(tenant_id, client_id, metadata_payload)
    if not ref_result.get("ok"):
        ref_result["secret_status"] = None
        return ref_result

    # 8. Resolve credential_ref from upsert result
    credential_status = ref_result.get("credential_status") or {}
    credential_ref: Optional[str] = credential_status.get("credential_ref")
    if not credential_ref:
        err = _make_admin_error(
            tenant_id, client_id,
            "credential_reference_missing",
            "Could not resolve credential reference after upsert.",
            recoverable=False,
        )
        err["secret_status"] = None
        return err

    # 9. Resolve secret store (injected for tests; factory for production)
    if secret_store is None:
        secret_store = create_secret_store()

    # 10. Write secret bundle — secret_payload lives only in this local scope
    try:
        secret_store.put_secret_bundle(
            credential_ref=credential_ref,
            integration_type=_INTEGRATION_TYPE,
            secrets=secret_payload,
        )
    except Exception:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="bundle_write",
            ok=False,
            error_codes=["secret_write_failed"],
        )
        err = _make_admin_error(
            tenant_id, client_id,
            "secret_write_failed",
            "Failed to write secret bundle. Check secret store configuration.",
            recoverable=True,
        )
        err["secret_status"] = None
        if not _ar.get("ok") and not _ar.get("skipped"):
            err["warnings"] = ["audit_append_failed"]
        return err

    _ar = _emit_credential_audit_event(tenant_id, client_id, operation="bundle_write", ok=True)

    # 11–12. Get redacted secret status (no secret values — configured_fields booleans only)
    try:
        secret_status_result = secret_store.get_secret_status(
            credential_ref=credential_ref,
            integration_type=_INTEGRATION_TYPE,
        )
    except Exception:
        secret_status_result = None

    # 13. Return combined redacted response — no secret values anywhere
    result = {
        "ok": True,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "integration_type": _INTEGRATION_TYPE,
        "credential_status": ref_result.get("credential_status"),
        "secret_status": secret_status_result,
        "errors": [],
    }
    if not _ar.get("ok") and not _ar.get("skipped"):
        result["warnings"] = ["audit_append_failed"]
    return result


def validate_google_ads_credentials(
    tenant_id: str,
    client_id: str,
    secret_store: Optional[SecretStore] = None,
) -> Dict[str, Any]:
    """
    Structural validation of stored Google Ads credentials.

    V5.15 Phase 2 — structural only. No Google Ads API call. No secret values fetched.

    Steps:
    A. Load CredentialReference — returns credential_not_found if missing.
    B. Resolve SecretStore (injected or factory).
    C. Call get_secret_status() — field presence check only, no raw values.
    D. Compute structurally_complete and missing_fields (field names only).
    E. Update CredentialReference: status → ACTIVE (complete) or VALIDATION_FAILED (incomplete).
    F. Emit audit event operation="validate".
    G. Return redacted validation result — no secret values, no raw exceptions.

    Secret values, credential_ref, secret_id, customer_id, login_customer_id are
    never included in the returned validation_result block.
    """
    _EMPTY_VALIDATION_RESULT: Dict[str, Any] = {
        "structurally_complete": False,
        "missing_fields": [],
        "live_api_tested": False,
    }

    # A. Load CredentialReference
    try:
        ref_store = LocalFileCredentialReferenceStore()
        ref = ref_store.get_reference(tenant_id, client_id, _INTEGRATION_TYPE)
    except Exception:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="validate",
            ok=False,
            error_codes=["credential_store_failed"],
        )
        err = _make_admin_error(
            tenant_id, client_id,
            "credential_store_failed",
            "Failed to load credential reference store. Check configuration.",
            recoverable=True,
        )
        err["validation_result"] = _EMPTY_VALIDATION_RESULT
        err["secret_status"] = None
        if not _ar.get("ok") and not _ar.get("skipped"):
            err["warnings"] = ["audit_append_failed"]
        return err

    if ref is None:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="validate",
            ok=False,
            error_codes=["credential_not_found"],
        )
        err = _make_admin_error(
            tenant_id, client_id,
            "credential_not_found",
            "No credential reference found for this tenant/client.",
            recoverable=False,
        )
        err["validation_result"] = _EMPTY_VALIDATION_RESULT
        err["secret_status"] = None
        if not _ar.get("ok") and not _ar.get("skipped"):
            err["warnings"] = ["audit_append_failed"]
        return err

    # B. Resolve credential_ref (internal use only — never echoed in response)
    _credential_ref: str = ref.credential_ref

    # C. Resolve SecretStore (injected for tests; factory for production)
    if secret_store is None:
        secret_store = create_secret_store()

    # D. Get redacted secret status — field presence booleans only, no raw values
    try:
        secret_status_result = secret_store.get_secret_status(
            credential_ref=_credential_ref,
            integration_type=_INTEGRATION_TYPE,
        )
    except Exception:
        secret_status_result = {"configured": False, "configured_fields": {}}

    configured_fields_map: Dict[str, bool] = secret_status_result.get("configured_fields") or {}
    missing_fields: List[str] = [
        f for f in GOOGLE_ADS_SECRET_FIELDS
        if not configured_fields_map.get(f)
    ]
    structurally_complete: bool = len(missing_fields) == 0

    # E. Update CredentialReference status and last_validated_at
    last_validated_at: str = now_utc_iso()
    new_status: str = (
        CredentialStatus.ACTIVE.value if structurally_complete
        else CredentialStatus.VALIDATION_FAILED.value
    )
    updated_credential_status: Optional[Dict[str, Any]] = None
    try:
        updated_ref = update_credential_status(ref, new_status, last_validated_at=last_validated_at)
        ref_store.put_reference(updated_ref)
        updated_credential_status = ref_store.get_status(tenant_id, client_id, _INTEGRATION_TYPE)
    except Exception:
        pass  # persist failure is non-fatal; validation result is still returned

    # F. Emit audit event — ok=True means validation process ran; error_codes signal completeness
    audit_error_codes: List[str] = [] if structurally_complete else ["secret_bundle_incomplete"]
    _ar = _emit_credential_audit_event(
        tenant_id, client_id,
        operation="validate",
        ok=True,
        error_codes=audit_error_codes,
    )

    # G. Return redacted validation result — no secret values anywhere
    result = {
        "ok": True,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "integration_type": _INTEGRATION_TYPE,
        "validation_result": {
            "structurally_complete": structurally_complete,
            "missing_fields": missing_fields,
            "last_validated_at": last_validated_at,
            "live_api_tested": False,
        },
        "credential_status": updated_credential_status,
        "secret_status": secret_status_result,
        "errors": [],
    }
    if not _ar.get("ok") and not _ar.get("skipped"):
        result["warnings"] = ["audit_append_failed"]
    return result


def _is_admin_delete_enabled() -> bool:
    return os.environ.get("OPENCLAW_ADMIN_DELETE_ENABLED", "false").strip().lower() == "true"


def delete_google_ads_credentials(
    tenant_id: str,
    client_id: str,
    secret_store: Optional[SecretStore] = None,
) -> Dict[str, Any]:
    """
    Delete a Google Ads credential bundle and mark CredentialReference as REVOKED.

    V5.15 Phase 3 — requires OPENCLAW_ADMIN_DELETE_ENABLED=true. Disabled by default.

    Steps:
    A. Check env gate — returns delete_not_enabled if not enabled.
    B. Load CredentialReference — returns credential_not_found if missing.
    C. Resolve SecretStore (injected or factory).
    D. Call delete_secret_bundle() — no get_secret_bundle(), no secret values accessed.
    E. Handle result:
       - True  → secrets deleted, update status to REVOKED, ok=true
       - False → secrets already absent (idempotent), update status to REVOKED,
                 ok=true, warnings=["secret_already_absent"]
       - raises → do not update status, ok=false, errors=["secret_delete_failed"]
    F. Emit audit event operation="delete".
    G. Return redacted response — no secret values, no credential_ref, no secret_id.
    """
    # A. Check env gate first — do not load or delete anything when disabled
    if not _is_admin_delete_enabled():
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="delete",
            ok=False,
            error_codes=["delete_not_enabled"],
        )
        _aw = [] if (_ar.get("ok") or _ar.get("skipped")) else ["audit_append_failed"]
        return {
            "ok": False,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "integration_type": _INTEGRATION_TYPE,
            "credential_status": None,
            "secret_status": None,
            "warnings": _aw,
            "errors": [
                {
                    "code": "delete_not_enabled",
                    "message": "Delete is disabled. Set OPENCLAW_ADMIN_DELETE_ENABLED=true to enable.",
                    "recoverable": False,
                    "source": "openclaw_admin",
                }
            ],
        }

    # B. Load CredentialReference
    try:
        ref_store = LocalFileCredentialReferenceStore()
        ref = ref_store.get_reference(tenant_id, client_id, _INTEGRATION_TYPE)
    except Exception:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="delete",
            ok=False,
            error_codes=["credential_store_failed"],
        )
        _aw = [] if (_ar.get("ok") or _ar.get("skipped")) else ["audit_append_failed"]
        return {
            "ok": False,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "integration_type": _INTEGRATION_TYPE,
            "credential_status": None,
            "secret_status": None,
            "warnings": _aw,
            "errors": [
                {
                    "code": "credential_store_failed",
                    "message": "Failed to load credential reference store. Check configuration.",
                    "recoverable": True,
                    "source": "openclaw_admin",
                }
            ],
        }

    if ref is None:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="delete",
            ok=False,
            error_codes=["credential_not_found"],
        )
        _aw = [] if (_ar.get("ok") or _ar.get("skipped")) else ["audit_append_failed"]
        return {
            "ok": False,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "integration_type": _INTEGRATION_TYPE,
            "credential_status": None,
            "secret_status": None,
            "warnings": _aw,
            "errors": [
                {
                    "code": "credential_not_found",
                    "message": "No credential reference found for this tenant/client.",
                    "recoverable": False,
                    "source": "openclaw_admin",
                }
            ],
        }

    # C. Resolve credential_ref (internal only — never echoed in response)
    _credential_ref: str = ref.credential_ref

    # D. Resolve SecretStore (injected for tests; factory for production)
    if secret_store is None:
        secret_store = create_secret_store()

    # E. Delete secret bundle — no get_secret_bundle(), no raw values accessed
    warnings: List[str] = []
    try:
        deleted: bool = secret_store.delete_secret_bundle(
            credential_ref=_credential_ref,
            integration_type=_INTEGRATION_TYPE,
        )
        if not deleted:
            # Idempotent — secret was already absent; still mark REVOKED
            warnings.append("secret_already_absent")
    except Exception:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="delete",
            ok=False,
            error_codes=["secret_delete_failed"],
        )
        _aw = [] if (_ar.get("ok") or _ar.get("skipped")) else ["audit_append_failed"]
        return {
            "ok": False,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "integration_type": _INTEGRATION_TYPE,
            "credential_status": None,
            "secret_status": None,
            "warnings": _aw,
            "errors": [
                {
                    "code": "secret_delete_failed",
                    "message": "Failed to delete secret bundle. Check secret store configuration.",
                    "recoverable": True,
                    "source": "openclaw_admin",
                }
            ],
        }

    # F. Update CredentialReference status to REVOKED
    updated_credential_status: Optional[Dict[str, Any]] = None
    try:
        updated_ref = update_credential_status(
            ref, CredentialStatus.REVOKED.value, last_validated_at=now_utc_iso()
        )
        ref_store.put_reference(updated_ref)
        updated_credential_status = ref_store.get_status(tenant_id, client_id, _INTEGRATION_TYPE)
    except Exception:
        pass  # status update failure is non-fatal; delete itself succeeded

    # Redacted secret status after delete (configured=false confirms removal)
    secret_status_result: Optional[Dict[str, Any]] = None
    try:
        secret_status_result = secret_store.get_secret_status(
            credential_ref=_credential_ref,
            integration_type=_INTEGRATION_TYPE,
        )
    except Exception:
        pass

    # G. Emit audit event — ok=true; error_codes reflects idempotent case
    audit_error_codes: List[str] = ["secret_already_absent"] if warnings else []
    _ar = _emit_credential_audit_event(
        tenant_id, client_id,
        operation="delete",
        ok=True,
        error_codes=audit_error_codes,
    )
    if not _ar.get("ok") and not _ar.get("skipped"):
        warnings.append("audit_append_failed")

    # H. Return redacted response — no secret values anywhere
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "integration_type": _INTEGRATION_TYPE,
        "credential_status": updated_credential_status,
        "secret_status": secret_status_result,
        "warnings": warnings,
        "errors": [],
    }


def rotate_google_ads_credentials(
    tenant_id: str,
    client_id: str,
    payload: Optional[Dict[str, Any]] = None,
    secret_store: Optional[SecretStore] = None,
) -> Dict[str, Any]:
    """
    Rotate Google Ads credentials for an existing CredentialReference.

    V5.16 Phase 3 — Requires AdminScope.ROTATE (only ADMIN tokens satisfy this).

    Allowed current statuses: ACTIVE, CONFIGURED, VALIDATION_FAILED.
    REVOKED credentials are rejected — create a new credential instead.

    Steps:
    A. Load CredentialReference — credential_not_found if missing.
    B. Reject REVOKED status — invalid_status_for_rotation.
    C. Validate payload — all four secret fields required (pre-write; no write occurs on failure).
    D. Resolve SecretStore (injected or factory).
    E. Write new bundle via put_secret_bundle() — no get_secret_bundle() call.
    F. Validate structurally via get_secret_status() only — no Google Ads API.
    G. Update CredentialReference: ACTIVE (complete) or VALIDATION_FAILED (incomplete).
    H. Emit audit event operation="rotate".
    I. Return redacted result.

    No secret values, credential_ref, secret_id, customer_id, or login_customer_id
    in any response or audit event.
    """
    _EMPTY_ROTATION_RESULT: Dict[str, Any] = {
        "structurally_complete": False,
        "missing_fields": [],
    }

    # A. Load CredentialReference
    try:
        ref_store = LocalFileCredentialReferenceStore()
        ref = ref_store.get_reference(tenant_id, client_id, _INTEGRATION_TYPE)
    except Exception:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="rotate",
            ok=False,
            error_codes=["credential_store_failed"],
        )
        err = _make_admin_error(
            tenant_id, client_id,
            "credential_store_failed",
            "Failed to load credential reference store. Check configuration.",
            recoverable=True,
        )
        err["rotation_result"] = _EMPTY_ROTATION_RESULT
        err["secret_status"] = None
        if not _ar.get("ok") and not _ar.get("skipped"):
            err["warnings"] = ["audit_append_failed"]
        return err

    if ref is None:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="rotate",
            ok=False,
            error_codes=["credential_not_found"],
        )
        err = _make_admin_error(
            tenant_id, client_id,
            "credential_not_found",
            "No credential reference found for this tenant/client.",
            recoverable=False,
        )
        err["rotation_result"] = _EMPTY_ROTATION_RESULT
        err["secret_status"] = None
        if not _ar.get("ok") and not _ar.get("skipped"):
            err["warnings"] = ["audit_append_failed"]
        return err

    # B. Reject REVOKED credentials — rotation is not permitted
    if ref.status == CredentialStatus.REVOKED.value:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="rotate",
            ok=False,
            error_codes=["invalid_status_for_rotation"],
        )
        err = _make_admin_error(
            tenant_id, client_id,
            "invalid_status_for_rotation",
            "Cannot rotate a revoked credential. Create a new credential instead.",
            recoverable=False,
        )
        err["rotation_result"] = _EMPTY_ROTATION_RESULT
        err["secret_status"] = None
        if not _ar.get("ok") and not _ar.get("skipped"):
            err["warnings"] = ["audit_append_failed"]
        return err

    # Resolve credential_ref (internal only — never echoed in response)
    _credential_ref: str = ref.credential_ref

    # C. Validate payload — all four secret fields required (pre-write)
    if not payload:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="rotate",
            ok=False,
            error_codes=["invalid_request"],
        )
        err = _make_admin_error(
            tenant_id, client_id,
            "invalid_request",
            "Request body with all four secret fields is required for rotation.",
        )
        err["rotation_result"] = _EMPTY_ROTATION_RESULT
        err["secret_status"] = None
        if not _ar.get("ok") and not _ar.get("skipped"):
            err["warnings"] = ["audit_append_failed"]
        return err

    secret_payload: Dict[str, Any] = {
        k: payload[k] for k in _GOOGLE_ADS_SECRET_FIELD_SET if k in payload
    }
    pre_write_missing: List[str] = [
        f for f in GOOGLE_ADS_SECRET_FIELDS
        if not payload.get(f) or not str(payload[f]).strip()
    ]
    if pre_write_missing:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="rotate",
            ok=False,
            error_codes=["secret_bundle_incomplete"],
        )
        err_body: Dict[str, Any] = {
            "ok": False,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "integration_type": _INTEGRATION_TYPE,
            "credential_status": None,
            "rotation_result": {
                "structurally_complete": False,
                "missing_fields": sorted(pre_write_missing),
            },
            "secret_status": None,
            "errors": [
                {
                    "code": "secret_bundle_incomplete",
                    "message": f"Missing or empty required secret fields: {sorted(pre_write_missing)}",
                    "recoverable": True,
                    "source": "openclaw_admin",
                }
            ],
        }
        if not _ar.get("ok") and not _ar.get("skipped"):
            err_body["warnings"] = ["audit_append_failed"]
        return err_body

    allowed, _rejected = assert_allowed_secret_fields(secret_payload, _INTEGRATION_TYPE)
    if not allowed:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="rotate",
            ok=False,
            error_codes=["secret_material_rejected"],
        )
        err = _make_admin_error(
            tenant_id, client_id,
            "secret_material_rejected",
            "Secret bundle contains disallowed fields.",
        )
        err["rotation_result"] = _EMPTY_ROTATION_RESULT
        err["secret_status"] = None
        if not _ar.get("ok") and not _ar.get("skipped"):
            err["warnings"] = ["audit_append_failed"]
        return err

    # D. Resolve SecretStore (injected for tests; factory for production)
    if secret_store is None:
        secret_store = create_secret_store()

    # E. Write new bundle — secret_payload lives only in this local scope; no get_secret_bundle()
    try:
        secret_store.put_secret_bundle(
            credential_ref=_credential_ref,
            integration_type=_INTEGRATION_TYPE,
            secrets=secret_payload,
        )
    except Exception:
        _ar = _emit_credential_audit_event(
            tenant_id, client_id,
            operation="rotate",
            ok=False,
            error_codes=["secret_write_failed"],
        )
        err = _make_admin_error(
            tenant_id, client_id,
            "secret_write_failed",
            "Failed to write new secret bundle. Check secret store configuration.",
            recoverable=True,
        )
        err["rotation_result"] = _EMPTY_ROTATION_RESULT
        err["secret_status"] = None
        if not _ar.get("ok") and not _ar.get("skipped"):
            err["warnings"] = ["audit_append_failed"]
        return err

    # F. Validate structurally via get_secret_status() only — no get_secret_bundle(), no API
    try:
        secret_status_result = secret_store.get_secret_status(
            credential_ref=_credential_ref,
            integration_type=_INTEGRATION_TYPE,
        )
    except Exception:
        secret_status_result = {"configured": False, "configured_fields": {}}

    configured_fields_map: Dict[str, bool] = secret_status_result.get("configured_fields") or {}
    post_write_missing: List[str] = [
        f for f in GOOGLE_ADS_SECRET_FIELDS
        if not configured_fields_map.get(f)
    ]
    structurally_complete: bool = len(post_write_missing) == 0

    # G. Update CredentialReference status and last_validated_at
    last_validated_at: str = now_utc_iso()
    new_status: str = (
        CredentialStatus.ACTIVE.value if structurally_complete
        else CredentialStatus.VALIDATION_FAILED.value
    )
    updated_credential_status: Optional[Dict[str, Any]] = None
    try:
        updated_ref = update_credential_status(ref, new_status, last_validated_at=last_validated_at)
        ref_store.put_reference(updated_ref)
        updated_credential_status = ref_store.get_status(tenant_id, client_id, _INTEGRATION_TYPE)
    except Exception:
        pass  # persist failure is non-fatal

    # H. Emit audit event — ok reflects structural completeness
    rotate_ok: bool = structurally_complete
    audit_error_codes: List[str] = [] if structurally_complete else ["secret_bundle_incomplete"]
    _ar = _emit_credential_audit_event(
        tenant_id, client_id,
        operation="rotate",
        ok=rotate_ok,
        error_codes=audit_error_codes,
    )

    # I. Return redacted result — no secret values, no credential_ref, no secret_id
    result: Dict[str, Any] = {
        "ok": rotate_ok,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "integration_type": _INTEGRATION_TYPE,
        "rotation_result": {
            "structurally_complete": structurally_complete,
            "missing_fields": post_write_missing,
            "last_validated_at": last_validated_at,
        },
        "credential_status": updated_credential_status,
        "secret_status": secret_status_result,
        "errors": [],
    }
    if not structurally_complete:
        result["errors"] = [
            {
                "code": "secret_bundle_incomplete",
                "message": f"Secret bundle incomplete after rotation: {sorted(post_write_missing)}",
                "recoverable": True,
                "source": "openclaw_admin",
            }
        ]
    if not _ar.get("ok") and not _ar.get("skipped"):
        result.setdefault("warnings", []).append("audit_append_failed")
    return result

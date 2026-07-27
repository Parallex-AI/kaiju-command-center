"""
V5.5 / V5.6 / V5.14 — OpenClaw admin helper for credential reference operations.

V5.5: get_google_ads_credential_status — read-only status lookup
V5.6: upsert_google_ads_credential_reference — create/update CredentialReference (no secrets)
V5.14: write_google_ads_credential_bundle — write full credential bundle (metadata →
  LocalFileCredentialReferenceStore, secrets → SecretStore). Routes to
  GCPSecretManagerStore or InMemorySecretStore based on GCP_SECRET_MANAGER_ENABLED.
  Secret values are never returned, logged, or echoed.

No secret values are returned by any function in this module.
"""

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
) -> None:
    """Emit a credential audit event. Swallows all exceptions — never affects write outcome."""
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
        append_audit_event(event)
    except Exception:
        pass


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
        _emit_credential_audit_event(tenant_id, client_id, operation="metadata_upsert", ok=True)
        return {
            "ok": True,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "integration_type": _INTEGRATION_TYPE,
            "credential_status": credential_status,
            "errors": [],
        }

    except ValueError:
        _emit_credential_audit_event(
            tenant_id, client_id,
            operation="metadata_upsert",
            ok=False,
            error_codes=["invalid_credential_reference"],
        )
        return _make_admin_error(
            tenant_id, client_id,
            "invalid_credential_reference",
            "Credential reference is invalid. Check field values.",
        )
    except Exception:
        _emit_credential_audit_event(
            tenant_id, client_id,
            operation="metadata_upsert",
            ok=False,
            error_codes=["credential_write_failed"],
        )
        return _make_admin_error(
            tenant_id, client_id,
            "credential_write_failed",
            "Failed to write credential reference. Check store configuration.",
            recoverable=True,
        )


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
        _emit_credential_audit_event(
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
        return err

    _emit_credential_audit_event(tenant_id, client_id, operation="bundle_write", ok=True)

    # 11–12. Get redacted secret status (no secret values — configured_fields booleans only)
    try:
        secret_status_result = secret_store.get_secret_status(
            credential_ref=credential_ref,
            integration_type=_INTEGRATION_TYPE,
        )
    except Exception:
        secret_status_result = None

    # 13. Return combined redacted response — no secret values anywhere
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "client_id": client_id,
        "integration_type": _INTEGRATION_TYPE,
        "credential_status": ref_result.get("credential_status"),
        "secret_status": secret_status_result,
        "errors": [],
    }

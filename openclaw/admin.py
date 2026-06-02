"""
V5.5 / V5.6 — OpenClaw admin helper for credential reference operations.

V5.5: get_google_ads_credential_status — read-only status lookup
V5.6: upsert_google_ads_credential_reference — create/update CredentialReference (no secrets)

No secret material is accepted, stored, or returned by any function in this module.
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

_INTEGRATION_TYPE = "google_ads"
_VALID_STATUSES = frozenset(s.value for s in CredentialStatus)

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
        return {
            "ok": True,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "integration_type": _INTEGRATION_TYPE,
            "credential_status": credential_status,
            "errors": [],
        }

    except ValueError:
        return _make_admin_error(
            tenant_id, client_id,
            "invalid_credential_reference",
            "Credential reference is invalid. Check field values.",
        )
    except Exception:
        return _make_admin_error(
            tenant_id, client_id,
            "credential_write_failed",
            "Failed to write credential reference. Check store configuration.",
            recoverable=True,
        )

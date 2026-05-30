"""
V5.2 — CredentialReference data model and metadata helpers.

This module contains only metadata: tenant/client identity, integration type,
credential status, and a credential_ref pointer to the secret backend.
No secret values (tokens, secrets, OAuth codes) are stored or returned here.
"""

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class CredentialStatus(Enum):
    MISSING = "missing"
    CONFIGURED = "configured"
    INVALID = "invalid"
    VALIDATION_FAILED = "validation_failed"
    ACTIVE = "active"
    REVOKED = "revoked"


class IntegrationType(Enum):
    GOOGLE_ADS = "google_ads"


_VALID_STATUSES: frozenset = frozenset(s.value for s in CredentialStatus)
_VALID_INTEGRATION_TYPES: frozenset = frozenset(t.value for t in IntegrationType)
_CONFIGURED_STATUSES: frozenset = frozenset({
    CredentialStatus.CONFIGURED.value,
    CredentialStatus.ACTIVE.value,
})

_SECRET_KEY_SUBSTRINGS: Tuple[str, ...] = (
    "token",
    "secret",
    "password",
    "credential",
    "authorization",
    "auth_header",
    "oauth_code",
    "refresh",
    "access",
)


@dataclass
class CredentialReference:
    """
    Metadata record for a tenant/client integration credential.

    Contains only non-secret fields. The actual secret material lives in the
    secret backend, referenced by credential_ref. This object is safe to log,
    audit, or pass through graph state — it never holds developer tokens,
    client secrets, refresh tokens, or OAuth codes.
    """

    tenant_id: str
    client_id: str
    integration_type: str
    credential_ref: str
    customer_id: Optional[str] = None
    login_customer_id: Optional[str] = None
    status: str = CredentialStatus.MISSING.value
    last_validated_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sanitize_identifier(value: str) -> str:
    """Lowercase, strip, replace unsafe chars with hyphens, collapse duplicates."""
    if not value or not value.strip():
        return "unknown"
    v = value.strip().lower()
    v = re.sub(r"[^a-z0-9_\-]", "-", v)
    v = re.sub(r"-+", "-", v)
    v = v.strip("-")
    return v or "unknown"


def make_credential_ref(tenant_id: str, client_id: str, integration_type: str) -> str:
    """
    Generate a deterministic, opaque credential reference.

    Uses a 12-char SHA-256 prefix to avoid leaking tenant or client names
    in the reference value while keeping it stable across calls with the
    same inputs.
    """
    raw = f"{tenant_id}|{client_id}|{integration_type}"
    short_hash = hashlib.sha256(raw.encode()).hexdigest()[:12]
    safe_type = sanitize_identifier(integration_type)
    return f"cred_{safe_type}_{short_hash}"


def filter_safe_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Return metadata with any potentially secret-bearing keys removed.

    Keys are matched case-insensitively against _SECRET_KEY_SUBSTRINGS.
    Filtered keys are dropped silently — no error is raised.
    """
    if not metadata:
        return {}
    result = {}
    for k, v in metadata.items():
        if any(sub in str(k).lower() for sub in _SECRET_KEY_SUBSTRINGS):
            continue
        result[k] = v
    return result


def create_credential_reference(
    tenant_id: str,
    client_id: str,
    integration_type: str = IntegrationType.GOOGLE_ADS.value,
    customer_id: Optional[str] = None,
    login_customer_id: Optional[str] = None,
    status: str = CredentialStatus.MISSING.value,
    metadata: Optional[Dict[str, Any]] = None,
) -> CredentialReference:
    """
    Create a new CredentialReference with sanitized IDs and filtered metadata.

    Sets created_at and updated_at to the current UTC time. Generates a
    deterministic credential_ref. No secrets are stored.
    """
    safe_tenant = sanitize_identifier(tenant_id)
    safe_client = sanitize_identifier(client_id)
    safe_type = sanitize_identifier(integration_type)
    now = now_utc_iso()
    credential_ref = make_credential_ref(tenant_id, client_id, integration_type)
    safe_meta = filter_safe_metadata(metadata) or None

    resolved_status = status if status in _VALID_STATUSES else CredentialStatus.MISSING.value
    safe_customer_id = customer_id.strip() if customer_id and customer_id.strip() else None
    safe_login_id = login_customer_id.strip() if login_customer_id and login_customer_id.strip() else None

    return CredentialReference(
        tenant_id=safe_tenant,
        client_id=safe_client,
        integration_type=safe_type,
        credential_ref=credential_ref,
        customer_id=safe_customer_id,
        login_customer_id=safe_login_id,
        status=resolved_status,
        created_at=now,
        updated_at=now,
        metadata=safe_meta,
    )


def credential_reference_to_dict(ref: CredentialReference) -> Dict[str, Any]:
    """Return a complete, safe dict representation of the CredentialReference."""
    return {
        "tenant_id": ref.tenant_id,
        "client_id": ref.client_id,
        "integration_type": ref.integration_type,
        "credential_ref": ref.credential_ref,
        "customer_id": ref.customer_id,
        "login_customer_id": ref.login_customer_id,
        "status": ref.status,
        "last_validated_at": ref.last_validated_at,
        "created_at": ref.created_at,
        "updated_at": ref.updated_at,
        "metadata": ref.metadata,
    }


def credential_reference_to_redacted_response(ref: CredentialReference) -> Dict[str, Any]:
    """
    Return an API-safe response dict.

    Adds a 'configured' bool (true when status is 'configured' or 'active').
    No secret values are present; this shape is safe to return from any endpoint.
    """
    return {
        "tenant_id": ref.tenant_id,
        "client_id": ref.client_id,
        "integration_type": ref.integration_type,
        "credential_ref": ref.credential_ref,
        "customer_id": ref.customer_id,
        "login_customer_id": ref.login_customer_id,
        "status": ref.status,
        "configured": ref.status in _CONFIGURED_STATUSES,
        "last_validated_at": ref.last_validated_at,
        "created_at": ref.created_at,
        "updated_at": ref.updated_at,
        "metadata": ref.metadata,
    }


def validate_credential_reference(
    ref: CredentialReference,
) -> Tuple[bool, List[Dict[str, str]]]:
    """
    Validate a CredentialReference for required fields and safe content.

    Returns (True, []) on success.
    Returns (False, [error, ...]) where each error has code, field, message.
    No secret values appear in error messages.
    """
    errors: List[Dict[str, str]] = []

    if not ref.tenant_id or not ref.tenant_id.strip():
        errors.append({
            "code": "invalid_credential_reference",
            "field": "tenant_id",
            "message": "tenant_id is required",
        })

    if not ref.client_id or not ref.client_id.strip():
        errors.append({
            "code": "invalid_credential_reference",
            "field": "client_id",
            "message": "client_id is required",
        })

    if ref.integration_type not in _VALID_INTEGRATION_TYPES:
        errors.append({
            "code": "invalid_credential_reference",
            "field": "integration_type",
            "message": (
                f"integration_type must be one of: {sorted(_VALID_INTEGRATION_TYPES)}"
            ),
        })

    if not ref.credential_ref or not ref.credential_ref.strip():
        errors.append({
            "code": "invalid_credential_reference",
            "field": "credential_ref",
            "message": "credential_ref is required",
        })

    if ref.status not in _VALID_STATUSES:
        errors.append({
            "code": "invalid_credential_reference",
            "field": "status",
            "message": f"status must be one of: {sorted(_VALID_STATUSES)}",
        })

    if ref.customer_id is not None and not ref.customer_id.strip():
        errors.append({
            "code": "invalid_credential_reference",
            "field": "customer_id",
            "message": "customer_id must be non-empty when provided",
        })

    if ref.metadata:
        for k in ref.metadata:
            if any(sub in str(k).lower() for sub in _SECRET_KEY_SUBSTRINGS):
                errors.append({
                    "code": "invalid_credential_reference",
                    "field": "metadata",
                    "message": "metadata contains a potentially sensitive key",
                })
                break

    return (len(errors) == 0, errors)


def update_credential_status(
    ref: CredentialReference,
    status: str,
    last_validated_at: Optional[str] = None,
) -> CredentialReference:
    """
    Return a new CredentialReference with updated status and timestamps.

    Raises ValueError for an unrecognised status string.
    """
    if status not in _VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {sorted(_VALID_STATUSES)}"
        )
    return replace(
        ref,
        status=status,
        updated_at=now_utc_iso(),
        last_validated_at=(
            last_validated_at if last_validated_at is not None else ref.last_validated_at
        ),
    )

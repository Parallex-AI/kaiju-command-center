"""
V5.7 — Credential Resolver bridge for CredentialReference metadata.

Resolves safe CredentialReference metadata from a CredentialStore.

This is NOT a secret resolver. No developer tokens, client secrets, refresh
tokens, access tokens, or OAuth codes are read, returned, or inspected here.
The resolver returns metadata only: tenant/client identity, integration type,
status, customer_id, login_customer_id, and the opaque credential_ref pointer.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from credentials.local_file_store import LocalFileCredentialReferenceStore
from credentials.models import (
    CredentialStatus,
    IntegrationType,
    credential_reference_to_redacted_response,
    validate_credential_reference,
)
from credentials.store import CredentialStore, missing_credential_status

_RESOLVER_FORBIDDEN_KEY_SUBSTRINGS: Tuple[str, ...] = (
    "token",
    "secret",
    "password",
    "authorization",
    "auth_header",
    "oauth_code",
    "refresh",
    "access",
)


@dataclass
class ResolvedCredentialReference:
    """
    Safe, redacted result of a credential reference resolution.

    Contains only non-secret metadata. Does not hold developer tokens,
    client secrets, refresh tokens, access tokens, or OAuth codes.
    The credential_ref field is an opaque hash-based pointer to a secret
    backend — it is not itself a secret value.
    """

    ok: bool
    tenant_id: str
    client_id: str
    integration_type: str
    credential_ref: Optional[str] = None
    status: Optional[str] = None
    configured: bool = False
    customer_id: Optional[str] = None
    login_customer_id: Optional[str] = None
    metadata: Optional[Dict] = None
    errors: Optional[List[Dict]] = field(default=None)


def make_resolver_error(
    code: str,
    message: str,
    recoverable: bool = True,
) -> Dict:
    """Return a safe error dict for inclusion in ResolvedCredentialReference.errors."""
    return {
        "code": code,
        "message": message,
        "recoverable": recoverable,
        "source": "credential_resolver",
    }


def resolve_credential_reference(
    tenant_id: str,
    client_id: str,
    integration_type: str = IntegrationType.GOOGLE_ADS.value,
    store: Optional[CredentialStore] = None,
) -> ResolvedCredentialReference:
    """
    Resolve safe CredentialReference metadata for a tenant/client integration.

    Uses LocalFileCredentialReferenceStore by default if no store is provided.

    Returns ok=True with redacted metadata when a valid reference is found.
    Returns ok=False with a controlled error when the reference is missing,
    invalid, or the store cannot be read.

    Does not read, return, or inspect any secret material.
    """
    if store is None:
        store = LocalFileCredentialReferenceStore()

    try:
        ref = store.get_reference(tenant_id, client_id, integration_type)
    except Exception:
        return ResolvedCredentialReference(
            ok=False,
            tenant_id=tenant_id,
            client_id=client_id,
            integration_type=integration_type,
            errors=[make_resolver_error(
                "credential_store_unavailable",
                "Credential reference store could not be read. Check store configuration.",
                recoverable=True,
            )],
        )

    if ref is None:
        return ResolvedCredentialReference(
            ok=False,
            tenant_id=tenant_id,
            client_id=client_id,
            integration_type=integration_type,
            status=CredentialStatus.MISSING.value,
            configured=False,
            credential_ref=None,
            errors=[make_resolver_error(
                "credentials_missing",
                "No credential reference found for this tenant/client/integration.",
                recoverable=True,
            )],
        )

    valid, validation_errors = validate_credential_reference(ref)
    if not valid:
        return ResolvedCredentialReference(
            ok=False,
            tenant_id=tenant_id,
            client_id=client_id,
            integration_type=integration_type,
            errors=[make_resolver_error(
                "credential_reference_invalid",
                "Stored credential reference failed validation.",
                recoverable=False,
            )],
        )

    redacted = credential_reference_to_redacted_response(ref)
    return ResolvedCredentialReference(
        ok=True,
        tenant_id=redacted["tenant_id"],
        client_id=redacted["client_id"],
        integration_type=redacted["integration_type"],
        credential_ref=redacted["credential_ref"],
        status=redacted["status"],
        configured=redacted["configured"],
        customer_id=redacted["customer_id"],
        login_customer_id=redacted["login_customer_id"],
        metadata=redacted.get("metadata"),
        errors=[],
    )


def resolved_credential_reference_to_dict(
    resolved: ResolvedCredentialReference,
) -> Dict:
    """Return a safe dict representation of a ResolvedCredentialReference."""
    return {
        "ok": resolved.ok,
        "tenant_id": resolved.tenant_id,
        "client_id": resolved.client_id,
        "integration_type": resolved.integration_type,
        "credential_ref": resolved.credential_ref,
        "status": resolved.status,
        "configured": resolved.configured,
        "customer_id": resolved.customer_id,
        "login_customer_id": resolved.login_customer_id,
        "metadata": resolved.metadata,
        "errors": resolved.errors if resolved.errors is not None else [],
    }


def assert_resolved_reference_has_no_secret_material(
    payload: Dict,
    _path: str = "",
) -> Tuple[bool, List[str]]:
    """
    Recursively scan dict keys for secret-like names.

    Returns (True, []) if clean.
    Returns (False, [offending key paths]) if any forbidden substrings are found.
    Values are not inspected — key names are sufficient for the check.
    """
    offending: List[str] = []
    for key, value in payload.items():
        full_path = f"{_path}.{key}" if _path else str(key)
        if any(sub in str(key).lower() for sub in _RESOLVER_FORBIDDEN_KEY_SUBSTRINGS):
            offending.append(full_path)
        if isinstance(value, dict):
            _, child = assert_resolved_reference_has_no_secret_material(value, _path=full_path)
            offending.extend(child)
    return (len(offending) == 0, offending)

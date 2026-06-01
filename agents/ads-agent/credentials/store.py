"""
V5.3 — CredentialStore abstraction and InMemoryCredentialStore.

Defines:
- CredentialStore: abstract base for reference-only credential metadata storage
- InMemoryCredentialStore: in-memory implementation for dev and testing
- make_store_key: deterministic composite key
- missing_credential_status: redacted status shape when no credential is configured
- assert_no_secret_material: recursive key-name scanner for secret-like fields

No secret material (tokens, secrets, OAuth codes) is stored, returned, or
passed through any method in this module.
"""

import copy
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

from credentials.models import (
    CredentialReference,
    CredentialStatus,
    IntegrationType,
    create_credential_reference,
    credential_reference_to_redacted_response,
    update_credential_status,
    validate_credential_reference,
)

_FORBIDDEN_KEY_SUBSTRINGS: Tuple[str, ...] = (
    "token",
    "secret",
    "password",
    "authorization",
    "oauth_code",
    "refresh",
    "access",
)


def make_store_key(tenant_id: str, client_id: str, integration_type: str) -> str:
    """Return a deterministic composite key: 'tenant_id/client_id/integration_type'."""
    return f"{tenant_id}/{client_id}/{integration_type}"


def missing_credential_status(
    tenant_id: str,
    client_id: str,
    integration_type: str,
) -> dict:
    """Return a redacted status shape for a credential that has not been configured."""
    return {
        "tenant_id": tenant_id,
        "client_id": client_id,
        "integration_type": integration_type,
        "credential_ref": None,
        "customer_id": None,
        "login_customer_id": None,
        "status": CredentialStatus.MISSING.value,
        "configured": False,
        "last_validated_at": None,
        "created_at": None,
        "updated_at": None,
        "metadata": {},
    }


def assert_no_secret_material(
    payload: dict,
    _path: str = "",
) -> Tuple[bool, List[str]]:
    """
    Recursively scan dict keys for secret-like names.

    Returns (True, []) if clean.
    Returns (False, [offending key paths]) if any forbidden substrings are found.
    Values are not inspected — key names are sufficient.
    """
    offending: List[str] = []
    for key, value in payload.items():
        full_path = f"{_path}.{key}" if _path else str(key)
        if any(sub in str(key).lower() for sub in _FORBIDDEN_KEY_SUBSTRINGS):
            offending.append(full_path)
        if isinstance(value, dict):
            _, child_offending = assert_no_secret_material(value, _path=full_path)
            offending.extend(child_offending)
    return (len(offending) == 0, offending)


class CredentialStore(ABC):
    """
    Abstract interface for tenant/client credential reference metadata storage.

    Stores CredentialReference objects only. Secret material (developer tokens,
    client secrets, refresh tokens, OAuth codes) must never be passed to or
    returned from any method defined here.
    """

    @abstractmethod
    def put_reference(self, ref: CredentialReference) -> CredentialReference:
        """
        Validate and store a CredentialReference.

        Raises ValueError if the reference is invalid or if its metadata contains
        any key whose name matches a forbidden secret-like substring.
        Returns a safe copy of the stored reference.
        """
        ...

    @abstractmethod
    def get_reference(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: str,
    ) -> Optional[CredentialReference]:
        """Return the stored CredentialReference, or None if not found."""
        ...

    @abstractmethod
    def get_status(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: str,
    ) -> dict:
        """
        Return the redacted status dict for a stored reference.

        Returns missing_credential_status(...) if no reference is found.
        The returned dict is safe to surface from any endpoint — no secret values.
        """
        ...

    @abstractmethod
    def update_status(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: str,
        status: str,
        last_validated_at: Optional[str] = None,
    ) -> Optional[CredentialReference]:
        """
        Update the status on a stored reference.

        Returns the updated CredentialReference, or None if not found.
        Raises ValueError for an unrecognised status string.
        """
        ...

    @abstractmethod
    def delete_reference(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: str,
    ) -> bool:
        """Delete a stored reference. Returns True if deleted, False if not found."""
        ...

    @abstractmethod
    def list_references(
        self,
        tenant_id: Optional[str] = None,
    ) -> List[CredentialReference]:
        """
        Return stored references, optionally filtered by tenant_id.

        Returns copies — callers cannot mutate the store through the returned objects.
        """
        ...


class InMemoryCredentialStore(CredentialStore):
    """
    In-memory CredentialReference store for development and testing.

    Uses a dict keyed by make_store_key(tenant_id, client_id, integration_type).
    All returned objects are deep copies to prevent accidental mutation.
    Not thread-safe. Not persistent across process restarts.
    No secret material is stored or returned.
    """

    def __init__(self) -> None:
        self._store: Dict[str, CredentialReference] = {}

    def put_reference(self, ref: CredentialReference) -> CredentialReference:
        valid, errors = validate_credential_reference(ref)
        if not valid:
            safe_codes = [e.get("code", "invalid") for e in errors]
            safe_fields = [e.get("field", "unknown") for e in errors]
            raise ValueError(
                f"CredentialReference is invalid — codes: {safe_codes}, fields: {safe_fields}"
            )
        if ref.metadata:
            clean, offending = assert_no_secret_material(ref.metadata)
            if not clean:
                raise ValueError(
                    f"CredentialReference metadata contains secret-like keys: {offending}"
                )
        key = make_store_key(ref.tenant_id, ref.client_id, ref.integration_type)
        self._store[key] = copy.deepcopy(ref)
        return copy.deepcopy(ref)

    def get_reference(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: str,
    ) -> Optional[CredentialReference]:
        key = make_store_key(tenant_id, client_id, integration_type)
        stored = self._store.get(key)
        if stored is None:
            return None
        return copy.deepcopy(stored)

    def get_status(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: str,
    ) -> dict:
        ref = self.get_reference(tenant_id, client_id, integration_type)
        if ref is None:
            return missing_credential_status(tenant_id, client_id, integration_type)
        return credential_reference_to_redacted_response(ref)

    def update_status(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: str,
        status: str,
        last_validated_at: Optional[str] = None,
    ) -> Optional[CredentialReference]:
        key = make_store_key(tenant_id, client_id, integration_type)
        stored = self._store.get(key)
        if stored is None:
            return None
        updated = update_credential_status(stored, status, last_validated_at)
        self._store[key] = copy.deepcopy(updated)
        return copy.deepcopy(updated)

    def delete_reference(
        self,
        tenant_id: str,
        client_id: str,
        integration_type: str,
    ) -> bool:
        key = make_store_key(tenant_id, client_id, integration_type)
        if key in self._store:
            del self._store[key]
            return True
        return False

    def list_references(
        self,
        tenant_id: Optional[str] = None,
    ) -> List[CredentialReference]:
        refs = list(self._store.values())
        if tenant_id is not None:
            refs = [r for r in refs if r.tenant_id == tenant_id]
        return [copy.deepcopy(r) for r in refs]

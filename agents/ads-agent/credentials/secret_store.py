"""
V5.8 — SecretStore abstraction and InMemorySecretStore.

Defines the contract for storing and retrieving secret bundles for integrations.
Secret bundles hold the actual credential values (developer_token, client_id,
client_secret, refresh_token) that are needed by adapters at runtime.

SecretRecord — redacted descriptor of which fields are configured; no values.
SecretStore — abstract base for secret bundle storage backends.
InMemorySecretStore — in-memory implementation for dev and testing only.

Non-secret fields (customer_id, login_customer_id) are NOT stored here.
Those belong in CredentialReference metadata (see models.py / local_file_store.py).

get_secret_bundle() returns raw secret values for internal adapter use only.
It must never be called in logging, audit, or API response paths.
No secrets are written to disk by any class in this module.
"""

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from credentials.models import IntegrationType, now_utc_iso

# ---------------------------------------------------------------------------
# Secret field registry
# ---------------------------------------------------------------------------

GOOGLE_ADS_SECRET_FIELDS: Tuple[str, ...] = (
    "developer_token",
    "client_id",
    "client_secret",
    "refresh_token",
)

_GOOGLE_ADS_SECRET_FIELD_SET: frozenset = frozenset(GOOGLE_ADS_SECRET_FIELDS)

# Fields always rejected regardless of integration type.
# access_token and oauth_code are ephemeral and must not be stored.
_GLOBALLY_REJECTED_FIELDS: frozenset = frozenset({
    "access_token",
    "oauth_code",
    "password",
    "authorization",
    "auth_header",
})

_INTEGRATION_ALLOWED_FIELDS: Dict[str, frozenset] = {
    IntegrationType.GOOGLE_ADS.value: _GOOGLE_ADS_SECRET_FIELD_SET,
}

_INTEGRATION_REQUIRED_FIELDS: Dict[str, Tuple[str, ...]] = {
    IntegrationType.GOOGLE_ADS.value: GOOGLE_ADS_SECRET_FIELDS,
}

# Value markers used in tests/demos to simulate fake secrets.
# These are checked by assert_no_secret_values_in_payload to verify that
# demo output dicts do not accidentally expose test fixture values.
_DEMO_SECRET_MARKERS: Tuple[str, ...] = (
    "fake-dev-token",
    "fake-client-secret",
    "fake-refresh-token",
    "ya29",
    "sk-",
)


# ---------------------------------------------------------------------------
# SecretRecord — contains no secret values
# ---------------------------------------------------------------------------

@dataclass
class SecretRecord:
    """
    Redacted descriptor of a stored secret bundle.

    Contains only which fields are configured, not their values.
    Safe to log, return from APIs, or pass through graph state.
    Never holds developer_token, client_secret, refresh_token, or client_id values.
    """

    credential_ref: str
    integration_type: str
    configured_fields: List[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_secret_store_key(credential_ref: str, integration_type: str) -> str:
    """Return a deterministic composite key: 'credential_ref/integration_type'."""
    return f"{credential_ref}/{integration_type}"


def assert_allowed_secret_fields(
    secrets: dict,
    integration_type: str,
) -> Tuple[bool, List[str]]:
    """
    Validate that all keys in secrets are in the allowed set for the integration type.

    Rejects globally forbidden fields (access_token, oauth_code, etc.) and
    any field not in the integration-specific allowed list.

    Returns (True, []) when all fields are valid.
    Returns (False, [rejected fields]) when any field is disallowed.
    """
    allowed = _INTEGRATION_ALLOWED_FIELDS.get(integration_type, frozenset())
    rejected: List[str] = []
    for key in secrets:
        if key in _GLOBALLY_REJECTED_FIELDS or key not in allowed:
            rejected.append(key)
    return (len(rejected) == 0, rejected)


def redact_secret_status(
    credential_ref: str,
    integration_type: str,
    configured_fields: List[str],
    metadata: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Return a safe, redacted status dict for a stored secret bundle.

    configured_fields maps each expected field name to a bool (present/absent).
    configured is True only when all required fields are present.
    No secret values are included.
    """
    required = _INTEGRATION_REQUIRED_FIELDS.get(integration_type, ())
    field_map: Dict[str, bool] = {
        field: (field in configured_fields) for field in required
    }
    all_configured = bool(field_map) and all(field_map.values())
    return {
        "credential_ref": credential_ref,
        "integration_type": integration_type,
        "configured": all_configured,
        "configured_fields": field_map,
        "metadata": metadata,
    }


def assert_no_secret_values_in_payload(
    payload: dict,
    _path: str = "",
) -> Tuple[bool, List[str]]:
    """
    Recursively scan dict values for known demo/test secret markers.

    Used in demos and tests to confirm that redacted output dicts do not
    accidentally contain test fixture values. Scans string values only.
    Markers: fake-dev-token, fake-client-secret, fake-refresh-token, ya29, sk-.
    """
    offending: List[str] = []
    for key, value in payload.items():
        full_path = f"{_path}.{key}" if _path else str(key)
        if isinstance(value, str):
            if any(marker in value for marker in _DEMO_SECRET_MARKERS):
                offending.append(full_path)
        elif isinstance(value, dict):
            _, child = assert_no_secret_values_in_payload(value, _path=full_path)
            offending.extend(child)
    return (len(offending) == 0, offending)


# ---------------------------------------------------------------------------
# SecretStore ABC
# ---------------------------------------------------------------------------

class SecretStore(ABC):
    """
    Abstract interface for storing and retrieving secret bundles.

    Stores Google Ads secrets: developer_token, client_id, client_secret,
    refresh_token. Non-secret fields (customer_id, login_customer_id) must
    NOT be stored here — those belong in CredentialReference.

    get_secret_bundle() is the only method that returns raw values.
    It is intended for internal adapter use only and must never be called
    in logging, audit, or API response paths.
    """

    @abstractmethod
    def put_secret_bundle(
        self,
        credential_ref: str,
        integration_type: str,
        secrets: dict,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SecretRecord:
        """
        Store a secret bundle and return a redacted SecretRecord.

        Validates allowed fields for the integration type.
        Rejects empty values, forbidden fields, and unknown fields.
        Returns SecretRecord only — never echoes secret values.
        Raises ValueError for invalid or empty fields.
        """
        ...

    @abstractmethod
    def get_secret_bundle(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> Optional[dict]:
        """
        Return the raw secret bundle for internal adapter use only.

        Returns None if not found.
        Callers are responsible for never logging or returning these values.
        This method must not be called from logging, audit, or API paths.
        """
        ...

    @abstractmethod
    def get_secret_status(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> dict:
        """
        Return a redacted status dict. Safe for logging and API responses.

        Uses redact_secret_status() — no secret values are present.
        Returns an unconfigured shape when no bundle is stored.
        """
        ...

    @abstractmethod
    def delete_secret_bundle(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> bool:
        """Delete a stored bundle. Returns True if deleted, False if not found."""
        ...

    @abstractmethod
    def list_secret_records(
        self,
        integration_type: Optional[str] = None,
    ) -> List[SecretRecord]:
        """
        Return SecretRecord list, optionally filtered by integration_type.

        Returns only SecretRecord objects — no raw secret values.
        """
        ...


# ---------------------------------------------------------------------------
# InMemorySecretStore
# ---------------------------------------------------------------------------

class InMemorySecretStore(SecretStore):
    """
    In-memory SecretStore for development and testing only.

    Stores secret bundles in a dict keyed by make_secret_store_key().
    All returned bundles from get_secret_bundle() are deep copies.
    Not thread-safe. Not persistent — secrets are lost on process restart.
    Never writes to disk.
    """

    def __init__(self) -> None:
        self._bundles: Dict[str, dict] = {}
        self._records: Dict[str, SecretRecord] = {}

    def put_secret_bundle(
        self,
        credential_ref: str,
        integration_type: str,
        secrets: dict,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SecretRecord:
        if not secrets:
            raise ValueError("secrets dict must not be empty")

        allowed, rejected = assert_allowed_secret_fields(secrets, integration_type)
        if not allowed:
            raise ValueError(
                f"Secrets contain disallowed fields for '{integration_type}': {rejected}"
            )

        empty_fields = [k for k, v in secrets.items() if not v or not str(v).strip()]
        if empty_fields:
            raise ValueError(
                f"Secret fields must not be empty: {empty_fields}"
            )

        key = make_secret_store_key(credential_ref, integration_type)
        now = now_utc_iso()
        existing = self._records.get(key)
        created_at = existing.created_at if existing else now

        self._bundles[key] = copy.deepcopy(secrets)
        record = SecretRecord(
            credential_ref=credential_ref,
            integration_type=integration_type,
            configured_fields=sorted(secrets.keys()),
            created_at=created_at,
            updated_at=now,
            metadata=copy.deepcopy(metadata) if metadata else None,
        )
        self._records[key] = record
        return copy.deepcopy(record)

    def get_secret_bundle(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> Optional[dict]:
        key = make_secret_store_key(credential_ref, integration_type)
        bundle = self._bundles.get(key)
        if bundle is None:
            return None
        return copy.deepcopy(bundle)

    def get_secret_status(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> dict:
        key = make_secret_store_key(credential_ref, integration_type)
        record = self._records.get(key)
        if record is None:
            return redact_secret_status(
                credential_ref,
                integration_type,
                configured_fields=[],
            )
        return redact_secret_status(
            credential_ref,
            integration_type,
            configured_fields=record.configured_fields,
            metadata=record.metadata,
        )

    def delete_secret_bundle(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> bool:
        key = make_secret_store_key(credential_ref, integration_type)
        if key in self._bundles:
            del self._bundles[key]
            del self._records[key]
            return True
        return False

    def list_secret_records(
        self,
        integration_type: Optional[str] = None,
    ) -> List[SecretRecord]:
        records = list(self._records.values())
        if integration_type is not None:
            records = [r for r in records if r.integration_type == integration_type]
        return [copy.deepcopy(r) for r in records]

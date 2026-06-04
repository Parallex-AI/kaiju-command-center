"""
V5.12.6 — Google Ads CredentialProvider composition layer.

V5.12.6: compose_google_ads_credentials now uses SecretStoreFactory when no
explicit secret_store is provided. Default behavior is unchanged — InMemorySecretStore
is still selected when GCP_SECRET_MANAGER_ENABLED=false (the default). When
GCP_SECRET_MANAGER_ENABLED=true, GCPSecretManagerStore is selected automatically.
Passing an explicit secret_store= bypasses the factory entirely (used in all tests).

V5.9 original: Composes a complete set of Google Ads credentials by combining:
- CredentialReference metadata (customer_id, login_customer_id) from the resolver
- Secret bundle (developer_token, client_id, client_secret, refresh_token) from a SecretStore

The result carries a GoogleAdsCredentials object internally for adapter use.
Redacted output (configured_fields booleans only) is safe for logging and APIs.
Raw credentials must never be printed, serialized to JSON, or returned from endpoints.

This layer is not wired into the live adapter path yet. Existing env-var credential
loading (load_google_ads_credentials) is unchanged.
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure agents/ads-agent/ is on sys.path so integrations is importable
_ADS_AGENT_DIR = str(Path(__file__).resolve().parents[1])
if _ADS_AGENT_DIR not in sys.path:
    sys.path.insert(0, _ADS_AGENT_DIR)

from credentials.models import IntegrationType
from credentials.resolver import resolve_credential_reference
from credentials.secret_store import SecretStore
from integrations.google_ads_adapter import GoogleAdsCredentials

_INTEGRATION_TYPE = IntegrationType.GOOGLE_ADS.value

_REQUIRED_SECRET_FIELDS: Tuple[str, ...] = (
    "developer_token",
    "client_id",
    "client_secret",
    "refresh_token",
)

_ALL_CREDENTIAL_FIELDS: Tuple[str, ...] = (
    "developer_token",
    "client_id",
    "client_secret",
    "refresh_token",
    "customer_id",
    "login_customer_id",
)

_PROVIDER_VALUE_MARKERS: Tuple[str, ...] = (
    "fake-dev-token",
    "fake-client-secret",
    "fake-refresh-token",
    "ya29",
    "sk-",
)


@dataclass
class GoogleAdsCredentialProviderResult:
    """
    Result of credential composition.

    May carry a GoogleAdsCredentials object in `credentials` for internal adapter use.
    The `credentials` field is excluded from repr to prevent accidental printing.
    Use google_ads_provider_result_to_redacted_dict() for any output or logging.
    """

    ok: bool
    tenant_id: str
    client_id: str
    credential_ref: Optional[str] = None
    credentials: Optional[GoogleAdsCredentials] = field(default=None, repr=False)
    source: str = "credential_provider"
    errors: Optional[List[Dict]] = field(default=None)
    metadata: Optional[Dict[str, Any]] = None


def make_provider_error(
    code: str,
    message: str,
    recoverable: bool = True,
) -> Dict:
    """Return a safe error dict for GoogleAdsCredentialProviderResult.errors."""
    return {
        "code": code,
        "message": message,
        "recoverable": recoverable,
        "source": "google_ads_credential_provider",
    }


def compose_google_ads_credentials(
    tenant_id: str,
    client_id: str,
    secret_store: Optional[SecretStore] = None,
) -> GoogleAdsCredentialProviderResult:
    """
    Compose a complete GoogleAdsCredentials from CredentialReference + SecretStore.

    Step 1: Resolve non-secret metadata (customer_id, login_customer_id) from the
    credential reference store (LocalFileCredentialReferenceStore by default).
    Step 2: Fetch the secret bundle from the secret_store.
    Step 3: Validate the bundle has all required secret fields.
    Step 4: Compose and return GoogleAdsCredentials.

    The resulting credentials object is for internal adapter use only.
    It must never be logged, printed, or returned from any API endpoint.
    """
    if secret_store is None:
        from credentials.secret_store_factory import create_secret_store
        secret_store = create_secret_store()

    # Step 1: Resolve CredentialReference metadata
    resolved = resolve_credential_reference(tenant_id, client_id, _INTEGRATION_TYPE)

    if not resolved.ok:
        error_code = (
            resolved.errors[0]["code"]
            if resolved.errors
            else "credentials_missing"
        )
        return GoogleAdsCredentialProviderResult(
            ok=False,
            tenant_id=tenant_id,
            client_id=client_id,
            errors=[make_provider_error(
                error_code,
                "Credential reference could not be resolved.",
                recoverable=True,
            )],
        )

    if not resolved.configured:
        return GoogleAdsCredentialProviderResult(
            ok=False,
            tenant_id=tenant_id,
            client_id=client_id,
            credential_ref=resolved.credential_ref,
            errors=[make_provider_error(
                "credential_reference_not_configured",
                (
                    f"Credential reference has status '{resolved.status}' which is "
                    "not configured or active."
                ),
                recoverable=True,
            )],
        )

    credential_ref = resolved.credential_ref

    # Step 2: Fetch secret bundle
    bundle = secret_store.get_secret_bundle(credential_ref, _INTEGRATION_TYPE)

    if bundle is None:
        return GoogleAdsCredentialProviderResult(
            ok=False,
            tenant_id=tenant_id,
            client_id=client_id,
            credential_ref=credential_ref,
            errors=[make_provider_error(
                "secret_bundle_missing",
                "No secret bundle found for this credential reference.",
                recoverable=True,
            )],
        )

    # Step 3: Validate bundle completeness
    missing_fields = [
        f for f in _REQUIRED_SECRET_FIELDS
        if not bundle.get(f) or not str(bundle[f]).strip()
    ]
    if missing_fields:
        return GoogleAdsCredentialProviderResult(
            ok=False,
            tenant_id=tenant_id,
            client_id=client_id,
            credential_ref=credential_ref,
            errors=[make_provider_error(
                "secret_bundle_incomplete",
                f"Secret bundle is missing required fields: {sorted(missing_fields)}",
                recoverable=False,
            )],
        )

    # Step 4: Compose GoogleAdsCredentials
    credentials = GoogleAdsCredentials(
        developer_token=bundle["developer_token"],
        client_id=bundle["client_id"],
        client_secret=bundle["client_secret"],
        refresh_token=bundle["refresh_token"],
        customer_id=resolved.customer_id,
        login_customer_id=resolved.login_customer_id,
    )

    return GoogleAdsCredentialProviderResult(
        ok=True,
        tenant_id=tenant_id,
        client_id=client_id,
        credential_ref=credential_ref,
        credentials=credentials,
        errors=[],
    )


def google_ads_provider_result_to_redacted_dict(
    result: GoogleAdsCredentialProviderResult,
) -> Dict:
    """
    Return a safe, redacted dict for logging or API responses.

    configured_fields shows which credential fields are present (True/False)
    without exposing their values. Actual credential values are never included.
    """
    creds = result.credentials
    configured_fields = {
        field_name: bool(creds and getattr(creds, field_name, None))
        for field_name in _ALL_CREDENTIAL_FIELDS
    }
    return {
        "ok": result.ok,
        "tenant_id": result.tenant_id,
        "client_id": result.client_id,
        "credential_ref": result.credential_ref,
        "source": result.source,
        "credentials_configured": bool(result.ok and creds is not None),
        "configured_fields": configured_fields,
        "metadata": result.metadata,
        "errors": result.errors if result.errors is not None else [],
    }


def assert_provider_output_has_no_secret_values(
    payload: Dict,
    _path: str = "",
) -> Tuple[bool, List[str]]:
    """
    Recursively scan dict values for known demo/test secret markers.

    Used in demos and tests to confirm that redacted output dicts do not
    accidentally contain test fixture values. Scans string values only.
    """
    offending: List[str] = []
    for key, value in payload.items():
        full_path = f"{_path}.{key}" if _path else str(key)
        if isinstance(value, str):
            if any(marker in value for marker in _PROVIDER_VALUE_MARKERS):
                offending.append(full_path)
        elif isinstance(value, dict):
            _, child = assert_provider_output_has_no_secret_values(value, _path=full_path)
            offending.extend(child)
    return (len(offending) == 0, offending)

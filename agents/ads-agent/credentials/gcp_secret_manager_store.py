"""
V5.12.2 — GCPSecretManagerStore scaffold with lazy import guard.

Provides a GCP Secret Manager backend for SecretStore.
In V5.12.2, no live GCP API calls are made. All methods return controlled
disabled/not_implemented responses. Live read/write is implemented in V5.12.3.

Environment variables:
  GCP_SECRET_MANAGER_ENABLED   — default false; gate for all live calls
  GCP_PROJECT_ID               — GCP project; fallback: GOOGLE_CLOUD_PROJECT
  GCP_SECRET_MANAGER_PREFIX    — secret name prefix; default: kaiju
  GCP_SECRET_MANAGER_ENV       — name segment; default: local; allowed: local, dev, staging, prod

Secret naming convention:
  {prefix}-{env}-{integration_type}-{credential_ref}
  e.g. kaiju-prod-google-ads-cred_google_ads_abcd1234ef56

No secret values are present in this module.
"""

import copy
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from credentials.models import now_utc_iso
from credentials.secret_store import (
    SecretRecord,
    SecretStore,
    assert_allowed_secret_fields,
    make_secret_store_key,
    redact_secret_status,
)


# ---------------------------------------------------------------------------
# Environment config helpers
# ---------------------------------------------------------------------------

def get_gcp_secret_manager_enabled() -> bool:
    """Return True if GCP_SECRET_MANAGER_ENABLED is set to a truthy value."""
    raw = os.getenv("GCP_SECRET_MANAGER_ENABLED", "false").strip().lower()
    return raw in ("true", "1", "yes", "on")


def get_gcp_project_id() -> Optional[str]:
    """
    Return the GCP project ID from GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT.
    Returns None if neither is set or both are empty.
    """
    for var in ("GCP_PROJECT_ID", "GOOGLE_CLOUD_PROJECT"):
        val = os.getenv(var, "").strip()
        if val:
            return val
    return None


def get_gcp_secret_manager_prefix() -> str:
    """Return GCP_SECRET_MANAGER_PREFIX, default 'kaiju'."""
    return os.getenv("GCP_SECRET_MANAGER_PREFIX", "kaiju").strip() or "kaiju"


def get_gcp_secret_manager_env() -> str:
    """
    Return GCP_SECRET_MANAGER_ENV segment for secret naming.
    Allowed: local, dev, staging, prod. Invalid values fall back to 'local'.
    """
    raw = os.getenv("GCP_SECRET_MANAGER_ENV", "local").strip().lower()
    if raw in ("local", "dev", "staging", "prod"):
        return raw
    return "local"


# ---------------------------------------------------------------------------
# Secret ID / resource name builders
# ---------------------------------------------------------------------------

_SAFE_CHAR_RE = re.compile(r"[^A-Za-z0-9\-_]")


def _sanitize_segment(value: str) -> str:
    """Replace any character not in [A-Za-z0-9-_] with an underscore, lowercase."""
    return _SAFE_CHAR_RE.sub("_", value).lower()


def build_gcp_secret_id(credential_ref: str, integration_type: str) -> str:
    """
    Build a deterministic GCP Secret Manager secret ID.

    Format: {prefix}-{env}-{integration_type}-{credential_ref}
    All segments are sanitized: only letters, numbers, hyphens, underscores.
    No slashes, spaces, or secret values.
    """
    prefix = _sanitize_segment(get_gcp_secret_manager_prefix())
    env = _sanitize_segment(get_gcp_secret_manager_env())
    itype = _sanitize_segment(integration_type)
    ref = _sanitize_segment(credential_ref)
    return f"{prefix}-{env}-{itype}-{ref}"


def build_gcp_secret_resource_name(project_id: str, secret_id: str) -> str:
    """Return the full GCP Secret Manager resource name for a secret."""
    return f"projects/{project_id}/secrets/{secret_id}"


# ---------------------------------------------------------------------------
# Lazy import guard
# ---------------------------------------------------------------------------

def load_secret_manager_client_class() -> Tuple[bool, Any, List[dict]]:
    """
    Attempt to import SecretManagerServiceClient from google-cloud-secret-manager.

    Returns (True, class, []) on success.
    Returns (False, None, [error_dict]) if the package is not installed.
    Never raises.
    """
    try:
        from google.cloud import secretmanager  # type: ignore
        return True, secretmanager.SecretManagerServiceClient, []
    except ImportError:
        return False, None, [{
            "code": "gcp_dependency_missing",
            "message": (
                "google-cloud-secret-manager is not installed. "
                "Run: pip install google-cloud-secret-manager>=2.20.0"
            ),
            "recoverable": False,
        }]


# ---------------------------------------------------------------------------
# GCPSecretManagerStore
# ---------------------------------------------------------------------------

class GCPSecretManagerStore(SecretStore):
    """
    GCP Secret Manager backend for SecretStore.

    V5.12.2 scaffold: disabled mode is fully functional; enabled mode raises
    NotImplementedError for all API methods (live calls implemented in V5.12.3).

    When enabled=False (default):
      - No GCP client is instantiated.
      - No network calls are made.
      - put_secret_bundle raises RuntimeError("GCP Secret Manager is disabled").
      - get_secret_bundle returns None.
      - get_secret_status returns a redacted unconfigured shape with disabled metadata.
      - delete_secret_bundle returns False.
      - list_secret_records returns [].

    Constructor args:
      project_id — GCP project; defaults to get_gcp_project_id()
      enabled    — override get_gcp_secret_manager_enabled()
      client     — inject a pre-built SecretManagerServiceClient (for testing)
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        enabled: Optional[bool] = None,
        client: Any = None,
    ) -> None:
        self._enabled: bool = enabled if enabled is not None else get_gcp_secret_manager_enabled()
        self._project_id: Optional[str] = project_id if project_id is not None else get_gcp_project_id()
        self._client: Any = None
        self._init_errors: List[dict] = []

        if not self._enabled:
            return

        if not self._project_id:
            self._init_errors.append({
                "code": "gcp_project_id_missing",
                "message": (
                    "GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT is required when "
                    "GCP_SECRET_MANAGER_ENABLED=true."
                ),
                "recoverable": False,
            })
            return

        if client is not None:
            self._client = client
            return

        available, client_class, errors = load_secret_manager_client_class()
        if not available:
            self._init_errors.extend(errors)
            return

        try:
            self._client = client_class()
        except Exception as exc:
            self._init_errors.append({
                "code": "gcp_secret_manager_init_failed",
                "message": f"Failed to instantiate SecretManagerServiceClient: {type(exc).__name__}",
                "recoverable": False,
            })

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_disabled(self) -> None:
        if not self._enabled:
            raise RuntimeError("GCP Secret Manager is disabled")

    def _check_ready(self) -> None:
        self._check_disabled()
        if self._init_errors:
            codes = ", ".join(e.get("code", "unknown") for e in self._init_errors)
            raise RuntimeError(
                f"GCPSecretManagerStore is not ready due to init errors: {codes}"
            )

    # ------------------------------------------------------------------
    # SecretStore interface — V5.12.2 scaffold
    # ------------------------------------------------------------------

    def put_secret_bundle(
        self,
        credential_ref: str,
        integration_type: str,
        secrets: dict,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SecretRecord:
        """
        Store a secret bundle in GCP Secret Manager.

        V5.12.2: raises RuntimeError when disabled.
        Raises NotImplementedError when enabled (live write implemented in V5.12.3).
        Validates allowed fields before any network call.
        """
        self._check_disabled()

        if not secrets:
            raise ValueError("secrets dict must not be empty")
        allowed, rejected = assert_allowed_secret_fields(secrets, integration_type)
        if not allowed:
            raise ValueError(
                f"Secrets contain disallowed fields for '{integration_type}': {rejected}"
            )

        self._check_ready()
        raise NotImplementedError(
            "GCPSecretManagerStore.put_secret_bundle is not yet implemented. "
            "Live GCP write support is added in V5.12.3."
        )

    def get_secret_bundle(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> Optional[dict]:
        """
        Retrieve a secret bundle from GCP Secret Manager.

        V5.12.2: returns None when disabled or not yet implemented.
        """
        if not self._enabled:
            return None
        if self._init_errors:
            return None
        raise NotImplementedError(
            "GCPSecretManagerStore.get_secret_bundle is not yet implemented. "
            "Live GCP read support is added in V5.12.3."
        )

    def get_secret_status(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> dict:
        """
        Return a redacted status dict. Safe for logging and API responses.

        V5.12.2: returns an unconfigured shape with backend metadata when disabled.
        Returns a not_implemented shape when enabled but V5.12.3 is not yet present.
        """
        if not self._enabled:
            return redact_secret_status(
                credential_ref,
                integration_type,
                configured_fields=[],
                metadata={"backend": "gcp_secret_manager", "backend_status": "disabled"},
            )
        if self._init_errors:
            codes = [e.get("code", "unknown") for e in self._init_errors]
            return redact_secret_status(
                credential_ref,
                integration_type,
                configured_fields=[],
                metadata={"backend": "gcp_secret_manager", "backend_status": "init_error", "error_codes": codes},
            )
        return redact_secret_status(
            credential_ref,
            integration_type,
            configured_fields=[],
            metadata={"backend": "gcp_secret_manager", "backend_status": "not_implemented"},
        )

    def delete_secret_bundle(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> bool:
        """
        Delete a stored secret bundle from GCP Secret Manager.

        V5.12.2: returns False when disabled. Raises NotImplementedError when enabled.
        """
        if not self._enabled:
            return False
        self._check_ready()
        raise NotImplementedError(
            "GCPSecretManagerStore.delete_secret_bundle is not yet implemented. "
            "Live GCP delete support is added in V5.12.3."
        )

    def list_secret_records(
        self,
        integration_type: Optional[str] = None,
    ) -> List[SecretRecord]:
        """
        Return a list of SecretRecord descriptors from GCP Secret Manager.

        V5.12.2: returns [] when disabled. Raises NotImplementedError when enabled.
        """
        if not self._enabled:
            return []
        self._check_ready()
        raise NotImplementedError(
            "GCPSecretManagerStore.list_secret_records is not yet implemented. "
            "Live GCP list support is added in V5.12.3."
        )


# ---------------------------------------------------------------------------
# Status helper
# ---------------------------------------------------------------------------

def gcp_secret_manager_status() -> dict:
    """
    Return safe config status for GCP Secret Manager.

    Contains no credentials, no secret values, no project tokens.
    Safe to log or return from admin endpoints.
    """
    available, _, _ = load_secret_manager_client_class()
    return {
        "enabled": get_gcp_secret_manager_enabled(),
        "project_id_configured": get_gcp_project_id() is not None,
        "prefix": get_gcp_secret_manager_prefix(),
        "environment": get_gcp_secret_manager_env(),
        "dependency_available": available,
    }

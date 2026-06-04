"""
V5.12.4 — GCPSecretManagerStore with write behavior.

V5.12.4 adds:
  build_gcp_project_resource_name()        — projects/{project_id} resource name
  build_gcp_secret_payload()               — validate and JSON-encode secrets to bytes
  _is_gcp_already_exists()                 — classify AlreadyExists exception
  _map_gcp_write_exception_to_error_code() — map write exceptions to safe codes
  GCPSecretManagerStore.put_secret_bundle() — create_secret + add_secret_version

delete_secret_bundle and list_secret_records remain deferred (V5.12.5+).

V5.12.3 added:
  build_gcp_secret_version_resource_name() — version resource name builder
  parse_gcp_secret_payload()               — decode, validate, and parse secret bytes
  GCPSecretManagerStore.get_secret_bundle() — live read via access_secret_version
  GCPSecretManagerStore.get_secret_status() — redacted status derived from bundle result

No live GCP calls are required for tests. The constructor accepts an injected
client= parameter so a mock SecretManagerServiceClient can be used.

Environment variables:
  GCP_SECRET_MANAGER_ENABLED   — default false; gate for all live calls
  GCP_PROJECT_ID               — GCP project; fallback: GOOGLE_CLOUD_PROJECT
  GCP_SECRET_MANAGER_PREFIX    — secret name prefix; default: kaiju
  GCP_SECRET_MANAGER_ENV       — name segment; default: local; allowed: local, dev, staging, prod

Secret naming convention:
  {prefix}-{env}-{integration_type}-{credential_ref}
  e.g. kaiju-prod-google_ads-cred_google_ads_abcd1234ef56

No secret values are present in this module at any scope.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from credentials.models import now_utc_iso
from credentials.secret_store import (
    SecretRecord,
    SecretStore,
    assert_allowed_secret_fields,
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


def build_gcp_project_resource_name(project_id: str) -> str:
    """Return the GCP project resource name used as the parent for secret creation."""
    return f"projects/{project_id}"


def build_gcp_secret_version_resource_name(
    project_id: str,
    secret_id: str,
    version: str = "latest",
) -> str:
    """Return the GCP Secret Manager version resource name for a secret."""
    return f"projects/{project_id}/secrets/{secret_id}/versions/{version}"


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
# Payload parsing and exception mapping
# ---------------------------------------------------------------------------

def parse_gcp_secret_payload(
    payload_bytes: Any,
    integration_type: str,
) -> dict:
    """
    Decode, parse, and validate a GCP Secret Manager secret payload.

    Returns the parsed secrets dict on success.
    Raises ValueError on any failure. Error messages do not include raw
    payload content to prevent accidental secret exposure in tracebacks.
    """
    if isinstance(payload_bytes, (bytes, bytearray)):
        try:
            raw = payload_bytes.decode("utf-8")
        except Exception:
            raise ValueError("Secret payload could not be decoded as UTF-8")
    elif isinstance(payload_bytes, str):
        raw = payload_bytes
    else:
        raise ValueError(
            f"Secret payload has unexpected type: {type(payload_bytes).__name__}"
        )

    try:
        parsed = json.loads(raw)
    except Exception:
        raise ValueError("Secret payload is not valid JSON")

    if not isinstance(parsed, dict):
        raise ValueError(
            f"Secret payload must be a JSON object, got: {type(parsed).__name__}"
        )

    if not parsed:
        raise ValueError("Secret payload must not be empty")

    allowed, rejected = assert_allowed_secret_fields(parsed, integration_type)
    if not allowed:
        raise ValueError(
            f"Secret payload contains disallowed fields for '{integration_type}': {rejected}"
        )

    empty_fields = [k for k, v in parsed.items() if not v or not str(v).strip()]
    if empty_fields:
        raise ValueError(f"Secret payload has empty values for fields: {empty_fields}")

    return parsed


def build_gcp_secret_payload(secrets: dict, integration_type: str) -> bytes:
    """
    Validate and encode a secrets dict to UTF-8 JSON bytes for GCP Secret Manager.

    Validates allowed fields and rejects empty values.
    Uses sorted key ordering for deterministic output.
    Never prints or logs the returned bytes — they contain secret values.
    Raises ValueError for any validation failure.
    """
    if not secrets:
        raise ValueError("secrets dict must not be empty")
    allowed, rejected = assert_allowed_secret_fields(secrets, integration_type)
    if not allowed:
        raise ValueError(
            f"secrets contain disallowed fields for '{integration_type}': {rejected}"
        )
    empty_fields = [k for k, v in secrets.items() if not v or not str(v).strip()]
    if empty_fields:
        raise ValueError(f"Secret fields must not be empty: {empty_fields}")
    return json.dumps(dict(sorted(secrets.items())), ensure_ascii=False).encode("utf-8")


def _map_gcp_exception_to_error_code(exc: Exception) -> str:
    """
    Map a GCP API exception to a safe, non-revealing error code.

    Tries to import google.api_core.exceptions to classify the exception type.
    Falls back to 'gcp_secret_read_failed' if the mapping is not possible.
    Does not expose exception messages — those may contain resource names
    that include project or tenant identifiers.
    """
    try:
        from google.api_core import exceptions as gcp_exc  # type: ignore
        if isinstance(exc, gcp_exc.NotFound):
            return "gcp_secret_not_found"
        if isinstance(exc, gcp_exc.PermissionDenied):
            return "gcp_secret_access_denied"
        if isinstance(exc, gcp_exc.InvalidArgument):
            return "gcp_secret_payload_invalid"
    except ImportError:
        pass
    return "gcp_secret_read_failed"


def _is_gcp_already_exists(exc: Exception) -> bool:
    """
    Return True if exc is a GCP AlreadyExists exception.

    Checks the real google.api_core exception type first, then falls back to
    a substring match on the exception message for mock/test environments.
    """
    try:
        from google.api_core import exceptions as gcp_exc  # type: ignore
        if isinstance(exc, gcp_exc.AlreadyExists):
            return True
    except ImportError:
        pass
    return "already exists" in str(exc).lower()


def _map_gcp_write_exception_to_error_code(exc: Exception) -> str:
    """
    Map a GCP write-path exception to a safe error code.

    Falls back to 'gcp_secret_write_failed'. Does not expose exception messages.
    """
    try:
        from google.api_core import exceptions as gcp_exc  # type: ignore
        if isinstance(exc, gcp_exc.PermissionDenied):
            return "gcp_secret_access_denied"
        if isinstance(exc, gcp_exc.InvalidArgument):
            return "gcp_secret_payload_invalid"
        if isinstance(exc, gcp_exc.AlreadyExists):
            return "gcp_secret_already_exists"
    except ImportError:
        pass
    return "gcp_secret_write_failed"


# ---------------------------------------------------------------------------
# GCPSecretManagerStore
# ---------------------------------------------------------------------------

class GCPSecretManagerStore(SecretStore):
    """
    GCP Secret Manager backend for SecretStore.

    V5.12.4: put_secret_bundle implemented via create_secret + add_secret_version.
    AlreadyExists on create_secret is handled safely (proceeds to add_secret_version).
    delete_secret_bundle and list_secret_records remain deferred (V5.12.5+).

    An injected client= parameter allows testing without real GCP credentials.

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

    def _fetch_secret_bundle(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> Tuple[Optional[dict], Optional[str]]:
        """
        Fetch and parse a secret bundle from GCP Secret Manager.

        Returns (bundle_dict, None) on success.
        Returns (None, error_code) on any failure.
        Never raises. Never logs secret values.
        Only called when self._enabled is True and self._client is set.
        """
        secret_id = build_gcp_secret_id(credential_ref, integration_type)
        version_name = build_gcp_secret_version_resource_name(
            self._project_id, secret_id  # type: ignore[arg-type]
        )

        try:
            response = self._client.access_secret_version(request={"name": version_name})
            payload_bytes = response.payload.data
        except Exception as exc:
            return None, _map_gcp_exception_to_error_code(exc)

        try:
            bundle = parse_gcp_secret_payload(payload_bytes, integration_type)
        except ValueError:
            return None, "gcp_secret_payload_invalid"

        return bundle, None

    # ------------------------------------------------------------------
    # SecretStore interface
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

        Creates the secret if it does not exist; adds a new version if it does.
        AlreadyExists on create_secret is handled safely — proceeds to add_secret_version.
        Returns a SecretRecord (no secret values). Never logs or returns the payload.

        Raises:
          RuntimeError — when disabled, project missing, client unavailable, or GCP error.
          ValueError   — when secrets dict is empty or contains disallowed/empty fields.

        Field validation and disabled/ready checks run before any GCP API call.
        """
        # Disabled check first.
        self._check_disabled()

        # Validate fields before any GCP call.
        if not secrets:
            raise ValueError("secrets dict must not be empty")
        allowed, rejected = assert_allowed_secret_fields(secrets, integration_type)
        if not allowed:
            raise ValueError(
                f"Secrets contain disallowed fields for '{integration_type}': {rejected}"
            )
        empty_fields = [k for k, v in secrets.items() if not v or not str(v).strip()]
        if empty_fields:
            raise ValueError(f"Secret fields must not be empty: {empty_fields}")

        # Check project_id and client are available.
        self._check_ready()

        # Build identifiers — no secret values here.
        secret_id = build_gcp_secret_id(credential_ref, integration_type)
        parent = build_gcp_project_resource_name(self._project_id)  # type: ignore[arg-type]
        secret_resource = build_gcp_secret_resource_name(
            self._project_id, secret_id  # type: ignore[arg-type]
        )

        # Encode payload bytes — internal only, never printed or returned.
        payload_bytes = build_gcp_secret_payload(secrets, integration_type)

        # Step 1: Create secret. AlreadyExists → continue to add_secret_version.
        try:
            self._client.create_secret(request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            })
        except Exception as exc:
            if not _is_gcp_already_exists(exc):
                error_code = _map_gcp_write_exception_to_error_code(exc)
                raise RuntimeError(f"Failed to create GCP secret: {error_code}")
            # AlreadyExists — proceed to add a new version.

        # Step 2: Add secret version.
        try:
            self._client.add_secret_version(request={
                "parent": secret_resource,
                "payload": {"data": payload_bytes},
            })
        except Exception as exc:
            error_code = _map_gcp_write_exception_to_error_code(exc)
            raise RuntimeError(f"Failed to add GCP secret version: {error_code}")

        # Return redacted SecretRecord — no secret values.
        now = now_utc_iso()
        record_meta: Dict[str, Any] = {
            "backend": "gcp_secret_manager",
            "enabled": True,
            "project_id_configured": True,
            "secret_id": secret_id,
            "write_mode": "add_secret_version",
        }
        return SecretRecord(
            credential_ref=credential_ref,
            integration_type=integration_type,
            configured_fields=sorted(secrets.keys()),
            created_at=now,
            updated_at=now,
            metadata=record_meta,
        )

    def get_secret_bundle(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> Optional[dict]:
        """
        Retrieve a secret bundle from GCP Secret Manager.

        Returns the raw secret dict for internal adapter use only.
        Returns None when disabled, when init errors prevent client access,
        or when the secret cannot be retrieved or parsed.
        Never logs or exposes secret values.
        """
        if not self._enabled:
            return None
        if self._init_errors or self._client is None:
            return None
        bundle, _ = self._fetch_secret_bundle(credential_ref, integration_type)
        return bundle

    def get_secret_status(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> dict:
        """
        Return a redacted status dict. Safe for logging and API responses.

        When disabled: unconfigured shape with backend_status=disabled.
        When init errors: unconfigured shape with error_codes.
        When enabled and bundle found: configured=true with field presence map.
        When enabled and bundle missing/error: configured=false with error_code.
        No secret values are present in any returned shape.
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
                metadata={
                    "backend": "gcp_secret_manager",
                    "backend_status": "init_error",
                    "error_codes": codes,
                },
            )

        if self._client is None:
            return redact_secret_status(
                credential_ref,
                integration_type,
                configured_fields=[],
                metadata={
                    "backend": "gcp_secret_manager",
                    "backend_status": "client_unavailable",
                },
            )

        bundle, error_code = self._fetch_secret_bundle(credential_ref, integration_type)

        if bundle is not None:
            return redact_secret_status(
                credential_ref,
                integration_type,
                configured_fields=list(bundle.keys()),
                metadata={
                    "backend": "gcp_secret_manager",
                    "enabled": True,
                    "project_id_configured": True,
                    "available": True,
                },
            )

        return redact_secret_status(
            credential_ref,
            integration_type,
            configured_fields=[],
            metadata={
                "backend": "gcp_secret_manager",
                "enabled": True,
                "project_id_configured": self._project_id is not None,
                "available": False,
                "error_code": error_code,
            },
        )

    def delete_secret_bundle(
        self,
        credential_ref: str,
        integration_type: str,
    ) -> bool:
        """
        Delete a stored secret bundle from GCP Secret Manager.

        Returns False when disabled. Raises NotImplementedError when enabled
        (live delete implemented in V5.12.5).
        """
        if not self._enabled:
            return False
        self._check_ready()
        raise NotImplementedError(
            "GCPSecretManagerStore.delete_secret_bundle is not yet implemented. "
            "Live GCP delete support is added in V5.12.5."
        )

    def list_secret_records(
        self,
        integration_type: Optional[str] = None,
    ) -> List[SecretRecord]:
        """
        Return a list of SecretRecord descriptors from GCP Secret Manager.

        Returns [] when disabled. Raises NotImplementedError when enabled
        (live list implemented in V5.12.5).
        """
        if not self._enabled:
            return []
        self._check_ready()
        raise NotImplementedError(
            "GCPSecretManagerStore.list_secret_records is not yet implemented. "
            "Live GCP list support is added in V5.12.5."
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

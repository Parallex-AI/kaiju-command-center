"""
V5.12.6 — SecretStoreFactory: select InMemorySecretStore or GCPSecretManagerStore.

When GCP_SECRET_MANAGER_ENABLED=false (default):
  create_secret_store() returns InMemorySecretStore().

When GCP_SECRET_MANAGER_ENABLED=true:
  create_secret_store() returns GCPSecretManagerStore().

An explicit backend argument overrides auto-selection.
An explicit client= argument allows mock injection for tests.

No secret values are present in this module at any scope.
"""

from typing import Any, Optional

from credentials.gcp_secret_manager_store import (
    GCPSecretManagerStore,
    gcp_secret_manager_status,
    get_gcp_secret_manager_enabled,
)
from credentials.secret_store import InMemorySecretStore, SecretStore

_VALID_BACKENDS = ("in_memory", "gcp_secret_manager")


def get_secret_store_backend_name() -> str:
    """
    Return the backend name that auto-selection would choose.

    Returns "gcp_secret_manager" when GCP_SECRET_MANAGER_ENABLED is truthy.
    Returns "in_memory" otherwise (default).
    """
    if get_gcp_secret_manager_enabled():
        return "gcp_secret_manager"
    return "in_memory"


def create_secret_store(
    backend: Optional[str] = None,
    *,
    client: Any = None,
    project_id: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> SecretStore:
    """
    Return a SecretStore configured for the selected backend.

    backend=None       — auto-select based on GCP_SECRET_MANAGER_ENABLED env var.
    backend="in_memory"        — always return InMemorySecretStore.
    backend="gcp_secret_manager" — return GCPSecretManagerStore.
    Any other value    — raises ValueError with a safe message.

    Keyword-only args forwarded to GCPSecretManagerStore when relevant:
      client     — inject a pre-built mock client (for testing; no live calls).
      project_id — override GCP_PROJECT_ID / GOOGLE_CLOUD_PROJECT.
      enabled    — override GCP_SECRET_MANAGER_ENABLED.

    InMemorySecretStore ignores client, project_id, and enabled.
    No GCP network calls are made unless the resulting GCPSecretManagerStore
    has enabled=True and attempts an API operation.
    """
    if backend is None:
        backend = get_secret_store_backend_name()

    if backend == "in_memory":
        return InMemorySecretStore()

    if backend == "gcp_secret_manager":
        return GCPSecretManagerStore(
            project_id=project_id,
            enabled=enabled,
            client=client,
        )

    raise ValueError(
        f"Unknown secret store backend: {backend!r}. "
        f"Valid backends: {list(_VALID_BACKENDS)}"
    )


def secret_store_factory_status() -> dict:
    """
    Return safe configuration status for the SecretStoreFactory.

    Contains no credentials or secret values.
    Safe to log or return from admin endpoints.
    """
    return {
        "selected_backend": get_secret_store_backend_name(),
        "gcp": gcp_secret_manager_status(),
    }

"""
V5.5 — OpenClaw admin helper for credential status read-only operations.

Provides get_google_ads_credential_status(tenant_id, client_id) which returns
a safe redacted status dict backed by LocalFileCredentialReferenceStore.

No secret material is accepted, stored, or returned by any function here.
This module is read-only — it contains no credential write operations.
"""

import sys
from pathlib import Path
from typing import Any, Dict

# Add agents/ads-agent/ to sys.path so the credentials package is importable
_ADS_AGENT_DIR = str(Path(__file__).resolve().parents[1] / "agents" / "ads-agent")
if _ADS_AGENT_DIR not in sys.path:
    sys.path.insert(0, _ADS_AGENT_DIR)

from credentials.local_file_store import LocalFileCredentialReferenceStore

_INTEGRATION_TYPE = "google_ads"


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
        return {
            "ok": False,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "integration_type": _INTEGRATION_TYPE,
            "credential_status": None,
            "errors": [
                {
                    "code": "credential_status_failed",
                    "message": (
                        "Failed to retrieve credential status. "
                        "Check CREDENTIAL_REFERENCE_STORE_PATH configuration."
                    ),
                    "recoverable": True,
                    "source": "openclaw_admin",
                }
            ],
        }

"""
V5.14 — Admin credential API write demo (FastAPI TestClient).

Tests POST /openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads
via FastAPI TestClient — no HTTP server, no network calls, no live GCP.
GCP_SECRET_MANAGER_ENABLED is unset/false → factory selects InMemorySecretStore.

Scenarios:
  A — metadata-only POST: existing path, no secret_status
  B — full secret bundle POST: routes to write_google_ads_credential_bundle
  C — incomplete bundle rejected with secret_bundle_incomplete
  D — forbidden extra field (access_token) rejected with secret_material_rejected
  E — leak assertion across all API responses

Usage:
    cd ~/kaiju/openclaw
    ~/kaiju/.venv/bin/python3 run_admin_credentials_api_write_demo.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Ensure openclaw directory is on sys.path before any local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Set env vars BEFORE importing server so module-level config reads correct values
os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)
os.environ["GOOGLE_ADS_LIVE_ENABLED"] = "false"
os.environ["OPENCLAW_API_AUTH_ENABLED"] = "false"

_SEP = "-" * 60

_FAKE_SECRETS = {
    "developer_token": "fake-dev-token",
    "client_id": "fake-client-id",
    "client_secret": "fake-client-secret",
    "refresh_token": "fake-refresh-token",
}
_FAKE_VALUES = set(_FAKE_SECRETS.values()) | {"fake-access-token"}


def section(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def assert_no_secret_values_in_payload(output: dict, label: str) -> None:
    """Assert none of the fake secret values appear anywhere in the serialized output."""
    output_str = json.dumps(output)
    for val in _FAKE_VALUES:
        assert val not in output_str, (
            f"[{label}] Fake secret value '{val}' leaked into API response"
        )


def main() -> None:
    # Use a temp file so this demo never pollutes runtime/ state
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        store_path = f.name
    os.environ["CREDENTIAL_REFERENCE_STORE_PATH"] = store_path

    try:
        from fastapi.testclient import TestClient
        from server import app

        client = TestClient(app)

        print("V5.14 — Admin Credential API Write Demo (FastAPI TestClient)")
        print("No HTTP server. GCP_SECRET_MANAGER_ENABLED unset → InMemorySecretStore.")
        print("GOOGLE_ADS_LIVE_ENABLED=false. OPENCLAW_API_AUTH_ENABLED=false.")

        BASE = (
            "/openclaw/admin/tenants/api-tenant/clients/api-client"
            "/credentials/google-ads"
        )

        # ------------------------------------------------------------------
        # A. Metadata-only POST: existing path unchanged
        # ------------------------------------------------------------------
        section("A. Metadata-only POST — existing path unchanged, no secret_status")

        resp_a = client.post(BASE, json={
            "customer_id": "1234567890",
            "login_customer_id": "0987654321",
        })
        print(f"Status: {resp_a.status_code}")
        d_a = resp_a.json()
        print(json.dumps(d_a, indent=2))

        assert resp_a.status_code == 200, f"Expected 200, got {resp_a.status_code}: {d_a}"
        assert d_a["ok"] is True, f"Expected ok=true: {d_a}"
        assert d_a["credential_status"]["configured"] is True, "configured must be true"
        assert "credential_ref" in d_a["credential_status"], "credential_ref must be present"
        assert "secret_status" not in d_a, (
            f"metadata-only POST must not include secret_status, got keys: {list(d_a.keys())}"
        )
        assert_no_secret_values_in_payload(d_a, "scenario-A")
        print("PASS: ok=true, configured=true, no secret_status, no leak")

        # ------------------------------------------------------------------
        # B. Full secret bundle POST: routes to write_google_ads_credential_bundle
        # ------------------------------------------------------------------
        section("B. Full bundle POST — routes to bundle writer, InMemorySecretStore")

        resp_b = client.post(BASE, json={
            "customer_id": "1234567890",
            "login_customer_id": "0987654321",
            **_FAKE_SECRETS,
        })
        print(f"Status: {resp_b.status_code}")
        d_b = resp_b.json()
        print(json.dumps(d_b, indent=2))

        assert resp_b.status_code == 200, f"Expected 200, got {resp_b.status_code}: {d_b}"
        assert d_b["ok"] is True, f"Expected ok=true: {d_b}"
        assert d_b["credential_status"]["configured"] is True, (
            "credential_status.configured must be true"
        )
        assert d_b["secret_status"]["configured"] is True, (
            "secret_status.configured must be true"
        )
        configured_fields = d_b["secret_status"]["configured_fields"]
        for field in ("developer_token", "client_id", "client_secret", "refresh_token"):
            assert configured_fields.get(field) is True, (
                f"Field '{field}' not marked configured in secret_status"
            )
        # GCP and live flags must remain false
        assert os.environ.get("GOOGLE_ADS_LIVE_ENABLED", "false").lower() not in ("true", "1"), (
            "GOOGLE_ADS_LIVE_ENABLED must remain false"
        )
        assert os.environ.get("GCP_SECRET_MANAGER_ENABLED", "").lower() not in ("true", "1"), (
            "GCP_SECRET_MANAGER_ENABLED must not be enabled"
        )
        assert_no_secret_values_in_payload(d_b, "scenario-B")
        print("PASS: ok=true, credential_status.configured=true, secret_status.configured=true, "
              "all 4 fields confirmed, GCP disabled, no live calls, no leak")

        # ------------------------------------------------------------------
        # C. Incomplete bundle: missing refresh_token
        # ------------------------------------------------------------------
        section("C. Incomplete bundle — missing refresh_token")

        resp_c = client.post(BASE, json={
            "customer_id": "1234567890",
            "developer_token": "fake-dev-token",
            "client_id": "fake-client-id",
            "client_secret": "fake-client-secret",
            # refresh_token intentionally omitted
        })
        print(f"Status: {resp_c.status_code}")
        d_c = resp_c.json()
        print(json.dumps(d_c, indent=2))

        assert resp_c.status_code == 400, f"Expected 400, got {resp_c.status_code}: {d_c}"
        assert d_c["ok"] is False, f"Expected ok=false: {d_c}"
        error_codes_c = [e["code"] for e in d_c.get("errors", [])]
        assert "secret_bundle_incomplete" in error_codes_c, (
            f"Expected secret_bundle_incomplete, got: {error_codes_c}"
        )
        assert_no_secret_values_in_payload(d_c, "scenario-C")
        print("PASS: incomplete bundle rejected with secret_bundle_incomplete, no leak")

        # ------------------------------------------------------------------
        # D. Forbidden extra field: access_token alongside valid secrets
        # ------------------------------------------------------------------
        section("D. Forbidden extra field — access_token alongside valid secrets")

        resp_d = client.post(BASE, json={
            "customer_id": "1234567890",
            **_FAKE_SECRETS,
            "access_token": "fake-access-token",
        })
        print(f"Status: {resp_d.status_code}")
        d_d = resp_d.json()
        print(json.dumps(d_d, indent=2))

        assert resp_d.status_code == 400, f"Expected 400, got {resp_d.status_code}: {d_d}"
        assert d_d["ok"] is False, f"Expected ok=false: {d_d}"
        error_codes_d = [e["code"] for e in d_d.get("errors", [])]
        assert "secret_material_rejected" in error_codes_d, (
            f"Expected secret_material_rejected, got: {error_codes_d}"
        )
        assert "fake-access-token" not in json.dumps(d_d), (
            "Forbidden field value must not appear in error response"
        )
        assert_no_secret_values_in_payload(d_d, "scenario-D")
        print("PASS: access_token rejected with secret_material_rejected, no value leaked")

        # ------------------------------------------------------------------
        # E. Leak assertion across all API responses
        # ------------------------------------------------------------------
        section("E. Leak assertion — all API responses (success and error)")

        all_responses = [
            ("scenario-A (success)", d_a),
            ("scenario-B (success)", d_b),
            ("scenario-C (error)", d_c),
            ("scenario-D (error)", d_d),
        ]
        for label, output in all_responses:
            assert_no_secret_values_in_payload(output, label)

        print(f"PASS: no fake secret values in any of {len(all_responses)} API responses")

        print(f"\n{_SEP}")
        print("  All assertions passed.")
        print(_SEP)

    finally:
        os.environ.pop("CREDENTIAL_REFERENCE_STORE_PATH", None)
        os.environ.pop("OPENCLAW_API_AUTH_ENABLED", None)
        os.environ.pop("GOOGLE_ADS_LIVE_ENABLED", None)
        Path(store_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()

"""
V5.14 — Admin credential bundle write demo.

Demonstrates write_google_ads_credential_bundle() with an injected InMemorySecretStore.
Does not call live GCP regardless of environment settings.
Uses fake credential values only — never real tokens or secrets.

Fake values used throughout:
  developer_token : fake-dev-token
  client_id (OAuth): fake-client-id
  client_secret   : fake-client-secret
  refresh_token   : fake-refresh-token

Usage:
    cd ~/kaiju/openclaw
    ~/kaiju/.venv/bin/python3 run_admin_credentials_gcp_write_demo.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Make openclaw package importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

# admin.py injects agents/ads-agent onto sys.path on import
from admin import (
    write_google_ads_credential_bundle,
    upsert_google_ads_credential_reference,
    get_google_ads_credential_status,
    GOOGLE_ADS_SECRET_FIELDS,
)

# InMemorySecretStore is now importable (admin injected the path)
from credentials.secret_store import InMemorySecretStore

_SEP = "-" * 60

_FAKE_SECRETS = {
    "developer_token": "fake-dev-token",
    "client_id": "fake-client-id",
    "client_secret": "fake-client-secret",
    "refresh_token": "fake-refresh-token",
}
_FAKE_VALUES = set(_FAKE_SECRETS.values())


def section(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def assert_no_secret_values_in_output(output: dict, label: str) -> None:
    """Assert none of the fake secret values appear anywhere in the serialized output."""
    output_str = json.dumps(output)
    for val in _FAKE_VALUES:
        assert val not in output_str, (
            f"[{label}] Fake secret value '{val}' leaked into response output"
        )


def main() -> None:
    # Use a temp file so this demo never pollutes runtime/ state
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        store_path = f.name
    os.environ["CREDENTIAL_REFERENCE_STORE_PATH"] = store_path

    try:
        print("V5.14 — Admin Credential Bundle Write Demo")
        print("InMemorySecretStore injected — no live GCP calls")

        # ------------------------------------------------------------------
        # 1. Full credential bundle write with injected InMemorySecretStore
        # ------------------------------------------------------------------
        section("1. Full bundle write — injected InMemorySecretStore, fake values")

        store = InMemorySecretStore()
        payload = {
            "customer_id": "123-456-7890",
            "login_customer_id": "000-000-0001",
            **_FAKE_SECRETS,
        }
        result = write_google_ads_credential_bundle(
            "demo-tenant",
            "demo-client",
            payload,
            secret_store=store,
        )
        print(json.dumps(result, indent=2))

        assert result["ok"] is True, f"Expected ok=true, got: {result}"
        assert result["tenant_id"] == "demo-tenant"
        assert result["client_id"] == "demo-client"
        assert result["integration_type"] == "google_ads"

        # credential_status — from CredentialReference metadata store
        cred_status = result["credential_status"]
        assert cred_status is not None, "credential_status must be present"
        assert cred_status["credential_ref"] is not None, "credential_ref must be set"
        assert cred_status["configured"] is True, "configured must be true"

        # secret_status — from SecretStore (no values, booleans only)
        secret_status = result["secret_status"]
        assert secret_status is not None, "secret_status must be present"
        assert secret_status["configured"] is True, "secret configured must be true"
        configured_fields = secret_status["configured_fields"]
        for field in GOOGLE_ADS_SECRET_FIELDS:
            assert configured_fields.get(field) is True, (
                f"Field '{field}' not marked configured in secret_status"
            )

        assert result["errors"] == []

        # Secret leak check
        assert_no_secret_values_in_output(result, "section-1")
        print("PASS: ok=true, credential_status.configured=true, "
              "secret_status.configured=true, all 4 fields confirmed, no secret values leaked")

        # ------------------------------------------------------------------
        # 2. Verify GET status reflects written CredentialReference
        # ------------------------------------------------------------------
        section("2. GET credential status — reflects written reference")

        status_result = get_google_ads_credential_status("demo-tenant", "demo-client")
        print(json.dumps(status_result, indent=2))

        assert status_result["ok"] is True
        assert status_result["credential_status"]["configured"] is True
        assert status_result["credential_status"]["credential_ref"] == cred_status["credential_ref"], (
            "credential_ref must match"
        )
        assert_no_secret_values_in_output(status_result, "section-2")
        print("PASS: GET status reflects written CredentialReference, credential_ref consistent")

        # ------------------------------------------------------------------
        # 3. Metadata-only write — existing path unaffected
        # ------------------------------------------------------------------
        section("3. Metadata-only write — existing upsert path unchanged")

        meta_result = upsert_google_ads_credential_reference(
            "demo-tenant-2",
            "demo-client-2",
            {"customer_id": "999-888-7777", "login_customer_id": "111-000-0000"},
        )
        print(json.dumps(meta_result, indent=2))

        assert meta_result["ok"] is True, f"Expected ok=true: {meta_result}"
        assert meta_result["credential_status"]["configured"] is True
        assert "secret_status" not in meta_result, (
            "metadata-only path must not add secret_status"
        )
        assert_no_secret_values_in_output(meta_result, "section-3")
        print("PASS: metadata-only write ok=true, no secret_status added, no leak")

        # ------------------------------------------------------------------
        # 4. Incomplete bundle — missing refresh_token
        # ------------------------------------------------------------------
        section("4. Incomplete bundle — missing refresh_token")

        incomplete_payload = {
            "customer_id": "123-456-7890",
            "developer_token": "fake-dev-token",
            "client_id": "fake-client-id",
            "client_secret": "fake-client-secret",
            # refresh_token intentionally omitted
        }
        incomplete_result = write_google_ads_credential_bundle(
            "demo-tenant",
            "demo-client",
            incomplete_payload,
            secret_store=InMemorySecretStore(),
        )
        print(json.dumps(incomplete_result, indent=2))

        assert incomplete_result["ok"] is False, (
            f"Expected ok=false for incomplete bundle: {incomplete_result}"
        )
        error_codes = [e["code"] for e in incomplete_result.get("errors", [])]
        assert "secret_bundle_incomplete" in error_codes, (
            f"Expected secret_bundle_incomplete, got: {error_codes}"
        )
        assert incomplete_result.get("secret_status") is None
        assert_no_secret_values_in_output(incomplete_result, "section-4")
        print("PASS: incomplete bundle rejected with secret_bundle_incomplete, no leak")

        # ------------------------------------------------------------------
        # 5. Forbidden extra field — access_token in bundle position
        # ------------------------------------------------------------------
        section("5. Forbidden extra field — access_token alongside valid secrets")

        # access_token is globally rejected by assert_allowed_secret_fields
        forbidden_payload = {
            "customer_id": "123-456-7890",
            **_FAKE_SECRETS,
            "access_token": "should-be-rejected",
        }
        forbidden_result = write_google_ads_credential_bundle(
            "demo-tenant",
            "demo-client",
            forbidden_payload,
            secret_store=InMemorySecretStore(),
        )
        print(json.dumps(forbidden_result, indent=2))

        assert forbidden_result["ok"] is False, (
            f"Expected ok=false for forbidden field: {forbidden_result}"
        )
        error_codes = [e["code"] for e in forbidden_result.get("errors", [])]
        assert "secret_material_rejected" in error_codes, (
            f"Expected secret_material_rejected, got: {error_codes}"
        )
        # Verify "should-be-rejected" value did not leak into error response
        assert "should-be-rejected" not in json.dumps(forbidden_result), (
            "Forbidden field value must not appear in error response"
        )
        assert forbidden_result.get("secret_status") is None
        print("PASS: access_token rejected with secret_material_rejected, no value leaked")

        # ------------------------------------------------------------------
        # 6. Factory default safety — GCP_SECRET_MANAGER_ENABLED not set → InMemory
        # ------------------------------------------------------------------
        section("6. Factory default — no secret_store injection, GCP disabled")

        os.environ.pop("GCP_SECRET_MANAGER_ENABLED", None)

        # Without secret_store= injection, factory is called. Since
        # GCP_SECRET_MANAGER_ENABLED is unset/false, InMemorySecretStore is used.
        factory_result = write_google_ads_credential_bundle(
            "demo-tenant-3",
            "demo-client-3",
            {"customer_id": "555-444-3333", **_FAKE_SECRETS},
            # no secret_store= — let factory decide
        )
        print(json.dumps(factory_result, indent=2))

        assert factory_result["ok"] is True, (
            f"Expected ok=true via factory: {factory_result}"
        )
        assert factory_result["secret_status"]["configured"] is True
        assert_no_secret_values_in_output(factory_result, "section-6")
        print("PASS: factory auto-selected InMemorySecretStore, ok=true, no leak")

        # ------------------------------------------------------------------
        # 7. Comprehensive secret leak assertion across all success outputs
        # ------------------------------------------------------------------
        section("7. Comprehensive secret leak assertion")

        all_outputs = [result, status_result, meta_result, factory_result]
        for i, output in enumerate(all_outputs, 1):
            assert_no_secret_values_in_output(output, f"final-check-{i}")

        forbidden_keys = [
            "developer_token", "client_secret", "refresh_token",
            "access_token", "oauth_code",
        ]
        for output in all_outputs:
            output_str = json.dumps(output)
            for key in forbidden_keys:
                # These keys may appear as configured_fields dict keys (safe — boolean values only)
                # but must never appear as direct response fields with raw values
                if key in output.get("credential_status", {}) or key in output.get("secret_status", {}):
                    pass  # presence as a status key is OK; values are booleans
            # Values must not appear
            for val in _FAKE_VALUES:
                assert val not in output_str, (
                    f"Fake secret value '{val}' found in output"
                )
        print(f"PASS: no fake secret values in any of {len(all_outputs)} success outputs")

        print(f"\n{_SEP}")
        print("  All assertions passed.")
        print(_SEP)

    finally:
        os.environ.pop("CREDENTIAL_REFERENCE_STORE_PATH", None)
        Path(store_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()

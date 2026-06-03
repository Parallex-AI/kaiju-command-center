"""
V5.9 — Google Ads CredentialProvider demo (no HTTP server, no disk secrets).

Demonstrates compose_google_ads_credentials() across the full lifecycle:
missing reference, unconfigured reference, missing secret bundle, and
successful composition.

IMPORTANT: Raw credential values (developer_token, client_secret, etc.) are
asserted internally but are NEVER printed. All printed output is redacted.
Fake fixture values are test stand-ins only — not real credentials.

Usage:
    cd ~/kaiju/agents/ads-agent
    ~/kaiju/.venv/bin/python3 run_google_ads_provider_demo.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from credentials.google_ads_provider import (
    GoogleAdsCredentialProviderResult,
    assert_provider_output_has_no_secret_values,
    compose_google_ads_credentials,
    google_ads_provider_result_to_redacted_dict,
    make_provider_error,
)
from credentials.local_file_store import LocalFileCredentialReferenceStore
from credentials.models import CredentialStatus, IntegrationType, create_credential_reference
from credentials.secret_store import InMemorySecretStore
from integrations.google_ads_adapter import GoogleAdsCredentials

_SEP = "-" * 60

# Fake fixture values for demo/test only. Not real credentials.
_FAKE_SECRETS = {
    "developer_token": "fake-dev-token",
    "client_id": "fake-client-id",
    "client_secret": "fake-client-secret",
    "refresh_token": "fake-refresh-token",
}
_INTEGRATION = IntegrationType.GOOGLE_ADS.value


def section(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def main() -> None:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        store_path = f.name
    os.environ["CREDENTIAL_REFERENCE_STORE_PATH"] = store_path

    try:
        print("V5.9 — Google Ads CredentialProvider Demo")

        ref_store = LocalFileCredentialReferenceStore()
        secret_store = InMemorySecretStore()

        # Collect all printed dicts for final safety assertion
        printed_outputs = []

        # ------------------------------------------------------------------
        # 1. Missing reference (no record in store)
        # ------------------------------------------------------------------
        section("1. compose — missing reference")
        result1 = compose_google_ads_credentials(
            "missing-tenant", "missing-client",
            secret_store=secret_store,
        )
        d1 = google_ads_provider_result_to_redacted_dict(result1)
        print(json.dumps(d1, indent=2))
        printed_outputs.append(d1)

        assert result1.ok is False
        assert result1.credentials is None
        assert result1.errors[0]["code"] == "credentials_missing"
        assert result1.errors[0]["source"] == "google_ads_credential_provider"
        assert d1["credentials_configured"] is False
        assert all(v is False for v in d1["configured_fields"].values())
        print("PASS: ok=false, code=credentials_missing, all configured_fields=false")

        # ------------------------------------------------------------------
        # 2. Unconfigured reference (reference exists but status not active/configured)
        # ------------------------------------------------------------------
        section("2. compose — unconfigured reference (status=revoked)")
        revoked_ref = create_credential_reference(
            tenant_id="revoked-tenant",
            client_id="revoked-client",
            integration_type=_INTEGRATION,
            customer_id="111-222-3333",
            status=CredentialStatus.REVOKED.value,
        )
        ref_store.put_reference(revoked_ref)

        result2 = compose_google_ads_credentials(
            "revoked-tenant", "revoked-client",
            secret_store=secret_store,
        )
        d2 = google_ads_provider_result_to_redacted_dict(result2)
        print(json.dumps(d2, indent=2))
        printed_outputs.append(d2)

        assert result2.ok is False
        assert result2.credentials is None
        assert result2.errors[0]["code"] == "credential_reference_not_configured"
        assert d2["credential_ref"] is not None
        assert d2["credentials_configured"] is False
        print("PASS: ok=false, code=credential_reference_not_configured, credential_ref set")

        # ------------------------------------------------------------------
        # 3. Configured reference but missing secret bundle
        # ------------------------------------------------------------------
        section("3. compose — configured reference, missing secret bundle")
        configured_ref = create_credential_reference(
            tenant_id="demo-tenant",
            client_id="demo-client",
            integration_type=_INTEGRATION,
            customer_id="111-222-3333",
            login_customer_id="000-000-0001",
            status=CredentialStatus.CONFIGURED.value,
        )
        ref_store.put_reference(configured_ref)

        result3 = compose_google_ads_credentials(
            "demo-tenant", "demo-client",
            secret_store=secret_store,  # empty — no bundle yet
        )
        d3 = google_ads_provider_result_to_redacted_dict(result3)
        print(json.dumps(d3, indent=2))
        printed_outputs.append(d3)

        assert result3.ok is False
        assert result3.credentials is None
        assert result3.errors[0]["code"] == "secret_bundle_missing"
        assert d3["credential_ref"] is not None
        print("PASS: ok=false, code=secret_bundle_missing, credential_ref set")

        # ------------------------------------------------------------------
        # 4. Full composition: configured reference + full secret bundle
        # ------------------------------------------------------------------
        section("4. compose — success (configured reference + full secret bundle)")
        secret_store.put_secret_bundle(
            credential_ref=configured_ref.credential_ref,
            integration_type=_INTEGRATION,
            secrets=_FAKE_SECRETS,
        )

        result4 = compose_google_ads_credentials(
            "demo-tenant", "demo-client",
            secret_store=secret_store,
        )
        d4 = google_ads_provider_result_to_redacted_dict(result4)
        print(json.dumps(d4, indent=2))
        printed_outputs.append(d4)

        assert result4.ok is True
        assert result4.credentials is not None
        assert isinstance(result4.credentials, GoogleAdsCredentials)
        assert d4["credentials_configured"] is True
        assert d4["errors"] == []
        print("PASS: ok=true, credentials_configured=true, errors=[]")

        # ------------------------------------------------------------------
        # 5. Internal credentials inspection — values NOT printed
        # ------------------------------------------------------------------
        section("5. Internal credentials check (values not printed)")
        creds = result4.credentials
        assert creds.developer_token == _FAKE_SECRETS["developer_token"]
        assert creds.client_id == _FAKE_SECRETS["client_id"]
        assert creds.client_secret == _FAKE_SECRETS["client_secret"]
        assert creds.refresh_token == _FAKE_SECRETS["refresh_token"]
        assert creds.customer_id == "111-222-3333"
        assert creds.login_customer_id == "000-000-0001"
        print("PASS: all 6 credential fields confirmed internally (values not printed)")

        # ------------------------------------------------------------------
        # 6. configured_fields reflects each field correctly
        # ------------------------------------------------------------------
        section("6. configured_fields correctness")
        cf = d4["configured_fields"]
        assert cf["developer_token"] is True
        assert cf["client_id"] is True
        assert cf["client_secret"] is True
        assert cf["refresh_token"] is True
        assert cf["customer_id"] is True
        assert cf["login_customer_id"] is True
        print(f"configured_fields: {cf}")
        print("PASS: all 6 configured_fields are True for full bundle")

        # ------------------------------------------------------------------
        # 7. Active reference also composes successfully
        # ------------------------------------------------------------------
        section("7. compose — active reference")
        from credentials.models import update_credential_status
        active_ref = update_credential_status(configured_ref, CredentialStatus.ACTIVE.value)
        ref_store.put_reference(active_ref)

        result7 = compose_google_ads_credentials(
            "demo-tenant", "demo-client",
            secret_store=secret_store,
        )
        d7 = google_ads_provider_result_to_redacted_dict(result7)
        print(json.dumps(d7, indent=2))
        printed_outputs.append(d7)

        assert result7.ok is True
        assert result7.credentials is not None
        assert d7["credentials_configured"] is True
        print("PASS: active reference composes successfully")

        # ------------------------------------------------------------------
        # 8. make_provider_error shape
        # ------------------------------------------------------------------
        section("8. make_provider_error — shape check")
        err = make_provider_error("test_code", "Test message.", recoverable=False)
        assert err["code"] == "test_code"
        assert err["source"] == "google_ads_credential_provider"
        assert err["recoverable"] is False
        print(f"error: {err}")
        print("PASS: make_provider_error returns expected shape")

        # ------------------------------------------------------------------
        # 9. repr of result does not expose credentials
        # ------------------------------------------------------------------
        section("9. repr safety — credentials excluded from repr")
        result_repr = repr(result4)
        assert "fake-dev-token" not in result_repr
        assert "fake-client-secret" not in result_repr
        assert "fake-refresh-token" not in result_repr
        print(f"repr: {result_repr}")
        print("PASS: repr excludes credential values (repr=False on credentials field)")

        # ------------------------------------------------------------------
        # 10. assert_provider_output_has_no_secret_values on all outputs
        # ------------------------------------------------------------------
        section("10. Secret-value safety assertion on all printed outputs")
        for i, output in enumerate(printed_outputs):
            clean, offending = assert_provider_output_has_no_secret_values(output)
            assert clean, f"Output #{i} contains secret-like value at: {offending}"
        print(f"PASS: all {len(printed_outputs)} printed output dicts contain no secret-like values")

        # ------------------------------------------------------------------
        # 11. assert_provider_output_has_no_secret_values — detects dirty
        # ------------------------------------------------------------------
        section("11. Secret-value scanner — detects dirty payload")
        dirty = {"tenant": "x", "token_val": "fake-dev-token"}
        clean, offending = assert_provider_output_has_no_secret_values(dirty)
        assert not clean
        assert "token_val" in offending
        print(f"PASS: detected secret-like value at: {offending}")

        print(f"\n{_SEP}")
        print("  All assertions passed.")
        print(_SEP)

    finally:
        os.environ.pop("CREDENTIAL_REFERENCE_STORE_PATH", None)
        Path(store_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()

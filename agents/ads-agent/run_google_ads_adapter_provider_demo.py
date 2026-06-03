import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integrations.google_ads_adapter import (
    fetch_google_ads_metrics,
    get_google_ads_credential_source,
    is_google_ads_live_enabled,
    load_google_ads_credentials_from_provider,
    redacted_google_ads_credentials,
    validate_google_ads_credentials,
)
from credentials.local_file_store import LocalFileCredentialReferenceStore
from credentials.secret_store import InMemorySecretStore
from credentials.models import IntegrationType
from credentials.store import make_store_key


DEMO_TENANT_ID = "tenant-demo-001"
DEMO_CLIENT_ID = "client-acme"


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def demo_credential_source_flag() -> None:
    _print_section("1. Credential source flag")
    source = get_google_ads_credential_source()
    raw = os.getenv("GOOGLE_ADS_CREDENTIAL_SOURCE", "(unset — defaults to env)")
    print(f"GOOGLE_ADS_CREDENTIAL_SOURCE env: {raw}")
    print(f"Resolved credential source:       {source}")


def demo_provider_path_no_live() -> None:
    _print_section("2. Provider path — live disabled (expected: google_ads_live_disabled)")
    os.environ.pop("GOOGLE_ADS_LIVE_ENABLED", None)
    result = fetch_google_ads_metrics(
        DEMO_CLIENT_ID,
        "summary",
        tenant_id=DEMO_TENANT_ID,
    )
    print(json.dumps(result, indent=2, default=str))


def demo_provider_path_missing_tenant() -> None:
    _print_section("3. Provider path — missing tenant_id (expected: tenant_id_required)")
    os.environ["GOOGLE_ADS_LIVE_ENABLED"] = "true"
    os.environ["GOOGLE_ADS_CREDENTIAL_SOURCE"] = "provider"
    result = fetch_google_ads_metrics(DEMO_CLIENT_ID, "summary")
    print(json.dumps(result, indent=2, default=str))
    os.environ.pop("GOOGLE_ADS_LIVE_ENABLED", None)
    os.environ.pop("GOOGLE_ADS_CREDENTIAL_SOURCE", None)


def demo_load_from_provider_no_store() -> None:
    _print_section("4. load_google_ads_credentials_from_provider — no credential ref (expected: not ok)")
    ok, credentials, errors = load_google_ads_credentials_from_provider(
        DEMO_TENANT_ID,
        DEMO_CLIENT_ID,
        secret_store=None,
    )
    print(f"ok: {ok}")
    if credentials:
        print("credentials: (present)")
        redacted = redacted_google_ads_credentials(credentials)
        print(json.dumps(redacted, indent=2))
    else:
        print("credentials: None")
    if errors:
        print("errors:")
        for err in errors:
            print(f"  [{err['code']}] {err['message']}")


def demo_load_from_provider_with_store(store_path: str) -> None:
    _print_section("5. load_google_ads_credentials_from_provider — with in-memory store")

    ref_store = LocalFileCredentialReferenceStore()
    secret_store = InMemorySecretStore()

    integration_type = IntegrationType.GOOGLE_ADS.value

    from credentials.models import CredentialStatus, create_credential_reference
    ref = create_credential_reference(
        tenant_id=DEMO_TENANT_ID,
        client_id=DEMO_CLIENT_ID,
        integration_type=integration_type,
        customer_id="1234567890",
        status=CredentialStatus.CONFIGURED.value,
        metadata={"note": "provider-demo"},
    )
    ref_store.put_reference(ref)

    secret_store.put_secret_bundle(
        credential_ref=ref.credential_ref,
        integration_type=integration_type,
        secrets={
            "developer_token": "demo-dev-token",
            "client_id": "demo-oauth-client-id",
            "client_secret": "demo-client-secret",
            "refresh_token": "demo-refresh-token",
        },
    )

    ok, credentials, errors = load_google_ads_credentials_from_provider(
        DEMO_TENANT_ID,
        DEMO_CLIENT_ID,
        secret_store=secret_store,
    )
    print(f"ok: {ok}")
    if credentials:
        redacted = redacted_google_ads_credentials(credentials)
        print("credentials (redacted):")
        print(json.dumps(redacted, indent=2))
        valid, val_errors = validate_google_ads_credentials(credentials)
        print(f"validation: {'PASS' if valid else 'FAIL'}")
        if val_errors:
            for err in val_errors:
                print(f"  [{err['code']}] {err['message']}")
    else:
        print("credentials: None")
    if errors:
        print("errors:")
        for err in errors:
            print(f"  [{err['code']}] {err['message']}")


def demo_env_path_unchanged() -> None:
    _print_section("6. Env path (default) — backward compatibility check")
    os.environ.pop("GOOGLE_ADS_CREDENTIAL_SOURCE", None)
    source = get_google_ads_credential_source()
    print(f"Credential source (no env var set): {source}")
    print("Calling fetch_google_ads_metrics('demo-client', 'summary') — 2-arg form:")
    result = fetch_google_ads_metrics("demo-client", "summary")
    code = result.get("error", {}).get("code", "—")
    print(f"  ok: {result.get('ok')}  error_code: {code}")
    print("  (expected: google_ads_live_disabled — live flag is off by default)")


def main() -> None:
    print("=== Kaiju Ads Agent | Google Ads Adapter Provider Demo (V5.10) ===")
    print("No live Google Ads API calls are made in this demo.")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        store_path = f.name
    os.environ["CREDENTIAL_REFERENCE_STORE_PATH"] = store_path

    try:
        demo_credential_source_flag()
        demo_provider_path_no_live()
        demo_provider_path_missing_tenant()
        demo_load_from_provider_no_store()
        demo_load_from_provider_with_store(store_path)
        demo_env_path_unchanged()
    finally:
        os.environ.pop("CREDENTIAL_REFERENCE_STORE_PATH", None)
        try:
            os.unlink(store_path)
        except OSError:
            pass

    print("\nDemo complete.")


if __name__ == "__main__":
    main()

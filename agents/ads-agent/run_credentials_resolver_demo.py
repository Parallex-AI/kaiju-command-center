"""
V5.7 — Credential Resolver demo (no HTTP server required).

Demonstrates resolve_credential_reference() across the full lifecycle:
missing reference, configured reference, active reference, invalid tenant.
Uses a temporary LocalFileCredentialReferenceStore path under /tmp.

Never prints secret values. All output is safe redacted metadata only.

Usage:
    cd ~/kaiju/agents/ads-agent
    ~/kaiju/.venv/bin/python3 run_credentials_resolver_demo.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from credentials.local_file_store import LocalFileCredentialReferenceStore
from credentials.models import (
    CredentialStatus,
    IntegrationType,
    create_credential_reference,
    update_credential_status,
)
from credentials.resolver import (
    ResolvedCredentialReference,
    assert_resolved_reference_has_no_secret_material,
    make_resolver_error,
    resolve_credential_reference,
    resolved_credential_reference_to_dict,
)

_SEP = "-" * 60


def section(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def main() -> None:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        store_path = f.name
    os.environ["CREDENTIAL_REFERENCE_STORE_PATH"] = store_path

    try:
        print("V5.7 — Credential Resolver Demo")

        store = LocalFileCredentialReferenceStore()

        # ------------------------------------------------------------------
        # 1. Resolve missing reference
        # ------------------------------------------------------------------
        section("1. resolve_credential_reference — missing")
        result = resolve_credential_reference(
            "demo-tenant", "demo-client",
            store=store,
        )
        d = resolved_credential_reference_to_dict(result)
        print(json.dumps(d, indent=2))

        assert result.ok is False
        assert result.status == CredentialStatus.MISSING.value
        assert result.configured is False
        assert result.credential_ref is None
        assert result.errors[0]["code"] == "credentials_missing"
        assert result.errors[0]["source"] == "credential_resolver"
        print("PASS: ok=false, status=missing, credential_ref=None, code=credentials_missing")

        # ------------------------------------------------------------------
        # 2. Write a configured reference, then resolve
        # ------------------------------------------------------------------
        section("2. resolve_credential_reference — configured")
        ref = create_credential_reference(
            tenant_id="demo-tenant",
            client_id="demo-client",
            integration_type=IntegrationType.GOOGLE_ADS.value,
            customer_id="111-222-3333",
            login_customer_id="000-000-0001",
            status=CredentialStatus.CONFIGURED.value,
        )
        store.put_reference(ref)

        result2 = resolve_credential_reference(
            "demo-tenant", "demo-client",
            store=store,
        )
        d2 = resolved_credential_reference_to_dict(result2)
        print(json.dumps(d2, indent=2))

        assert result2.ok is True
        assert result2.status == CredentialStatus.CONFIGURED.value
        assert result2.configured is True
        assert result2.credential_ref is not None
        assert result2.customer_id == "111-222-3333"
        assert result2.login_customer_id == "000-000-0001"
        assert result2.errors == []
        print("PASS: ok=true, status=configured, configured=true, customer_id set")

        # ------------------------------------------------------------------
        # 3. Update status to active, resolve active reference
        # ------------------------------------------------------------------
        section("3. resolve_credential_reference — active")
        updated_ref = update_credential_status(ref, CredentialStatus.ACTIVE.value)
        store.put_reference(updated_ref)

        result3 = resolve_credential_reference(
            "demo-tenant", "demo-client",
            store=store,
        )
        d3 = resolved_credential_reference_to_dict(result3)
        print(json.dumps(d3, indent=2))

        assert result3.ok is True
        assert result3.status == CredentialStatus.ACTIVE.value
        assert result3.configured is True
        assert result3.credential_ref == result2.credential_ref, (
            "credential_ref must be stable across status changes"
        )
        print("PASS: ok=true, status=active, configured=true, credential_ref stable")

        # ------------------------------------------------------------------
        # 4. Different tenant — still missing
        # ------------------------------------------------------------------
        section("4. resolve_credential_reference — different tenant, missing")
        result4 = resolve_credential_reference(
            "acme-corp", "client-001",
            store=store,
        )
        assert result4.ok is False
        assert result4.status == CredentialStatus.MISSING.value
        assert result4.configured is False
        print(f"tenant_id : {result4.tenant_id}")
        print(f"client_id : {result4.client_id}")
        print(f"status    : {result4.status}")
        print("PASS: isolated tenant returns missing, configured=false")

        # ------------------------------------------------------------------
        # 5. resolved_credential_reference_to_dict shape check
        # ------------------------------------------------------------------
        section("5. resolved_credential_reference_to_dict — shape")
        d5 = resolved_credential_reference_to_dict(result3)
        expected_keys = {
            "ok", "tenant_id", "client_id", "integration_type",
            "credential_ref", "status", "configured",
            "customer_id", "login_customer_id", "metadata", "errors",
        }
        assert set(d5.keys()) == expected_keys, f"Unexpected keys: {set(d5.keys())}"
        print(f"Keys present: {sorted(d5.keys())}")
        print("PASS: dict has expected keys, no extras")

        # ------------------------------------------------------------------
        # 6. assert_resolved_reference_has_no_secret_material
        # ------------------------------------------------------------------
        section("6. assert_resolved_reference_has_no_secret_material — clean")
        for d_check in [d, d2, d3]:
            clean, offending = assert_resolved_reference_has_no_secret_material(d_check)
            assert clean, f"Unexpected secret-like keys in resolved dict: {offending}"
        print("PASS: all resolved dicts contain no secret-like key names")

        section("6b. assert_resolved_reference_has_no_secret_material — detects dirty")
        dirty = {"customer_id": "123", "refresh_token": "should-be-caught"}
        clean, offending = assert_resolved_reference_has_no_secret_material(dirty)
        assert not clean
        assert "refresh_token" in offending
        print(f"PASS: detected forbidden key in: {offending}")

        # ------------------------------------------------------------------
        # 7. make_resolver_error shape
        # ------------------------------------------------------------------
        section("7. make_resolver_error — shape")
        err = make_resolver_error("test_code", "Test message.", recoverable=False)
        assert err["code"] == "test_code"
        assert err["message"] == "Test message."
        assert err["recoverable"] is False
        assert err["source"] == "credential_resolver"
        print(f"error: {err}")
        print("PASS: make_resolver_error returns expected shape")

        # ------------------------------------------------------------------
        # 8. resolve uses default store (env var path)
        # ------------------------------------------------------------------
        section("8. resolve_credential_reference — default store (env var)")
        result8 = resolve_credential_reference("demo-tenant", "demo-client")
        assert result8.ok is True
        assert result8.status == CredentialStatus.ACTIVE.value
        print(f"status: {result8.status}, configured: {result8.configured}")
        print("PASS: default store resolved using CREDENTIAL_REFERENCE_STORE_PATH")

        # ------------------------------------------------------------------
        # 9. Secret-safety assertion on all output dicts
        # ------------------------------------------------------------------
        section("9. Secret-safety assertion on all outputs")
        all_dicts = [d, d2, d3, resolved_credential_reference_to_dict(result4)]
        forbidden_keys = [
            "developer_token", "client_secret", "refresh_token",
            "access_token", "oauth_code",
        ]
        for rd in all_dicts:
            output_str = json.dumps(rd)
            for key in forbidden_keys:
                assert key not in output_str, f"Forbidden key '{key}' found in output"
        print("PASS: no secret-bearing keys in any resolved output")

        print(f"\n{_SEP}")
        print("  All assertions passed.")
        print(_SEP)

    finally:
        os.environ.pop("CREDENTIAL_REFERENCE_STORE_PATH", None)
        Path(store_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()

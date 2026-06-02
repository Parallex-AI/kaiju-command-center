"""
V5.6 — Admin credential reference write demo (no HTTP server required).

Calls upsert_google_ads_credential_reference() directly and prints the safe
redacted JSON response. Demonstrates create, update, and secret-rejection paths.

Usage:
    cd ~/kaiju/openclaw
    ~/kaiju/.venv/bin/python3 run_admin_credentials_write_demo.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from admin import upsert_google_ads_credential_reference, get_google_ads_credential_status

_SEP = "-" * 60


def section(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def main() -> None:
    # Use a temp file so this demo never pollutes runtime/ state
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        store_path = f.name
    os.environ["CREDENTIAL_REFERENCE_STORE_PATH"] = store_path

    try:
        print("V5.6 — Admin Credential Reference Write Demo")

        # ------------------------------------------------------------------
        # 1. Create a new credential reference
        # ------------------------------------------------------------------
        section("1. upsert — create new reference")
        result = upsert_google_ads_credential_reference(
            "demo-tenant",
            "demo-client",
            {"customer_id": "123-456-7890", "login_customer_id": "000-000-0001"},
        )
        print(json.dumps(result, indent=2))

        assert result["ok"] is True, f"Expected ok=true, got: {result}"
        assert result["tenant_id"] == "demo-tenant"
        assert result["client_id"] == "demo-client"
        assert result["integration_type"] == "google_ads"
        assert result["credential_status"]["status"] == "configured"
        assert result["credential_status"]["configured"] is True
        assert result["credential_status"]["credential_ref"] is not None
        assert result["errors"] == []
        print("PASS: ok=true, status=configured, configured=true, credential_ref set")

        # ------------------------------------------------------------------
        # 2. Update existing reference — preserve created_at, credential_ref
        # ------------------------------------------------------------------
        section("2. upsert — update existing reference")
        first_ref = result["credential_status"]["credential_ref"]
        first_created_at = result["credential_status"].get("created_at")

        result2 = upsert_google_ads_credential_reference(
            "demo-tenant",
            "demo-client",
            {"customer_id": "999-888-7777", "status": "active"},
        )
        print(json.dumps(result2, indent=2))

        assert result2["ok"] is True
        assert result2["credential_status"]["status"] == "active"
        assert result2["credential_status"]["credential_ref"] == first_ref, (
            "credential_ref must be preserved on update"
        )
        if first_created_at:
            assert result2["credential_status"].get("created_at") == first_created_at, (
                "created_at must be preserved on update"
            )
        print("PASS: status updated, credential_ref and created_at preserved")

        # ------------------------------------------------------------------
        # 3. GET status reflects written state
        # ------------------------------------------------------------------
        section("3. get_google_ads_credential_status — reflects written state")
        status_result = get_google_ads_credential_status("demo-tenant", "demo-client")
        print(json.dumps(status_result, indent=2))

        assert status_result["ok"] is True
        assert status_result["credential_status"]["status"] == "active"
        assert status_result["credential_status"]["configured"] is True
        print("PASS: GET status reflects written state")

        # ------------------------------------------------------------------
        # 4. Reject secret-like fields
        # ------------------------------------------------------------------
        section("4. upsert — reject secret-like fields")
        forbidden_payloads = [
            {"customer_id": "123", "developer_token": "secret-value"},
            {"customer_id": "123", "client_secret": "shh"},
            {"customer_id": "123", "refresh_token": "tok123"},
            {"customer_id": "123", "access_token": "abc"},
            {"customer_id": "123", "metadata": {"oauth_code": "code123"}},
            {"customer_id": "123", "auth_header": "Bearer xyz"},
        ]
        for bad_payload in forbidden_payloads:
            r = upsert_google_ads_credential_reference("demo-tenant", "demo-client", bad_payload)
            assert r["ok"] is False, f"Expected rejection for payload: {bad_payload}"
            assert r["errors"][0]["code"] == "secret_material_rejected", (
                f"Expected secret_material_rejected, got: {r['errors'][0]['code']}"
            )
            output_str = json.dumps(r)
            for val in bad_payload.values():
                if isinstance(val, str):
                    assert val not in output_str, f"Secret value '{val}' leaked into response"
        print(f"PASS: all {len(forbidden_payloads)} forbidden payloads rejected with secret_material_rejected")

        # ------------------------------------------------------------------
        # 5. Reject empty/None payload
        # ------------------------------------------------------------------
        section("5. upsert — reject empty payload")
        r_empty = upsert_google_ads_credential_reference("demo-tenant", "demo-client", None)
        assert r_empty["ok"] is False
        assert r_empty["errors"][0]["code"] == "invalid_request"
        r_empty2 = upsert_google_ads_credential_reference("demo-tenant", "demo-client", {})
        assert r_empty2["ok"] is False
        assert r_empty2["errors"][0]["code"] == "invalid_request"
        print("PASS: None and empty-dict payloads rejected with invalid_request")

        # ------------------------------------------------------------------
        # 6. Reject invalid status value
        # ------------------------------------------------------------------
        section("6. upsert — reject invalid status")
        r_bad_status = upsert_google_ads_credential_reference(
            "demo-tenant", "demo-client",
            {"customer_id": "123", "status": "not_a_real_status"},
        )
        assert r_bad_status["ok"] is False
        assert r_bad_status["errors"][0]["code"] == "invalid_status"
        print("PASS: invalid status rejected with invalid_status")

        # ------------------------------------------------------------------
        # 7. Secret-safety assertion on all outputs
        # ------------------------------------------------------------------
        section("7. Secret-safety assertion")
        all_results = [result, result2, status_result]
        forbidden_keys = [
            "developer_token", "client_secret", "refresh_token",
            "access_token", "oauth_code",
        ]
        for r in all_results:
            output_str = json.dumps(r)
            for key in forbidden_keys:
                assert key not in output_str, f"Forbidden key '{key}' found in output"
        print("PASS: no secret-bearing keys in any success response")

        print(f"\n{_SEP}")
        print("  All assertions passed.")
        print(_SEP)

    finally:
        os.environ.pop("CREDENTIAL_REFERENCE_STORE_PATH", None)
        Path(store_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()

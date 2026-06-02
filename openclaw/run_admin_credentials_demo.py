"""
V5.5 — Admin credential status demo (no HTTP server required).

Calls get_google_ads_credential_status() directly and prints the safe
redacted JSON response. Demonstrates the missing-credential path.

Usage:
    cd ~/kaiju/openclaw
    ~/kaiju/.venv/bin/python3 run_admin_credentials_demo.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from admin import get_google_ads_credential_status

_SEP = "-" * 60


def section(title: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {title}")
    print(_SEP)


def main() -> None:
    print("V5.5 — Admin Credential Status Demo")

    # ------------------------------------------------------------------
    # 1. Missing credential (no store file yet)
    # ------------------------------------------------------------------
    section("1. get_google_ads_credential_status — missing")
    result = get_google_ads_credential_status("demo-tenant", "demo-client")
    print(json.dumps(result, indent=2))

    assert result["ok"] is True, f"Expected ok=true, got: {result}"
    assert result["tenant_id"] == "demo-tenant"
    assert result["client_id"] == "demo-client"
    assert result["integration_type"] == "google_ads"
    assert result["credential_status"]["status"] == "missing"
    assert result["credential_status"]["configured"] is False
    assert result["credential_status"]["credential_ref"] is None
    assert result["errors"] == []
    print("PASS: ok=true, status=missing, configured=false, errors=[]")

    # ------------------------------------------------------------------
    # 2. Verify no secret values in output
    # ------------------------------------------------------------------
    section("2. Secret-safety assertion")
    output_str = json.dumps(result)
    forbidden = [
        "developer_token",
        "client_secret",
        "refresh_token",
        "access_token",
        "oauth_code",
    ]
    for key in forbidden:
        assert key not in output_str, f"Forbidden key '{key}' found in output"
    print("PASS: no secret-bearing keys present in output")

    # ------------------------------------------------------------------
    # 3. Different tenant/client — still safe
    # ------------------------------------------------------------------
    section("3. Different tenant/client — missing")
    result2 = get_google_ads_credential_status("acme-corp", "client-001")
    assert result2["ok"] is True
    assert result2["credential_status"]["status"] == "missing"
    assert result2["tenant_id"] == "acme-corp"
    assert result2["client_id"] == "client-001"
    print(f"tenant_id : {result2['tenant_id']}")
    print(f"client_id : {result2['client_id']}")
    print(f"status    : {result2['credential_status']['status']}")
    print("PASS: returns missing status for any unconfigured tenant/client")

    print(f"\n{_SEP}")
    print("  All assertions passed.")
    print(_SEP)


if __name__ == "__main__":
    main()

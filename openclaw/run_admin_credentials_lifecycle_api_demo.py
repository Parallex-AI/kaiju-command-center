"""
V5.15 Phase 2 — Credential lifecycle validation API demo (FastAPI TestClient).

Verifies the POST /credentials/google-ads/validate endpoint via TestClient.
No HTTP server. No GCP. No live Google Ads API calls. Fake values only.

Scenarios:
  Validate A — after full bundle write: structurally_complete=true, status=active
  Validate B — before any write (credential_not_found): 404
  Validate C — after metadata-only write (no secrets): structurally_complete=false

Env vars are set before importing server to avoid module-level config issues.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

_OPENCLAW_DIR = str(Path(__file__).resolve().parent)
_ADS_AGENT_DIR = str(Path(__file__).resolve().parents[1] / "agents" / "ads-agent")
for _p in (_OPENCLAW_DIR, _ADS_AGENT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_FAKE_SECRETS = {
    "developer_token": "fake-dev-token",
    "client_id": "fake-client-id",
    "client_secret": "fake-client-secret",
    "refresh_token": "fake-refresh-token",
}
_FAKE_VALUES: set = set(_FAKE_SECRETS.values()) | {"fake-access-token"}

_PASS = "PASS"
_FAIL = "FAIL"


def _check(condition: bool, label: str) -> bool:
    tag = _PASS if condition else _FAIL
    print(f"  {tag}: {label}")
    return condition


def _no_fake_values(d: dict, label: str) -> bool:
    raw = json.dumps(d)
    leaked = [v for v in _FAKE_VALUES if v in raw]
    ok = len(leaked) == 0
    tag = _PASS if ok else _FAIL
    detail = f" — leaked: {leaked}" if leaked else ""
    print(f"  {tag}: {label}{detail}")
    return ok


def run_demo():
    tmp_dir = tempfile.mkdtemp(prefix="kaiju_lifecycle_api_demo_")
    tmp_store_path = os.path.join(tmp_dir, "credential_references.json")

    original_env = {}
    env_overrides = {
        "CREDENTIAL_REFERENCE_STORE_PATH": tmp_store_path,
        "OPENCLAW_API_AUTH_ENABLED": "false",
        "GCP_SECRET_MANAGER_ENABLED": "false",
        "GOOGLE_ADS_LIVE_ENABLED": "false",
        "OPENCLAW_AUDIT_ENABLED": "false",
    }
    for k, v in env_overrides.items():
        original_env[k] = os.environ.get(k)
        os.environ[k] = v

    for mod in list(sys.modules.keys()):
        if mod in ("server", "admin", "config", "auth", "openclaw", "schemas", "audit"):
            del sys.modules[mod]

    print("V5.15 — Admin Credential Lifecycle Validation Demo (FastAPI TestClient)")
    print("No HTTP server. GCP_SECRET_MANAGER_ENABLED=false → InMemorySecretStore.")
    print("GOOGLE_ADS_LIVE_ENABLED=false. OPENCLAW_API_AUTH_ENABLED=false.\n")

    try:
        from fastapi.testclient import TestClient
        from server import app
        import admin as _admin_mod
        from credentials.secret_store import InMemorySecretStore as _InMemory

        # Patch create_secret_store so that all routes in this demo share the same
        # in-memory backend. Without this, each factory call returns a fresh instance
        # and the bundle written by the write route would be invisible to the validate
        # route. In production, a persistent backend (GCP) shares state naturally.
        _shared_store = _InMemory()
        _original_create_secret_store = _admin_mod.create_secret_store
        _admin_mod.create_secret_store = lambda: _shared_store

        client = TestClient(app, raise_server_exceptions=True)

        _TENANT = "api-lifecycle-tenant"
        _CLIENT = "api-lifecycle-client"
        _BASE = f"/openclaw/admin/tenants/{_TENANT}/clients/{_CLIENT}/credentials/google-ads"

        all_pass = True

        # ── Scenario Validate B — validate before any write (404) ─────────────
        print("-" * 60)
        print("  Validate B. Validate before write → 404 credential_not_found")
        print("-" * 60)
        r_vb = client.post(f"{_BASE}/validate")
        print(f"Status: {r_vb.status_code}")
        d_vb = r_vb.json()
        print(json.dumps(d_vb, indent=2))
        ok_vb = _check(r_vb.status_code == 404, "status 404 for missing credential")
        ok_vb &= _check(d_vb.get("ok") is False, "ok=false")
        codes_vb = [e.get("code") for e in d_vb.get("errors", []) if isinstance(e, dict)]
        ok_vb &= _check("credential_not_found" in codes_vb, "error credential_not_found")
        ok_vb &= _no_fake_values(d_vb, "no fake values in 404 response")
        all_pass = all_pass and ok_vb

        # ── Scenario Validate A — full bundle, then validate → 200, complete ──
        print("\n" + "-" * 60)
        print("  Validate A. Full bundle POST then validate → 200, complete")
        print("-" * 60)
        r_write = client.post(_BASE, json={"customer_id": "1234567890", **_FAKE_SECRETS})
        assert r_write.status_code == 200, f"bundle write failed: {r_write.text[:200]}"
        r_va = client.post(f"{_BASE}/validate")
        print(f"Status: {r_va.status_code}")
        d_va = r_va.json()
        print(json.dumps(d_va, indent=2))
        ok_va = _check(r_va.status_code == 200, "status 200")
        ok_va &= _check(d_va.get("ok") is True, "ok=true")
        vr_va = d_va.get("validation_result") or {}
        ok_va &= _check(vr_va.get("structurally_complete") is True, "structurally_complete=true")
        ok_va &= _check(vr_va.get("missing_fields") == [], "missing_fields=[]")
        ok_va &= _check(vr_va.get("live_api_tested") is False, "live_api_tested=false")
        ok_va &= _check(vr_va.get("last_validated_at") is not None, "last_validated_at set")
        cred_va = d_va.get("credential_status") or {}
        ok_va &= _check(cred_va.get("status") == "active", "credential status=active")
        ss_va = d_va.get("secret_status") or {}
        ok_va &= _check(ss_va.get("configured") is True, "secret_status.configured=true")
        ok_va &= _no_fake_values(d_va, "no fake values in validate response")
        all_pass = all_pass and ok_va

        # ── Scenario Validate C — metadata-only write, then validate → incomplete
        print("\n" + "-" * 60)
        print("  Validate C. Metadata-only write then validate → incomplete")
        print("-" * 60)
        _T_C = "api-lifecycle-tenant-c"
        _C_C = "api-lifecycle-client-c"
        _BASE_C = f"/openclaw/admin/tenants/{_T_C}/clients/{_C_C}/credentials/google-ads"
        r_meta = client.post(_BASE_C, json={"customer_id": "9999999999"})
        assert r_meta.status_code == 200, f"metadata write failed: {r_meta.text[:200]}"
        r_vc = client.post(f"{_BASE_C}/validate")
        print(f"Status: {r_vc.status_code}")
        d_vc = r_vc.json()
        print(json.dumps(d_vc, indent=2))
        ok_vc = _check(r_vc.status_code == 200, "status 200 (process ran)")
        ok_vc &= _check(d_vc.get("ok") is True, "ok=true")
        vr_vc = d_vc.get("validation_result") or {}
        ok_vc &= _check(vr_vc.get("structurally_complete") is False, "structurally_complete=false")
        missing_vc = vr_vc.get("missing_fields") or []
        ok_vc &= _check(len(missing_vc) > 0, f"missing_fields non-empty (got {missing_vc})")
        ok_vc &= _check(vr_vc.get("live_api_tested") is False, "live_api_tested=false")
        cred_vc = d_vc.get("credential_status") or {}
        ok_vc &= _check(cred_vc.get("status") == "validation_failed", "status=validation_failed")
        ok_vc &= _no_fake_values(d_vc, "no fake values in incomplete validate response")
        all_pass = all_pass and ok_vc

        # ── Leak assertion across all API responses ───────────────────────────
        print("\n" + "-" * 60)
        print("  Leak assertion — all API responses")
        print("-" * 60)
        ok_leak = True
        for resp_dict, label in [(d_vb, "404 response"), (d_va, "validate-A"), (d_vc, "validate-C")]:
            ok_leak &= _no_fake_values(resp_dict, f"no fake values in {label}")
        all_pass = all_pass and ok_leak

        print()
        if all_pass:
            print("-" * 60)
            print("  All assertions passed.")
            print("-" * 60)
        else:
            print("-" * 60)
            print("  FAIL: Some assertions failed — see above.")
            print("-" * 60)

        return 0 if all_pass else 1

    finally:
        try:
            _admin_mod.create_secret_store = _original_create_secret_store
        except NameError:
            pass
        for k, v in original_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
        for mod in list(sys.modules.keys()):
            if mod in ("server", "admin", "config", "auth", "openclaw", "schemas", "audit"):
                del sys.modules[mod]


if __name__ == "__main__":
    sys.exit(run_demo())

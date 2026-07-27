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

        # ── Scenario Delete E — auth required ────────────────────────────────
        print("\n" + "-" * 60)
        print("  Delete E. DELETE without auth token → 401")
        print("-" * 60)
        # get_config() reads env fresh on every call (no cache), so temporarily
        # enabling auth here is picked up immediately by the live route handler.
        # No server reimport needed.
        os.environ["OPENCLAW_API_AUTH_ENABLED"] = "true"
        os.environ["OPENCLAW_API_KEYS"] = "test-delete-key"
        r_de = client.delete(_BASE)
        print(f"Status: {r_de.status_code}")
        ok_de = _check(r_de.status_code == 401, "status 401 without auth token")
        ok_de &= _check(r_de.json().get("ok") is False, "ok=false")
        ok_de &= _no_fake_values(r_de.json(), "no fake values in 401 response")
        os.environ["OPENCLAW_API_AUTH_ENABLED"] = "false"
        os.environ.pop("OPENCLAW_API_KEYS", None)
        all_pass = all_pass and ok_de

        # ── Scenario Delete A — disabled by default → 403 ────────────────────
        print("\n" + "-" * 60)
        print("  Delete A. DELETE without OPENCLAW_ADMIN_DELETE_ENABLED → 403")
        print("-" * 60)
        os.environ.pop("OPENCLAW_ADMIN_DELETE_ENABLED", None)
        r_da = client.delete(_BASE)
        print(f"Status: {r_da.status_code}")
        d_da = r_da.json()
        print(json.dumps(d_da, indent=2))
        ok_da = _check(r_da.status_code == 403, "status 403 when delete disabled")
        ok_da &= _check(d_da.get("ok") is False, "ok=false")
        codes_da = [e.get("code") for e in d_da.get("errors", []) if isinstance(e, dict)]
        ok_da &= _check("delete_not_enabled" in codes_da, "error delete_not_enabled")
        ok_da &= _no_fake_values(d_da, "no fake values in 403 response")
        all_pass = all_pass and ok_da

        # ── Scenario Delete D — enabled missing credential → 404 ─────────────
        print("\n" + "-" * 60)
        print("  Delete D. DELETE enabled but missing credential → 404")
        print("-" * 60)
        os.environ["OPENCLAW_ADMIN_DELETE_ENABLED"] = "true"
        _T_D2 = "api-delete-missing-tenant"
        _C_D2 = "api-delete-missing-client"
        _BASE_D2 = f"/openclaw/admin/tenants/{_T_D2}/clients/{_C_D2}/credentials/google-ads"
        r_dd = client.delete(_BASE_D2)
        print(f"Status: {r_dd.status_code}")
        d_dd = r_dd.json()
        print(json.dumps(d_dd, indent=2))
        ok_dd = _check(r_dd.status_code == 404, "status 404 for missing credential")
        ok_dd &= _check(d_dd.get("ok") is False, "ok=false")
        codes_dd = [e.get("code") for e in d_dd.get("errors", []) if isinstance(e, dict)]
        ok_dd &= _check("credential_not_found" in codes_dd, "error credential_not_found")
        ok_dd &= _no_fake_values(d_dd, "no fake values in 404 delete response")
        all_pass = all_pass and ok_dd

        # ── Scenario Delete B — enabled success → 200, status=revoked ────────
        print("\n" + "-" * 60)
        print("  Delete B. Full bundle then DELETE → 200, status=revoked")
        print("-" * 60)
        _T_B2 = "api-delete-success-tenant"
        _C_B2 = "api-delete-success-client"
        _BASE_B2 = f"/openclaw/admin/tenants/{_T_B2}/clients/{_C_B2}/credentials/google-ads"
        r_write2 = client.post(_BASE_B2, json={"customer_id": "7777777777", **_FAKE_SECRETS})
        assert r_write2.status_code == 200, f"bundle write failed: {r_write2.text[:200]}"
        r_db = client.delete(_BASE_B2)
        print(f"Status: {r_db.status_code}")
        d_db = r_db.json()
        print(json.dumps(d_db, indent=2))
        ok_db = _check(r_db.status_code == 200, "status 200 for successful delete")
        ok_db &= _check(d_db.get("ok") is True, "ok=true")
        ok_db &= _check(d_db.get("errors") == [], "errors=[]")
        cred_db = d_db.get("credential_status") or {}
        ok_db &= _check(cred_db.get("status") == "revoked", "credential status=revoked")
        ss_db = d_db.get("secret_status") or {}
        ok_db &= _check(ss_db.get("configured") is False, "secret_status.configured=false")
        ok_db &= _no_fake_values(d_db, "no fake values in delete response")
        all_pass = all_pass and ok_db

        # ── Scenario Delete C — idempotent delete → 200, warnings ────────────
        print("\n" + "-" * 60)
        print("  Delete C. DELETE same credential again → 200, idempotent")
        print("-" * 60)
        r_dc = client.delete(_BASE_B2)
        print(f"Status: {r_dc.status_code}")
        d_dc = r_dc.json()
        print(json.dumps(d_dc, indent=2))
        ok_dc = _check(r_dc.status_code == 200, "status 200 for idempotent delete")
        ok_dc &= _check(d_dc.get("ok") is True, "ok=true")
        ok_dc &= _check("secret_already_absent" in (d_dc.get("warnings") or []),
                        "warnings includes secret_already_absent")
        cred_dc = d_dc.get("credential_status") or {}
        ok_dc &= _check(cred_dc.get("status") == "revoked", "status remains revoked")
        ok_dc &= _no_fake_values(d_dc, "no fake values in idempotent delete response")
        all_pass = all_pass and ok_dc

        # ── Leak assertion across all API responses ───────────────────────────
        print("\n" + "-" * 60)
        print("  Leak assertion — all API responses")
        print("-" * 60)
        ok_leak = True
        all_responses = [
            (d_vb, "404-validate"), (d_va, "validate-A"), (d_vc, "validate-C"),
            (d_da, "403-delete-disabled"), (d_dd, "404-delete-missing"),
            (d_db, "delete-success"), (d_dc, "delete-idempotent"),
        ]
        for resp_dict, label in all_responses:
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
        os.environ.pop("OPENCLAW_ADMIN_DELETE_ENABLED", None)
        os.environ.pop("OPENCLAW_API_KEYS", None)
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

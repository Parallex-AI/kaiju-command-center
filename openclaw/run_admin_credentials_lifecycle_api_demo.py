"""
V5.15 / V5.16 / V5.17 — Credential lifecycle validation, RBAC, rotation, and per-tenant
token isolation API demo (FastAPI TestClient).

No HTTP server. No GCP. No live Google Ads API calls. Fake values only.

V5.15 scenarios:
  Validate A — after full bundle write: structurally_complete=true, status=active
  Validate B — before any write (credential_not_found): 404
  Validate C — after metadata-only write (no secrets): structurally_complete=false
  Delete E/A/D/B/C — auth, gate, missing, success, idempotent

V5.16 RBAC scenarios (A–H):
  RBAC A — read key can read status (GET)
  RBAC B — read key cannot write (POST bundle → 403 scope_not_granted)
  RBAC C — read key cannot validate (POST validate → 403 scope_not_granted)
  RBAC D — read key cannot delete even if OPENCLAW_ADMIN_DELETE_ENABLED=true
  RBAC E — admin key can write, validate, delete
  RBAC F — OPENCLAW_API_KEYS fallback grants read only
  RBAC G — invalid token → 401 unauthorized
  RBAC H — missing token → 401 unauthorized

V5.16 Phase 2 audit warning:
  Audit Warning API — audit failure → HTTP 200 with warnings=['audit_append_failed']

V5.16 Phase 3 rotate scenarios (A–F):
  Rotate A — full bundle write, then rotate → 200, ok=true, status=active
  Rotate B — rotate before any write → 404 credential_not_found
  Rotate C — rotate REVOKED credential → 409 invalid_status_for_rotation
  Rotate D — rotate with incomplete payload → 400, missing_fields
  Rotate E — read token cannot rotate → 403 scope_not_granted
  Rotate F — admin token can rotate → 200 ok=true

V5.17 Phase 3 per-tenant token isolation scenarios (A–G):
  Tenant A — no OPENCLAW_TENANT_KEYS → backward compat, all tenants accessible
  Tenant B — token restricted to tenant-a → allowed; tenant-b → 403 tenant_access_denied
  Tenant C — token for multiple tenants → all listed tenants allowed
  Tenant D — token not listed while map is set → global access (backward compat)
  Tenant E — scope check before tenant check: read token on WRITE → scope_not_granted
  Tenant F — invalid token → 401 unauthorized (not tenant_access_denied)
  Tenant G — no token values or allow-list strings in any tenant scenario response

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

        # ── RBAC scenarios ────────────────────────────────────────────────────
        # Enable auth for all RBAC scenarios; restore to false at the end.
        _ADMIN_TOKEN = "rbac-admin-test-key"
        _READ_TOKEN = "rbac-read-test-key"
        _API_FALLBACK_TOKEN = "rbac-api-fallback-key"
        _INVALID_TOKEN = "totally-invalid-token-xyz"

        os.environ["OPENCLAW_API_AUTH_ENABLED"] = "true"
        os.environ["OPENCLAW_ADMIN_KEYS"] = _ADMIN_TOKEN
        os.environ["OPENCLAW_READ_KEYS"] = _READ_TOKEN
        os.environ.pop("OPENCLAW_API_KEYS", None)

        _RBAC_TENANT = "rbac-test-tenant"
        _RBAC_CLIENT = "rbac-test-client"
        _RBAC_BASE = f"/openclaw/admin/tenants/{_RBAC_TENANT}/clients/{_RBAC_CLIENT}/credentials/google-ads"
        _READ_HDR = {"Authorization": f"Bearer {_READ_TOKEN}"}
        _ADMIN_HDR = {"Authorization": f"Bearer {_ADMIN_TOKEN}"}

        # ── RBAC A — read token can read status ───────────────────────────────
        print("\n" + "-" * 60)
        print("  RBAC A. Read token can read status (GET /status)")
        print("-" * 60)
        r_ra = client.get(f"{_RBAC_BASE}/status", headers=_READ_HDR)
        print(f"Status: {r_ra.status_code}")
        d_ra = r_ra.json()
        ok_ra = _check(r_ra.status_code == 200, "status 200 with read token")
        ok_ra &= _check(d_ra.get("ok") is True, "ok=true")
        ok_ra &= _no_fake_values(d_ra, "no fake values in RBAC A response")
        all_pass = all_pass and ok_ra

        # ── RBAC B — read token cannot write bundle ────────────────────────────
        print("\n" + "-" * 60)
        print("  RBAC B. Read token cannot write bundle (POST / → 403)")
        print("-" * 60)
        r_rb = client.post(_RBAC_BASE, json={"customer_id": "1111111111", **_FAKE_SECRETS},
                           headers=_READ_HDR)
        print(f"Status: {r_rb.status_code}")
        d_rb = r_rb.json()
        ok_rb = _check(r_rb.status_code == 403, "status 403 scope_not_granted for write")
        ok_rb &= _check(d_rb.get("ok") is False, "ok=false")
        codes_rb = [e.get("code") for e in d_rb.get("errors", []) if isinstance(e, dict)]
        ok_rb &= _check("scope_not_granted" in codes_rb, "error code scope_not_granted")
        ok_rb &= _no_fake_values(d_rb, "no fake values in RBAC B response")
        all_pass = all_pass and ok_rb

        # ── RBAC C — read token cannot validate ───────────────────────────────
        print("\n" + "-" * 60)
        print("  RBAC C. Read token cannot validate (POST /validate → 403)")
        print("-" * 60)
        r_rc = client.post(f"{_RBAC_BASE}/validate", headers=_READ_HDR)
        print(f"Status: {r_rc.status_code}")
        d_rc = r_rc.json()
        ok_rc = _check(r_rc.status_code == 403, "status 403 scope_not_granted for validate")
        ok_rc &= _check(d_rc.get("ok") is False, "ok=false")
        codes_rc = [e.get("code") for e in d_rc.get("errors", []) if isinstance(e, dict)]
        ok_rc &= _check("scope_not_granted" in codes_rc, "error code scope_not_granted")
        ok_rc &= _no_fake_values(d_rc, "no fake values in RBAC C response")
        all_pass = all_pass and ok_rc

        # ── RBAC D — read token cannot delete even if gate enabled ────────────
        print("\n" + "-" * 60)
        print("  RBAC D. Read token cannot delete even when OPENCLAW_ADMIN_DELETE_ENABLED=true")
        print("-" * 60)
        os.environ["OPENCLAW_ADMIN_DELETE_ENABLED"] = "true"
        r_rd = client.delete(_RBAC_BASE, headers=_READ_HDR)
        print(f"Status: {r_rd.status_code}")
        d_rd = r_rd.json()
        ok_rd = _check(r_rd.status_code == 403, "status 403 (scope_not_granted, not delete_not_enabled)")
        ok_rd &= _check(d_rd.get("ok") is False, "ok=false")
        codes_rd = [e.get("code") for e in d_rd.get("errors", []) if isinstance(e, dict)]
        ok_rd &= _check("scope_not_granted" in codes_rd, "error code scope_not_granted")
        ok_rd &= _check("delete_not_enabled" not in codes_rd, "not delete_not_enabled")
        ok_rd &= _no_fake_values(d_rd, "no fake values in RBAC D response")
        os.environ.pop("OPENCLAW_ADMIN_DELETE_ENABLED", None)
        all_pass = all_pass and ok_rd

        # ── RBAC E — admin token can write, validate, and delete ──────────────
        print("\n" + "-" * 60)
        print("  RBAC E. Admin token can write, validate, and delete")
        print("-" * 60)
        _RE_TENANT = "rbac-e-tenant"
        _RE_CLIENT = "rbac-e-client"
        _RE_BASE = f"/openclaw/admin/tenants/{_RE_TENANT}/clients/{_RE_CLIENT}/credentials/google-ads"
        ok_re = True
        # write
        r_re_w = client.post(_RE_BASE, json={"customer_id": "2222222222", **_FAKE_SECRETS},
                             headers=_ADMIN_HDR)
        print(f"  Write status: {r_re_w.status_code}")
        ok_re &= _check(r_re_w.status_code == 200, "admin write → 200")
        ok_re &= _no_fake_values(r_re_w.json(), "no fake values in RBAC E write")
        # validate
        r_re_v = client.post(f"{_RE_BASE}/validate", headers=_ADMIN_HDR)
        print(f"  Validate status: {r_re_v.status_code}")
        ok_re &= _check(r_re_v.status_code == 200, "admin validate → 200")
        vr_re = r_re_v.json().get("validation_result") or {}
        ok_re &= _check(vr_re.get("structurally_complete") is True, "structurally_complete=true")
        ok_re &= _no_fake_values(r_re_v.json(), "no fake values in RBAC E validate")
        # delete
        os.environ["OPENCLAW_ADMIN_DELETE_ENABLED"] = "true"
        r_re_d = client.delete(_RE_BASE, headers=_ADMIN_HDR)
        print(f"  Delete status: {r_re_d.status_code}")
        ok_re &= _check(r_re_d.status_code == 200, "admin delete → 200")
        cred_re = r_re_d.json().get("credential_status") or {}
        ok_re &= _check(cred_re.get("status") == "revoked", "status=revoked after delete")
        ok_re &= _no_fake_values(r_re_d.json(), "no fake values in RBAC E delete")
        os.environ.pop("OPENCLAW_ADMIN_DELETE_ENABLED", None)
        all_pass = all_pass and ok_re

        # ── RBAC F — OPENCLAW_API_KEYS fallback grants read only ──────────────
        print("\n" + "-" * 60)
        print("  RBAC F. OPENCLAW_API_KEYS fallback grants read only")
        print("-" * 60)
        os.environ.pop("OPENCLAW_ADMIN_KEYS", None)
        os.environ.pop("OPENCLAW_READ_KEYS", None)
        os.environ["OPENCLAW_API_KEYS"] = _API_FALLBACK_TOKEN
        _FALLBACK_HDR = {"Authorization": f"Bearer {_API_FALLBACK_TOKEN}"}
        _RF_BASE = f"/openclaw/admin/tenants/rbac-f-tenant/clients/rbac-f-client/credentials/google-ads"
        # read works
        r_rf_r = client.get(f"{_RF_BASE}/status", headers=_FALLBACK_HDR)
        print(f"  Status status: {r_rf_r.status_code}")
        ok_rf = _check(r_rf_r.status_code == 200, "api_keys fallback token can read status")
        # write denied
        r_rf_w = client.post(_RF_BASE, json={"customer_id": "3333333333", **_FAKE_SECRETS},
                              headers=_FALLBACK_HDR)
        print(f"  Write status: {r_rf_w.status_code}")
        ok_rf &= _check(r_rf_w.status_code == 403, "api_keys fallback token cannot write (403)")
        codes_rf = [e.get("code") for e in r_rf_w.json().get("errors", []) if isinstance(e, dict)]
        ok_rf &= _check("scope_not_granted" in codes_rf, "error code scope_not_granted")
        ok_rf &= _no_fake_values(r_rf_w.json(), "no fake values in RBAC F response")
        # restore
        os.environ["OPENCLAW_ADMIN_KEYS"] = _ADMIN_TOKEN
        os.environ["OPENCLAW_READ_KEYS"] = _READ_TOKEN
        os.environ.pop("OPENCLAW_API_KEYS", None)
        all_pass = all_pass and ok_rf

        # ── RBAC G — invalid token → 401 ──────────────────────────────────────
        print("\n" + "-" * 60)
        print("  RBAC G. Invalid token → 401 unauthorized")
        print("-" * 60)
        _INVALID_HDR = {"Authorization": f"Bearer {_INVALID_TOKEN}"}
        r_rg = client.get(f"{_RBAC_BASE}/status", headers=_INVALID_HDR)
        print(f"Status: {r_rg.status_code}")
        d_rg = r_rg.json()
        ok_rg = _check(r_rg.status_code == 401, "status 401 for invalid token")
        ok_rg &= _check(d_rg.get("ok") is False, "ok=false")
        codes_rg = [e.get("code") for e in d_rg.get("errors", []) if isinstance(e, dict)]
        ok_rg &= _check("unauthorized" in codes_rg, "error code unauthorized")
        ok_rg &= _no_fake_values(d_rg, "no fake values in RBAC G response")
        all_pass = all_pass and ok_rg

        # ── RBAC H — missing token → 401 ──────────────────────────────────────
        print("\n" + "-" * 60)
        print("  RBAC H. Missing token → 401 unauthorized")
        print("-" * 60)
        r_rh = client.post(f"{_RBAC_BASE}/validate")
        print(f"Status: {r_rh.status_code}")
        d_rh = r_rh.json()
        ok_rh = _check(r_rh.status_code == 401, "status 401 for missing token")
        ok_rh &= _check(d_rh.get("ok") is False, "ok=false")
        codes_rh = [e.get("code") for e in d_rh.get("errors", []) if isinstance(e, dict)]
        ok_rh &= _check("unauthorized" in codes_rh, "error code unauthorized")
        ok_rh &= _no_fake_values(d_rh, "no fake values in RBAC H response")
        all_pass = all_pass and ok_rh

        # Restore to no-auth state for remaining scenarios
        os.environ["OPENCLAW_API_AUTH_ENABLED"] = "false"
        os.environ.pop("OPENCLAW_ADMIN_KEYS", None)
        os.environ.pop("OPENCLAW_READ_KEYS", None)

        # ── Audit Warning API — audit failure propagated as response warning ───
        print("\n" + "-" * 60)
        print("  Audit Warning API. Audit failure → 200 with warnings=['audit_append_failed']")
        print("-" * 60)
        _AW_TENANT = "audit-warn-tenant"
        _AW_CLIENT = "audit-warn-client"
        _AW_BASE = f"/openclaw/admin/tenants/{_AW_TENANT}/clients/{_AW_CLIENT}/credentials/google-ads"

        # Prep: write a credential reference so validate has something to find
        r_aw_prep = client.post(_AW_BASE, json={"customer_id": "8888888888"})
        assert r_aw_prep.status_code == 200, f"prep write failed: {r_aw_prep.text[:200]}"

        # Monkeypatch append_audit_event in admin's namespace to always return failure
        _original_append_audit = _admin_mod.append_audit_event
        _admin_mod.append_audit_event = lambda event: {"ok": False, "error": "IOError"}
        try:
            r_aw = client.post(_AW_BASE, json={"customer_id": "7654321098"})
            print(f"  Write status: {r_aw.status_code}")
            d_aw = r_aw.json()
            ok_aw = _check(r_aw.status_code == 200, "audit failure → still HTTP 200")
            ok_aw &= _check(d_aw.get("ok") is True, "ok=true despite audit failure")
            ok_aw &= _check(
                "audit_append_failed" in (d_aw.get("warnings") or []),
                f"warnings includes audit_append_failed (got {d_aw.get('warnings')!r})"
            )
            ok_aw &= _no_fake_values(d_aw, "no fake values in audit-warn write response")
        finally:
            _admin_mod.append_audit_event = _original_append_audit
        all_pass = all_pass and ok_aw

        # ── Rotate scenarios (A–F) ────────────────────────────────────────────
        # Auth is disabled at this point (restored after RBAC and Audit Warning).
        _ROTATE_TENANT = "rotate-api-tenant"
        _ROTATE_CLIENT = "rotate-api-client"
        _ROTATE_BASE = (
            f"/openclaw/admin/tenants/{_ROTATE_TENANT}/clients/{_ROTATE_CLIENT}"
            f"/credentials/google-ads"
        )

        # ── Rotate A — full bundle then rotate → 200, ok=true, active ────────
        print("\n" + "-" * 60)
        print("  Rotate A. Full bundle then rotate → 200, ok=true, status=active")
        print("-" * 60)
        r_rot_init = client.post(_ROTATE_BASE, json={"customer_id": "5050505050", **_FAKE_SECRETS})
        assert r_rot_init.status_code == 200, f"initial bundle write failed: {r_rot_init.text[:200]}"
        r_rot_a = client.post(f"{_ROTATE_BASE}/rotate", json={**_FAKE_SECRETS})
        print(f"Status: {r_rot_a.status_code}")
        d_rot_a = r_rot_a.json()
        print(json.dumps(d_rot_a, indent=2))
        ok_rot_a = _check(r_rot_a.status_code == 200, "rotate A: status 200")
        ok_rot_a &= _check(d_rot_a.get("ok") is True, "rotate A: ok=true")
        rr_a = d_rot_a.get("rotation_result") or {}
        ok_rot_a &= _check(rr_a.get("structurally_complete") is True, "rotate A: structurally_complete=true")
        ok_rot_a &= _check(rr_a.get("missing_fields") == [], "rotate A: missing_fields=[]")
        ok_rot_a &= _check(rr_a.get("last_validated_at") is not None, "rotate A: last_validated_at set")
        cred_rot_a = d_rot_a.get("credential_status") or {}
        ok_rot_a &= _check(cred_rot_a.get("status") == "active", "rotate A: status=active")
        ss_rot_a = d_rot_a.get("secret_status") or {}
        ok_rot_a &= _check(ss_rot_a.get("configured") is True, "rotate A: secret_status.configured=true")
        ok_rot_a &= _no_fake_values(d_rot_a, "rotate A: no fake values")
        all_pass = all_pass and ok_rot_a

        # ── Rotate B — rotate before any write → 404 ─────────────────────────
        print("\n" + "-" * 60)
        print("  Rotate B. Rotate before any write → 404 credential_not_found")
        print("-" * 60)
        _ROT_B_BASE = (
            "/openclaw/admin/tenants/rotate-api-notfound-t"
            "/clients/rotate-api-notfound-c/credentials/google-ads"
        )
        r_rot_b = client.post(f"{_ROT_B_BASE}/rotate", json={**_FAKE_SECRETS})
        print(f"Status: {r_rot_b.status_code}")
        d_rot_b = r_rot_b.json()
        print(json.dumps(d_rot_b, indent=2))
        ok_rot_b = _check(r_rot_b.status_code == 404, "rotate B: status 404 for missing credential")
        ok_rot_b &= _check(d_rot_b.get("ok") is False, "rotate B: ok=false")
        codes_rot_b = [e.get("code") for e in d_rot_b.get("errors", []) if isinstance(e, dict)]
        ok_rot_b &= _check("credential_not_found" in codes_rot_b, "rotate B: error credential_not_found")
        ok_rot_b &= _no_fake_values(d_rot_b, "rotate B: no fake values in 404 response")
        all_pass = all_pass and ok_rot_b

        # ── Rotate C — rotate REVOKED credential → 409 ───────────────────────
        print("\n" + "-" * 60)
        print("  Rotate C. Rotate REVOKED credential → 409 invalid_status_for_rotation")
        print("-" * 60)
        _ROT_C_TENANT = "rotate-api-revoked-t"
        _ROT_C_CLIENT = "rotate-api-revoked-c"
        _ROT_C_BASE = (
            f"/openclaw/admin/tenants/{_ROT_C_TENANT}/clients/{_ROT_C_CLIENT}"
            f"/credentials/google-ads"
        )
        r_rot_c_w = client.post(_ROT_C_BASE, json={"customer_id": "6060606060", **_FAKE_SECRETS})
        assert r_rot_c_w.status_code == 200, f"rotate-C bundle write failed: {r_rot_c_w.text[:200]}"
        os.environ["OPENCLAW_ADMIN_DELETE_ENABLED"] = "true"
        r_rot_c_d = client.delete(_ROT_C_BASE)
        assert r_rot_c_d.status_code == 200, f"rotate-C delete failed: {r_rot_c_d.text[:200]}"
        os.environ.pop("OPENCLAW_ADMIN_DELETE_ENABLED", None)
        r_rot_c = client.post(f"{_ROT_C_BASE}/rotate", json={**_FAKE_SECRETS})
        print(f"Status: {r_rot_c.status_code}")
        d_rot_c = r_rot_c.json()
        print(json.dumps(d_rot_c, indent=2))
        ok_rot_c = _check(r_rot_c.status_code == 409, "rotate C: status 409 for revoked credential")
        ok_rot_c &= _check(d_rot_c.get("ok") is False, "rotate C: ok=false")
        codes_rot_c = [e.get("code") for e in d_rot_c.get("errors", []) if isinstance(e, dict)]
        ok_rot_c &= _check(
            "invalid_status_for_rotation" in codes_rot_c,
            "rotate C: error invalid_status_for_rotation"
        )
        ok_rot_c &= _no_fake_values(d_rot_c, "rotate C: no fake values in 409 response")
        all_pass = all_pass and ok_rot_c

        # ── Rotate D — incomplete payload → 400, missing_fields ──────────────
        print("\n" + "-" * 60)
        print("  Rotate D. Incomplete payload → 400, missing_fields")
        print("-" * 60)
        r_rot_d = client.post(
            f"{_ROTATE_BASE}/rotate",
            json={"developer_token": "fake-dev-token", "client_id": "fake-client-id"},
        )
        print(f"Status: {r_rot_d.status_code}")
        d_rot_d = r_rot_d.json()
        print(json.dumps(d_rot_d, indent=2))
        ok_rot_d = _check(r_rot_d.status_code == 400, "rotate D: status 400 for incomplete payload")
        ok_rot_d &= _check(d_rot_d.get("ok") is False, "rotate D: ok=false")
        codes_rot_d = [e.get("code") for e in d_rot_d.get("errors", []) if isinstance(e, dict)]
        ok_rot_d &= _check("secret_bundle_incomplete" in codes_rot_d, "rotate D: error secret_bundle_incomplete")
        rr_d = d_rot_d.get("rotation_result") or {}
        missing_rot_d = rr_d.get("missing_fields") or []
        ok_rot_d &= _check(len(missing_rot_d) > 0, f"rotate D: missing_fields non-empty (got {missing_rot_d})")
        ok_rot_d &= _no_fake_values(d_rot_d, "rotate D: no fake values in 400 response")
        all_pass = all_pass and ok_rot_d

        # ── Rotate E — read token cannot rotate → 403 ────────────────────────
        print("\n" + "-" * 60)
        print("  Rotate E. Read token cannot rotate → 403 scope_not_granted")
        print("-" * 60)
        os.environ["OPENCLAW_API_AUTH_ENABLED"] = "true"
        os.environ["OPENCLAW_ADMIN_KEYS"] = _ADMIN_TOKEN
        os.environ["OPENCLAW_READ_KEYS"] = _READ_TOKEN
        r_rot_e = client.post(
            f"{_ROTATE_BASE}/rotate",
            json={**_FAKE_SECRETS},
            headers=_READ_HDR,
        )
        print(f"Status: {r_rot_e.status_code}")
        d_rot_e = r_rot_e.json()
        ok_rot_e = _check(r_rot_e.status_code == 403, "rotate E: status 403 for read token")
        ok_rot_e &= _check(d_rot_e.get("ok") is False, "rotate E: ok=false")
        codes_rot_e = [e.get("code") for e in d_rot_e.get("errors", []) if isinstance(e, dict)]
        ok_rot_e &= _check("scope_not_granted" in codes_rot_e, "rotate E: error scope_not_granted")
        ok_rot_e &= _no_fake_values(d_rot_e, "rotate E: no fake values in 403 response")
        all_pass = all_pass and ok_rot_e

        # ── Rotate F — admin token can rotate → 200 ──────────────────────────
        print("\n" + "-" * 60)
        print("  Rotate F. Admin token can rotate → 200 ok=true")
        print("-" * 60)
        r_rot_f = client.post(
            f"{_ROTATE_BASE}/rotate",
            json={**_FAKE_SECRETS},
            headers=_ADMIN_HDR,
        )
        print(f"Status: {r_rot_f.status_code}")
        d_rot_f = r_rot_f.json()
        print(json.dumps(d_rot_f, indent=2))
        ok_rot_f = _check(r_rot_f.status_code == 200, "rotate F: status 200 for admin token")
        ok_rot_f &= _check(d_rot_f.get("ok") is True, "rotate F: ok=true")
        ok_rot_f &= _no_fake_values(d_rot_f, "rotate F: no fake values in admin rotate response")
        all_pass = all_pass and ok_rot_f

        # Restore to no-auth state
        os.environ["OPENCLAW_API_AUTH_ENABLED"] = "false"
        os.environ.pop("OPENCLAW_ADMIN_KEYS", None)
        os.environ.pop("OPENCLAW_READ_KEYS", None)

        # ── Tenant A–G: Per-tenant token isolation (V5.17 Phase 3) ──────────
        _ADMIN_TENANT_TOKEN = "admin-tenant-token"
        _READ_TENANT_TOKEN = "read-tenant-token"
        _OTHER_TOKEN = "other-tenant-token"
        _TENANT_TOKEN_VALUES = {_ADMIN_TENANT_TOKEN, _READ_TENANT_TOKEN, _OTHER_TOKEN}
        _ISO_CLIENT = "tenant-iso-client"
        _TENANT_A_HDR = {"Authorization": f"Bearer {_ADMIN_TENANT_TOKEN}"}
        _TENANT_R_HDR = {"Authorization": f"Bearer {_READ_TENANT_TOKEN}"}
        _TENANT_O_HDR = {"Authorization": f"Bearer {_OTHER_TOKEN}"}

        os.environ["OPENCLAW_API_AUTH_ENABLED"] = "true"
        os.environ["OPENCLAW_ADMIN_KEYS"] = _ADMIN_TENANT_TOKEN
        os.environ["OPENCLAW_READ_KEYS"] = _READ_TENANT_TOKEN

        # ── Tenant A — no OPENCLAW_TENANT_KEYS → backward compat ─────────────
        print("\n" + "-" * 60)
        print("  Tenant A. No OPENCLAW_TENANT_KEYS → all tenants accessible")
        print("-" * 60)
        os.environ.pop("OPENCLAW_TENANT_KEYS", None)
        _TA_URL = f"/openclaw/admin/tenants/tenant-a/clients/{_ISO_CLIENT}/credentials/google-ads/status"
        r_ta = client.get(_TA_URL, headers=_TENANT_A_HDR)
        print(f"Status: {r_ta.status_code}")
        d_ta = r_ta.json()
        ok_ta = _check(r_ta.status_code == 200, "tenant A: no restriction → 200")
        ok_ta &= _check(d_ta.get("ok") is True, "tenant A: ok=true")
        all_pass = all_pass and ok_ta

        # ── Tenant B — token restricted to one tenant ─────────────────────────
        print("\n" + "-" * 60)
        print("  Tenant B. Token restricted to tenant-a → allowed; tenant-b → 403")
        print("-" * 60)
        os.environ["OPENCLAW_TENANT_KEYS"] = f"{_ADMIN_TENANT_TOKEN}:tenant-a"
        _TB_OK_URL = f"/openclaw/admin/tenants/tenant-a/clients/{_ISO_CLIENT}/credentials/google-ads/status"
        _TB_DENY_URL = f"/openclaw/admin/tenants/tenant-b/clients/{_ISO_CLIENT}/credentials/google-ads/status"
        r_tb_ok = client.get(_TB_OK_URL, headers=_TENANT_A_HDR)
        print(f"  tenant-a status: {r_tb_ok.status_code}")
        d_tb_ok = r_tb_ok.json()
        ok_tb = _check(r_tb_ok.status_code == 200, "tenant B: allowed tenant → 200")
        ok_tb &= _check(d_tb_ok.get("ok") is True, "tenant B: ok=true for allowed tenant")
        r_tb_deny = client.get(_TB_DENY_URL, headers=_TENANT_A_HDR)
        print(f"  tenant-b status: {r_tb_deny.status_code}")
        d_tb_deny = r_tb_deny.json()
        ok_tb &= _check(r_tb_deny.status_code == 403, "tenant B: unlisted tenant → 403")
        ok_tb &= _check(d_tb_deny.get("ok") is False, "tenant B: ok=false for denied tenant")
        codes_tb = [e.get("code") for e in d_tb_deny.get("errors", []) if isinstance(e, dict)]
        ok_tb &= _check("tenant_access_denied" in codes_tb, "tenant B: error code tenant_access_denied")
        all_pass = all_pass and ok_tb

        # ── Tenant C — token allowed for multiple tenants ─────────────────────
        print("\n" + "-" * 60)
        print("  Tenant C. Token for two tenants → both allowed")
        print("-" * 60)
        os.environ["OPENCLAW_TENANT_KEYS"] = (
            f"{_ADMIN_TENANT_TOKEN}:tenant-a,{_ADMIN_TENANT_TOKEN}:tenant-b"
        )
        _TC_A_URL = f"/openclaw/admin/tenants/tenant-a/clients/{_ISO_CLIENT}/credentials/google-ads/status"
        _TC_B_URL = f"/openclaw/admin/tenants/tenant-b/clients/{_ISO_CLIENT}/credentials/google-ads/status"
        r_tc_a = client.get(_TC_A_URL, headers=_TENANT_A_HDR)
        r_tc_b = client.get(_TC_B_URL, headers=_TENANT_A_HDR)
        print(f"  tenant-a status: {r_tc_a.status_code}, tenant-b status: {r_tc_b.status_code}")
        d_tc_a = r_tc_a.json()
        d_tc_b = r_tc_b.json()
        ok_tc = _check(r_tc_a.status_code == 200, "tenant C: tenant-a allowed → 200")
        ok_tc &= _check(r_tc_b.status_code == 200, "tenant C: tenant-b allowed → 200")
        all_pass = all_pass and ok_tc

        # ── Tenant D — token not listed while map is set → global access ──────
        print("\n" + "-" * 60)
        print("  Tenant D. Unlisted token while map set → global access")
        print("-" * 60)
        os.environ["OPENCLAW_TENANT_KEYS"] = f"{_READ_TENANT_TOKEN}:tenant-x"
        _TD_URL = f"/openclaw/admin/tenants/tenant-y/clients/{_ISO_CLIENT}/credentials/google-ads/status"
        r_td = client.get(_TD_URL, headers=_TENANT_A_HDR)
        print(f"Status: {r_td.status_code}")
        d_td = r_td.json()
        ok_td = _check(r_td.status_code == 200, "tenant D: unlisted admin token → global access → 200")
        ok_td &= _check(d_td.get("ok") is True, "tenant D: ok=true")
        all_pass = all_pass and ok_td

        # ── Tenant E — scope checked before tenant; read token on WRITE → 403 scope
        print("\n" + "-" * 60)
        print("  Tenant E. Read token on WRITE route → scope_not_granted (not tenant_access_denied)")
        print("-" * 60)
        os.environ["OPENCLAW_TENANT_KEYS"] = f"{_READ_TENANT_TOKEN}:tenant-x"
        _TE_URL = f"/openclaw/admin/tenants/tenant-y/clients/{_ISO_CLIENT}/credentials/google-ads"
        r_te = client.post(_TE_URL, json={"customer_id": "1234509876"}, headers=_TENANT_R_HDR)
        print(f"Status: {r_te.status_code}")
        d_te = r_te.json()
        ok_te = _check(r_te.status_code == 403, "tenant E: scope check → 403")
        ok_te &= _check(d_te.get("ok") is False, "tenant E: ok=false")
        codes_te = [e.get("code") for e in d_te.get("errors", []) if isinstance(e, dict)]
        ok_te &= _check("scope_not_granted" in codes_te, "tenant E: error scope_not_granted (not tenant_access_denied)")
        ok_te &= _check("tenant_access_denied" not in codes_te, "tenant E: no tenant_access_denied in scope failure")
        all_pass = all_pass and ok_te

        # ── Tenant F — invalid token → 401 even if listed in tenant_keys ──────
        print("\n" + "-" * 60)
        print("  Tenant F. Invalid token (not in any key list) → 401 unauthorized")
        print("-" * 60)
        os.environ["OPENCLAW_TENANT_KEYS"] = f"{_OTHER_TOKEN}:tenant-a"
        _TF_URL = f"/openclaw/admin/tenants/tenant-a/clients/{_ISO_CLIENT}/credentials/google-ads/status"
        r_tf = client.get(_TF_URL, headers=_TENANT_O_HDR)
        print(f"Status: {r_tf.status_code}")
        d_tf = r_tf.json()
        ok_tf = _check(r_tf.status_code == 401, "tenant F: invalid token → 401 (not tenant_access_denied)")
        ok_tf &= _check(d_tf.get("ok") is False, "tenant F: ok=false")
        codes_tf = [e.get("code") for e in d_tf.get("errors", []) if isinstance(e, dict)]
        ok_tf &= _check("unauthorized" in codes_tf, "tenant F: error unauthorized")
        ok_tf &= _check("tenant_access_denied" not in codes_tf, "tenant F: no tenant_access_denied for invalid token")
        all_pass = all_pass and ok_tf

        # ── Tenant G — no token values or allow-list in tenant scenario responses
        print("\n" + "-" * 60)
        print("  Tenant G. No token values or allow-list strings in tenant scenario responses")
        print("-" * 60)
        ok_tg = True
        tenant_responses = [
            (d_ta, "tenant-A-backward-compat"),
            (d_tb_ok, "tenant-B-allowed"),
            (d_tb_deny, "tenant-B-denied"),
            (d_tc_a, "tenant-C-a-allowed"),
            (d_tc_b, "tenant-C-b-allowed"),
            (d_td, "tenant-D-global"),
            (d_te, "tenant-E-scope-first"),
            (d_tf, "tenant-F-invalid-token"),
        ]
        for resp_dict, label in tenant_responses:
            raw = json.dumps(resp_dict)
            leaked_tokens = [v for v in _TENANT_TOKEN_VALUES if v in raw]
            ok_one = len(leaked_tokens) == 0
            tag = _PASS if ok_one else _FAIL
            detail = f" — leaked: {leaked_tokens}" if leaked_tokens else ""
            print(f"  {tag}: no token values in {label}{detail}")
            ok_tg &= ok_one
            ok_tg &= _no_fake_values(resp_dict, f"no credential values in {label}")
        all_pass = all_pass and ok_tg

        # Restore to no-auth state
        os.environ["OPENCLAW_API_AUTH_ENABLED"] = "false"
        os.environ.pop("OPENCLAW_ADMIN_KEYS", None)
        os.environ.pop("OPENCLAW_READ_KEYS", None)
        os.environ.pop("OPENCLAW_TENANT_KEYS", None)

        # ── Leak assertion across all API responses ───────────────────────────
        print("\n" + "-" * 60)
        print("  Leak assertion — all API responses")
        print("-" * 60)
        ok_leak = True
        all_responses = [
            (d_vb, "404-validate"), (d_va, "validate-A"), (d_vc, "validate-C"),
            (d_da, "403-delete-disabled"), (d_dd, "404-delete-missing"),
            (d_db, "delete-success"), (d_dc, "delete-idempotent"),
            (d_ra, "rbac-A-read-status"), (d_rb, "rbac-B-write-denied"),
            (d_rc, "rbac-C-validate-denied"), (d_rd, "rbac-D-delete-denied"),
            (d_rg, "rbac-G-invalid-token"), (d_rh, "rbac-H-missing-token"),
            (d_aw, "audit-warn-write"),
            (d_rot_a, "rotate-A-success"), (d_rot_b, "rotate-B-notfound"),
            (d_rot_c, "rotate-C-revoked"), (d_rot_d, "rotate-D-incomplete"),
            (d_rot_e, "rotate-E-read-denied"), (d_rot_f, "rotate-F-admin-ok"),
            (d_ta, "tenant-A-backward-compat"), (d_tb_ok, "tenant-B-allowed"),
            (d_tb_deny, "tenant-B-denied"), (d_tc_a, "tenant-C-a-allowed"),
            (d_tc_b, "tenant-C-b-allowed"), (d_td, "tenant-D-global"),
            (d_te, "tenant-E-scope-first"), (d_tf, "tenant-F-invalid-token"),
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
        os.environ.pop("OPENCLAW_ADMIN_KEYS", None)
        os.environ.pop("OPENCLAW_READ_KEYS", None)
        os.environ.pop("OPENCLAW_TENANT_KEYS", None)
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

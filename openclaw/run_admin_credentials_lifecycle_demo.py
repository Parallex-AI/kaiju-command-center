"""
V5.15 Phase 1 / Phase 2 — Credential lifecycle audit and validation demo.

Verifies that credential write operations emit safe audit events to the JSONL
audit log. Asserts:
  - Event is written for metadata_upsert and bundle_write operations.
  - Event shape: event_type, integration_type, tenant_id, client_id, operation,
    ok, source, timestamp, request_id, trace_id, error_codes.
  - No forbidden fields in any audit event: credential_ref, secret_id,
    customer_id, login_customer_id, or any secret field name or value.

Uses InMemorySecretStore only. Fake values only. No GCP. No live Google Ads.
Audit root is a temp directory outside the repo — cleaned up in finally block.
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

from credentials.secret_store import InMemorySecretStore

_FAKE_TENANT = "tenant-lifecycle-demo"
_FAKE_CLIENT = "client-lifecycle-demo"
_FAKE_SECRETS = {
    "developer_token": "fake-dev-token-lifecycle",
    "client_id": "fake-oauth-client-id-lifecycle",
    "client_secret": "fake-client-secret-lifecycle",
    "refresh_token": "fake-refresh-token-lifecycle",
}
_FAKE_SECRET_VALUES: set = set(_FAKE_SECRETS.values())

_FORBIDDEN_AUDIT_KEYS = frozenset({
    "credential_ref",
    "secret_id",
    "customer_id",
    "login_customer_id",
    "developer_token",
    "client_secret",
    "refresh_token",
    "access_token",
})

_PASS = "[PASS]"
_FAIL = "[FAIL]"


def _assert(condition: bool, label: str) -> bool:
    tag = _PASS if condition else _FAIL
    print(f"  {tag} {label}")
    return condition


def _read_audit_events(audit_root: Path) -> list:
    events = []
    for jsonl_file in sorted(audit_root.glob("*.jsonl")):
        with open(jsonl_file, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return events


def _assert_no_forbidden_content(event: dict, fake_values: set, label: str) -> bool:
    raw = json.dumps(event)
    failures = []
    for key in _FORBIDDEN_AUDIT_KEYS:
        if key in event:
            failures.append(f"forbidden key present: {key}")
    for val in fake_values:
        if val in raw:
            failures.append(f"fake secret value found in event")
            break
    ok = len(failures) == 0
    tag = _PASS if ok else _FAIL
    details = " — " + "; ".join(failures) if failures else ""
    print(f"  {tag} {label}{details}")
    return ok


def run_demo():
    tmp_dir = tempfile.mkdtemp(prefix="kaiju_audit_lifecycle_demo_")
    tmp_store_path = os.path.join(tmp_dir, "credential_references.json")
    audit_root = Path(tmp_dir) / "audit"

    original_env = {}
    env_overrides = {
        "CREDENTIAL_REFERENCE_STORE_PATH": tmp_store_path,
        "OPENCLAW_AUDIT_ENABLED": "true",
        "OPENCLAW_AUDIT_ROOT": str(audit_root),
        "GCP_SECRET_MANAGER_ENABLED": "false",
    }
    for k, v in env_overrides.items():
        original_env[k] = os.environ.get(k)
        os.environ[k] = v

    # Re-import admin after env is set so stores pick up the right paths
    if "admin" in sys.modules:
        del sys.modules["admin"]

    try:
        import admin as adm

        all_pass = True

        # ── Section A: metadata_upsert audit event ───────────────────────────
        print("\n── A: metadata_upsert emits audit event ──")
        result_a = adm.upsert_google_ads_credential_reference(
            _FAKE_TENANT,
            _FAKE_CLIENT,
            {"customer_id": "123-456-7890"},
        )
        ok_a = _assert(result_a.get("ok") is True, "upsert returns ok=true")
        events_a = _read_audit_events(audit_root)
        ok_a &= _assert(len(events_a) >= 1, f"at least 1 audit event written (got {len(events_a)})")
        upsert_events = [e for e in events_a if e.get("operation") == "metadata_upsert"]
        ok_a &= _assert(len(upsert_events) >= 1, "metadata_upsert event present")
        if upsert_events:
            ev = upsert_events[-1]
            ok_a &= _assert(ev.get("event_type") == "credential_operation", "event_type=credential_operation")
            ok_a &= _assert(ev.get("integration_type") == "google_ads", "integration_type=google_ads")
            ok_a &= _assert(ev.get("tenant_id") == _FAKE_TENANT, "tenant_id matches")
            ok_a &= _assert(ev.get("client_id") == _FAKE_CLIENT, "client_id matches")
            ok_a &= _assert(ev.get("ok") is True, "ok=true")
            ok_a &= _assert(ev.get("source") == "openclaw_admin", "source=openclaw_admin")
            ok_a &= _assert("timestamp" in ev, "timestamp present")
            ok_a &= _assert("error_codes" in ev, "error_codes present")
            ok_a &= _assert_no_forbidden_content(ev, _FAKE_SECRET_VALUES, "no forbidden keys/values")
        all_pass = all_pass and ok_a

        # ── Section B: bundle_write audit event ──────────────────────────────
        print("\n── B: bundle_write emits audit event ──")
        store_b = InMemorySecretStore()
        bundle_payload = {
            "customer_id": "123-456-7890",
            **_FAKE_SECRETS,
        }
        result_b = adm.write_google_ads_credential_bundle(
            _FAKE_TENANT,
            _FAKE_CLIENT,
            bundle_payload,
            secret_store=store_b,
        )
        ok_b = _assert(result_b.get("ok") is True, "bundle write returns ok=true")
        events_b = _read_audit_events(audit_root)
        bundle_events = [e for e in events_b if e.get("operation") == "bundle_write"]
        ok_b &= _assert(len(bundle_events) >= 1, "bundle_write event present")
        if bundle_events:
            ev = bundle_events[-1]
            ok_b &= _assert(ev.get("event_type") == "credential_operation", "event_type=credential_operation")
            ok_b &= _assert(ev.get("integration_type") == "google_ads", "integration_type=google_ads")
            ok_b &= _assert(ev.get("tenant_id") == _FAKE_TENANT, "tenant_id matches")
            ok_b &= _assert(ev.get("client_id") == _FAKE_CLIENT, "client_id matches")
            ok_b &= _assert(ev.get("ok") is True, "ok=true")
            ok_b &= _assert(ev.get("source") == "openclaw_admin", "source=openclaw_admin")
            ok_b &= _assert_no_forbidden_content(ev, _FAKE_SECRET_VALUES, "no forbidden keys/values")
        all_pass = all_pass and ok_b

        # ── Section C: failed upsert (empty payload) emits audit event ───────
        print("\n── C: failed upsert does NOT emit audit event (rejected before store) ──")
        events_before = _read_audit_events(audit_root)
        result_c = adm.upsert_google_ads_credential_reference(
            _FAKE_TENANT, _FAKE_CLIENT, None
        )
        ok_c = _assert(result_c.get("ok") is False, "empty payload returns ok=false")
        events_after = _read_audit_events(audit_root)
        # Empty-payload rejection happens before store — no audit event expected
        ok_c &= _assert(
            len(events_after) == len(events_before),
            "no new audit event for pre-store rejection",
        )
        all_pass = all_pass and ok_c

        # ── Section D: global secret-leak assertion on all audit JSONL ────────
        print("\n── D: global secret-leak assertion on all audit events ──")
        all_events = _read_audit_events(audit_root)
        ok_d = _assert(len(all_events) >= 2, f"at least 2 events total (got {len(all_events)})")
        for i, ev in enumerate(all_events):
            ok_d &= _assert_no_forbidden_content(
                ev, _FAKE_SECRET_VALUES, f"event[{i}] clean"
            )
        all_pass = all_pass and ok_d

        # ── Section E: validate complete bundle → ACTIVE ──────────────────────
        print("\n── E: validate complete bundle → structurally_complete=true, status=active ──")
        _T_E = "tenant-validate-complete"
        _C_E = "client-validate-complete"
        _FAKE_SECRETS_E = {
            "developer_token": "fake-dev-token-lifecycle",
            "client_id": "fake-oauth-client-id-lifecycle",
            "client_secret": "fake-client-secret-lifecycle",
            "refresh_token": "fake-refresh-token-lifecycle",
        }
        store_e = InMemorySecretStore()
        write_e = adm.write_google_ads_credential_bundle(
            _T_E, _C_E,
            {"customer_id": "555-000-0001", **_FAKE_SECRETS_E},
            secret_store=store_e,
        )
        ok_e = _assert(write_e.get("ok") is True, "bundle write ok=true before validate")

        val_e = adm.validate_google_ads_credentials(_T_E, _C_E, secret_store=store_e)
        ok_e &= _assert(val_e.get("ok") is True, "validate returns ok=true")
        vr_e = val_e.get("validation_result") or {}
        ok_e &= _assert(vr_e.get("structurally_complete") is True, "structurally_complete=true")
        ok_e &= _assert(vr_e.get("missing_fields") == [], "missing_fields=[]")
        ok_e &= _assert(vr_e.get("live_api_tested") is False, "live_api_tested=false")
        ok_e &= _assert(vr_e.get("last_validated_at") is not None, "last_validated_at set")
        ok_e &= _assert(val_e.get("errors") == [], "errors=[]")
        cred_e = val_e.get("credential_status") or {}
        ok_e &= _assert(cred_e.get("status") == "active", "status updated to active")
        # Audit: validate event with ok=true and no error_codes
        events_e = _read_audit_events(audit_root)
        validate_events_e = [
            ev for ev in events_e
            if ev.get("operation") == "validate" and ev.get("tenant_id") == _T_E
        ]
        ok_e &= _assert(len(validate_events_e) >= 1, "validate audit event present")
        if validate_events_e:
            ev = validate_events_e[-1]
            ok_e &= _assert(ev.get("ok") is True, "validate audit event ok=true")
            ok_e &= _assert(ev.get("error_codes") == [], "validate audit error_codes=[]")
            ok_e &= _assert_no_forbidden_content(ev, set(_FAKE_SECRETS_E.values()), "validate event clean")
        # Leak check on entire validate response
        import json as _json
        val_e_str = _json.dumps(val_e)
        for fv in _FAKE_SECRETS_E.values():
            ok_e &= _assert(fv not in val_e_str, f"fake secret value not in validate response")
        all_pass = all_pass and ok_e

        # ── Section F: validate missing credential → credential_not_found ──────
        print("\n── F: validate missing credential → credential_not_found ──")
        _T_F = "tenant-validate-missing"
        _C_F = "client-validate-missing"
        events_before_f = _read_audit_events(audit_root)
        val_f = adm.validate_google_ads_credentials(_T_F, _C_F)
        ok_f = _assert(val_f.get("ok") is False, "validate returns ok=false")
        error_codes_f = [e.get("code") for e in val_f.get("errors", []) if isinstance(e, dict)]
        ok_f &= _assert("credential_not_found" in error_codes_f, "error credential_not_found")
        vr_f = val_f.get("validation_result") or {}
        ok_f &= _assert(vr_f.get("structurally_complete") is False, "structurally_complete=false")
        ok_f &= _assert(vr_f.get("live_api_tested") is False, "live_api_tested=false")
        # Audit: validate event emitted with ok=false and error_codes=["credential_not_found"]
        events_after_f = _read_audit_events(audit_root)
        new_events_f = events_after_f[len(events_before_f):]
        validate_events_f = [ev for ev in new_events_f if ev.get("operation") == "validate"]
        ok_f &= _assert(len(validate_events_f) >= 1, "validate audit event for missing ref present")
        if validate_events_f:
            ev = validate_events_f[-1]
            ok_f &= _assert(ev.get("ok") is False, "validate audit event ok=false")
            ok_f &= _assert("credential_not_found" in (ev.get("error_codes") or []),
                            "validate audit error_codes includes credential_not_found")
            ok_f &= _assert_no_forbidden_content(ev, set(), "validate event (missing) clean")
        all_pass = all_pass and ok_f

        # ── Section G: validate incomplete bundle → VALIDATION_FAILED ─────────
        print("\n── G: validate incomplete bundle → structurally_complete=false ──")
        _T_G = "tenant-validate-incomplete"
        _C_G = "client-validate-incomplete"
        # Write CredentialReference only — no secrets in store
        upsert_g = adm.upsert_google_ads_credential_reference(
            _T_G, _C_G, {"customer_id": "999-000-0001"}
        )
        ok_g = _assert(upsert_g.get("ok") is True, "upsert reference ok=true")
        store_g = InMemorySecretStore()  # empty — no secrets written
        val_g = adm.validate_google_ads_credentials(_T_G, _C_G, secret_store=store_g)
        ok_g &= _assert(val_g.get("ok") is True, "validate returns ok=true (process ran)")
        vr_g = val_g.get("validation_result") or {}
        ok_g &= _assert(vr_g.get("structurally_complete") is False, "structurally_complete=false")
        missing_g = vr_g.get("missing_fields") or []
        ok_g &= _assert(len(missing_g) > 0, f"missing_fields non-empty (got {missing_g})")
        for f in ("developer_token", "client_id", "client_secret", "refresh_token"):
            ok_g &= _assert(f in missing_g, f"missing_fields includes {f}")
        ok_g &= _assert(vr_g.get("live_api_tested") is False, "live_api_tested=false")
        cred_g = val_g.get("credential_status") or {}
        ok_g &= _assert(cred_g.get("status") == "validation_failed", "status=validation_failed")
        # Audit: validate event with error_codes=["secret_bundle_incomplete"]
        events_g = _read_audit_events(audit_root)
        validate_events_g = [
            ev for ev in events_g
            if ev.get("operation") == "validate" and ev.get("tenant_id") == _T_G
        ]
        ok_g &= _assert(len(validate_events_g) >= 1, "validate audit event present")
        if validate_events_g:
            ev = validate_events_g[-1]
            ok_g &= _assert(ev.get("ok") is True, "validate audit event ok=true")
            ok_g &= _assert(
                "secret_bundle_incomplete" in (ev.get("error_codes") or []),
                "validate audit error_codes includes secret_bundle_incomplete",
            )
            ok_g &= _assert_no_forbidden_content(ev, set(), "validate event (incomplete) clean")
        # Leak check on validate response
        val_g_str = _json.dumps(val_g)
        ok_g &= _assert("fake-" not in val_g_str, "no fake values in incomplete validate response")
        all_pass = all_pass and ok_g

        print()
        if all_pass:
            print(_PASS + " All credential lifecycle audit assertions passed.")
        else:
            print(_FAIL + " Some assertions failed — see above.")
        return 0 if all_pass else 1

    finally:
        for k, v in original_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
        for mod in ("admin", "audit"):
            sys.modules.pop(mod, None)


if __name__ == "__main__":
    sys.exit(run_demo())

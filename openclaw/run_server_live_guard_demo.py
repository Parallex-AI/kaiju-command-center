"""
V5.19 Phase 5 — Server live guard demo and test script.

Tests the live guard helper and the server route:
  POST /openclaw/admin/live-google-ads/preflight

Route tests use FastAPI TestClient. No HTTP server. No GCP. No Google Ads API.
No real credentials. All signals are synthetic.

Route note: GOOGLE_ADS_LIVE_ENABLED=false in env → route always returns
live_disabled regardless of request body signals. This is correct behaviour —
the route derives live_enabled from server-side env, never from the request body.
Specific denial-code tests use the guard helper directly with live_enabled=True.
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

_PASS = "[PASS]"
_FAIL = "[FAIL]"
_failures: list = []


def _assert(condition: bool, label: str) -> bool:
    tag = _PASS if condition else _FAIL
    print(f"  {tag} {label}")
    if not condition:
        _failures.append(label)
    return condition


def _no_forbidden_keys(d: dict, label: str) -> bool:
    from live_guard import LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS
    found = [k for k in LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS if k in d]
    ok = not found
    tag = _PASS if ok else _FAIL
    detail = f" — leaked: {found}" if found else ""
    print(f"  {tag} {label}{detail}")
    if not ok:
        _failures.append(label)
    return ok


def run_demo():
    tmp_dir = tempfile.mkdtemp(prefix="kaiju_live_guard_demo_")
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
        if mod in ("server", "admin", "config", "auth", "openclaw", "schemas",
                   "audit", "rate_limit", "live_guard", "live_gate", "preflight", "approval"):
            del sys.modules[mod]

    print("V5.19 Phase 5 — Server Live Guard Demo")
    print("No HTTP server. GCP_SECRET_MANAGER_ENABLED=false. "
          "GOOGLE_ADS_LIVE_ENABLED=false. OPENCLAW_API_AUTH_ENABLED=false.\n")

    try:
        from fastapi.testclient import TestClient
        from server import app
        from live_guard import (
            guard_live_google_ads_operation,
            guard_live_google_ads_from_signals,
            LIVE_OPERATION_FORBIDDEN_RESPONSE_KEYS,
            response_has_no_forbidden_keys,
        )
        from approval import ApprovalStatus, ApprovalScope, create_approval_record
        from live_gate import LiveGateDenialCode
        from preflight import LiveOperationPreflightInput

        client = TestClient(app, raise_server_exceptions=True)
        _BASE = "/openclaw/admin/live-google-ads/preflight"

        _TENANT = "tenant-alpha"
        _CLIENT = "client-alpha"
        _INTEGRATION = "google_ads"
        _SCOPE = ApprovalScope.GOOGLE_ADS_LIVE_VALIDATION

        def _make_valid_approval():
            return create_approval_record(
                tenant_id=_TENANT,
                client_id=_CLIENT,
                integration_type=_INTEGRATION,
                scope=_SCOPE,
                operator_label="demo-operator",
                reason="Controlled demo testing",
                rollback_plan="Disable live mode and revoke approval",
                status=ApprovalStatus.APPROVED,
            )

        def _all_pass_signals(**overrides):
            base = dict(
                approval_present=True,
                approval_valid=True,
                preflight_passed=True,
                audit_enabled=True,
                credential_configured=True,
                credential_status="ACTIVE",
                tenant_allowed=True,
                client_allowed=True,
                rollback_plan_present=True,
                operator_confirmed=True,
                operation="google_ads_metrics_fetch",
            )
            base.update(overrides)
            return base

        # ── Route test 1: route always denies with live_disabled (env=false) ─────
        print("── Route 1: live_disabled — GOOGLE_ADS_LIVE_ENABLED=false (default)")
        r = client.post(_BASE, json=_all_pass_signals())
        d = r.json()
        _assert(r.status_code == 403, "route live_disabled: status 403")
        _assert(d.get("ok") is False, "route live_disabled: ok=false")
        _assert(d.get("error_code") == "live_disabled",
                f"route live_disabled: error_code=live_disabled (got {d.get('error_code')})")
        _assert(d.get("live_allowed") is False, "route live_disabled: live_allowed=false")
        _assert(d.get("live_api_tested") is False, "route live_disabled: live_api_tested=false")
        _no_forbidden_keys(d, "route live_disabled: no forbidden keys")

        # ── Route test 2: all inputs → live_disabled because env=false ───────────
        print("\n── Route 2: route denies all variations when env=false")
        for label, overrides in [
            ("no approval", dict(approval_present=False, approval_valid=False)),
            ("revoked cred", dict(credential_status="REVOKED")),
            ("tenant denied", dict(tenant_allowed=False)),
        ]:
            r = client.post(_BASE, json=_all_pass_signals(**overrides))
            d = r.json()
            _assert(d.get("ok") is False, f"route {label}: ok=false")
            _assert(d.get("error_code") == "live_disabled", f"route {label}: error_code=live_disabled")
            _assert(d.get("live_api_tested") is False, f"route {label}: live_api_tested=false")
            _no_forbidden_keys(d, f"route {label}: no forbidden keys")

        # ── Route test 3: response structure ────────────────────────────────────
        print("\n── Route 3: response structure")
        r = client.post(_BASE, json=_all_pass_signals())
        d = r.json()
        _assert(isinstance(d.get("reasons"), list), "response: reasons is list")
        _assert(len(d.get("reasons", [])) > 0, "response: reasons non-empty")
        _assert(isinstance(d.get("required_actions"), list), "response: required_actions is list")
        _assert("request_id" in d, "response: request_id present")
        _assert("trace_id" in d, "response: trace_id present")
        _assert(d.get("integration_type") == "google_ads", "response: integration_type=google_ads")
        _assert(d.get("error") == "live_preflight_failed", "response: error=live_preflight_failed")

        # ── Route test 4: operation field propagated ─────────────────────────────
        print("\n── Route 4: operation field propagated")
        r = client.post(_BASE, json=_all_pass_signals(operation="test_op_name"))
        d = r.json()
        _assert(d.get("operation") == "test_op_name", "response: operation field propagated")

        # ── Helper test 5: live_disabled via helper ───────────────────────────────
        print("\n── Helper 5: guard_live_google_ads_from_signals — live_disabled")
        result = guard_live_google_ads_from_signals(
            live_enabled=False,
            approval_present=True, approval_valid=True,
            preflight_passed=True, audit_enabled=True,
            credential_configured=True, credential_status="ACTIVE",
            tenant_allowed=True, client_allowed=True,
            rollback_plan_present=True, operator_confirmed=True,
            operation="direct_helper_test",
        )
        _assert(result.get("ok") is False, "helper live_disabled: ok=false")
        _assert(result.get("error_code") == LiveGateDenialCode.LIVE_DISABLED,
                "helper live_disabled: error_code correct")
        _assert(result.get("live_api_tested") is False, "helper live_disabled: live_api_tested=false")
        _assert(response_has_no_forbidden_keys(result), "helper live_disabled: no forbidden keys")

        # ── Helper test 6: approval_missing via helper ────────────────────────────
        print("\n── Helper 6: guard_live_google_ads_from_signals — approval_missing")
        result = guard_live_google_ads_from_signals(
            live_enabled=True,
            approval_present=False, approval_valid=False,
            preflight_passed=True, audit_enabled=True,
            credential_configured=True, credential_status="ACTIVE",
            tenant_allowed=True, client_allowed=True,
            rollback_plan_present=True, operator_confirmed=True,
        )
        _assert(result.get("ok") is False, "helper approval_missing: ok=false")
        _assert(result.get("error_code") == LiveGateDenialCode.APPROVAL_MISSING,
                "helper approval_missing: error_code correct")
        _assert(result.get("live_api_tested") is False, "helper approval_missing: live_api_tested=false")
        _no_forbidden_keys(result, "helper approval_missing: no forbidden keys")

        # ── Helper test 7: approval_invalid via helper ────────────────────────────
        print("\n── Helper 7: guard_live_google_ads_from_signals — approval_invalid")
        result = guard_live_google_ads_from_signals(
            live_enabled=True,
            approval_present=True, approval_valid=False,
            preflight_passed=True, audit_enabled=True,
            credential_configured=True, credential_status="ACTIVE",
            tenant_allowed=True, client_allowed=True,
            rollback_plan_present=True, operator_confirmed=True,
        )
        _assert(result.get("error_code") == LiveGateDenialCode.APPROVAL_INVALID,
                "helper approval_invalid: error_code correct")
        _assert(result.get("live_api_tested") is False, "helper approval_invalid: live_api_tested=false")

        # ── Helper test 8: credential_not_active via helper ──────────────────────
        print("\n── Helper 8: guard_live_google_ads_from_signals — credential_not_active")
        result = guard_live_google_ads_from_signals(
            live_enabled=True,
            approval_present=True, approval_valid=True,
            preflight_passed=True, audit_enabled=True,
            credential_configured=True, credential_status="REVOKED",
            tenant_allowed=True, client_allowed=True,
            rollback_plan_present=True, operator_confirmed=True,
        )
        _assert(result.get("error_code") == LiveGateDenialCode.CREDENTIAL_NOT_ACTIVE,
                "helper credential_not_active: error_code correct")
        _assert(result.get("live_api_tested") is False, "helper credential_not_active: live_api_tested=false")

        # ── Helper test 9: tenant/client denied via helper ────────────────────────
        print("\n── Helper 9: guard_live_google_ads_from_signals — tenant/client denied")
        for label, kwargs in [
            ("tenant_not_allowed", dict(tenant_allowed=False, client_allowed=True)),
            ("client_not_allowed", dict(tenant_allowed=True, client_allowed=False)),
        ]:
            result = guard_live_google_ads_from_signals(
                live_enabled=True,
                approval_present=True, approval_valid=True,
                preflight_passed=True, audit_enabled=True,
                credential_configured=True, credential_status="ACTIVE",
                rollback_plan_present=True, operator_confirmed=True,
                **kwargs,
            )
            _assert(result.get("ok") is False, f"helper {label}: ok=false")
            _assert(result.get("live_api_tested") is False, f"helper {label}: live_api_tested=false")
            _no_forbidden_keys(result, f"helper {label}: no forbidden keys")

        # ── Helper test 10: guard_live_google_ads_operation — allow path ──────────
        print("\n── Helper 10: guard_live_google_ads_operation — allow path (full ApprovalRecord)")
        rec = _make_valid_approval()
        preflight_inp = LiveOperationPreflightInput(
            tenant_id=_TENANT,
            client_id=_CLIENT,
            integration_type=_INTEGRATION,
            operation="google_ads_metrics_fetch",
            live_enabled=True,
            approval_record=rec,
            required_approval_scope=_SCOPE,
            preflight_passed=True,
            audit_enabled=True,
            credential_configured=True,
            credential_status="ACTIVE",
            tenant_allowed=True,
            client_allowed=True,
            rollback_plan_present=True,
            operator_confirmed=True,
        )
        result = guard_live_google_ads_operation(preflight_inp)
        _assert(result.get("ok") is True, "allow path: ok=true")
        _assert(result.get("live_allowed") is True, "allow path: live_allowed=true")
        _assert(result.get("error_code") is None, "allow path: error_code=None")
        _assert(result.get("live_api_tested") is False, "allow path: live_api_tested=false")
        _assert(result.get("approval_valid") is True, "allow path: approval_valid=true")
        _assert(response_has_no_forbidden_keys(result), "allow path: no forbidden keys")

        # ── Helper test 11: sanitized summary — no forbidden identifiers ──────────
        print("\n── Helper 11: sanitized summary — no forbidden identifiers")
        summary = result.get("sanitized_summary", {})
        _assert("tenant_id" not in summary, "sanitized summary: tenant_id absent")
        _assert("client_id" not in summary, "sanitized summary: client_id absent")
        _assert("approval_id" not in summary, "sanitized summary: approval_id absent")
        _assert(isinstance(summary.get("approval_present"), bool),
                "sanitized summary: approval_present is bool")
        _assert(isinstance(summary.get("approval_valid"), bool),
                "sanitized summary: approval_valid is bool")
        _assert(isinstance(summary.get("live_gate_allowed"), bool),
                "sanitized summary: live_gate_allowed is bool")

        # ── Helper test 12: response_has_no_forbidden_keys utility ───────────────
        print("\n── Helper 12: response_has_no_forbidden_keys utility")
        clean = {"ok": False, "error_code": "live_disabled", "live_api_tested": False}
        dirty = {"ok": False, "tenant_id": "some-tenant", "error_code": "live_disabled"}
        _assert(response_has_no_forbidden_keys(clean) is True,
                "clean dict: no forbidden keys → True")
        _assert(response_has_no_forbidden_keys(dirty) is False,
                "dirty dict: tenant_id present → False")

    finally:
        for k, v in original_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


run_demo()

print()
if _failures:
    print(f"[FAIL] {len(_failures)} assertion(s) failed:")
    for f in _failures:
        print(f"  - {f}")
    sys.exit(1)

print("All assertions passed.")

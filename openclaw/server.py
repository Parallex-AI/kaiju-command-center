from pathlib import Path as _Path
import sys as _sys
import json
import os

_OPENCLAW_DIR = str(_Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in _sys.path:
    _sys.path.insert(0, _OPENCLAW_DIR)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from openclaw import process_request
from schemas import (
    OPENCLAW_VERSION,
    generate_request_id,
    generate_trace_id,
    utc_now_iso,
    make_error,
    make_openclaw_envelope,
)
from auth import validate_api_auth, validate_tenant_access, extract_bearer_token, AdminScope
from rate_limit import check_rate_limit, RateLimitCategory
from config import get_config
from admin import (
    get_google_ads_credential_status,
    upsert_google_ads_credential_reference,
    write_google_ads_credential_bundle,
    validate_google_ads_credentials,
    delete_google_ads_credentials,
    rotate_google_ads_credentials,
    GOOGLE_ADS_SECRET_FIELDS,
)
from live_guard import guard_live_google_ads_from_signals

SERVICE_NAME = "kaiju-openclaw"

# Header → payload/metadata mapping for V3.3 context propagation
_META_HEADERS = {
    "x-trace-id": "trace_id",
    "x-request-id": "request_id",
    "x-tenant-id": "tenant_id",
}

app = FastAPI(title=SERVICE_NAME, version=OPENCLAW_VERSION, docs_url=None, redoc_url=None)

# CORS (V3.5.4) — read origins from config at startup
_cors_origins = get_config().allowed_origins
_cors_credentials = "*" not in _cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": SERVICE_NAME,
        "version": OPENCLAW_VERSION,
        "status": "ok",
        "endpoints": ["/", "/openclaw/health", "/openclaw/process"],
    }


@app.get("/openclaw/health")
def health():
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "version": OPENCLAW_VERSION,
        "status": "healthy",
    }


@app.get(
    "/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/status"
)
async def admin_google_ads_credential_status(
    tenant_id: str,
    client_id: str,
    request: Request,
):
    """
    V5.5 — Read-only credential status for a tenant/client Google Ads integration.

    Returns the redacted CredentialReference status. Never returns secret values.
    Accepts no request body. Only path params: tenant_id, client_id.
    Auth applies when OPENCLAW_API_AUTH_ENABLED=true.
    """
    request_id = request.headers.get("x-request-id") or generate_request_id()
    trace_id = request.headers.get("x-trace-id") or generate_trace_id()
    config = get_config()

    auth_ok, auth_errors = validate_api_auth(
        headers=dict(request.headers), required_scope=AdminScope.READ, config=config
    )
    if not auth_ok:
        _codes = [e.get("code") for e in auth_errors if isinstance(e, dict)]
        return JSONResponse(
            status_code=403 if "scope_not_granted" in _codes else 401,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "credential_status": None,
                "errors": auth_errors,
            },
        )

    token = extract_bearer_token(
        dict(request.headers).get("authorization") or dict(request.headers).get("Authorization")
    )
    tenant_ok, tenant_errors = validate_tenant_access(token, tenant_id, config)
    if not tenant_ok:
        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "errors": tenant_errors,
            },
        )

    rl_ok, rl_errors = check_rate_limit(token, RateLimitCategory.STANDARD, config)
    if not rl_ok:
        return JSONResponse(
            status_code=429,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "errors": rl_errors,
            },
        )

    result = get_google_ads_credential_status(tenant_id, client_id)
    result["request_id"] = request_id
    result["trace_id"] = trace_id
    return JSONResponse(status_code=200, content=result)


@app.post(
    "/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads"
)
async def admin_upsert_google_ads_credential_reference(
    tenant_id: str,
    client_id: str,
    request: Request,
):
    """
    V5.6 — Create or update a CredentialReference for a tenant/client Google Ads integration.

    Accepts only safe metadata fields: customer_id, login_customer_id, status, metadata.
    Rejects any payload containing secret-like key names.
    Never accepts or stores developer_token, client_secret, refresh_token, access_token,
    oauth_code, or any other secret material.
    Auth applies when OPENCLAW_API_AUTH_ENABLED=true.
    """
    request_id = request.headers.get("x-request-id") or generate_request_id()
    trace_id = request.headers.get("x-trace-id") or generate_trace_id()
    config = get_config()

    auth_ok, auth_errors = validate_api_auth(
        headers=dict(request.headers), required_scope=AdminScope.WRITE, config=config
    )
    if not auth_ok:
        _codes = [e.get("code") for e in auth_errors if isinstance(e, dict)]
        return JSONResponse(
            status_code=403 if "scope_not_granted" in _codes else 401,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "credential_status": None,
                "errors": auth_errors,
            },
        )

    token = extract_bearer_token(
        dict(request.headers).get("authorization") or dict(request.headers).get("Authorization")
    )
    tenant_ok, tenant_errors = validate_tenant_access(token, tenant_id, config)
    if not tenant_ok:
        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "errors": tenant_errors,
            },
        )

    rl_ok, rl_errors = check_rate_limit(token, RateLimitCategory.STANDARD, config)
    if not rl_ok:
        return JSONResponse(
            status_code=429,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "errors": rl_errors,
            },
        )

    try:
        body = await request.body()
        if not body:
            payload = None
        else:
            payload = json.loads(body)
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "credential_status": None,
                "errors": [
                    {
                        "code": "invalid_json",
                        "message": "Request body is not valid JSON.",
                        "recoverable": False,
                        "source": "openclaw_admin",
                    }
                ],
            },
        )

    # Route to bundle write when any known Google Ads secret field is present in payload;
    # otherwise use the existing metadata-only path (backward-compatible).
    if (
        payload
        and isinstance(payload, dict)
        and any(k in GOOGLE_ADS_SECRET_FIELDS for k in payload)
    ):
        result = write_google_ads_credential_bundle(tenant_id, client_id, payload)
    else:
        result = upsert_google_ads_credential_reference(tenant_id, client_id, payload)
    result["request_id"] = request_id
    result["trace_id"] = trace_id
    status_code = 200 if result.get("ok") else 400
    return JSONResponse(status_code=status_code, content=result)


@app.post(
    "/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/validate"
)
async def admin_validate_google_ads_credentials(
    tenant_id: str,
    client_id: str,
    request: Request,
):
    """
    V5.15 — Structural validation of stored Google Ads credentials.

    Checks whether all required secret fields are configured in the SecretStore.
    Does NOT call the Google Ads API. Does NOT fetch secret values.
    Updates CredentialReference status to ACTIVE (complete) or VALIDATION_FAILED (incomplete).
    Emits audit event operation="validate".

    Returns 200 when the validation process ran (even if structurally incomplete).
    Returns 404 when no credential reference exists for the tenant/client.
    Auth applies when OPENCLAW_API_AUTH_ENABLED=true.
    """
    request_id = request.headers.get("x-request-id") or generate_request_id()
    trace_id = request.headers.get("x-trace-id") or generate_trace_id()
    config = get_config()

    auth_ok, auth_errors = validate_api_auth(
        headers=dict(request.headers), required_scope=AdminScope.VALIDATE, config=config
    )
    if not auth_ok:
        _codes = [e.get("code") for e in auth_errors if isinstance(e, dict)]
        return JSONResponse(
            status_code=403 if "scope_not_granted" in _codes else 401,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "validation_result": None,
                "credential_status": None,
                "secret_status": None,
                "errors": auth_errors,
            },
        )

    token = extract_bearer_token(
        dict(request.headers).get("authorization") or dict(request.headers).get("Authorization")
    )
    tenant_ok, tenant_errors = validate_tenant_access(token, tenant_id, config)
    if not tenant_ok:
        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "errors": tenant_errors,
            },
        )

    rl_ok, rl_errors = check_rate_limit(token, RateLimitCategory.STANDARD, config)
    if not rl_ok:
        return JSONResponse(
            status_code=429,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "errors": rl_errors,
            },
        )

    result = validate_google_ads_credentials(tenant_id, client_id)
    result["request_id"] = request_id
    result["trace_id"] = trace_id

    error_codes = [e.get("code") for e in result.get("errors", []) if isinstance(e, dict)]
    if "credential_not_found" in error_codes:
        status_code = 404
    elif result.get("ok"):
        status_code = 200
    else:
        status_code = 400
    return JSONResponse(status_code=status_code, content=result)


@app.delete(
    "/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads"
)
async def admin_delete_google_ads_credentials(
    tenant_id: str,
    client_id: str,
    request: Request,
):
    """
    V5.15 — Delete a Google Ads credential bundle and mark CredentialReference as REVOKED.

    Requires OPENCLAW_ADMIN_DELETE_ENABLED=true. Disabled by default (returns 403).
    Calls delete_secret_bundle() only — no secret values fetched or returned.
    Idempotent on already-absent secrets (returns 200 with warnings=[secret_already_absent]).
    Emits audit event operation="delete".
    Auth applies when OPENCLAW_API_AUTH_ENABLED=true.
    """
    request_id = request.headers.get("x-request-id") or generate_request_id()
    trace_id = request.headers.get("x-trace-id") or generate_trace_id()
    config = get_config()

    auth_ok, auth_errors = validate_api_auth(
        headers=dict(request.headers), required_scope=AdminScope.DELETE, config=config
    )
    if not auth_ok:
        _codes = [e.get("code") for e in auth_errors if isinstance(e, dict)]
        return JSONResponse(
            status_code=403 if "scope_not_granted" in _codes else 401,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "credential_status": None,
                "secret_status": None,
                "warnings": [],
                "errors": auth_errors,
            },
        )

    token = extract_bearer_token(
        dict(request.headers).get("authorization") or dict(request.headers).get("Authorization")
    )
    tenant_ok, tenant_errors = validate_tenant_access(token, tenant_id, config)
    if not tenant_ok:
        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "errors": tenant_errors,
            },
        )

    rl_ok, rl_errors = check_rate_limit(token, RateLimitCategory.SENSITIVE, config)
    if not rl_ok:
        return JSONResponse(
            status_code=429,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "errors": rl_errors,
            },
        )

    result = delete_google_ads_credentials(tenant_id, client_id)
    result["request_id"] = request_id
    result["trace_id"] = trace_id

    error_codes = [e.get("code") for e in result.get("errors", []) if isinstance(e, dict)]
    if "delete_not_enabled" in error_codes:
        status_code = 403
    elif "credential_not_found" in error_codes:
        status_code = 404
    elif result.get("ok"):
        status_code = 200
    else:
        status_code = 400
    return JSONResponse(status_code=status_code, content=result)


@app.post(
    "/openclaw/admin/tenants/{tenant_id}/clients/{client_id}/credentials/google-ads/rotate"
)
async def admin_rotate_google_ads_credentials(
    tenant_id: str,
    client_id: str,
    request: Request,
):
    """
    V5.16 Phase 3 — Rotate Google Ads credentials for a tenant/client.

    Replaces the stored secret bundle for an existing CredentialReference.
    Credential must exist and must not be REVOKED.
    Allowed current statuses: ACTIVE, CONFIGURED, VALIDATION_FAILED.
    Validates structurally via get_secret_status() only — no Google Ads API.
    Updates CredentialReference status to ACTIVE (complete) or VALIDATION_FAILED (incomplete).
    Emits audit event operation="rotate".
    Requires AdminScope.ROTATE — only admin tokens satisfy this scope.
    """
    request_id = request.headers.get("x-request-id") or generate_request_id()
    trace_id = request.headers.get("x-trace-id") or generate_trace_id()
    config = get_config()

    auth_ok, auth_errors = validate_api_auth(
        headers=dict(request.headers), required_scope=AdminScope.ROTATE, config=config
    )
    if not auth_ok:
        _codes = [e.get("code") for e in auth_errors if isinstance(e, dict)]
        return JSONResponse(
            status_code=403 if "scope_not_granted" in _codes else 401,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "rotation_result": None,
                "credential_status": None,
                "secret_status": None,
                "errors": auth_errors,
            },
        )

    token = extract_bearer_token(
        dict(request.headers).get("authorization") or dict(request.headers).get("Authorization")
    )
    tenant_ok, tenant_errors = validate_tenant_access(token, tenant_id, config)
    if not tenant_ok:
        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "errors": tenant_errors,
            },
        )

    rl_ok, rl_errors = check_rate_limit(token, RateLimitCategory.SENSITIVE, config)
    if not rl_ok:
        return JSONResponse(
            status_code=429,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "errors": rl_errors,
            },
        )

    try:
        body = await request.body()
        if not body:
            payload = None
        else:
            payload = json.loads(body)
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "tenant_id": tenant_id,
                "client_id": client_id,
                "integration_type": "google_ads",
                "rotation_result": None,
                "credential_status": None,
                "secret_status": None,
                "errors": [
                    {
                        "code": "invalid_json",
                        "message": "Request body is not valid JSON.",
                        "recoverable": False,
                        "source": "openclaw_admin",
                    }
                ],
            },
        )

    result = rotate_google_ads_credentials(tenant_id, client_id, payload)
    result["request_id"] = request_id
    result["trace_id"] = trace_id

    error_codes = [e.get("code") for e in result.get("errors", []) if isinstance(e, dict)]
    if "credential_not_found" in error_codes:
        status_code = 404
    elif "invalid_status_for_rotation" in error_codes:
        status_code = 409
    elif result.get("ok"):
        status_code = 200
    else:
        status_code = 400
    return JSONResponse(status_code=status_code, content=result)


@app.post("/openclaw/admin/live-google-ads/preflight")
async def admin_live_google_ads_preflight(request: Request):
    """
    V5.19 Phase 5 — Live Google Ads operation preflight probe.

    Evaluates live gate readiness using pre-resolved boolean signals supplied by
    the caller. live_enabled is always derived from GOOGLE_ADS_LIVE_ENABLED (server-
    side env var, default false) — never accepted from the request body.

    Does NOT call Google Ads API. Does NOT fetch credentials. Does NOT call GCP.
    Returns a safe structured response with live_api_tested=false always.
    Auth applies when OPENCLAW_API_AUTH_ENABLED=true (requires VALIDATE scope).
    """
    request_id = request.headers.get("x-request-id") or generate_request_id()
    trace_id = request.headers.get("x-trace-id") or generate_trace_id()
    config = get_config()

    auth_ok, auth_errors = validate_api_auth(
        headers=dict(request.headers), required_scope=AdminScope.VALIDATE, config=config
    )
    if not auth_ok:
        _codes = [e.get("code") for e in auth_errors if isinstance(e, dict)]
        return JSONResponse(
            status_code=403 if "scope_not_granted" in _codes else 401,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "integration_type": "google_ads",
                "errors": auth_errors,
            },
        )

    token = extract_bearer_token(
        dict(request.headers).get("authorization") or dict(request.headers).get("Authorization")
    )
    rl_ok, rl_errors = check_rate_limit(token, RateLimitCategory.STANDARD, config)
    if not rl_ok:
        return JSONResponse(
            status_code=429,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "integration_type": "google_ads",
                "errors": rl_errors,
            },
        )

    try:
        body = await request.body()
        payload = json.loads(body) if body else {}
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "request_id": request_id,
                "trace_id": trace_id,
                "integration_type": "google_ads",
                "errors": [make_error(
                    "invalid_json",
                    "Request body is not valid JSON.",
                    recoverable=False,
                    source="openclaw_admin",
                )],
            },
        )

    # live_enabled is server-side config — never accepted from request body.
    live_enabled = os.getenv("GOOGLE_ADS_LIVE_ENABLED", "false").strip().lower() in ("true", "1")

    result = guard_live_google_ads_from_signals(
        live_enabled=live_enabled,
        approval_present=bool(payload.get("approval_present", False)),
        approval_valid=bool(payload.get("approval_valid", False)),
        preflight_passed=bool(payload.get("preflight_passed", False)),
        audit_enabled=bool(payload.get("audit_enabled", config.audit_enabled)),
        credential_configured=bool(payload.get("credential_configured", False)),
        credential_status=str(payload.get("credential_status", "CONFIGURED")),
        tenant_allowed=bool(payload.get("tenant_allowed", False)),
        client_allowed=bool(payload.get("client_allowed", False)),
        rollback_plan_present=bool(payload.get("rollback_plan_present", False)),
        operator_confirmed=bool(payload.get("operator_confirmed", False)),
        operation=str(payload.get("operation", "")),
    )
    result["request_id"] = request_id
    result["trace_id"] = trace_id

    status_code = 200 if result.get("live_allowed") else 403
    return JSONResponse(status_code=status_code, content=result)


@app.post("/openclaw/process")
async def process(request: Request):
    try:
        body = await request.body()
        payload = json.loads(body)
    except Exception:
        now = utc_now_iso()
        envelope = make_openclaw_envelope(
            ok=False,
            request_id=generate_request_id(),
            trace_id=generate_trace_id(),
            tenant="unknown",
            agent="unknown",
            execution_mode="none",
            started_at=now,
            finished_at=now,
            duration_ms=0,
            data={},
            errors=[make_error("invalid_json", "Request body is not valid JSON.", source="openclaw")],
            warnings=[],
        )
        return JSONResponse(status_code=400, content=envelope)

    headers = request.headers
    headers_dict = dict(headers)

    # Check API key auth before any further processing (V3.5.3)
    auth_ok, auth_errors = validate_api_auth(headers=headers_dict)
    if not auth_ok:
        # Propagate trace/request IDs even on auth failure
        meta = dict(payload.get("metadata") or {}) if isinstance(payload, dict) else {}
        trace_id = headers.get("x-trace-id") or meta.get("trace_id") or generate_trace_id()
        request_id = headers.get("x-request-id") or meta.get("request_id") or generate_request_id()
        client_id = payload.get("client_id", "unknown") if isinstance(payload, dict) else "unknown"
        agent = payload.get("agent", "unknown") if isinstance(payload, dict) else "unknown"
        now = utc_now_iso()
        envelope = make_openclaw_envelope(
            ok=False,
            request_id=request_id,
            trace_id=trace_id,
            tenant=client_id,
            agent=agent,
            execution_mode="none",
            started_at=now,
            finished_at=now,
            duration_ms=0,
            data={},
            errors=auth_errors,
            warnings=[],
        )
        return JSONResponse(status_code=401, content=envelope)

    # Inject trace_id, request_id, tenant_id from headers into metadata
    # Headers win over body metadata
    meta = dict(payload.get("metadata") or {})
    for header, meta_key in _META_HEADERS.items():
        val = headers.get(header)
        if val:
            meta[meta_key] = val
    payload["metadata"] = meta

    # user_id and channel go into payload top-level (highest precedence in context)
    if headers.get("x-user-id"):
        payload["user_id"] = headers.get("x-user-id")
    if headers.get("x-channel"):
        payload["channel"] = headers.get("x-channel")

    result = process_request(payload)
    return JSONResponse(status_code=200, content=result)

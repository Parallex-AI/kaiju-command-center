from pathlib import Path as _Path
import sys as _sys
import json

_OPENCLAW_DIR = str(_Path(__file__).resolve().parent)
if _OPENCLAW_DIR not in _sys.path:
    _sys.path.insert(0, _OPENCLAW_DIR)

from fastapi import FastAPI, Request
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
from auth import validate_api_auth

SERVICE_NAME = "kaiju-openclaw"

# Header → payload/metadata mapping for V3.3 context propagation
_META_HEADERS = {
    "x-trace-id": "trace_id",
    "x-request-id": "request_id",
    "x-tenant-id": "tenant_id",
}

app = FastAPI(title=SERVICE_NAME, version=OPENCLAW_VERSION, docs_url=None, redoc_url=None)


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

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

SERVICE_NAME = "kaiju-openclaw"

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

    result = process_request(payload)
    return JSONResponse(status_code=200, content=result)

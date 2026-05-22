from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from router import route_request

app = FastAPI(title="Kaiju Command Center Router", version="0.1.0")


@app.get("/")
def root():
    return {
        "service": "kaiju-command-center-router",
        "version": "0.1.0",
        "endpoints": ["/health", "/route"],
    }


@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "kaiju-command-center-router",
        "status": "healthy",
    }


@app.post("/route")
async def route(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "invalid_json",
                "message": "Request body must be valid JSON.",
            },
        )

    result = route_request(payload)
    return JSONResponse(content=result)

from pathlib import Path as _Path
import sys as _sys


def _try_load_profile(client_id: str) -> tuple:
    try:
        _ads_agent_dir = str(_Path(__file__).resolve().parents[1] / "agents" / "ads-agent")
        if _ads_agent_dir not in _sys.path:
            _sys.path.insert(0, _ads_agent_dir)
        from mempalace import read_profile
        profile = read_profile(client_id)
        return profile, []
    except Exception as exc:
        return None, [f"profile_load_failed: {exc}"]


def resolve_context(payload: dict) -> dict:
    client_id = payload.get("client_id") or "demo-client"
    metadata = dict(payload.get("metadata") or {})

    # channel: payload > metadata > default
    channel = payload.get("channel") or metadata.get("channel") or "local"

    # user_id: payload > metadata > default
    user_id = payload.get("user_id") or metadata.get("user_id") or "local-user"

    # tenant: metadata.tenant_id overrides client_id if present
    tenant_id = metadata.get("tenant_id") or None
    tenant = tenant_id if tenant_id else client_id

    profile, warnings = _try_load_profile(client_id)
    profile_loaded = profile is not None

    return {
        "client_id": client_id,
        "tenant": tenant,
        "tenant_id": tenant_id,
        "channel": channel,
        "user_id": user_id,
        "metadata": metadata,
        "profile": profile,
        "profile_loaded": profile_loaded,
        "warnings": warnings,
    }

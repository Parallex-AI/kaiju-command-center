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
    channel = payload.get("channel") or "local"
    user_id = payload.get("user_id") or "local-user"
    metadata = payload.get("metadata") or {}

    profile, warnings = _try_load_profile(client_id)

    return {
        "client_id": client_id,
        "tenant": client_id,
        "channel": channel,
        "user_id": user_id,
        "metadata": metadata,
        "profile": profile,
        "warnings": warnings,
    }

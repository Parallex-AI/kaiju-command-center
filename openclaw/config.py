import os
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Primitive parsers
# ---------------------------------------------------------------------------

def parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    return default


def parse_csv(value: Optional[str], default: list) -> list:
    if value is None:
        return default
    parts = [p.strip() for p in value.split(",")]
    result = [p for p in parts if p]
    return result if result else default


def parse_float(value: Optional[str], default: float, min_value: Optional[float] = None) -> float:
    if value is None:
        return default
    try:
        parsed = float(value.strip())
    except (ValueError, AttributeError):
        return default
    if min_value is not None and parsed <= min_value:
        return default
    return parsed


def parse_int(value: Optional[str], default: int, min_value: Optional[int] = None) -> int:
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except (ValueError, AttributeError):
        return default
    if min_value is not None and parsed <= min_value:
        return default
    return parsed


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------

@dataclass
class OpenClawConfig:
    env: str
    api_auth_enabled: bool
    api_keys: list
    allowed_origins: list
    default_tenant: str
    require_tenant_header: bool
    audit_enabled: bool
    audit_root: str
    memory_enabled: bool
    memory_root: str
    n8n_ads_webhook_url: Optional[str]
    n8n_webhook_timeout: float
    port: int


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

_VALID_ENVS = {"local", "staging", "production"}


def get_config() -> OpenClawConfig:
    raw_env = os.getenv("OPENCLAW_ENV", "local").strip().lower()
    env = raw_env if raw_env in _VALID_ENVS else "local"

    api_auth_enabled = parse_bool(os.getenv("OPENCLAW_API_AUTH_ENABLED"), default=False)

    api_keys = parse_csv(os.getenv("OPENCLAW_API_KEYS"), default=[])

    allowed_origins = parse_csv(os.getenv("OPENCLAW_ALLOWED_ORIGINS"), default=["*"])

    raw_tenant = (os.getenv("OPENCLAW_DEFAULT_TENANT") or "").strip()
    default_tenant = raw_tenant if raw_tenant else "demo-client"

    require_tenant_header = parse_bool(os.getenv("OPENCLAW_REQUIRE_TENANT_HEADER"), default=False)

    audit_enabled = parse_bool(os.getenv("OPENCLAW_AUDIT_ENABLED"), default=True)

    raw_audit_root = (os.getenv("OPENCLAW_AUDIT_ROOT") or "").strip()
    audit_root = raw_audit_root if raw_audit_root else "openclaw/audit"

    memory_enabled = parse_bool(os.getenv("MEMORY_ENABLED"), default=True)

    raw_memory_root = (os.getenv("MEMORY_ROOT") or "").strip()
    memory_root = raw_memory_root if raw_memory_root else "memory/client-memory"

    raw_n8n_url = (os.getenv("N8N_ADS_WEBHOOK_URL") or "").strip()
    n8n_ads_webhook_url = raw_n8n_url if raw_n8n_url else None

    n8n_webhook_timeout = parse_float(
        os.getenv("N8N_WEBHOOK_TIMEOUT"), default=15.0, min_value=0.0
    )

    port = parse_int(os.getenv("PORT"), default=8100, min_value=0)

    return OpenClawConfig(
        env=env,
        api_auth_enabled=api_auth_enabled,
        api_keys=api_keys,
        allowed_origins=allowed_origins,
        default_tenant=default_tenant,
        require_tenant_header=require_tenant_header,
        audit_enabled=audit_enabled,
        audit_root=audit_root,
        memory_enabled=memory_enabled,
        memory_root=memory_root,
        n8n_ads_webhook_url=n8n_ads_webhook_url,
        n8n_webhook_timeout=n8n_webhook_timeout,
        port=port,
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def config_to_dict(config: OpenClawConfig) -> dict:
    return {
        "env": config.env,
        "api_auth_enabled": config.api_auth_enabled,
        "api_keys": config.api_keys,
        "allowed_origins": config.allowed_origins,
        "default_tenant": config.default_tenant,
        "require_tenant_header": config.require_tenant_header,
        "audit_enabled": config.audit_enabled,
        "audit_root": config.audit_root,
        "memory_enabled": config.memory_enabled,
        "memory_root": config.memory_root,
        "n8n_ads_webhook_url": config.n8n_ads_webhook_url,
        "n8n_webhook_timeout": config.n8n_webhook_timeout,
        "port": config.port,
    }


def redacted_config_dict(config: OpenClawConfig) -> dict:
    d = config_to_dict(config)
    d["api_keys"] = {
        "configured": len(config.api_keys) > 0,
        "count": len(config.api_keys),
    }
    return d

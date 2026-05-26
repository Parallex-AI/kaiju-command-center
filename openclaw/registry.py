AGENT_REGISTRY = {
    "ads-agent": {
        "status": "active",
        "description": "Google Ads performance analysis agent",
        "supported_requests": ["summary", "cpa", "conversions", "raw"],
        "router_agent": "ads-agent",
        "memory_enabled": True,
    }
}


def get_agent(agent_name: str) -> dict | None:
    return AGENT_REGISTRY.get(agent_name)


def list_agents() -> dict:
    return dict(AGENT_REGISTRY)


def get_supported_agents() -> list:
    return [name for name, meta in AGENT_REGISTRY.items() if meta.get("status") == "active"]


def get_supported_requests(agent_name: str) -> list:
    agent = get_agent(agent_name)
    if agent is None:
        return []
    return list(agent.get("supported_requests", []))

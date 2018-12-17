from app.agent_cli import get_agent_cli
from app.exports.agents.registry import export_agents

cli = get_agent_cli(export_agents, registry_file="app/exports/agents/registry.py")


if __name__ == "__main__":
    cli()

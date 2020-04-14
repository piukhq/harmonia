from app.agent_cli import get_agent_cli
from app.imports.agents.registry import import_agents

cli = get_agent_cli(import_agents, registry_file="app/imports/agents/registry.py")


if __name__ == "__main__":
    cli()

from app.agent_cli import get_agent_cli
from app.export_result.registry import export_result_agents

cli = get_agent_cli(export_result_agents, registry_file="app/export_result/registry.py")


if __name__ == "__main__":
    cli()

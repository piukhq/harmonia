from app.agent_cli import get_agent_cli
from app.unmatched_transactions import unmatched_transaction_agents

cli = get_agent_cli(unmatched_transaction_agents, registry_file="app/unmatched_transactions/registry.py")


if __name__ == "__main__":
    cli()

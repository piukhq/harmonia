from app.registry import Registry
from app.unmatched_transactions.base import BaseAgent

unmatched_transaction_agents = Registry[BaseAgent]()
unmatched_transaction_agents.add("stonegate_unmatched", "app.unmatched_transactions.stonegate.Stonegate")

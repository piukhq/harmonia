from app.registry import Registry
from app.matching.agents.base import BaseMatchingAgent

matching_agents = Registry[BaseMatchingAgent]()
matching_agents.add("bink-payment", "app.matching.agents.default.Default")
matching_agents.add("visa", "app.matching.agents.default.Default")
matching_agents.add("amex", "app.matching.agents.default.Default")
matching_agents.add("mastercard", "app.matching.agents.default.Default")

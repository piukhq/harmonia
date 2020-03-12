from app.registry import Registry
from app.matching.agents.base import BaseMatchingAgent

matching_agents = Registry[BaseMatchingAgent]()
matching_agents.add("bink-loyalty", "app.matching.agents.generic_loyalty.GenericLoyalty")
matching_agents.add("cooperative", "app.matching.agents.generic_loyalty.GenericLoyalty")
matching_agents.add("harvey-nichols", "app.matching.agents.harvey_nichols.HarveyNichols")
matching_agents.add("iceland-bonus-card", "app.matching.agents.generic_loyalty.GenericLoyalty")
matching_agents.add("burger-king-rewards", "app.matching.agents.generic_spotted.GenericSpotted")

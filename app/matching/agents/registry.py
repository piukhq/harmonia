from app.registry import Registry
from app.matching.agents.base import BaseMatchingAgent

matching_agents = Registry[BaseMatchingAgent]()
matching_agents.add("bink-loyalty", "app.matching.agents.generic_loyalty.GenericLoyalty")
matching_agents.add("cooperative", "app.matching.agents.generic_loyalty.GenericLoyalty")
matching_agents.add("harvey-nichols", "app.matching.agents.harvey_nichols.HarveyNichols")
matching_agents.add("iceland-bonus-card", "app.matching.agents.iceland.Iceland")
matching_agents.add("burger-king-rewards", "app.matching.agents.generic_spotted.GenericSpotted")
matching_agents.add("fatface", "app.matching.agents.generic_spotted.GenericSpotted")
matching_agents.add("whsmith-rewards", "app.matching.agents.whsmith.WhSmith")
matching_agents.add("wasabi-club", "app.matching.agents.wasabi.Wasabi")
matching_agents.add("bpl-trenette", "app.matching.agents.generic_spotted.GenericSpotted")

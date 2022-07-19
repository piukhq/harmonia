from app.matching.agents.base import BaseMatchingAgent
from app.registry import Registry

matching_agents = Registry[BaseMatchingAgent]()
matching_agents.add("cooperative", "app.matching.agents.generic_loyalty.GenericLoyalty")
matching_agents.add("harvey-nichols", "app.matching.agents.harvey_nichols.HarveyNichols")
matching_agents.add("iceland-bonus-card", "app.matching.agents.iceland.Iceland")
matching_agents.add("wasabi-club", "app.matching.agents.wasabi.Wasabi")
matching_agents.add("bpl-asos", "app.matching.agents.generic_spotted.GenericSpotted")
matching_agents.add("bpl-viator", "app.matching.agents.generic_spotted.GenericSpotted")
matching_agents.add("bpl-trenette", "app.matching.agents.generic_spotted.GenericSpotted")
matching_agents.add("bpl-cortado", "app.matching.agents.generic_spotted.GenericSpotted")

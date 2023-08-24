from app.matching.agents.base import BaseMatchingAgent
from app.registry import Registry

# *******IMPORTANT*************
# The registry entries here are used to determine if a merchant is a matching or spotting type.
# Currently all spotting merchants are GenericSpotted types. If this changes then review code that depends on this
# For example the Amex Auth class only imports transactions if they are none spotting or streaming.
matching_agents = Registry[BaseMatchingAgent]()
matching_agents.add("cooperative", "app.matching.agents.generic_loyalty.GenericLoyalty")
matching_agents.add("harvey-nichols", "app.matching.agents.harvey_nichols.HarveyNichols")
matching_agents.add("iceland-bonus-card", "app.matching.agents.iceland.Iceland")
matching_agents.add("wasabi-club", "app.matching.agents.wasabi.Wasabi")
matching_agents.add("bpl-asos", "app.matching.agents.generic_spotted.GenericSpotted")
matching_agents.add("bpl-viator", "app.matching.agents.generic_spotted.GenericSpotted")
matching_agents.add("bpl-trenette", "app.matching.agents.generic_spotted.GenericSpotted")
matching_agents.add("bpl-cortado", "app.matching.agents.generic_spotted.GenericSpotted")
matching_agents.add("costa", "app.matching.agents.costa.Costa")
matching_agents.add("the-works", "app.matching.agents.generic_spotted.GenericSpotted")
matching_agents.add("itsu", "app.matching.agents.itsu.Itsu")
matching_agents.add("slim-chickens", "app.matching.agents.slim_chickens.SlimChickens")

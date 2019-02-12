from app.registry import Registry
from app.matching.agents.base import BaseMatchingAgent

matching_agents = Registry[BaseMatchingAgent]()
matching_agents.add(
    "example-loyalty-scheme",
    "app.matching.agents.example_loyalty_scheme.ExampleLoyaltySchemeAgent",
)

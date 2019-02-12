from app.registry import Registry

matching_agents = Registry()
matching_agents.add(
    "example-loyalty-scheme",
    "app.matching.agents.example_loyalty_scheme.ExampleLoyaltySchemeAgent",
)

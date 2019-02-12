from app.registry import Registry

export_agents = Registry()
export_agents.add(
    "example-loyalty-scheme",
    "app.exports.agents.example_loyalty_scheme.ExampleLoyaltySchemeAgent",
)

from app.registry import Registry
from app.exports.agents.bases.base import BaseAgent

export_agents = Registry[BaseAgent]()
export_agents.add(
    "example-loyalty-scheme",
    "app.exports.agents.example_loyalty_scheme.ExampleLoyaltySchemeAgent",
)

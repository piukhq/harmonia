from app.registry import Registry
from app.matching.agents.base import BaseMatchingAgent

matching_agents = Registry[BaseMatchingAgent]()
matching_agents.add(
    "example-payment-provider",
    "app.matching.agents.example_payment_provider.ExamplePaymentProviderAgent",
)

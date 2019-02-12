from app.registry import Registry

import_agents = Registry()
import_agents.add(
    "example-loyalty-scheme",
    "app.imports.agents.example_loyalty_scheme.ExampleLoyaltySchemeAgent",
)
import_agents.add(
    "example-payment-provider",
    "app.imports.agents.example_payment_provider.ExamplePaymentProviderAgent",
)
import_agents.add("amex", "app.imports.agents.amex.AmexAgent")
import_agents.add("visa", "app.imports.agents.visa.VisaAgent")
import_agents.add("mastercard", "app.imports.agents.mastercard.MastercardAgent")
import_agents.add(
    "harvey-nichols", "app.imports.agents.harvey_nichols.HarveyNicholsAgent"
)
import_agents.add("iceland-bonus-card", "app.imports.agents.iceland.IcelandAgent")

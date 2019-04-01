from app.registry import Registry
from app.imports.agents import BaseAgent

import_agents = Registry[BaseAgent]()
import_agents.add("amex", "app.imports.agents.amex.Amex")
import_agents.add("visa", "app.imports.agents.visa.Visa")
import_agents.add("mastercard", "app.imports.agents.mastercard.Mastercard")
import_agents.add("harvey-nichols", "app.imports.agents.harvey_nichols.HarveyNichols")
import_agents.add("iceland-bonus-card", "app.imports.agents.iceland.Iceland")
import_agents.add("bink-loyalty", "app.imports.agents.bink_loyalty.BinkLoyalty")
import_agents.add("bink-payment", "app.imports.agents.bink_payment.BinkPayment")

import_agents.add("example-loyalty-scheme", "app.imports.agents.example_loyalty_scheme.ExampleLoyaltySchemeAgent")
import_agents.add("example-payment-provider", "app.imports.agents.example_payment_provider.ExamplePaymentProviderAgent")

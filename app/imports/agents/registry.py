from app.registry import Registry
from app.imports.agents import BaseAgent

import_agents = Registry[BaseAgent]()
import_agents.add("amex", "app.imports.agents.amex.Amex")
import_agents.add("amex-auth", "app.imports.agents.amex.AmexAuth")
import_agents.add("visa-auth", "app.imports.agents.visa.VisaAuth")
import_agents.add("visa-settlement", "app.imports.agents.visa.VisaSettlement")
import_agents.add("mastercard-settled", "app.imports.agents.mastercard.MastercardSettled")
import_agents.add("mastercard-auth", "app.imports.agents.mastercard.MastercardAuth")
import_agents.add("cooperative", "app.imports.agents.cooperative.Cooperative")
import_agents.add("harvey-nichols", "app.imports.agents.harvey_nichols.HarveyNichols")
import_agents.add("iceland-bonus-card", "app.imports.agents.iceland.Iceland")
import_agents.add("wasabi-club", "app.imports.agents.wasabi.Wasabi")
import_agents.add("whsmith-rewards", "app.imports.agents.whsmith.WhSmith")
import_agents.add("bink-loyalty", "app.imports.agents.bink_loyalty.BinkLoyalty")
import_agents.add("bink-payment", "app.imports.agents.bink_payment.BinkPayment")

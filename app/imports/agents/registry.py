import settings
from app.imports.agents.bases.base import BaseAgent
from app.registry import Registry

import_agents = Registry[BaseAgent]()
import_agents.add("amex", "app.imports.agents.amex.Amex")
import_agents.add("amex-auth", "app.imports.agents.amex.AmexAuth")
import_agents.add("amex-settlement", "app.imports.agents.amex.AmexSettlement")
import_agents.add("visa-auth", "app.imports.agents.visa.VisaAuth")
import_agents.add("visa-settlement", "app.imports.agents.visa.VisaSettlement")
import_agents.add("visa-refund", "app.imports.agents.visa.VisaRefund")
import_agents.add("mastercard-auth", "app.imports.agents.mastercard.MastercardAuth")
import_agents.add("cooperative", "app.imports.agents.cooperative.Cooperative")
import_agents.add("harvey-nichols", "app.imports.agents.harvey_nichols.HarveyNichols")
import_agents.add("iceland-bonus-card", "app.imports.agents.iceland.Iceland")
import_agents.add("wasabi-club", "app.imports.agents.wasabi.Wasabi")
import_agents.add("whsmith-rewards", "app.imports.agents.whsmith.WhSmith")

# TEMPORARY: remove when TS44 feed is deprecated.
if settings.MASTERCARD_TGX2_ENABLED:
    import_agents.add("mastercard-settled", "app.imports.agents.mastercard.MastercardTGX2Settlement")
else:
    import_agents.add("mastercard-settled", "app.imports.agents.mastercard.MastercardTS44Settlement")

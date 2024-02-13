from app.imports.agents.bases.base import BaseAgent
from app.registry import Registry

import_agents = Registry[BaseAgent]()
import_agents.add("amex-auth", "app.imports.agents.amex.AmexAuth")
import_agents.add("amex-settlement", "app.imports.agents.amex.AmexSettlement")
import_agents.add("visa-auth", "app.imports.agents.visa.VisaAuth")
import_agents.add("visa-settlement", "app.imports.agents.visa.VisaSettlement")
import_agents.add("visa-refund", "app.imports.agents.visa.VisaRefund")
import_agents.add("mastercard-auth", "app.imports.agents.mastercard.MastercardAuth")
import_agents.add("mastercard-settled", "app.imports.agents.mastercard.MastercardTGX2Settlement")
import_agents.add("mastercard-refund", "app.imports.agents.mastercard.MastercardTGX2Refund")
import_agents.add("costa", "app.imports.agents.costa.Costa")
import_agents.add("iceland-bonus-card", "app.imports.agents.iceland.Iceland")
import_agents.add("wasabi-club", "app.imports.agents.wasabi.Wasabi")
import_agents.add("itsu", "app.imports.agents.itsu.Itsu")
# import_agents.add("slim-chickens", "app.imports.agents.slim_chickens.SlimChickens") holding until import is available
import_agents.add("stonegate", "app.imports.agents.stonegate.Stonegate")
import_agents.add("tgi-fridays", "app.imports.agents.tgi-fridays.TGIFridays")

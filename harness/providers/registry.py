from app.registry import Registry
from harness.providers.base import BaseImportDataProvider


import_data_providers = Registry[BaseImportDataProvider]()
import_data_providers.add("bink-loyalty", "harness.providers.bink_loyalty.BinkLoyalty")
import_data_providers.add("bink-payment", "harness.providers.bink_payment.BinkPayment")
import_data_providers.add("harvey-nichols", "harness.providers.harvey_nichols.HarveyNichols")
import_data_providers.add("iceland-bonus-card", "harness.providers.iceland.Iceland")
import_data_providers.add("amex", "harness.providers.amex.Amex")
import_data_providers.add("mastercard", "harness.providers.mastercard.Mastercard")

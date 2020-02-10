from app.registry import Registry
from harness.providers.base import BaseImportDataProvider


import_data_providers = Registry[BaseImportDataProvider]()
import_data_providers.add("bink-loyalty", "harness.providers.bink_loyalty.BinkLoyalty")
import_data_providers.add("bink-payment", "harness.providers.bink_payment.BinkPayment")

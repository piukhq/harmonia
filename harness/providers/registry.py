from app.registry import Registry
from harness.providers.base import BaseImportDataProvider

import_data_providers = Registry[BaseImportDataProvider]()
import_data_providers.add("harvey-nichols", "harness.providers.harvey_nichols.HarveyNichols")
import_data_providers.add("iceland-bonus-card", "harness.providers.iceland.Iceland")
import_data_providers.add("amex-settlement", "harness.providers.amex.AmexSettlement")
import_data_providers.add("amex-auth", "harness.providers.amex.AmexAuth")
import_data_providers.add("mastercard-auth", "harness.providers.mastercard.MastercardAuth")
import_data_providers.add("mastercard-settled", "harness.providers.mastercard.MastercardTGX2Settlement")
import_data_providers.add("visa-auth", "harness.providers.visa.VisaAuth")
import_data_providers.add("visa-settlement", "harness.providers.visa.VisaSettlement")
import_data_providers.add("visa-refund", "harness.providers.visa.VisaRefund")
import_data_providers.add("wasabi-club", "harness.providers.wasabi.Wasabi")

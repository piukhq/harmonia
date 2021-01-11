import string

from app import models
from app.config import Config, ConfigValue, KEY_PREFIX
from app.exports.agents.bases.ecrebo import Ecrebo

PROVIDER_SLUG = "burger-king-rewards"


RECEIPT_XML_TEMPLATE = string.Template(
    """<?xml version="1.0" encoding="UTF-8"?>
<POSLog xmlns="http://www.nrf-arts.org/IXRetail/namespace/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" MajorVersion="6" MinorVersion="0" FixVersion="0">
    <Transaction>
        <BusinessUnit>
            <UnitID Name="Burger King">$MID</UnitID>
            <Website>www.burgerking.co.uk</Website>
        </BusinessUnit>
       <ReceiptNumber>$TRANSACTION_ID</ReceiptNumber>
      <POSLogDateTime TypeCode="Transaction">$TRANSACTION_DATE</POSLogDateTime>
      <CurrencyCode>BKU</CurrencyCode>
      <CustomerOrderTransaction TypeCode="Transaction" TransactionStatus="Tendered">
           <Total TotalType="TransactionGrandAmount">$TRANSACTION_VALUE</Total>
      </CustomerOrderTransaction>
    </Transaction>
</POSLog>"""
)


REWARD_UPLOAD_PATH_KEY = f"{KEY_PREFIX}{PROVIDER_SLUG}.reward_upload_path"
RECEIPT_UPLOAD_PATH_KEY = f"{KEY_PREFIX}{PROVIDER_SLUG}.receipt_upload_path"
SCHEDULE_KEY = f"{KEY_PREFIX}{PROVIDER_SLUG}.schedule"


class BurgerKing(Ecrebo):
    provider_slug = PROVIDER_SLUG
    matching_type = models.MatchingType.SPOTTED
    receipt_xml_template = RECEIPT_XML_TEMPLATE
    provider_short_code = "BK"

    config = Config(
        ConfigValue("reward_upload_path", key=REWARD_UPLOAD_PATH_KEY, default="upload/staging/rewards"),
        ConfigValue("receipt_upload_path", key=RECEIPT_UPLOAD_PATH_KEY, default="upload/staging/receipts"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

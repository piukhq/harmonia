import string

from app import config
from app.exports.agents.bases.ecrebo import Ecrebo

PROVIDER_SLUG = "fatface"


RECEIPT_XML_TEMPLATE = string.Template(
    """<?xml version="1.0" encoding="UTF-8"?>
<POSLog xmlns="http://www.nrf-arts.org/IXRetail/namespace/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" MajorVersion="6" MinorVersion="0" FixVersion="0">
    <Transaction>
        <BusinessUnit>
            <UnitID Name="Fat Face">$MID</UnitID>
            <Website>www.fatface.com</Website>
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


REWARD_UPLOAD_PATH_KEY = f"{config.KEY_PREFIX}{PROVIDER_SLUG}.reward_upload_path"
RECEIPT_UPLOAD_PATH_KEY = f"{config.KEY_PREFIX}{PROVIDER_SLUG}.receipt_upload_path"
SCHEDULE_KEY = f"{config.KEY_PREFIX}{PROVIDER_SLUG}.schedule"


class FatFace(Ecrebo):
    provider_slug = PROVIDER_SLUG
    receipt_xml_template = RECEIPT_XML_TEMPLATE
    provider_short_code = "FF"

    class Config:
        reward_upload_path = config.ConfigValue(REWARD_UPLOAD_PATH_KEY, default="upload/staging/rewards")
        receipt_upload_path = config.ConfigValue(RECEIPT_UPLOAD_PATH_KEY, default="upload/staging/receipts")
        schedule = config.ConfigValue(SCHEDULE_KEY, "* * * * *")

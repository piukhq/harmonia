import json
import typing as t

import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pennies
from app.feeds import FeedType
from app.imports.agents.bases.base import SchemeTransactionFields
from app.imports.agents.bases.file_agent import FileAgent
from app.service.hermes import PaymentProviderSlug

PROVIDER_SLUG = "harvey-nichols"
PATH_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.path"
SCHEDULE_KEY = f"{KEY_PREFIX}imports.agents.{PROVIDER_SLUG}.schedule"

DATE_FORMAT = "YYYY-MM-DD"
DATETIME_FORMAT = "YYYY-MM-DD-HH.mm.ss"


STORE_ID_TO_MIDS: t.Dict[str, t.List[str]] = {
    # Knightsbridge
    "0001": [
        "92040913",
        "92040173",
        "92040593",
        "92041223",
        "80289201",
        "80289611",
        "14247791",
        "82433621",
        "56742051",
        "24870721",
        "9425544541",
        "9423447317",
        "9421355991",
        "9421576323",
        "9420461865",
        "9448629014",
        "9600280796",
        "3563043",
        "3563463",
        "3563543",
        "3562493",
        "3561923",
        "3561843",
        "3561763",
        "3562233",
        "3563123",
        "3562733",
        "3562573",
        "3561503",
        "3561683",
        "3562313",
        "3562993",
        "3563203",
        "3563383",
        "3562813",
        "3553323",
        "3562073",
    ],
    # Harvey Nichols Online
    "0002": ["92042873", "88096831", "9426993077", "57741381", "19410201", "19410121", "19410381", "19410461"],
    # Birmingham
    "0003": [
        "05447373",
        "95049623",
        "95050313",
        "82287021",
        "9427586888",
        "3559503",
        "3561003",
        "3561423",
        "3560793",
        "3554053",
        "3560533",
        "3561263",
        "3559683",
        "3559923",
        "3560113",
        "3560953",
        "3560873",
        "3560613",
        "3560293",
        "3559763",
        "3560373",
    ],
    # Leeds
    "0004": [
        "92044153",
        "92043503",
        "92043923",
        "80383251",
        "9424029692",
        "62456821",
        "9421011404",
        "2694231",
        "9600360903",
        "3164346",
    ],
    # Edinburgh
    "0005": [
        "92042033",
        "92041563",
        "92041983",
        "83897511",
        "9420682379",
        "83897021",
        "9420682361",
        "55526581",
        "9445689920",
        "3163221",
    ],
    # Manchester
    "0006": ["92044733", "92044233", "87256081", "9425638210", "87255901", "9425638228"],
    # Ireland (Not part of the loyalty scheme so no MIDs)
    "0007": [],
    # Bristol
    "0009": ["92042453", "92042793", "51428981", "9444905814", "51428491", "9444905822"],
    # Beauty Bazaar Liverpool
    "0018": ["92043263", "65069761", "9447987371", "65119011", "9447988304", "11493993"],
    # Oxo
    "0020": ["92052253", "62461441", "9421011339"],
    # Prism
    "0025": ["65010921", "9421353707"],
}


payment_provider_map = {
    "AMERICAN EXPRESS": PaymentProviderSlug.AMEX,
    "AMEX": PaymentProviderSlug.AMEX,
    "DCC MASTERCARD": PaymentProviderSlug.MASTERCARD,
    "Mastercard DB": PaymentProviderSlug.MASTERCARD,
    "MAESTRO": PaymentProviderSlug.MASTERCARD,
    "MASTERCARD": PaymentProviderSlug.MASTERCARD,
    "SOLO": PaymentProviderSlug.MASTERCARD,
    "SWITCH": PaymentProviderSlug.MASTERCARD,
    "DCC VISA": PaymentProviderSlug.VISA,
    "DELTA": PaymentProviderSlug.VISA,
    "ELECTRON": PaymentProviderSlug.VISA,
    "VISA": PaymentProviderSlug.VISA,
}


class HarveyNichols(FileAgent):
    feed_type = FeedType.MERCHANT
    provider_slug = PROVIDER_SLUG
    config = Config(
        ConfigValue("path", PATH_KEY, default=f"{PROVIDER_SLUG}/"),
        ConfigValue("schedule", SCHEDULE_KEY, default="* * * * *"),
    )

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["files_received", "transactions"],
            "gauges": ["last_file_timestamp"],
        }

    """
    Harvey Nichols send transaction data with unrecognised payment providers, EG "ACCESS (NOT USED)"
    The following generator only yields the valid payment provider transactions, only these are stored.
    """

    def yield_transactions_data(self, data: bytes) -> t.Iterable[dict]:
        transactions = json.loads(data.decode())["transactions"]
        for transaction in transactions:
            if transaction["card"]["scheme"] not in payment_provider_map:
                continue

            # raising an error for a bad datetime format at this point allows the rest of the file to be imported.
            self.get_transaction_date(transaction)

            yield transaction

    def to_transaction_fields(self, data: dict) -> SchemeTransactionFields:
        return SchemeTransactionFields(
            merchant_slug=self.provider_slug,
            payment_provider_slug=payment_provider_map[data["card"]["scheme"]],
            transaction_date=self.get_transaction_date(data),
            has_time=True,
            spend_amount=to_pennies(data["amount"]["value"]),
            spend_multiplier=100,
            spend_currency=data["amount"]["unit"],
            auth_code=self.process_auth_code(data["auth_code"]),
            first_six=data["card"]["first_6"],
            last_four=data["card"]["last_4"],
        )

    def process_auth_code(self, auth_code: str) -> str:
        auth_code = auth_code.strip()
        return auth_code[2:] if auth_code.startswith("00") else auth_code

    @staticmethod
    def get_transaction_id(data: dict) -> str:
        return data["id"]

    def get_primary_mids(self, data: dict) -> list[str]:
        # This is purely here to satisfy the need for this function in an agent
        # Harvey Nichols is currently not operational - rethink if and when reinstated
        return [data["store_id"]]

    def get_transaction_date(self, data: dict) -> pendulum.DateTime:
        return self.pendulum_parse(data["timestamp"], tz="Europe/London")

import csv
import io
from collections.abc import Callable, Iterable
from decimal import Decimal

import pendulum

from app.config import KEY_PREFIX, Config, ConfigValue
from app.export_result.agents.bases.results_file_agent import ResultsFileAgent
from app.service.atlas import AuditTransaction

PROVIDER_SLUG = "stonegate-unmatched"
PATH_KEY = f"{KEY_PREFIX}results.agents.{PROVIDER_SLUG}.path"
SCHEDULE_KEY = f"{KEY_PREFIX}results.agents.{PROVIDER_SLUG}.schedule"


class Stonegate(ResultsFileAgent):
    provider_slug = PROVIDER_SLUG
    config = Config(
        ConfigValue("path", key=PATH_KEY, default=f"results/{PROVIDER_SLUG}/"),
        ConfigValue("schedule", key=SCHEDULE_KEY, default="* * * * *"),
    )

    def __init__(self):
        super().__init__()

        # Set up Prometheus metric types
        self.prometheus_metrics = {
            "counters": ["files_received", "transactions"],
            "gauges": ["last_file_timestamp"],
        }

    field_transforms: dict[str, Callable] = {
        "transaction_id": str,
        "member_number": str,
        "retailer_location_id": str,
        "transaction_amount": Decimal,
        "transaction_date": lambda x: pendulum.parse(x).isoformat(),
        "result": str,
    }

    def yield_results_data(self, data: bytes) -> Iterable[dict]:
        fd = io.StringIO(data.decode())
        reader = csv.DictReader(fd)
        for raw_data in reader:
            yield {k: self.field_transforms.get(k, str)(v) for k, v in raw_data.items()}

    def format_audit_transaction(self, result: dict) -> list[AuditTransaction]:
        """
        This is necessary to provide Atlas with a "list" of the transactions, in the atlas format.
        The list will consist of a single transaction since we process each row in a batch of transactions.
        """
        created_date = pendulum.now().isoformat()
        return [
            AuditTransaction(
                event_date_time=created_date,
                user_id="",
                transaction_id=result["transaction_id"],
                transaction_date=result["transaction_date"],
                spend_amount=result["transaction_amount"],
                spend_currency="GBP",
                loyalty_id=None,
                mid=None,
                scheme_account_id=None,
                encrypted_credentials=None,
                status="EXPORTED",
                feed_type=None,
                location_id=result["retailer_location_id"],
                merchant_internal_id=None,
                payment_card_account_id=None,
                settlement_key=None,
                authorisation_code=None,
                approval_code=None,
                loyalty_identifier=result["member_number"],
                record_uid=None,
                export_uid=result["uid"],
            )
        ]

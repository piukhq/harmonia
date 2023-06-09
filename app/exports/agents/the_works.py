import uuid
from decimal import Decimal

import pendulum

from app import db, models
from app.config import KEY_PREFIX, Config, ConfigValue
from app.currency import to_pounds
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.bases.singular_export_agent import SingularExportAgent
from app.service import atlas, the_works

PROVIDER_SLUG = "the-works"

BASE_URL_KEY = f"{KEY_PREFIX}exports.agents.{PROVIDER_SLUG}.base_url"


class DedupeDelayRetry(Exception):
    def __init__(self, delay_seconds: int = 5, *args: object) -> None:
        self.delay_seconds = delay_seconds
        super().__init__(*args)


class TheWorks(SingularExportAgent):
    provider_slug = PROVIDER_SLUG
    config = Config(ConfigValue("base_url", key=BASE_URL_KEY, default="https://reflector.staging.gb.bink.com/mock/"))

    def get_retry_datetime(self, retry_count: int, *, exception: Exception | None = None) -> pendulum.DateTime | None:
        if isinstance(exception, DedupeDelayRetry):
            return pendulum.now().add(seconds=exception.delay_seconds)

        # we account for the original dedupe delay by decrementing the retry
        # count to essentially act as if the second retry is actually the first.
        return super().get_retry_datetime(retry_count - 1, exception=exception)

    def find_export_transaction(
        self, pending_export: models.PendingExport, *, session: db.Session
    ) -> models.ExportTransaction:
        # Get the saved transaction for export and compare to the works historical transactions
        matched_transaction = super().find_export_transaction(pending_export, session=session)

        if matched_transaction:
            # The Works export transaction process requires a check against known rewarded transactions
            # This means we need to request a transaction history from The Works, the compare
            # the current transaction with the works transactions.
            api = the_works.TheWorksAPI(self.config.get("base_url", session))
            # Get transactions history from GiveX The Works.
            historical_rewarded_transactions = api.transaction_history(matched_transaction.loyalty_id)
            if not exportable_transaction(matched_transaction, historical_rewarded_transactions):
                self.log.warning("Transaction has already been rewarded in The Works - GiveX system.")
                raise db.NoResultFound

        return matched_transaction

    def make_export_data(self, export_transaction: models.ExportTransaction, session: db.Session) -> AgentExportData:
        api = the_works.TheWorksAPI(self.config.get("base_url", session))
        user_id, password = api.get_credentials()
        transaction_code = str(uuid.uuid4())
        return AgentExportData(
            outputs=[
                AgentExportDataOutput(
                    "export.json",
                    {
                        "jsonrpc": "2.0",
                        "method": "dc_911",  # request method
                        "id": 1,
                        "params": [
                            "en",  # language code
                            transaction_code,
                            user_id,
                            password,
                            export_transaction.loyalty_id,  # givex number
                            to_pounds(export_transaction.spend_amount),
                        ],
                    },
                )
            ],
            transactions=[export_transaction],
            extra_data=export_transaction.extra_fields,
        )

    def export(self, export_data: AgentExportData, *, retry_count: int = 0, session: db.Session) -> None:
        if retry_count == 0:
            created_at = pendulum.instance(export_data.transactions[0].created_at)
            if pendulum.now().diff(created_at).total_seconds() < 5:
                raise DedupeDelayRetry

        body: dict
        _, body = export_data.outputs[0]  # type: ignore

        api = the_works.TheWorksAPI(self.config.get("base_url", session))

        request_timestamp = pendulum.now().to_datetime_string()
        response = api.transactions(body, "")
        response_timestamp = pendulum.now().to_datetime_string()

        request_url = api.base_url
        atlas.queue_audit_message(
            atlas.make_audit_message(
                self.provider_slug,
                atlas.make_audit_transactions(
                    export_data.transactions, tx_loyalty_ident_callback=lambda tx: tx.loyalty_id
                ),
                request=body,
                request_timestamp=request_timestamp,
                response=response,
                response_timestamp=response_timestamp,
                request_url=request_url,
                retry_count=retry_count,
            )
        )


def exportable_transaction(matched_transaction: models.ExportTransaction, historical_rewarded_transactions: dict):
    # Check if the current transactions has already been rewarded in the historical transactions
    can_be_exported = True

    # Check for errors in the response
    if historical_rewarded_transactions["result"] and int(historical_rewarded_transactions["result"][1]) > 0:
        return False

    for transaction in historical_rewarded_transactions["result"][5]:
        current_tx_points = int(Decimal(matched_transaction.spend_amount) / 100) * 5
        history_points = int(Decimal(transaction[3]))  # Should be the points
        current_tx_date = pendulum.instance(matched_transaction.transaction_date).to_date_string()
        history_tx_date = pendulum.parse(transaction[0]).to_date_string()  # Date part only, time is a separate value.

        if current_tx_date == history_tx_date and current_tx_points == history_points:
            can_be_exported = False
            break

    return can_be_exported

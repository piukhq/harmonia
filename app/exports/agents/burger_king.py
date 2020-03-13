import csv
import io
import string
import typing as t
from base64 import b64encode
from decimal import Decimal
from uuid import uuid4

import pendulum
from lxml import etree
from soteria.configuration import Configuration
from soteria.encryption import PGP
from sqlalchemy.orm import Load, joinedload

import settings
from app import db, models, config
from app.exports.agents import AgentExportData, AgentExportDataOutput, BatchExportAgent
from app.exports.sequencing import Sequencer
from app.service.atlas import atlas
from app.service.sftp import SFTP

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


REWARD_UPLOAD_PATH_KEY = f"{config.KEY_PREFIX}{PROVIDER_SLUG}.reward_upload_path"
RECEIPT_UPLOAD_PATH_KEY = f"{config.KEY_PREFIX}{PROVIDER_SLUG}.receipt_upload_path"


class ExportFileSet(t.NamedTuple):
    receipt_data: str
    reward_data: str
    transaction_count: int


class BurgerKing(BatchExportAgent):
    provider_slug = PROVIDER_SLUG
    saved_output_index = 2  # save rewards CSV to export_transaction table

    class Config:
        reward_upload_path = config.ConfigValue(REWARD_UPLOAD_PATH_KEY, default="upload/staging/receipts")
        receipt_upload_path = config.ConfigValue(REWARD_UPLOAD_PATH_KEY, default="upload/staging/rewards")

    def __init__(self):
        super().__init__()

        config = Configuration(
            self.provider_slug,
            Configuration.TRANSACTION_MATCHING_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.SOTERIA_URL,
        )

        security_credentials = {
            c["credential_type"]: c["value"] for c in config.security_credentials["outbound"]["credentials"]
        }

        self.pgp = PGP(security_credentials["merchant_public_key"].encode())
        self.sftp_credentials = security_credentials["compound_key"]
        self.skey = security_credentials["bink_private_key"]

        self.sequencer = Sequencer(self.provider_slug)

    def _get_transaction_id(self, seq_number):
        transaction_number = str(seq_number).rjust(10, "0")
        return "BKBNK{}".format(transaction_number)

    def _create_receipt_data(self, transactions: t.List[models.MatchedTransaction], sequence_number: int) -> str:
        date = pendulum.now().format("YYYY-MM-DDTHH:mm:ss")

        buf = io.StringIO()

        xml_parser = etree.XMLParser(remove_blank_text=True)
        for transaction in transactions:
            transaction_id = self._get_transaction_id(sequence_number)
            transaction_amount = Decimal(transaction.spend_amount * 5) / Decimal(100)
            sequence_number += 1

            xml_string = RECEIPT_XML_TEMPLATE.substitute(
                MID=transaction.merchant_identifier.mid,
                TRANSACTION_ID=transaction_id,
                TRANSACTION_DATE=date,
                TRANSACTION_VALUE=transaction_amount.quantize(Decimal("0.01")),
            )
            xml = etree.XML(bytes(xml_string, "utf-8"), parser=xml_parser)
            formatted_xml = b64encode(etree.tostring(xml)).decode()
            print(formatted_xml, file=buf)

        return buf.getvalue()

    def _create_reward_data(
        self, transactions: t.List[models.MatchedTransaction], sequence_number: int
    ) -> t.Tuple[str, t.List[dict]]:
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter="|")

        atlas_calls: t.List[dict] = []

        for transaction in transactions:
            transaction_id = self._get_transaction_id(sequence_number)
            sequence_number += 1
            record_uid = str(uuid4())
            loyalty_id = transaction.payment_transaction.user_identity.loyalty_id
            if not loyalty_id:
                error_msg = f"No loyalty card ID saved on transaction. Transaction ID: {transaction.transaction_id}"
                self.log.error(error_msg)
                atlas_calls.append(
                    {"response": error_msg, "transaction": transaction, "status": atlas.Status.NOT_ASSIGNED}
                )
            else:
                writer.writerow((loyalty_id, transaction_id, record_uid))
                atlas_calls.append(
                    {"response": "success", "transaction": transaction, "status": atlas.Status.BINK_ASSIGNED}
                )
        return buf.getvalue(), atlas_calls

    def _create_fileset(self, transactions: t.List[models.MatchedTransaction]) -> t.Tuple[ExportFileSet, t.List[dict]]:
        transactions = [tx for tx in transactions if tx.spend_amount > 0]
        sequence_number = self.sequencer.next_value()
        reward_data, atlas_calls = self._create_reward_data(transactions, sequence_number)
        fileset = ExportFileSet(
            receipt_data=self._create_receipt_data(transactions, sequence_number),
            reward_data=reward_data,
            transaction_count=len(transactions),
        )
        self.sequencer.set_next_value(sequence_number + fileset.transaction_count)
        return fileset, atlas_calls

    def yield_export_data(self) -> t.Iterable[AgentExportData]:
        pending_exports_q = (
            db.session.query(models.PendingExport)
            .options(
                joinedload(models.PendingExport.matched_transaction, innerjoin=True)
                .joinedload(models.MatchedTransaction.payment_transaction, innerjoin=True)
                .joinedload(models.PaymentTransaction.user_identity, innerjoin=True),
                Load(models.PendingExport).raiseload("*"),
            )
            .filter(models.PendingExport.provider_slug == self.provider_slug)
        )

        pending_exports = pending_exports_q.all()

        transactions = [pe.matched_transaction for pe in pending_exports]
        fileset, atlas_calls = self._create_fileset(transactions)
        ts = pendulum.now().int_timestamp

        # the order of these outputs is used to upload to SFTP in sequence.
        yield AgentExportData(
            outputs=[
                AgentExportDataOutput(f"receipt_{ts}.base64", fileset.receipt_data),
                AgentExportDataOutput(f"receipt_{ts}.chk", str(fileset.transaction_count)),
                AgentExportDataOutput(f"rewards_{ts}.csv", fileset.reward_data),
                AgentExportDataOutput(f"rewards_{ts}.chk", str(fileset.transaction_count)),
            ],
            transactions=transactions,
            extra_data={},
        )

        def delete_pending_exports():
            pending_exports_q.delete()
            db.session.commit()

        db.run_query(delete_pending_exports, description="delete pending exports")

        for atlas_call in atlas_calls:
            atlas.save_transaction(provider_slug=self.provider_slug, **atlas_call)

    def send_export_data(self, export_data: AgentExportData):
        # place output data into BytesIO objects for SFTP usage.
        buffered_outputs = [(name, io.BytesIO(t.cast(str, content).encode())) for name, content in export_data.outputs]

        # we have to send the files in a very specific order.
        skey = io.StringIO(self.skey)
        with SFTP(self.sftp_credentials, skey, self.Config.receipt_upload_path) as sftp:
            name, buf = buffered_outputs[0]
            sftp.client.putfo(buf, name)
            name, buf = buffered_outputs[1]
            sftp.client.putfo(buf, name)

        with SFTP(self.sftp_credentials, skey, self.Config.reward_upload_path) as sftp:
            name, buf = buffered_outputs[2]
            sftp.client.putfo(buf, name)
            name, buf = buffered_outputs[3]
            sftp.client.putfo(buf, name)

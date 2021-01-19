import csv
import io
import typing as t
from base64 import b64encode
from decimal import Decimal
from uuid import UUID, uuid3

import pendulum
from soteria.encryption import PGP

import settings
from app import models, db, xml_utils
from app.config import Config
from app.soteria import SoteriaConfigMixin
from app.utils import missing_property
from app.exports.agents import AgentExportData, AgentExportDataOutput, BatchExportAgent
from app.exports.sequencing import Sequencer
from app.service import atlas
from app.service.sftp import SFTP, SFTPCredentials


class ExportFileSet(t.NamedTuple):
    receipt_data: t.Optional[str]
    reward_data: str
    transaction_count: int


class next_sequence_number:
    def __init__(
        self,
        sequencer: Sequencer,
        matching_type: t.Literal[models.MatchingType.SPOTTED, models.MatchingType.LOYALTY],
        delta: int,
        session: db.Session,
    ) -> None:
        self.sequencer = sequencer
        self.session = session
        self.start = 0
        self.delta = delta
        self.spotting = matching_type == models.MatchingType.SPOTTED

    def __enter__(self):
        if self.spotting:
            self.start = self.sequencer.next_value(session=self.session)
        return self.start

    def __exit__(self, exc_type, exc_value, traceback):
        if self.spotting:
            self.sequencer.set_next_value(self.start + self.delta, session=self.session)


class Ecrebo(BatchExportAgent, SoteriaConfigMixin):
    saved_output_index = 2  # save rewards CSV to export_transaction table

    config = Config()

    def __init__(self):
        super().__init__()

        if settings.ATLAS_URL is None:
            raise settings.ConfigVarRequiredError(
                f"The {self.provider_slug} export agent requires the Atlas URL to be set."
            )

        soteria_config = self.get_soteria_config()
        security_credentials = {
            c["credential_type"]: c["value"] for c in soteria_config.security_credentials["outbound"]["credentials"]
        }

        self.pgp = PGP(security_credentials["merchant_public_key"].encode())
        compound_key = security_credentials["compound_key"]
        self.sftp_credentials = SFTPCredentials(**{k: compound_key.get(k) for k in SFTPCredentials._fields})
        self.skey = security_credentials.get("bink_private_key")

        self.sequencer = Sequencer(self.provider_slug)

    @property
    def receipt_xml_template(self):
        if self.matching_type == models.MatchingType.SPOTTED:
            return missing_property(type(self), "receipt_xml_template")

    @property
    def provider_short_code(self):
        return missing_property(type(self), "provider_short_code")

    @property
    def matching_type(self):
        return missing_property(type(self), "matching_type")

    def _get_transaction_id(self, transaction: models.MatchedTransaction, seq_number: int) -> str:
        if self.matching_type == models.MatchingType.SPOTTED:
            transaction_number = str(seq_number).rjust(10, "0")
            return f"{self.provider_short_code}BNK{transaction_number}"
        else:
            return f"{transaction.transaction_id}"

    def _create_receipt_data(self, transactions: t.List[models.MatchedTransaction], sequence_number: int) -> str:
        date = pendulum.now().format("YYYY-MM-DDTHH:mm:ss")

        buf = io.StringIO()

        for sequence_number, transaction in enumerate(transactions, start=sequence_number):
            transaction_id = self._get_transaction_id(transaction, sequence_number)
            transaction_amount = Decimal(transaction.spend_amount * 5) / Decimal(100)

            xml_string = self.receipt_xml_template.substitute(
                MID=transaction.merchant_identifier.mid,
                TRANSACTION_ID=transaction_id,
                TRANSACTION_DATE=date,
                TRANSACTION_VALUE=transaction_amount.quantize(Decimal("0.01")),
            )
            formatted_xml = b64encode(xml_utils.minify(xml_string).encode()).decode()
            print(formatted_xml, file=buf)

        return buf.getvalue()

    @staticmethod
    def get_merchant_identifier(matched_transaction: models.MatchedTransaction) -> str:
        return matched_transaction.payment_transaction.user_identity.loyalty_id

    @staticmethod
    def get_record_uid(matched_transaction: models.MatchedTransaction) -> str:
        return str(uuid3(UUID(int=matched_transaction.id), matched_transaction.transaction_id))

    def _create_reward_data(self, transactions: t.List[models.MatchedTransaction], sequence_number: int) -> str:
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter="|")

        for sequence_number, transaction in enumerate(transactions, start=sequence_number):
            transaction_id = self._get_transaction_id(transaction, sequence_number)
            record_uid = self.get_record_uid(transaction)
            loyalty_id = self.get_merchant_identifier(transaction)
            if not loyalty_id:
                error_msg = (
                    f"No loyalty card ID saved on transaction. Skipping transaction ID: {transaction.transaction_id}."
                )
                self.log.error(error_msg)
            else:
                writer.writerow((loyalty_id, transaction_id, record_uid))
        return buf.getvalue()

    def _create_fileset(self, transactions: t.List[models.MatchedTransaction], *, session: db.Session) -> ExportFileSet:
        transactions = [tx for tx in transactions if tx.spend_amount > 0]

        with next_sequence_number(self.sequencer, self.matching_type, len(transactions), session) as sequence_number:
            reward_data = self._create_reward_data(transactions, sequence_number)
            receipt_data = (
                self._create_receipt_data(transactions, sequence_number)
                if self.matching_type == models.MatchingType.SPOTTED
                else None
            )
            fileset = ExportFileSet(
                receipt_data=receipt_data, reward_data=reward_data, transaction_count=len(transactions),
            )
        return fileset

    def yield_export_data(
        self, transactions: t.List[models.MatchedTransaction], *, session: db.Session
    ) -> t.Iterable[AgentExportData]:
        fileset = self._create_fileset(transactions, session=session)
        ts = pendulum.now().int_timestamp

        # the order of these outputs is used to upload to SFTP in sequence.
        outputs = []
        if fileset.receipt_data is not None:
            outputs.extend(
                [
                    AgentExportDataOutput(f"receipts_{self.provider_short_code}{ts}.base64", fileset.receipt_data),
                    AgentExportDataOutput(
                        f"receipts_{self.provider_short_code}{ts}.chk", str(fileset.transaction_count)
                    ),
                ]
            )
        outputs.extend(
            [
                AgentExportDataOutput(f"rewards_{self.provider_short_code}{ts}.csv", fileset.reward_data),
                AgentExportDataOutput(f"rewards_{self.provider_short_code}{ts}.chk", str(fileset.transaction_count)),
            ]
        )
        yield AgentExportData(outputs=outputs, transactions=transactions, extra_data={})

    def _prepare_for_sftp(self, output: AgentExportDataOutput) -> t.Tuple[str, io.BytesIO]:
        if output.key.endswith((".base64", ".csv")):
            return (f"{output.key}.gpg", io.BytesIO(self.pgp.encrypt(output.data)))
        else:
            return (output.key, io.BytesIO(t.cast(str, output.data).encode()))

    def send_export_data(self, export_data: AgentExportData, session: db.Session) -> None:
        # place output data into BytesIO objects for SFTP usage.
        # this will also encrypt the .base64 and .csv files with PGP and append `.gpg` to the key
        buffered_outputs = list(map(self._prepare_for_sftp, export_data.outputs))

        # we have to send the files in a very specific order.
        if self.matching_type == models.MatchingType.SPOTTED:
            with SFTP(
                self.sftp_credentials, self.skey, self.config.get("receipt_upload_path", session=session)
            ) as sftp:  # type: ignore
                name, buf = buffered_outputs[0]
                sftp.client.putfo(buf, name)
                name, buf = buffered_outputs[1]
                sftp.client.putfo(buf, name)

        with SFTP(self.sftp_credentials, self.skey, self.config.get("reward_upload_path", session=session)) as sftp:
            name, buf = buffered_outputs[2]
            sftp.client.putfo(buf, name)
            name, buf = buffered_outputs[3]
            sftp.client.putfo(buf, name)

        blob_names = self.save_to_blob(settings.BLOB_AUDIT_CONTAINER, export_data)
        atlas.queue_audit_data(
            self.provider_slug,
            atlas.make_audit_transactions(
                export_data.transactions,
                tx_merchant_ident_callback=self.get_merchant_identifier,
                tx_record_uid_callback=self.get_record_uid,
            ),
            blob_names=blob_names,
        )

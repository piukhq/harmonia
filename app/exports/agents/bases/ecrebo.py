import csv
import io
import typing as t
from base64 import b64encode
from decimal import Decimal
from uuid import uuid4

import pendulum
from soteria.configuration import Configuration
from soteria.encryption import PGP

import settings
from app import models, db, xml_utils
from app.utils import classproperty, missing_property
from app.exports.agents import AgentExportData, AgentExportDataOutput, BatchExportAgent
from app.exports.sequencing import Sequencer
from app.service.atlas import atlas
from app.service.sftp import SFTP


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


class EcreboConfig:
    def __init__(self, matching_type: t.Literal[models.MatchingType.SPOTTED, models.MatchingType.LOYALTY]) -> None:
        self.matching_type = matching_type

    @classproperty
    def reward_upload_path(self):
        return missing_property(self, "reward_upload_path")

    @classproperty
    def receipt_upload_path(self):
        if self.matching_type == models.MatchingType.SPOTTED:
            return missing_property(self, "receipt_upload_path")

    @classproperty
    def schedule(self):
        return missing_property(self, "schedule")


class Ecrebo(BatchExportAgent):
    saved_output_index = 2  # save rewards CSV to export_transaction table

    class Config(EcreboConfig):
        pass

    def __init__(self):
        super().__init__()

        if settings.ATLAS_URL is None:
            raise settings.ConfigVarRequiredError(
                f"The {self.provider_slug} export agent requires the Atlas URL to be set."
            )

        if settings.EUROPA_URL is None:
            raise settings.ConfigVarRequiredError(
                f"The {self.provider_slug} export agent requires the Europa URL to be set."
            )

        if settings.VAULT_URL is None or settings.VAULT_TOKEN is None:
            raise settings.ConfigVarRequiredError(
                f"The {self.provider_slug} export agent requires both the Vault URL and token to be set."
            )

        config = Configuration(
            self.provider_slug,
            Configuration.TRANSACTION_MATCHING_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.EUROPA_URL,
        )

        security_credentials = {
            c["credential_type"]: c["value"] for c in config.security_credentials["outbound"]["credentials"]
        }

        self.pgp = PGP(security_credentials["merchant_public_key"].encode())
        self.sftp_credentials = security_credentials["compound_key"]
        self.skey = security_credentials["bink_private_key"]

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
            formatted_xml = b64encode(xml_utils.minify(xml_string).encode())
            print(formatted_xml, file=buf)

        return buf.getvalue()

    def _create_reward_data(
        self, transactions: t.List[models.MatchedTransaction], sequence_number: int
    ) -> t.Tuple[str, t.List[dict]]:
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter="|")

        atlas_calls: t.List[dict] = []

        for sequence_number, transaction in enumerate(transactions, start=sequence_number):
            transaction_id = self._get_transaction_id(transaction, sequence_number)
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

    def _create_fileset(
        self, transactions: t.List[models.MatchedTransaction], *, session: db.Session
    ) -> t.Tuple[ExportFileSet, t.List[dict]]:
        transactions = [tx for tx in transactions if tx.spend_amount > 0]

        with next_sequence_number(self.sequencer, self.matching_type, len(transactions), session) as sequence_number:
            reward_data, atlas_calls = self._create_reward_data(transactions, sequence_number)
            receipt_data = (
                self._create_receipt_data(transactions, sequence_number)
                if self.matching_type == models.MatchingType.SPOTTED
                else None
            )
            fileset = ExportFileSet(
                receipt_data=receipt_data, reward_data=reward_data, transaction_count=len(transactions),
            )
        return fileset, atlas_calls

    def yield_export_data(
        self, transactions: t.List[models.MatchedTransaction], *, session: db.Session
    ) -> t.Iterable[AgentExportData]:
        fileset, atlas_calls = self._create_fileset(transactions, session=session)
        ts = pendulum.now().int_timestamp

        # the order of these outputs is used to upload to SFTP in sequence.
        outputs = []
        if fileset.receipt_data is not None:
            outputs.extend(
                [
                    AgentExportDataOutput(f"receipt_{self.provider_short_code}{ts}.base64", fileset.receipt_data),
                    AgentExportDataOutput(
                        f"receipt_{self.provider_short_code}{ts}.chk", str(fileset.transaction_count)
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

        for atlas_call in atlas_calls:
            atlas.save_transaction(provider_slug=self.provider_slug, **atlas_call)

    def send_export_data(self, export_data: AgentExportData):
        # place output data into BytesIO objects for SFTP usage.
        buffered_outputs = [(name, io.BytesIO(t.cast(str, content).encode())) for name, content in export_data.outputs]

        # we have to send the files in a very specific order.
        skey = io.StringIO(self.skey)
        if self.matching_type == models.MatchingType.SPOTTED:
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

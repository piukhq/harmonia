import datetime
import json
import random

from app.db import SessionMaker
from mimesis import Generic
from mimesis.providers.base import BaseProvider as mimesis_baseprovider
from sqlalchemy.orm import scoped_session

session = scoped_session(SessionMaker)


class JSONProvider(mimesis_baseprovider):
    class Meta:
        name = "json_provider"

    @staticmethod
    def json():
        """
        Generate JSON, we don't care what's in it and it doesn't have to be unique
        """
        data = {
            "offer_id": "0",
            "TransactionCardFirst6": "370003",
            "TransactionCardLast4": "0005",
            "TransactionCardExpiry": "01/80",
            "TransactionCardSchemeId": 1,
            "TransactionCardScheme": "Amex",
            "TransactionCashbackValue": {"__type__": "decimal.Decimal", "repr": "0.00"},
            "TransactionCashbackUnit": "GBP",
        }

        return json.dumps(data)


class TransactionDateProvider(mimesis_baseprovider):
    class Meta:
        name = "transaction_date_provider"

    @staticmethod
    def transaction_date(days: int):
        start_date = datetime.datetime.today()
        random_number_of_days = random.randrange(days)
        random_date = start_date - datetime.timedelta(days=random_number_of_days)

        return random_date


generic = Generic("en-gb")
generic.add_provider(JSONProvider)
generic.add_provider(TransactionDateProvider)

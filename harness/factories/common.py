import json
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


generic = Generic("en-gb")
generic.add_provider(JSONProvider)

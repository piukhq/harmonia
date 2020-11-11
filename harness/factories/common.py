import json
import random

import factory
from app import models
from app.db import SessionMaker
from faker.providers import BaseProvider as faker_baseprovider
from mimesis import Generic
from mimesis.providers.base import BaseProvider as mimesis_baseprovider
from sqlalchemy.orm import scoped_session

session = scoped_session(SessionMaker)
fake = factory.Faker


class TransactionStatusProvider(faker_baseprovider):
    @staticmethod
    def transaction_status():
        return random.choice([x for x in models.TransactionStatus])


class MatchedTransactionStatusProvider(faker_baseprovider):
    @staticmethod
    def matched_transaction_status():
        return random.choice([x for x in models.MatchedTransactionStatus])


class MatchingTypeProvider(faker_baseprovider):
    @staticmethod
    def matching_type():
        return random.choice([x for x in models.MatchingType])


fake.add_provider(TransactionStatusProvider)
fake.add_provider(MatchedTransactionStatusProvider)
fake.add_provider(MatchingTypeProvider)


class JSONProvider(mimesis_baseprovider):
    class Meta:
        name = "json_provider"

    @staticmethod
    def json():
        """
        Generate some random JSON, we don't care what's in it
        """
        data = {}
        for _ in range(5):
            data.update({generic.text.random.randstr(unique=True, length=10): generic.text.random.randstr(length=50)})

        return json.dumps(data)


generic = Generic("en-gb")
generic.add_provider(JSONProvider)

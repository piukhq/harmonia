import random

import factory
from app import models
from app.db import SessionMaker
from faker.providers import BaseProvider
from mimesis import Generic
from sqlalchemy.orm import scoped_session

session = scoped_session(SessionMaker)
fake = factory.Faker


class TransactionStatusProvider(BaseProvider):
    @staticmethod
    def transaction_status():
        return random.choice([x for x in models.TransactionStatus])


class MatchedTransactionStatusProvider(BaseProvider):
    @staticmethod
    def matched_transaction_status():
        return random.choice([x for x in models.MatchedTransactionStatus])


class MatchingTypeProvider(BaseProvider):
    @staticmethod
    def matching_type():
        return random.choice([x for x in models.MatchingType])


fake.add_provider(TransactionStatusProvider)
fake.add_provider(MatchedTransactionStatusProvider)
fake.add_provider(MatchingTypeProvider)
generic = Generic("en-gb")

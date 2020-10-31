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


fake.add_provider(TransactionStatusProvider)
generic = Generic("en-gb")

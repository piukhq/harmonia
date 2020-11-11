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
        Generate some random JSON, we don't care what's in it
        """
        data = {}
        for _ in range(5):
            data.update({generic.text.random.randstr(unique=True, length=10): generic.text.random.randstr(length=50)})

        return json.dumps(data)


generic = Generic("en-gb")
generic.add_provider(JSONProvider)

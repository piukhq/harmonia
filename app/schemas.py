from marshmallow import Schema, post_load

from app import models


class SchemeTransactionSchema(Schema):
    class Meta:
        fields = ('transaction_id', 'pence', 'points_earned', 'card_id', 'total_points',)

    @post_load
    def make_transaction(self, data):
        return models.SchemeTransaction(**data)

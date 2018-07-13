from marshmallow import Schema


class SchemeTransactionSchema(Schema):
    class Meta:
        fields = ('transaction_id', 'pence', 'points_earned', 'card_id', 'total_points',)

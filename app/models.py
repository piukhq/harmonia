from sqlalchemy import Column, Integer, String, DateTime, JSON

from app.db import Base, auto_repr

# import other module's models here to be recognised by alembic.
from app.imports.models import ImportTransaction  # noqa
from app import postgres


@auto_repr
class SchemeTransaction(Base):
    __tablename__ = 'scheme_transactions'

    id = Column(Integer, primary_key=True)
    provider_slug = Column(String(50), nullable=False)  # hermes scheme slug for the scheme that sent us the transaction
    mid = Column(String(50), nullable=False)  # merchant ID of the merchant/store this transaction originated from
    transaction_id = Column(String(100), nullable=False)  # unique identifier assigned by the provider
    transaction_date = Column(DateTime, nullable=False)  # date this transaction was originally made
    spend_amount = Column(Integer, nullable=False)  # the amount of money that was involved in the transaction
    spend_multiplier = Column(Integer, nullable=False)  # amount that spend_amount was multiplied by to make it integral
    spend_currency = Column(String(3), nullable=False)  # ISO 4217 alphabetic code for the currency involved
    points_amount = Column(Integer)  # number of points that were involved in the transaction
    points_multiplier = Column(Integer)  # amount points_amount was multiplied by to make it integral

    extra_fields = Column(JSON)  # any extra data used for exports

    created_at = Column(DateTime, server_default=postgres.utcnow())
    updated_at = Column(DateTime, onupdate=postgres.utcnow())


@auto_repr
class PaymentTransaction(Base):
    __tablename__ = 'payment_transactions'

    id = Column(Integer, primary_key=True)
    provider_slug = Column(String(50), nullable=False)  # hermes payment card slug for the provider of the transaction
    mid = Column(String(50), nullable=False)  # merchant ID of the merchant/store this transaction originated from
    transaction_id = Column(String(100), nullable=False)  # unique identifier assigned by the provider
    transaction_date = Column(DateTime, nullable=False)  # date this transaction was originally made
    spend_amount = Column(Integer, nullable=False)  # the amount of money that was involved in the transaction
    spend_multiplier = Column(Integer, nullable=False)  # amount that spend_amount was multiplied by to make it integral
    spend_currency = Column(String(3), nullable=False)  # ISO 4217 alphabetic code for the currency involved
    card_token = Column(String(100))  # token assigned to the card that was used

    extra_fields = Column(JSON)  # any extra data used for exports

    created_at = Column(DateTime, server_default=postgres.utcnow())
    updated_at = Column(DateTime, onupdate=postgres.utcnow())

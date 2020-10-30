import factory
from harness.factories.app import factories as app_factories
from harness.factories.app.exports import factories as exports_factories
from harness.factories.app.imports import factories as imports_factories
from harness.factories.common import session

LOYALTY_SCHEME_COUNT = 10
PAYMENT_PROVIDER_COUNT = 3
MERCHANT_IDENTIFIER_COUNT = 200


def bulk_load_db():
    # Create 10 random loyalty schemes
    app_factories.LoyaltySchemeFactory.create_batch(LOYALTY_SCHEME_COUNT)
    # Create our payment providers
    app_factories.PaymentProviderFactory.create_batch(
        PAYMENT_PROVIDER_COUNT, slug=factory.Iterator(["visa", "mastercard", "amex"])
    )
    session.commit()
    # Create 10000 random merchant ids
    app_factories.MerchantIdentifierFactory.create_batch(MERCHANT_IDENTIFIER_COUNT)
    session.commit()


def main():

    bulk_load_db()


if __name__ == "__main__":
    main()

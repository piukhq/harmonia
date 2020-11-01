import factory
from harness.factories.app import factories as app_factories
from harness.factories.app.exports import factories as exports_factories
from harness.factories.app.imports import factories as imports_factories
from harness.factories.common import session

LOYALTY_SCHEME_COUNT = 10
PAYMENT_PROVIDER_COUNT = 3
MERCHANT_IDENTIFIER_COUNT = 200
USER_IDENTITY_COUNT = 8
PAYMENT_TRANSACTION_COUNT = 1000
SCHEME_TRANSACTION_COUNT = 1000
MATCHED_TRANSACTION_COUNT = 100


def bulk_load_db():
    # Create 10 random loyalty schemes
    app_factories.LoyaltySchemeFactory.create_batch(LOYALTY_SCHEME_COUNT)
    # Create our payment providers
    app_factories.PaymentProviderFactory.create_batch(
        PAYMENT_PROVIDER_COUNT, slug=factory.Iterator(["visa", "mastercard", "amex"])
    )
    session.commit()
    # Create random merchant ids
    app_factories.MerchantIdentifierFactory.create_batch(MERCHANT_IDENTIFIER_COUNT)
    session.commit()
    # Create random users
    app_factories.UserIdentityFactory.create_batch(USER_IDENTITY_COUNT)
    session.commit()
    # Create payment transactions, linking to our users
    app_factories.PaymentTransactionFactory.create_batch(PAYMENT_TRANSACTION_COUNT)
    session.commit()
    # Create random scheme transactions
    app_factories.SchemeTransactionFactory.create_batch(SCHEME_TRANSACTION_COUNT)
    session.commit()
    # Create random matched transactions
    app_factories.MatchedTransactionFactory.create_batch(MATCHED_TRANSACTION_COUNT)
    session.commit()


def main():

    bulk_load_db()


if __name__ == "__main__":
    main()

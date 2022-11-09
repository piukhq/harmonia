from __future__ import annotations

import pendulum
import responses

import settings
from app import db, encryption, models
from app.feeds import FeedType
from app.imports.agents.mastercard import MastercardTGX2Settlement
from app.models import IdentifierType

settings.VAULT_URL = "https://vault"


def add_mock_routes():
    responses.add(
        "GET",
        f"{settings.VAULT_URL}/secrets/aes-keys/",
        json={"id": "http://test-123/a/b/c", "value": '{"AES_KEY": "value-123"}'},
    )


@responses.activate
def get_default_credentials(card_number, merchant_identifier, email):
    add_mock_routes()
    return encryption.encrypt_credentials(
        {
            "card_number": card_number,
            "merchant_identifier": merchant_identifier,
            "email": email,
        }
    )


class Default:
    transaction_id: str = "db0b14a3-0ca8-4281-9a77-57b5b88ec0a4"
    transaction_date: pendulum.DateTime = pendulum.now().in_timezone(pendulum.UTC)
    feed_type: FeedType = FeedType.AUTH
    identifier_type: IdentifierType = IdentifierType.PRIMARY
    primary_identifier: str = "test_primary_identifier"
    secondary_identifier: str = "test_secondary_identifier"
    psimi_identifier: str = "test_psimi_identifier"
    merchant_slug: str = "bpl-Trenette"
    loyalty_id: str = "test_loyalty_id"
    payment_provider_slug: str = "amex"
    settlement_key: str = "MjAwRUZGQTEtNkVGMC00MjEwLUIzN0ItMjkwNkE3NEI3RDEx"
    auth_code: str = "472624"
    match_group: str = "0fef514e-7b3c-4ea5-b8d0-22200a50536d"
    spend_amount: int = 55.66
    spend_multiplier: int = 100
    spend_currency: str = "GBP"
    card_token: str = "123456"
    user_id: int = 1
    user_token: str = "CqN58fD9MI1s7ePn0M5F1RxRu1P"
    card_number: str = "loyalty-123"
    email: str = "test-123@testbink.com"
    location: str = "Ascot"
    postcode: str = "SL5 9FE"
    scheme_account_id: int = 1
    third_party_id: str = "MjAwRUZGQ"
    credentials = get_default_credentials(
        card_number,
        primary_identifier,
        email,
    )


def add_item_to_database(session: db.Session, item):
    def add_item():
        session.add(item)
        session.commit()

    db.run_query(add_item, session=session, description="create settled transaction")


def get_or_create_loyalty_scheme(
    session: db.Session | None = None,
    slug: str = Default.merchant_slug,
) -> models.LoyaltyScheme:
    if session:
        loyalty_scheme, _ = db.get_or_create(models.LoyaltyScheme, slug=slug, session=session)
    else:
        loyalty_scheme = models.LoyaltyScheme(slug=slug)
    return loyalty_scheme


def get_or_create_payment_provider(
    session: db.Session | None = None,
    slug: str = Default.payment_provider_slug,
) -> models.PaymentProvider:
    if session:
        payment_provider, _ = db.get_or_create(models.PaymentProvider, slug=slug, session=session)
    else:
        payment_provider = models.LoyaltyScheme(slug=slug)
    return payment_provider


def create_merchant_identifier(
    session: db.Session | None = None,
    identifier: str = Default.primary_identifier,
    identifier_type: IdentifierType = Default.identifier_type,
    merchant_slug: str = Default.merchant_slug,
    payment_provider_slug: str = Default.payment_provider_slug,
    loyalty_scheme: models.LoyaltyScheme = None,
    payment_provider: models.PaymentProvider = None,
) -> models.MerchantIdentifier:
    merchant_identifier = models.MerchantIdentifier(
        identifier=identifier,
        identifier_type=identifier_type,
        loyalty_scheme=loyalty_scheme or get_or_create_loyalty_scheme(session=session, slug=merchant_slug),
        payment_provider=payment_provider
        or get_or_create_payment_provider(session=session, slug=payment_provider_slug),
        location=Default.location,
        postcode=Default.postcode,
    )
    if session:
        add_item_to_database(session, merchant_identifier)
    return merchant_identifier


def create_import_transaction(
    session: db.Session | None = None,
    transaction_id: str = Default.transaction_id,
    feed_type: FeedType = Default.feed_type,
    provider_slug: str = Default.payment_provider_slug,
    identified: bool = True,
    match_group: str = Default.match_group,
    **kwargs,
) -> models.ImportTransaction:
    import_transaction = models.ImportTransaction(
        transaction_id=transaction_id,
        feed_type=feed_type,
        provider_slug=provider_slug,
        match_group=match_group,
        identified=identified,
        **kwargs,
    )
    if session:
        add_item_to_database(session, import_transaction)
    return import_transaction


def create_transaction(
    session: db.Session | None = None,
    transaction_id: str = Default.transaction_id,
    feed_type: FeedType = Default.feed_type,
    status: str = "IMPORTED",
    merchant_identifier_ids: list[int] = [1],
    primary_identifier: str = Default.primary_identifier,
    merchant_slug: str = Default.merchant_slug,
    payment_provider_slug: str = Default.payment_provider_slug,
    match_group: str = Default.match_group,
    transaction_date: pendulum.DateTime = Default.transaction_date,
    spend_amount: int = Default.spend_amount,
    spend_multiplier: int = Default.spend_multiplier,
    spend_currency: str = Default.spend_currency,
    **kwargs,
) -> models.Transaction:
    transaction = models.Transaction(
        transaction_id=transaction_id,
        feed_type=feed_type,
        status=status,
        merchant_identifier_ids=merchant_identifier_ids,
        primary_identifier=primary_identifier,
        merchant_slug=merchant_slug,
        payment_provider_slug=payment_provider_slug,
        match_group=match_group,
        transaction_date=transaction_date,
        spend_amount=spend_amount,
        spend_multiplier=spend_multiplier,
        spend_currency=spend_currency,
        **kwargs,
    )
    if session:
        add_item_to_database(session, transaction)
    return transaction


def create_scheme_transaction(
    session: db.Session | None = None,
    merchant_identifier_ids: list[int] = [1],
    primary_identifier: str = Default.primary_identifier,
    provider_slug: str = Default.merchant_slug,
    payment_provider_slug: str = Default.payment_provider_slug,
    transaction_id: str = Default.transaction_id,
    transaction_date: pendulum.DateTime = Default.transaction_date,
    spend_amount: int = Default.spend_amount,
    spend_multiplier: int = Default.spend_multiplier,
    spend_currency: str = Default.spend_currency,
    **kwargs,
) -> models.SchemeTransaction:
    scheme_transaction = models.SchemeTransaction(
        merchant_identifier_ids=merchant_identifier_ids,
        primary_identifier=primary_identifier,
        provider_slug=provider_slug,
        payment_provider_slug=payment_provider_slug,
        transaction_id=transaction_id,
        transaction_date=transaction_date,
        spend_amount=spend_amount,
        spend_multiplier=spend_multiplier,
        spend_currency=spend_currency,
        **kwargs,
    )
    if session:
        add_item_to_database(session, scheme_transaction)
    return scheme_transaction


def create_payment_transaction(
    session: db.Session | None = None,
    merchant_identifier_ids: list[int] = [1],
    primary_identifier: str = Default.primary_identifier,
    provider_slug: str = Default.payment_provider_slug,
    transaction_id: str = Default.transaction_id,
    transaction_date: pendulum.DateTime = Default.transaction_date,
    spend_amount: int = Default.spend_amount,
    spend_multiplier: int = Default.spend_multiplier,
    spend_currency: str = Default.spend_currency,
    card_token: str = Default.card_token,
    **kwargs,
) -> models.PaymentTransaction:
    payment_transaction = models.PaymentTransaction(
        merchant_identifier_ids=merchant_identifier_ids,
        primary_identifier=primary_identifier,
        provider_slug=provider_slug,
        transaction_id=transaction_id,
        transaction_date=transaction_date,
        spend_amount=spend_amount,
        spend_multiplier=spend_multiplier,
        spend_currency=spend_currency,
        card_token=card_token,
        **kwargs,
    )
    if session:
        add_item_to_database(session, payment_transaction)
    return payment_transaction


def create_export_transaction(
    session: db.Session | None = None,
    transaction_id: str = Default.transaction_id,
    provider_slug: str = Default.merchant_slug,
    transaction_date: pendulum.DateTime = Default.transaction_date,
    spend_amount: int = Default.spend_amount,
    spend_currency: str = Default.spend_currency,
    loyalty_id: str = Default.loyalty_id,
    mid: str = Default.primary_identifier,
    primary_identifier: str = Default.primary_identifier,
    user_id: int = Default.user_id,
    scheme_account_id: int = Default.scheme_account_id,
    credentials: str = Default.credentials,
    **kwargs,
) -> models.ExportTransaction:
    export_transaction = models.ExportTransaction(
        transaction_id=transaction_id,
        provider_slug=provider_slug,
        transaction_date=transaction_date,
        spend_amount=spend_amount,
        spend_currency=spend_currency,
        loyalty_id=loyalty_id,
        mid=mid,
        primary_identifier=primary_identifier,
        user_id=user_id,
        scheme_account_id=scheme_account_id,
        credentials=credentials,
        **kwargs,
    )
    if session:
        add_item_to_database(session, export_transaction)
    return export_transaction


class SampleTransactions:
    def amex_auth(self):
        return {
            "approval_code": "472624",
            "cm_alias": "CqN58fD9MI1s7ePn0M5F1RxRu1P",
            "merchant_number": Default.primary_identifier,
            "offer_id": "0",
            "transaction_amount": Default.spend_amount,
            "transaction_currency": "UKL",
            "transaction_id": "Qzg0Q0FBQzctRTJDMS00RUFGLTkyQTEtRTRDQzZEMEI1MTk5",
            "transaction_time": "2022-11-04 08:55:50",
        }

    def amex_settlement(self):
        return {
            "approvalCode": "472624",
            "cardToken": "CqN58fD9MI1s7ePn0M5F1RxRu1P",
            "currencyCode": "840",
            "dpan": "123456XXXXX7890",
            "merchantNumber": Default.primary_identifier,
            "offerId": "0",
            "partnerId": "AADP0050",
            "recordId": "NUE3QTUyNzktMDFEMi00ODQwLUI5NDItRTkzQjMwNUQ0QTBBAADP00400",
            "transactionAmount": Default.spend_amount,
            "transactionDate": "2022-11-04 15:55:50",
            "transactionId": "NUE3QTUyNzktMDFEMi00ODQwLUI5NDItRTkzQjMwNUQ0QTBB",
        }

    def mastercard_auth(
            self,
            amount: int = Default.spend_amount*100,
            currency_code: str = Default.spend_currency,
            mid: str = Default.primary_identifier,
            payment_card_token: str = Default.card_token,
            third_party_id: str = Default.third_party_id,
            time: str = Default.transaction_date
    ):
        return {
            "amount": amount,
            "currency_code": currency_code,
            "mid": mid,
            "payment_card_token": payment_card_token,
            "third_party_id": third_party_id,
            "time": time,
        }

    def mastercard_settlement_file(self):
        return b'H20221104164125      mastercard-tgx2-settlement.txt\n        ' \
               b'D                    CqN58fD9MI1s7ePn0M5F1RxRu1P                                                  ' \
               b'    20221104                                                                                      ' \
               b'                                                                                                  ' \
               b'                                                                                                  ' \
               b'                                                           test_primary_id                        ' \
               b'                            000000005566                                 1555472624               ' \
               b'                                                                                                  ' \
               b'                                                                           MjAwRUZGQ\n        ' \
               b'T20221104164125      mastercard-tgx2-settlement.txt '
        # return """H20221104164125      mastercard-tgx2-settlement.txt
        # D                    CqN58fD9MI1s7ePn0M5F1RxRu1P                                                      20221104                                                                                                                                                                                                                                                                                                                                                     test_primary_id                                                    000000005566                                 1555472624                                                                                                                                                                                            MjAwRUZGQ
        # T20221104164125      mastercard-tgx2-settlement.txt """

    def mastercard_settlement(self):
        transaction = []
        for item in MastercardTGX2Settlement().yield_transactions_data(self.mastercard_settlement_file()):
            transaction.append(item)
            yield
        return transaction

    def visa_auth(
        self,
        transaction_id: str = Default.transaction_id,
        transaction_date: str = pendulum.instance(Default.transaction_date).isoformat(),
        primary_identifier: str = Default.primary_identifier,
        secondary_identifier: str = Default.secondary_identifier,
        psimi_identifier: str = Default.psimi_identifier,
        user_token: str = Default.user_token,
        spend_amount: int = Default.spend_amount,
        auth_code: str = Default.auth_code,
    ):
        return {
            "CardId": transaction_id[0:9],
            "ExternalUserId": user_token,
            "MessageElementsCollection": [
                {"Key": "Transaction.MerchantCardAcceptorId", "Value": primary_identifier},
                {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
                {"Key": "Transaction.TransactionAmount", "Value": str(spend_amount)},
                {"Key": "Transaction.VipTransactionId", "Value": transaction_id},
                {"Key": "Transaction.VisaMerchantName", "Value": ""},
                {"Key": "Transaction.VisaMerchantId", "Value": psimi_identifier},
                {"Key": "Transaction.VisaStoreName", "Value": ""},
                {"Key": "Transaction.VisaStoreId", "Value": secondary_identifier},
                {"Key": "Transaction.CurrencyCodeNumeric", "Value": "840"},
                {"Key": "Transaction.BillingCurrencyCode", "Value": "840"},
                {"Key": "Transaction.USDAmount", "Value": str(spend_amount)},
                {"Key": "Transaction.MerchantLocalPurchaseDate", "Value": "2022-11-04"},
                {"Key": "Transaction.MerchantGroup.0.Name", "Value": "TEST_MG"},
                {"Key": "Transaction.MerchantGroup.0.ExternalId", "Value": "Trenette"},
                {"Key": "Transaction.AuthCode", "Value": auth_code},
                {"Key": "Transaction.PanLastFour", "Value": "7890"},
                {"Key": "Transaction.MerchantDateTimeGMT", "Value": "2022-11-04 15:55:50"},
                {"Key": "Transaction.BillingAmount", "Value": str(spend_amount)},
                {"Key": "Transaction.TimeStampYYMMDD", "Value": transaction_date},
                {"Key": "Transaction.SettlementDate", "Value": ""},
                {"Key": "Transaction.SettlementAmount", "Value": "0"},
                {"Key": "Transaction.SettlementCurrencyCodeNumeric", "Value": "0"},
                {"Key": "Transaction.SettlementBillingAmount", "Value": "0"},
                {"Key": "Transaction.SettlementBillingCurrency", "Value": ""},
                {"Key": "Transaction.SettlementUSDAmount", "Value": "0"},
            ],
            "MessageId": "863FD84E-B7F4-4F9C-A0DF-887CB5DC6A7F",
            "MessageName": "AuthMessageTest",
            "UserDefinedFieldsCollection": [{"Key": "TransactionType", "Value": "Auth"}],
            "UserProfileId": "302EBB9B-8ED8-41AD-B673-33DF5B5BD796",
        }

    def visa_settlement(
        self,
        transaction_id: str = Default.transaction_id,
        transaction_date: pendulum.DateTime = Default.transaction_date,
        primary_identifier: str = Default.primary_identifier,
        secondary_identifier: str = Default.secondary_identifier,
        psimi_identifier: str = Default.psimi_identifier,
        user_token: str = Default.user_token,
        spend_amount: int = Default.spend_amount,
        auth_code: str = Default.auth_code,
    ):
        return {
            "CardId": transaction_id[0:9],
            "ExternalUserId": user_token,
            "MessageElementsCollection": [
                {"Key": "Transaction.MerchantCardAcceptorId", "Value": primary_identifier},
                {"Key": "Transaction.MerchantAcquirerBin", "Value": "3423432"},
                {"Key": "Transaction.TransactionAmount", "Value": str(spend_amount)},
                {"Key": "Transaction.VipTransactionId", "Value": transaction_id},
                {"Key": "Transaction.VisaMerchantName", "Value": ""},
                {"Key": "Transaction.VisaMerchantId", "Value": psimi_identifier},
                {"Key": "Transaction.VisaStoreName", "Value": ""},
                {"Key": "Transaction.VisaStoreId", "Value": secondary_identifier},
                {"Key": "Transaction.CurrencyCodeNumeric", "Value": "840"},
                {"Key": "Transaction.BillingCurrencyCode", "Value": "840"},
                {"Key": "Transaction.USDAmount", "Value": str(spend_amount)},
                {"Key": "Transaction.MerchantLocalPurchaseDate", "Value": "2022-11-04"},
                {"Key": "Transaction.MerchantGroup.0.Name", "Value": "TEST_MG"},
                {"Key": "Transaction.MerchantGroup.0.ExternalId", "Value": "Trenette"},
                {"Key": "Transaction.AuthCode", "Value": auth_code},
                {"Key": "Transaction.PanLastFour", "Value": "7890"},
                {"Key": "Transaction.MerchantDateTimeGMT", "Value": transaction_date.isoformat()},
                {"Key": "Transaction.BillingAmount", "Value": str(spend_amount)},
                {"Key": "Transaction.TimeStampYYMMDD", "Value": pendulum.instance(transaction_date).isoformat()},
                {"Key": "Transaction.SettlementDate", "Value": pendulum.now().isoformat()},
                {"Key": "Transaction.SettlementAmount", "Value": str(spend_amount)},
                {"Key": "Transaction.SettlementCurrencyCodeNumeric", "Value": "826"},
                {"Key": "Transaction.SettlementBillingAmount", "Value": str(spend_amount)},
                {"Key": "Transaction.SettlementBillingCurrency", "Value": "826"},
                {"Key": "Transaction.SettlementUSDAmount", "Value": str(spend_amount)},
            ],
            "MessageId": "DBF0F66C-8C8B-474A-B70A-8E1775FDE747",
            "MessageName": "AuthMessageTest",
            "UserDefinedFieldsCollection": [{"Key": "TransactionType", "Value": "Settle"}],
            "UserProfileId": "24F97CF4-255D-4050-989B-825E2112F5CA",
        }

    def visa_refund(
        self,
        transaction_id: str = Default.transaction_id,
        transaction_date: pendulum.DateTime = Default.transaction_date,
        primary_identifier: str = Default.primary_identifier,
        secondary_identifier: str = Default.secondary_identifier,
        psimi_identifier: str = Default.psimi_identifier,
        user_token: str = Default.user_token,
        spend_amount: int = Default.spend_amount,
        auth_code: str = Default.auth_code,
        settlement_key: str = Default.settlement_key,
    ):
        return {
            "CardId": transaction_id[0:9],
            "ExternalUserId": user_token,
            "MessageElementsCollection": [
                {"Key": "ReturnTransaction.CardAcceptorIdCode", "Value": primary_identifier},
                {"Key": "ReturnTransaction.AcquirerBIN", "Value": "3423432"},
                {"Key": "ReturnTransaction.Amount", "Value": str(spend_amount)},
                {"Key": "ReturnTransaction.VipTransactionId", "Value": transaction_id},
                {"Key": "ReturnTransaction.SettlementId", "Value": settlement_key},
                {"Key": "ReturnTransaction.VisaMerchantName", "Value": ""},
                {"Key": "ReturnTransaction.VisaMerchantId", "Value": psimi_identifier},
                {"Key": "ReturnTransaction.VisaStoreName", "Value": ""},
                {"Key": "ReturnTransaction.VisaStoreId", "Value": secondary_identifier},
                {"Key": "ReturnTransaction.AcquirerAmount", "Value": str(spend_amount)},
                {"Key": "ReturnTransaction.AcquirerCurrencyCode", "Value": "840"},
                {"Key": "ReturnTransaction.CurrencyCode", "Value": "840"},
                {"Key": "ReturnTransaction.TransactionUSDAmount", "Value": str(spend_amount)},
                {
                    "Key": "ReturnTransaction.DateTime",
                    "Value": pendulum.instance(transaction_date).format("M/D/YYYY h:m:s A"),
                },
                {"Key": "ReturnTransaction.MerchantGroup.0.Name", "Value": "TEST_MG"},
                {"Key": "ReturnTransaction.MerchantGroupName.0.ExternalId", "Value": "Trenette"},
                {"Key": "ReturnTransaction.AuthCode", "Value": auth_code},
            ],
            "MessageId": "AF9D1B43-17C6-44AE-B572-714B2DB416DD",
            "MessageName": "AuthMessageTest",
            "UserDefinedFieldsCollection": [{"Key": "TransactionType", "Value": "RETURN"}],
            "UserProfileId": "7CB803CB-39EF-4CFC-9251-0A23F7016C22",
        }

    # Amex, MasterCard/MasterCard One or Visa
    iceland = f"""TransactionCardFirst6,TransactionCardLast4,TransactionCardExpiry,TransactionCardSchemeId,TransactionCardScheme,TransactionStore_Id,TransactionTimestamp,TransactionAmountValue,TransactionAmountUnit,TransactionCashbackValue,TransactionCashbackUnit,TransactionId,TransactionAuthCode
    123456,7890,01/80,1,Amex,{Default.primary_identifier},2022-11-04 15:55:50,{Default.spend_amount/100,},{Default.spend_currency},.00,{Default.spend_currency},1522A4E9-C7D6-4FD3-BA20-A496E1052F74,472624"""
    # American Express, Mastercard or Visa
    wasabi = f"""Store No_,Entry No_,Transaction No_,Tender Type,Amount,Card Number,Card Type Name,Auth_code,Authorisation Ok,Date,Time,EFT Merchant No_,Receipt No_
    A076,0,NUE3QTUyNzktMDFEMi00ODQwLUI5NDItRTkzQjMwNUQ0QTBB,3,{Default.spend_currency},123456******7890,American Express,472624,1,04/11/2022,15:55:50,{Default.primary_identifier},NUE3QTUyNzktMDFEMi00ODQwLUI5NDItRTkzQjMwNUQ0QTBB"""

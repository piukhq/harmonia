import responses

from app.exports.agents.iceland import Iceland
import settings
from app import encryption

settings.EUROPA_URL = "http://europa"
settings.ATLAS_URL = "http://atlas"
settings.VAULT_URL = "http://vault"
settings.VAULT_TOKEN = ""

MOCK_URL = "http://iceland.test"


def add_mock_routes():
    responses.add(
        "GET",
        f"{settings.EUROPA_URL}/configuration",
        json={
            "merchant_url": f"{MOCK_URL}/",
            "integration_service": 0,
            "retry_limit": 100,
            "log_level": 0,
            "callback_url": f"{MOCK_URL}/callback",
            "country": "uk",
            "security_credentials": {
                "outbound": {"credentials": [{"storage_key": "test1"}]},
                "inbound": {"credentials": [{"storage_key": "test2"}]},
            },
        },
    )

    responses.add("GET", f"{settings.VAULT_URL}/v1/secret/data/test1", json={"data": {"data": {"value": "test3"}}})
    responses.add("GET", f"{settings.VAULT_URL}/v1/secret/data/test2", json={"data": {"data": {"value": "test4"}}})


class Expected:
    request_data = {
        "message_uid": "cda38736-0251-11ea-9936-3af9d3be8080",
        "transactions": [
            {
                "record_uid": "o219ly03jorvmnxz0rw8z7qxpgkd5e4x",
                "merchant_scheme_id1": "o219ly03jorvmnxz0rw8z7qxpgkd5e4x",
                "merchant_scheme_id2": "35573492",
                "transaction_id": "0000943_YF4OTBJP37",
            },
            {
                "record_uid": "jjzl2gem71540nem1dwyq98prdkvo3x7",
                "merchant_scheme_id1": "jjzl2gem71540nem1dwyq98prdkvo3x7",
                "merchant_scheme_id2": "96553073",
                "transaction_id": "0003975_7KB63BB6Y7",
            },
        ],
    }
    request_json = {
        "json": {
            "message_uid": "cda38736-0251-11ea-9936-3af9d3be8080",
            "transactions": [
                {
                    "record_uid": "o219ly03jorvmnxz0rw8z7qxpgkd5e4x",
                    "merchant_scheme_id1": "o219ly03jorvmnxz0rw8z7qxpgkd5e4x",
                    "merchant_scheme_id2": "35573492",
                    "transaction_id": "0000943_YF4OTBJP37",
                },
                {
                    "record_uid": "jjzl2gem71540nem1dwyq98prdkvo3x7",
                    "merchant_scheme_id1": "jjzl2gem71540nem1dwyq98prdkvo3x7",
                    "merchant_scheme_id2": "96553073",
                    "transaction_id": "0003975_7KB63BB6Y7",
                },
            ],
        },
        "headers": {"Authorization": "Signature my_signature_ok", "X-REQ-TIMESTAMP": "1573236127"},
    }
    formatted_transaction = [
        {
            "record_uid": "voydgerxzp4k97w0pn0q2lo183j5mvjx",
            "merchant_scheme_id1": "vryp7xv4l2ejg36p0nmk1qd0z5o89rlp",
            "merchant_scheme_id2": 10,
            "transaction_id": 1,
        },
        {
            "record_uid": "voydgerxzp4k97w0pn0q2lo183j5mvjx",
            "merchant_scheme_id1": "vryp7xv4l2ejg36p0nmk1qd0z5o89rlp",
            "merchant_scheme_id2": 20,
            "transaction_id": 2,
        },
    ]
    response_error_codes = {
        "error_codes": [{"code": "VALIDATION", "description": "Card number must be provided"}],
        "message_uid": "d07fa702-3e5f-11e9-a0ff-f2ddecdc4819",
    }
    response_internal_server_error = {
        "Type": "ServiceException",
        "Code": "InternalServerError",
        "Description": 'Cannot open database "Synch" requested by the login. '
        "The login failed.\r\nLogin failed for user 'Ice_Api'.",
    }


class Response:
    def __init__(self, response):
        self.response = response

    def json(self):
        return self.response


class ResponseNoContent:
    def __init__(self, response):
        self.response = response


class UserIdentity:
    def __init__(self, scheme_account_id, user_id, credentials):
        self.scheme_account_id = scheme_account_id
        self.user_id = user_id
        self.credentials = credentials

    @property
    def decrypted_credentials(self):
        return encryption.decrypt_credentials(self.credentials)


class MerchantIdentifier:
    def __init__(self, mid):
        self.mid = mid


class MockPaymentTransaction:
    def __init__(self, user_identity):
        self.user_identity = user_identity


class MockMatchedTransaction:
    def __init__(self, transaction_id, scheme_account_id, user_id, merchant_identifier):
        self.transaction_id = transaction_id
        mock_credentials = {"card_number": "loyalty-123", "merchant_identifier": merchant_identifier}
        mock_credentials = encryption.encrypt_credentials(mock_credentials)
        identity = UserIdentity(scheme_account_id, user_id, mock_credentials)
        self.payment_transaction = MockPaymentTransaction(identity)


@responses.activate
def test_format_transactions() -> None:
    add_mock_routes()
    transactions = [MockMatchedTransaction(1, 2, 3, 10), MockMatchedTransaction(2, 2, 3, 20)]

    iceland = Iceland()
    formatted_transaction = iceland.format_transactions(transactions)

    assert formatted_transaction == Expected.formatted_transaction

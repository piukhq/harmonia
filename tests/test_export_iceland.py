from app.exports.agents.iceland import Iceland


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
            "merchant_scheme_id1": "voydgerxzp4k97w0pn0q2lo183j5mvjx",
            "merchant_scheme_id2": 10,
            "transaction_id": 1,
        },
        {
            "record_uid": "voydgerxzp4k97w0pn0q2lo183j5mvjx",
            "merchant_scheme_id1": "voydgerxzp4k97w0pn0q2lo183j5mvjx",
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
    def __init__(self, scheme_account_id):
        self.scheme_account_id = scheme_account_id


class MerchantIdentifier:
    def __init__(self, mid):
        self.mid = mid


class MockTransaction:
    def __init__(self, transaction_id, scheme_account_id, mid):
        self.transaction_id = transaction_id
        self.user_identity = UserIdentity(scheme_account_id)
        self.merchant_identifier = MerchantIdentifier(mid)


def test_request_data() -> None:
    iceland = Iceland()
    request_data = iceland.format_request(Expected.request_data)

    assert request_data.keys() == Expected.request_json.keys()


def test_format_transactions() -> None:
    transactions = [MockTransaction(1, 2, 10), MockTransaction(2, 2, 20)]

    iceland = Iceland()
    formatted_transaction = iceland.format_transactions(transactions)

    assert formatted_transaction == Expected.formatted_transaction


def test_check_response_error_codes() -> None:
    response = Response(Expected.response_error_codes)
    expected = Expected.response_error_codes
    iceland = Iceland()
    try:
        iceland.check_response(response)

    except Exception as error:
        error_response = error

    assert str(expected["error_codes"]) in str(error_response)


def test_check_response_error_codes_internal_server_error() -> None:
    response = ResponseNoContent(Expected.response_internal_server_error)
    iceland = Iceland()
    try:
        iceland.check_response(response)

    except Exception as error:
        error_response = error

    assert "no attribute" in str(error_response)

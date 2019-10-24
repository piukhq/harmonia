from app.exports.agents.cooperative import Cooperative


class Expected:
    credentials = {
        "card_number": "7188567b-0b89-4137-abe9-7fc22ebe4fb9",
        "email": "email=bv@gmail.com",
        "password": "1234567",
        "consents": [],
    }
    encrypted_credentials = (
        "BWr24pEVTxyIlxBpoAokfuf0C8ZLEh55rvehyaRBbGgPaHSZNHEU"
        "3oWb/peQhLF/nq4Unpk5PT6qm0CynVWC2O6tLEuefF44niRWdTA4"
        "T7/CrwjLugupcGMw/jPnFat5bFg0ptRpLFLQ3mtF1UQqklz9JZpF"
        "O6rUtCs16WVDkf9LP1oRpkLmiLc1A/hA5knM"
    )
    json_data = {
        "message_uid": "fed057de-f582-11e9-9173-3af9d3be8080",
        "transactions": [
            {
                "record_uid": "fed02a52-f582-11e9-9173-3af9d3be8080",
                "member_id": 8,
                "card_number": "37f140b3-8b5b-4686-b339-9be35ba71fbe",
                "transaction_id": "7deec56b-9ba5-11e9-9b02-3d3e2f734b26-1",
            },
            {
                "record_uid": "fed0569e-f582-11e9-9173-3af9d3be8080",
                "member_id": 7,
                "card_number": "10d58d42-ff8d-41b4-9c02-29f87193f6bc",
                "transaction_id": "7deec56b-9ba5-11e9-9b02-3d3e2f734b26-2",
            },
        ],
    }
    request_data = {
        "json": {
            "message_uid": "fed057de-f582-11e9-9173-3af9d3be8080",
            "transactions": [
                {
                    "record_uid": "fed02a52-f582-11e9-9173-3af9d3be8080",
                    "member_id": 8,
                    "card_number": "37f140b3-8b5b-4686-b339-9be35ba71fbe",
                    "transaction_id": "7deec56b-9ba5-11e9-9b02-3d3e2f734b26-1",
                },
                {
                    "record_uid": "fed0569e-f582-11e9-9173-3af9d3be8080",
                    "member_id": 7,
                    "card_number": "10d58d42-ff8d-41b4-9c02-29f87193f6bc",
                    "transaction_id": "7deec56b-9ba5-11e9-9b02-3d3e2f734b26-2",
                },
            ],
        },
        "headers": {"Authorization": "my_mock_prefix my_signature_ok", "X-API-KEY": "my_mock_api_key"},
    }


def test_decrypt_credentials() -> None:
    cooperative = Cooperative()
    credentials_result = cooperative.decrypt_credentials(Expected.encrypted_credentials)
    assert credentials_result == Expected.credentials


def test_request_data() -> None:
    cooperative = Cooperative()
    request_data = cooperative.build_request_data(Expected.json_data)
    assert request_data == Expected.request_data

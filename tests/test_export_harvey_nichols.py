from app.exports.agents.harvey_nichols import HarveyNichols


class Expected:
    credentials = {
        "card_number": "feada0e6-c76e-4a62-952b-39188bb35abd",
        "email": "email=bv@gmail.com",
        "password": "1234567",
        "consents": [],
    }
    encrypted_credentials = (
        "HhBCeQgQQFXF+taUWAXHESLTeKinlhSILHdpT2vFKqi8"
        "j/OLSXSEaY8B85c+Fh3wZeKpuyobzohJCCRlStUmcR4f"
        "QlBiHATfYLw89ExPJ+5ErhdJdvIbVn1mycuhqPo9LqZC"
        "vRh1NdcbehlCDDVEWgPPWZpZrtlHxMNwUIpu5wX/KAeV"
        "2WpCIB1bnyRLjAN2"
    )
    token = "abc1234567abc"
    transaction_id = 1
    export_data = {
        "CustomerClaimTransactionRequest": {
            "token": token,
            "customerNumber": credentials["card_number"],
            "id": transaction_id,
        }
    }


def test_decrypt_credentials() -> None:
    harvey_nichols = HarveyNichols()
    credentials_result = harvey_nichols.decrypt_credentials(Expected.encrypted_credentials)
    assert credentials_result == Expected.credentials

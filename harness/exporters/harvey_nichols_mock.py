import requests

from app.reporting import get_logger
from app.core.requests_retry import requests_retry_session
from app.exports.agents import AgentExportData
from unittest.mock import Mock
from requests.models import Response

log = get_logger("harvey-nichols")


class HarveyNicholsMockAPI:
    """Mock Harvey Nichols API responses

    This is a mock claim transaction method to allow testing of the Harvey Nichols ClaimTransaction
    endpoint process, without actually calling Harvey Nichols's services.

    Ensure your .env file has TXM_DEBUG=true to use the mock
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def claim_transaction(self, export_data: AgentExportData, body: dict) -> requests.Response:
        export_data = export_data
        body = body
        response = Mock(spec=Response)

        response.json.return_value = {"CustomerClaimTransactionResponse": {"outcome": "Success"}}

        # response.json.return_value = {
        #     "CustomerClaimTransactionResponse": {
        #         "errorDetails": {
        #             "errorCode": "AlreadyAssigned",
        #             "messageText": "Transaction already assigned to the customer"
        #         },
        #         "outcome": "AlreadyAssigned"
        #     }
        # }

        response.status_code = 200
        return response

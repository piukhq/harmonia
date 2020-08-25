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

    Ensure your .env file has the follwoing settings for using the mock:
    TXM_SIMULATE_EXPORTS=false
    TXM_DEVELOPMENT=true

    """
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.session = requests_retry_session()

    def claim_transaction(self, export_data: AgentExportData, body: dict) -> requests:
        export_data = export_data
        body = body
        response = Mock(spec=Response)
        response.json.return_value = {"outcome": "success"}
        response.status_code = 200

        '''Sample AlreadyAssigned response
        
        response = {"errorDetails": {"messageText":
        "Transaction already assigned to the customer", "errorCode": "AlreadyAssigned"}, "outcome": "AlreadyAssigned"}
        
        '''
        return response

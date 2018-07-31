import inspect

from app.imports.agents.bases.active_api_agent import ActiveAPIAgent
from app.config import ConfigValue, KEY_PREFIX


SCHEDULE = f"{KEY_PREFIX}imports.agents.iceland.schedule"


class IcelandAPIAgent(ActiveAPIAgent):
    url = 'https://test.iceland/api/transactions'
    serializer_class = 'IcelandTransactionSerializer'

    class Config:
        schedule = ConfigValue(SCHEDULE, default='* * * * *')

    def help(self):
        return inspect.cleandoc(
            f"""
            This is the Iceland API import agent.
            It calls the Iceland API on a schedule and inserts new transactions
            into the transaction matching system.
            The current schedule is "{self.Config.schedule}".
            """)

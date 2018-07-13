import inspect

from .bases.active_api_agent import ActiveAPIAgent
from app.config import ConfigValue, KEY_PREFIX


SCHEDULE = f"{KEY_PREFIX}imports.agents.irg.schedule"


class IRGAPIAgent(ActiveAPIAgent):
    url = 'https://test.irg/api/transactions'
    serializer_class = 'IRGTransactionSerializer'

    class Config:
        schedule = ConfigValue(SCHEDULE, default='*/3 * * * *')

    def help(self):
        return inspect.cleandoc(
            f"""
            This is the IRG API import agent.
            It calls the IRG API on a schedule and inserts new transactions
            into the transaction matching system.
            The current schedule is "{self.Config.schedule}".
            """)

    def do_import(self):
        pass

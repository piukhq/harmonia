import inspect


class BaseAgent:
    def help(self):
        return inspect.cleandoc(
            """
            This is a new import agent.
            Implement all the required methods (see app/import/agent.py) and
            override this help method to provide specific information.
            """)

    def run(self, immediate=False):
        raise NotImplementedError(inspect.cleandoc(
            """
            Override the run method in your agent to act as the main entry point
            into the import process.
            """))

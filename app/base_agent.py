class BaseAgent:
    def help(self) -> str:
        raise NotImplementedError

    def run(self, *, once: bool = False):
        raise NotImplementedError

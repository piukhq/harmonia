import typing as t


class BaseImportDataProvider:
    def provide(self, fixture: dict) -> t.List[dict]:
        raise NotImplementedError("provide(fixture) must be overridden by subclasses!")

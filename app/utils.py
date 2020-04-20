import typing as t


class classproperty:
    def __init__(self, method=None):
        self.fget = method

    def __get__(self, instance, cls=None):
        return self.fget(cls)


def missing_property(t: t.Type, prop: str) -> t.NoReturn:
    """
    Useful for ensuring a given property exists on a subclass,
    and providing a helpful error if it does not.
    """
    raise NotImplementedError(f"{t.__name__} is missing a required property: {prop}")

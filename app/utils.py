import typing as t


def missing_property(t: t.Type, prop: str) -> t.NoReturn:
    """
    Useful for ensuring a given property exists on a subclass,
    and providing a helpful error if it does not.
    """
    raise NotImplementedError(f"{t.__name__} is missing a required property: {prop}")

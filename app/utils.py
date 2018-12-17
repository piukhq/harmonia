import typing as t

import marshmallow
import pendulum


def missing_property(obj: object, prop: str) -> t.NoReturn:
    """Useful for ensuring a given property exists on a subclass, and providing a helpful error if it does not."""
    raise NotImplementedError(
        f"{type(obj).__name__} is missing a required property: {prop}"
    )


def file_split(fd: t.IO, *, sep: str, buf_size: int = 1024) -> t.Iterable[str]:
    buf = ""
    while True:
        data = fd.read(buf_size)
        if not data:
            break
        parts = data.split(sep)
        if len(parts) > 1:
            yield buf + parts[0]
            buf = parts[-1]
            for part in parts[1:-1]:
                yield part
        else:
            buf += data
    if buf:
        yield buf


class PendulumField(marshmallow.fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return pendulum.DateTime()
        return value.isoformat()

    def _deserialize(self, value, attr, data, **kwargs):
        return pendulum.parse(value)

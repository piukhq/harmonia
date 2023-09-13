import datetime
import decimal
import json

import pendulum


def _default(val):
    if isinstance(val, pendulum.DateTime):
        return {"__type__": "pendulum.DateTime", "epoch": val.int_timestamp}
    elif isinstance(val, datetime.datetime):
        return {"__type__": "pendulum.DateTime", "epoch": int(val.timestamp())}
    elif isinstance(val, decimal.Decimal):
        return {"__type__": "decimal.Decimal", "repr": str(val)}

    raise TypeError(
        f"Custom serializer can't handle {type(val).__name__} ({val}) yet! You can add support in {__file__}."
    )


def _object_hook(val):
    if not isinstance(val, dict) or "__type__" not in val:
        return val

    t = val["__type__"]
    if t == "pendulum.DateTime":
        return pendulum.from_timestamp(val["epoch"])
    elif t == "decimal.Decimal":
        return decimal.Decimal(val["repr"])

    raise TypeError(
        f"Custom deserializer can't handle {type(val).__name__} ({val}) yet! You can add support in {__file__}."
    )


def dumps(d):
    return json.dumps(d, default=_default)


def loads(s):
    return json.loads(s, object_hook=_object_hook)

from datetime import datetime
from decimal import Decimal
import json

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import settings


def _default(val):
    if isinstance(val, datetime):
        return {
            '__type__': 'datetime',
            'epoch': val.timestamp(),
        }
    elif isinstance(val, Decimal):
        return {
            '__type__': 'Decimal',
            'repr': str(val),
        }

    raise TypeError(f"custom serializer can't handle {type(val).__name__} ({val}) yet! "
                    f"you can add support in {__file__}")


def _object_hook(val):
    if not isinstance(val, dict) or '__type__' not in val:
        return val

    t = val['__type__']
    if t == 'datetime':
        return datetime.fromtimestamp(t['epoch'])
    elif t == 'Decimal':
        return Decimal(val['repr'])

    raise TypeError(f"custom deserializer can't handle {type(val).__name__} ({val}) yet! "
                    f"you can add support in {__file__}")


def _dumps(d):
    return json.dumps(d, default=_default)


def _loads(s):
    return json.loads(s, object_hook=_object_hook)


db_engine = create_engine(settings.POSTGRES_DSN, json_serializer=_dumps, json_deserializer=_loads)
Session = sessionmaker(bind=db_engine)

Base = declarative_base()


def auto_repr(cls):
    """Generates a __repr__ method for the wrapped class that contains all the member variables"""

    def __repr__(self):
        print(vars(self))
        return '{}({})'.format(
            type(self).__name__, ', '.join(f"{k}={repr(v)}" for k, v in vars(self).items() if not k.startswith('_')))

    cls.__repr__ = __repr__
    return cls

import typing as t
from decimal import Decimal


def to_pennies(amount: t.Union[float, str]) -> int:
    """
    Takes an amount in pounds and converts it to an integer number of pennies.

    We convert the input to a string to avoid any nasty rounding errors:
    >>> Decimal(12.34)
    Decimal('12.339999999999999857891452847979962825775146484375')

    >>> Decimal(str(12.34))
    Decimal('12.34')
    """
    return int(Decimal(str(amount)) * 100)


def to_pounds(pennies: int) -> str:
    return str(Decimal(pennies) / 100)

from decimal import Decimal


def to_pennies(amount: str) -> int:
    return int(Decimal(amount) * 100)


def to_pounds(pennies: int) -> str:
    return str(Decimal(pennies) / 100)

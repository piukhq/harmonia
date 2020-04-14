from decimal import Decimal


def to_pennies(amount: float) -> int:
    return int(Decimal(amount * 100))


def to_pounds(pennies: int) -> float:
    return float(Decimal(pennies) / 100)

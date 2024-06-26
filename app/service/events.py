import typing as t

from blinker import signal

from app.data_warehouse.models import send_unexported_transaction


def connect_signals() -> None:
    signal("unexported-transaction").connect(unexported_transaction)


def unexported_transaction(sender: t.Union[object, str], transactions: list) -> None:
    send_unexported_transaction(transactions)

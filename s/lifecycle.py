#! /usr/bin/env python3
import typing as t
import inspect

import click

from app.db import session, Base
from app.models import ImportTransaction, SchemeTransaction, PaymentTransaction, MatchedTransaction, ExportTransaction


BOX_WIDTH = 60


def box(text: str) -> str:
    in_lines = inspect.cleandoc(text).split("\n")
    lines = []
    width = BOX_WIDTH
    lines.append(f"┏{'━' * width}┓")

    lines.append(f"┃{in_lines[0]:^{width}}┃")
    for line in in_lines[1:]:
        if line.strip() == "":
            lines.append(f"┠{'╌' * width}┨")
        elif line.strip() == "---":
            lines.append(f"┣{'━' * width}┫")
        else:
            lines.append(f"┃{line:^{width}}┃")
    lines.append(f"┗{'━' * width}┛")
    return "\n".join(lines)


def down_arrow() -> str:
    return f"{'⬇':^{BOX_WIDTH}}"


def import_tx_str(tx: ImportTransaction) -> str:
    return "\n".join(["IMPORT TX", "", f"imported at {tx.created_at}", f"from {tx.source}"])


def scheme_tx_str(tx: SchemeTransaction) -> str:
    return "\n".join([f"SCHEME TX ({tx.status.name})", "", f"created from import at {tx.created_at}"])


def payment_tx_str(tx: PaymentTransaction) -> str:
    return "\n".join([f"PAYMENT TX ({tx.status.name})", "", f"created from import at {tx.created_at}"])


def matched_tx_str(tx: MatchedTransaction) -> str:
    return "\n".join(
        [f"MATCHED TX ({tx.status.name})", "", f"created from a {tx.matching_type.name} match", f"at {tx.created_at}"]
    )


def export_tx_str(tx: ExportTransaction) -> str:
    return "\n".join(["EXPORT TX", "", f"exported at {tx.created_at}", f"to {tx.destination}"])


def tx_str(tx: Base) -> str:
    return {
        ImportTransaction: import_tx_str,
        SchemeTransaction: scheme_tx_str,
        PaymentTransaction: payment_tx_str,
        MatchedTransaction: matched_tx_str,
        ExportTransaction: export_tx_str,
    }[type(tx)](tx)


def chain_tx_str(txs: t.List[Base]) -> str:
    return "\n---\n".join(tx_str(tx) for tx in txs)


@click.group(help="find the entire lifecycle of a transaction as it went through the transaction matching system")
def cli() -> None:
    pass


@cli.command(help="start from an import transaction")
@click.argument("import_transaction_id")
def forward(import_transaction_id: int) -> None:
    import_transaction = session.query(ImportTransaction).get(import_transaction_id)

    scheme_transaction = (
        session.query(SchemeTransaction)
        .filter(SchemeTransaction.transaction_id == import_transaction.transaction_id)
        .one_or_none()
    )
    payment_transaction = (
        session.query(PaymentTransaction)
        .filter(PaymentTransaction.transaction_id == import_transaction.transaction_id)
        .one_or_none()
    )

    q = session.query(MatchedTransaction)
    if scheme_transaction is not None:
        q = q.filter(MatchedTransaction.scheme_transaction_id == scheme_transaction.id)
    if payment_transaction is not None:
        q = q.filter(MatchedTransaction.payment_transaction_id == payment_transaction.id)

    matched_transaction = q.one()

    if scheme_transaction is None:
        scheme_transaction = session.query(SchemeTransaction).get(matched_transaction.scheme_transaction_id)
    if payment_transaction is None:
        payment_transaction = session.query(PaymentTransaction).get(matched_transaction.payment_transaction_id)

    export_transaction = (
        session.query(ExportTransaction)
        .filter(ExportTransaction.matched_transaction_id == matched_transaction.id)
        .one()
    )

    print(box(import_tx_str(import_transaction)))
    print(down_arrow())
    print(box(chain_tx_str([scheme_transaction, payment_transaction])))
    print(down_arrow())
    print(box(matched_tx_str(matched_transaction)))
    print(down_arrow())
    print(box(export_tx_str(export_transaction)))


@cli.command(help="work backwards from an export transaction")
@click.argument("export_transaction_id")
def reverse(export_transaction_id: int) -> None:
    export_transaction = session.query(ExportTransaction).get(export_transaction_id)
    matched_transaction = (
        session.query(MatchedTransaction)
        .filter(MatchedTransaction.id == export_transaction.matched_transaction_id)
        .one()
    )
    scheme_transaction = (
        session.query(SchemeTransaction).filter(SchemeTransaction.id == matched_transaction.scheme_transaction_id).one()
    )
    payment_transaction = (
        session.query(PaymentTransaction)
        .filter(PaymentTransaction.id == matched_transaction.payment_transaction_id)
        .one()
    )
    scheme_import_transaction = (
        session.query(ImportTransaction)
        .filter(ImportTransaction.transaction_id == scheme_transaction.transaction_id)
        .one()
    )
    payment_import_transaction = (
        session.query(ImportTransaction)
        .filter(ImportTransaction.transaction_id == payment_transaction.transaction_id)
        .one()
    )

    print(box(chain_tx_str([scheme_import_transaction, payment_import_transaction])))
    print(down_arrow())
    print(box(chain_tx_str([scheme_transaction, payment_transaction])))
    print(down_arrow())
    print(box(matched_tx_str(matched_transaction)))
    print(down_arrow())
    print(box(export_tx_str(export_transaction)))


if __name__ == "__main__":
    cli()

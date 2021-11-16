"""
receipt numbers:

SELECT
    matched_transaction.id
FROM
    matched_transaction
INNER JOIN
    merchant_identifier ON matched_transaction.merchant_identifier_id = merchant_identifier.id
INNER JOIN
    loyalty_scheme ON merchant_identifier.loyalty_scheme_id = loyalty_scheme.id
WHERE
    loyalty_scheme.slug = 'wasabi-club' AND
    matched_transaction.created_at > '2021-09-18' AND
    matched_transaction.status != 'EXPORTED'
ORDER BY matched_transaction.transaction_date
;
"""

# list of matched_transaction IDs to requeue for export.
transaction_ids: list[int] = []

from app import db  # noqa
from app.core.export_director import ExportDirector  # noqa

director = ExportDirector()
with db.session_scope() as session:
    for transaction_id in transaction_ids:
        director.handle_matched_transaction(transaction_id, session=session)

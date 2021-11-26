from functools import lru_cache

from app import db, models, tasks
from app.imports.agents.registry import import_agents
from app.imports.exceptions import MissingMID
from app.reporting import get_logger

# list of transaction_id strings to requeue
txids: list[str] = []

log = get_logger("requeue-failed-imports")


@lru_cache()
def get_agent(slug: str):
    return import_agents.instantiate(slug)


queue_transactions = []
match_group_set = set()
with db.session_scope() as session:
    log.info("[SCRIPT] looping through import transactions")
    for txid in txids:

        def get_itx():
            return (
                session.query(models.ImportTransaction)
                .filter(
                    models.ImportTransaction.provider_slug == "wasabi-club",
                    models.ImportTransaction.transaction_id == txid,
                    models.ImportTransaction.identified.is_(True),
                )
                .one()
            )

        itx = db.run_query(get_itx, session=session, description="find import_transaction by transaction ID")
        log.info(f"[SCRIPT] found {itx}")
        tx_data = itx.data

        agent = get_agent(itx.provider_slug)
        log.info(f"[SCRIPT] handling with {agent}")

        mids = agent.get_mids(tx_data)
        log.info(f"[SCRIPT] using mids: {mids}")

        merchant_identifier_ids = []
        for mid in mids:
            try:
                merchant_identifier_ids.extend(agent._identify_mid(mid, session=session))
            except MissingMID:
                pass

        queue_transactions.append(
            agent._build_queue_transaction(
                model=models.SchemeTransaction,
                transaction_data=tx_data,
                merchant_identifier_ids=merchant_identifier_ids,
                transaction_id=itx.transaction_id,
                match_group=itx.match_group,
            )
        )

        match_group_set.add(itx.match_group)

if len(match_group_set) > 1:
    raise ValueError("[SCRIPT] there's more than one match group in this TXID set.")

log.info(f"[SCRIPT] prepared {len(queue_transactions)} queue transactions")
if queue_transactions:
    match_group = match_group_set.pop()
    log.info(f"[SCRIPT] queueing import task for match group {match_group} with {len(queue_transactions)} transactions")
    for tx in queue_transactions:
        log.info(f"[SCRIPT] {repr(tx)}")
    tasks.matching_queue.enqueue(tasks.persist_scheme_transactions, queue_transactions, match_group=match_group)

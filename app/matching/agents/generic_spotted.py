import typing as t

from app import db, models
from app.matching.agents import BaseMatchingAgent, MatchResult


class GenericSpotted(BaseMatchingAgent):
    def _find_applicable_scheme_transactions(self, *, session: db.Session):
        return []

    def do_match(self, scheme_transactions, db_session: db.Session) -> t.Optional[MatchResult]:
        return MatchResult(
            matched_transaction=models.MatchedTransaction(
                **self.make_spotted_transaction_fields(db_session),
                matching_type=models.MatchingType.SPOTTED,
            ),
            user_identity=self.user_identity,
            scheme_transaction_id=None,
        )

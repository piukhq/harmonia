from app import db, models


class Sequencer:
    def __init__(self, provider_slug: str):
        self.provider_slug = provider_slug

    def _get_fsn(self, default_next_value: int, *, session: db.Session) -> models.FileSequenceNumber:
        fsn, _ = db.get_or_create(
            models.FileSequenceNumber,
            provider_slug=self.provider_slug,
            defaults={"next_value": default_next_value},
            session=session,
        )
        return fsn

    def next_value(self, *, session: db.Session, default_initial_value: int = 1) -> int:
        return self._get_fsn(default_initial_value, session=session).next_value

    def set_next_value(self, next_value: int, *, session: db.Session):
        fsn = self._get_fsn(next_value, session=session)

        def update_next_value():
            fsn.next_value = next_value
            session.commit()

        db.run_query(
            update_next_value,
            session=session,
            description=f"update next {self.provider_slug} sequence value",
        )

from app import db, models


class Sequencer:
    def __init__(self, provider_slug: str):
        self.provider_slug = provider_slug

    def _get_fsn(self, default_next_value: int) -> models.FileSequenceNumber:
        fsn, _ = db.get_or_create(
            models.FileSequenceNumber, provider_slug=self.provider_slug, defaults={"next_value": default_next_value},
        )
        return fsn

    def next_value(self, *, default_initial_value: int = 1) -> int:
        return self._get_fsn(default_initial_value).next_value

    def set_next_value(self, next_value: int):
        fsn = self._get_fsn(next_value)

        def update_next_value():
            fsn.next_value = next_value
            db.session.commit()

        db.run_query(
            update_next_value, description=f"update next {self.provider_slug} sequence value",
        )

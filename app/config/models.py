import sqlalchemy as s

from app.db import Base, ModelMixin, auto_repr, auto_str


@auto_repr
@auto_str("key", "value")
class ConfigItem(Base, ModelMixin):
    __tablename__ = "config_item"

    key = s.Column(s.String(100), nullable=False, index=True, unique=True)
    value = s.Column(s.String(100), nullable=False)

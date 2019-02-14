import sqlalchemy as s

from app.db import Base, auto_repr, ModelMixin


@auto_repr
class Administrator(Base, ModelMixin):
    __tablename__ = "administrator"

    uid = s.Column(s.String(64), nullable=False)
    email_address = s.Column(s.String(256), nullable=False)
    password_hash = s.Column(s.Text, nullable=False)
    salt = s.Column(s.String(64), nullable=False)
    is_active = s.Column(s.Boolean, default=True, nullable=False)

import secrets
import hashlib
import base64

from flask_login import UserMixin

from app import models, db
from app.reporting import get_logger


log = get_logger("auth")


PASSWORD_HASH_DIGEST = hashlib.sha512().name
PASSWORD_ALGORITHM = f"pbkdf2_{PASSWORD_HASH_DIGEST}"


def _generate_user_uid() -> str:
    return secrets.token_urlsafe(48)  # 48-byte token in a 64-character base64 string.


def _generate_user_salt() -> str:
    return secrets.token_urlsafe(48)  # 48-byte token in a 64-character base64 string.


def _generate_password_hash(password: str, salt: str) -> str:
    """
    Password generation based on Django auth.
    The password and salt parameters are both UTF-8 strings.
    References:
    * https://github.com/django/django/blob/master/django/contrib/auth/hashers.py#L241
    * https://github.com/django/django/blob/master/django/utils/crypto.py#L77
    """
    assert "$" not in salt
    iterations = 200_000
    password_hash = _hash_password(password, salt, iterations)
    return f"{PASSWORD_ALGORITHM}${iterations}${salt}${password_hash}"


def _hash_password(password: str, salt: str, iterations: int):
    password_hash = hashlib.pbkdf2_hmac(
        PASSWORD_HASH_DIGEST, password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    password_b64 = base64.b64encode(password_hash).decode("utf-8")
    return password_b64


def validate_password(password: str, password_hash: str) -> bool:
    algorithm, iterations_str, salt, password_hash = password_hash.split("$")

    if algorithm != PASSWORD_ALGORITHM:
        log.warning(f"Unsupported password algorithm: {repr(algorithm)}")
        return False

    try:
        iterations = int(iterations_str)
    except ValueError:
        log.warning(f"Invalid 'iterations' value in password: {repr(iterations_str)}")
        return False

    confirmation_hash = _hash_password(password, salt, iterations)

    if password_hash != confirmation_hash:
        return False

    return True


def create_user(email_address: str, password: str) -> models.Administrator:
    salt = _generate_user_salt()
    administrator = models.Administrator(
        uid=_generate_user_uid(),
        email_address=email_address,
        password_hash=_generate_password_hash(password, salt),
        salt=salt,
    )
    db.session.add(administrator)
    db.session.commit()
    return administrator


def get_user(email_address: str) -> models.Administrator:
    return User(
        db.session.query(models.Administrator).filter(models.Administrator.email_address == email_address).one()
    )


class User(UserMixin):
    """
    Wraps app.api.models.Administrator for flask-login usage.
    """

    def __init__(self, instance: models.Administrator):
        self.instance = instance

    def is_authenticated(self) -> bool:
        return True

    def is_active(self) -> bool:
        return self.instance.is_active

    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return self.instance.uid

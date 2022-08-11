import pytest
from sqlalchemy.orm import Session

from app import db


@pytest.fixture
def db_session():
    connection = db.engine.connect()
    session = Session(bind=connection)
    transaction = connection.begin_nested()
    try:
        yield session
    finally:
        transaction.rollback()
        session.close()

import pytest
from sqlalchemy.orm import Session

from app import db


@pytest.fixture()
def test_db():
    db.Base.metadata.create_all(bind=db.engine)
    yield
    db.Base.metadata.drop_all(bind=db.engine)


@pytest.fixture
def db_session(test_db):
    connection = db.engine.connect()
    session = Session(bind=connection)
    transaction = connection.begin_nested()
    try:
        yield session
    finally:
        transaction.rollback()
        session.close()

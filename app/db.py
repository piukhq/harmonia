from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import settings


db_engine = create_engine(settings.POSTGRES_DSN)
Session = sessionmaker(bind=db_engine)

Base = declarative_base()

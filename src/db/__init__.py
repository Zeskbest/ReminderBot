from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import declarative_base

engine = create_engine("sqlite:///bot.db")
metadata = MetaData(bind=engine)
Base = declarative_base(bind=engine, metadata=metadata)

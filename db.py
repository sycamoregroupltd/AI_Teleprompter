from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# For local testing, we’ll use SQLite stored in a file named test.db
DATABASE_URL = "sqlite:///./test.db"

# Create the engine
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# SessionLocal is what we'll use to interact with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def init_db():
    """
    Call this function once (e.g., on startup) to create database tables.
    """
    Base.metadata.create_all(bind=engine)

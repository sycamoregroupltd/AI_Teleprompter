# feedback.py
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
engine = create_engine("sqlite:///feedback.db")
SessionLocal = sessionmaker(bind=engine)

class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True)
    call_id = Column(String)
    response = Column(String)
    rating = Column(Integer)  # e.g., 1=bad, 5=great

Base.metadata.create_all(bind=engine)

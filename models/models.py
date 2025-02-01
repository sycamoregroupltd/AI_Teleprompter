from db import Base
from sqlalchemy import Column, String
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID

# This is our user database table
class UserTable(SQLAlchemyBaseUserTableUUID, Base):
    """
    Inherits from SQLAlchemyBaseUserTableUUID:
    - Provides id (UUID primary key), email, hashed_password, is_active, etc.
    We can add extra columns if we like. For example:
    """
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

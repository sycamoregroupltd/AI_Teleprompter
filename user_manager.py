from typing import Optional
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from models import UserTable
from db import SessionLocal
from sqlalchemy.orm import sessionmaker

# The secret key used for signing tokens (JWT)
SECRET = "CHANGE_ME_TO_SOMETHING_SECURE"

# Create a user database instance
# SessionLocal() returns a new session
user_db = SQLAlchemyUserDatabase(UserTable, SessionLocal())

class UserManager(UUIDIDMixin, BaseUserManager[UserTable, str]):
    # If using UUID for IDs, use [UserTable, UUID] or similar.
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: UserTable, request=None):
        print(f"User {user.id} has registered.")

async def get_user_manager():
    """
    Dependency that returns an instance of UserManager.
    """
    yield UserManager(user_db)

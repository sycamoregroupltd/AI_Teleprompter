from typing import Optional
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from models import UserTable
from db import SessionLocal
from sqlalchemy.orm import sessionmaker

# Secret key for signing tokens (e.g., JWT). 
# NOTE: Change this key to a secure, unpredictable value in production.
SECRET = "CHANGE_ME_TO_SOMETHING_SECURE"

# Create a user database instance using SQLAlchemy.
# SessionLocal() returns a new database session for each operation.
user_db = SQLAlchemyUserDatabase(UserTable, SessionLocal())

class UserManager(UUIDIDMixin, BaseUserManager[UserTable, str]):
    """
    UserManager is responsible for managing user operations such as registration, authentication,
    password resets, and token verification. It extends BaseUserManager from fastapi_users while using
    UUIDIDMixin for handling user identifiers.

    The secret keys for resetting passwords and verifying users are defined using the SECRET constant.
    """
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: UserTable, request: Optional[object] = None):
        """
        Callback invoked after a user has successfully registered.
        
        This method is used to perform any post-registration operations such as logging,
        sending welcome emails, or additional verification steps.
        
        Parameters:
            user (UserTable): The user instance that was registered.
            request (Optional[object]): The request object associated with the registration (if available).
        """
        print(f"User {user.id} has registered.")

async def get_user_manager():
    """
    Dependency function that yields an instance of UserManager.
    
    This is used by FastAPI's dependency injection system to provide a UserManager instance where needed.
    
    Yields:
        UserManager: An instance connected to the configured user database.
    """
    yield UserManager(user_db)

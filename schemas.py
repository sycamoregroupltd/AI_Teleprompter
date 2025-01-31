from fastapi_users import schemas

# For reading user info (public data)
class UserRead(schemas.BaseUser[int]):  # or [UUID]
    first_name: str | None
    last_name: str | None

# For creating a new user (registration)
class UserCreate(schemas.BaseUserCreate):
    first_name: str | None
    last_name: str | None

# For updating user info
class UserUpdate(schemas.BaseUserUpdate):
    first_name: str | None
    last_name: str | None

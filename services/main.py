import logging
nlogging.basicConfig(level=logging.INFO)
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

from db import init_db
from user_manager import get_user_manager, SECRET
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import JWTStrategy, BearerTransport, AuthenticationBackend
from schemas import UserRead, UserCreate, UserUpdate
from models import UserTable
from fastapi import Depends

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[UserTable, str](
    get_user_manager,
    [auth_backend],
)

load_dotenv()
app = FastAPI()

@app.on_event("startup")
def on_startup():
    init_db()

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

@app.post("/handle-call")
async def handle_call(request: Request):
    response = VoiceResponse()
    response.say("Welcome to the AI Teleprompter!")
    return {"twiml": str(response)}

# Auth routes
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

@app.get("/protected")
async def protected_route(user=Depends(fastapi_users.current_user())):
    return {"message": f"Hello, {user.email}. You are authenticated!"}

@app.get("/")
async def home():
    return {"message": "AI Teleprompter is running!"}
from fastapi import APIRouter
from app.api.routes import pricing, business, auth, chat

api_router = APIRouter()
api_router.include_router(pricing.router)
api_router.include_router(business.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
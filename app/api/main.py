from fastapi import APIRouter
from app.api.routes import pricing

api_router = APIRouter()
api_router.include_router(pricing.router)
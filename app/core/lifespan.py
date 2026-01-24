from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import init_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_logging()
    yield
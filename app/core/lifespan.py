from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import init_logging
from app.infrastructure.database.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_logging()
    init_db()
    yield
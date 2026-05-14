from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import init_logging
from app.infrastructure.agents.graph.builder import build_graph
from app.infrastructure.agents.graph.checkpointer import get_checkpointer
from app.infrastructure.database.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_logging()
    await init_db()

    async with get_checkpointer() as checkpointer:
        app.state.agent_graph = build_graph(checkpointer)
        yield

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.database import init_db

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(
    title="Commander R&D Collaboration System",
    version="0.1.0",
    description="多子项目研发协同管理系统 MVP",
    lifespan=lifespan,
)


app.include_router(router, prefix="/api/v1", tags=["mvp"])

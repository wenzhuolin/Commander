from fastapi import FastAPI

from app.api.routes import router
from app.core.database import init_db

app = FastAPI(
    title="Commander R&D Collaboration System",
    version="0.1.0",
    description="多子项目研发协同管理系统 MVP",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(router, prefix="/api/v1", tags=["mvp"])

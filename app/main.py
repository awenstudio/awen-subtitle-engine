"""FastAPI Application - Awen Subtitle Engine"""

from fastapi import FastAPI

from app.config import APP_VERSION, WHISPER_MODEL
from app.api.routes import router

app = FastAPI(
    title="Awen Subtitle Engine",
    version=APP_VERSION,
    description="AI字幕自动生成服务",
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup():
    pass


@app.on_event("shutdown")
async def shutdown():
    pass

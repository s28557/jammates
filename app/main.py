from fastapi import FastAPI
from app.core.config import settings
from app.api.endpoints.loginAuth import router as auth_router

app = FastAPI(title=settings.APP_NAME)
app.include_router(auth_router, prefix="/api/v1") # register auth endpoints

@app.get("/health")
async def health():
    """check if server is running"""
    return {"status": "ok", "app": settings.APP_NAME}
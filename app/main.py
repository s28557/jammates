from fastapi import FastAPI
from app.core.config import settings
from app.api.endpoints.loginAuth import router as auth_router
from app.api.endpoints.users import router as users_router

app = FastAPI(title=settings.APP_NAME)
app.include_router(auth_router, prefix="/api/v1") # register auth endpoints
app.include_router(users_router, prefix="/api/v1") # user profile endpoints

@app.get("/health")
async def health():
    """check if server is running"""
    return {"status": "ok", "app": settings.APP_NAME}
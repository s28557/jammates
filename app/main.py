from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api.endpoints.loginAuth import router as auth_router
from app.api.endpoints.users import router as users_router
from app.api.endpoints.circles import router as circles_router
from app.api.endpoints.spotify import router as spotify_router
from app.api.endpoints.concerts import router as concerts_router
from app.api.endpoints.recommendations import router as recommendations_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api/v1") # register auth endpoints
app.include_router(users_router, prefix="/api/v1") # user profile endpoints
app.include_router(circles_router, prefix="/api/v1")  # circles endpoints
app.include_router(spotify_router, prefix="/api/v1")  # spotify data endpoints
app.include_router(concerts_router, prefix="/api/v1")  # concert endpoints
app.include_router(recommendations_router, prefix="/api/v1")  # recommendation endpoints
Path("uploads").mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/health")
async def health():
    """check if server is running"""
    return {"status": "ok", "app": settings.APP_NAME}

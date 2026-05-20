from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    App configuration
    Sensitive values are loaded from .env file
    """
    APP_NAME: str = "JamMates"
    SECRET_KEY: str = "tmp-whatever"
    DATABASE_URI: str = ""  # in .env file
    SPOTIFY_CLIENT_ID: str = "" # in .env file
    SPOTIFY_CLIENT_SECRET: str = "" # in .env file
    SPOTIFY_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/auth/spotify/callback"
    CIRCLE_MAX_MEMBERS: int = 4

    class Config:
        env_file = ".env"

settings = Settings()

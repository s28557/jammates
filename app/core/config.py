from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "JamMates"
    SECRET_KEY: str = "tmp-whatever"
    DATABASE_URI: str = "postgresql+asyncpg://postgres:Ania8424@localhost:5432/jammates"

    class Config:
        env_file = ".env"

settings = Settings()

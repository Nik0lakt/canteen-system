from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://meal:mealpass@localhost:5432/meal"
    APP_TZ: str = "Europe/Moscow"

    # Security
    JWT_SECRET: str = "change-me"
    JWT_ALG: str = "HS256"
    LIVENESS_TOKEN_TTL_SEC: int = 60

    # Limits
    SUBSIDY_DAILY_CENTS: int = 10000  # 100 rub
    MAX_MEAL_CENTS: int = 100000      # 1000 rub
    MAX_RECEIPT_CENTS: int = 50000    # 500 rub

    # Face
    FACE_DIST_THRESHOLD: float = 0.52

    # Liveness
    LIVENESS_SESSION_TTL_SEC: int = 25
    COMMAND_WINDOW_SEC: int = 4

    # Telegram
    TELEGRAM_BOT_TOKEN: str | None = None

settings = Settings()

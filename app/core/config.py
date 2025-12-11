import os
from functools import lru_cache


class Settings:
    APP_NAME: str = "Canteen System"
    APP_ENV: str = os.getenv("APP_ENV", "dev")

    # По умолчанию SQLite для MVP, но можно переопределить переменной окружения
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./canteen.db"
    )

    # Liveness
    LIVENESS_SESSION_TTL_SECONDS: int = 45
    LIVENESS_TOKEN_TTL_SECONDS: int = 60

    # Финансы
    DAILY_SUBSIDY_CENTS: int = 100 * 100
    MAX_CHECK_AMOUNT_CENTS: int = 500 * 100

    # Порог для face_recognition (можно менять)
    FACE_DISTANCE_THRESHOLD: float = 0.55


@lru_cache()
def get_settings() -> Settings:
    return Settings()

import hashlib
import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.core.errors import AppError

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def make_liveness_token(employee_id: str, session_id: str, terminal_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": employee_id,
        "sid": session_id,
        "tid": terminal_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.LIVENESS_TOKEN_TTL_SEC)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)

def verify_liveness_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise AppError("LIVENESS_TOKEN_EXPIRED", "Токен liveness истёк.", 401)
    except jwt.InvalidTokenError:
        raise AppError("LIVENESS_TOKEN_INVALID", "Некорректный токен liveness.", 401)

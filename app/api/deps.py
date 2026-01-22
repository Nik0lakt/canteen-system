from fastapi import Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AppError
from app.core.security import hash_token
from app.db.models import Terminal
from app.db.session import get_db

async def get_terminal(
    db: AsyncSession,
    x_terminal_token: str | None = Header(default=None)
) -> Terminal:
    if not x_terminal_token:
        raise AppError("TERMINAL_UNAUTHORIZED", "Не указан токен терминала.", 401)
    token_hash = hash_token(x_terminal_token)
    term = (await db.execute(select(Terminal).where(Terminal.api_token_hash == token_hash))).scalar_one_or_none()
    if not term:
        raise AppError("TERMINAL_UNAUTHORIZED", "Неверный токен терминала.", 401)
    if term.status != "ACTIVE":
        raise AppError("TERMINAL_BLOCKED", "Терминал заблокирован.", 403)
    return term

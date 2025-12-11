from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db


def get_db_dep() -> Session:
    from app.db.session import get_db
    return next(get_db())


def get_cashier_client_id(x_cashier_id: str = Header(default="CASHIER_DEV")) -> str:
    # В реале здесь надо проверять токен / API-key
    return x_cashier_id

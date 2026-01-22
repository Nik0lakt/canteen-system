import base64
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_terminal
from app.core.config import settings
from app.core.errors import AppError
from app.db.models import Card, Employee, Face, MonthlyBalance, DailyBalance
from app.db.session import get_db
from app.services.calendar import is_company_workday, is_employee_working
from app.services.finance import year_month

router = APIRouter()

@router.get("/api/employee_info")
async def employee_info(card_uid: str, db: AsyncSession = Depends(get_db), terminal=Depends(get_terminal)):
    card = (await db.execute(select(Card).where(Card.uid == card_uid))).scalar_one_or_none()
    if not card:
        raise AppError("CARD_NOT_FOUND", "Карта не найдена.", 404)
    if card.status != "ACTIVE":
        raise AppError("CARD_BLOCKED", "Карта заблокирована.", 403)

    emp = (await db.execute(select(Employee).where(Employee.id == card.employee_id))).scalar_one()
    if emp.status != "ACTIVE":
        raise AppError("EMPLOYEE_BLOCKED", "Сотрудник заблокирован.", 403)

    face = (await db.execute(select(Face).where(Face.employee_id == emp.id, Face.is_active == True))).scalar_one_or_none()
    needs_face = face is None

    tz = ZoneInfo(settings.APP_TZ)
    today = datetime.now(tz=tz).date()
    ym = year_month(today)

    dbal = (await db.execute(select(DailyBalance).where(DailyBalance.employee_id == emp.id, DailyBalance.date == today))).scalar_one_or_none()
    used_today = dbal.used_cents if dbal else 0

    mbal = (await db.execute(select(MonthlyBalance).where(MonthlyBalance.employee_id == emp.id, MonthlyBalance.year_month == ym))).scalar_one_or_none()
    monthly_used = mbal.used_cents if mbal else 0
    monthly_limit = (mbal.limit_cents if mbal else emp.monthly_limit_cents)

    eligible = (emp.employee_type == "WORKER" and await is_company_workday(db, today) and await is_employee_working(db, emp.id, today))
    subsidy_left = max(0, settings.SUBSIDY_DAILY_CENTS - used_today) if eligible else 0
    monthly_left = max(0, monthly_limit - monthly_used)

    photo_b64 = base64.b64encode(emp.photo_jpeg).decode("ascii") if emp.photo_jpeg else None

    return {
        "ok": True,
        "data": {
            "employee_id": str(emp.id),
            "full_name": emp.full_name,
            "employee_type": emp.employee_type,
            "status": emp.status,
            "photo_base64": photo_b64,
            "subsidy_today_left_cents": subsidy_left,
            "monthly_left_cents": monthly_left,
            "needs_face_enrollment": needs_face,
        }
    }

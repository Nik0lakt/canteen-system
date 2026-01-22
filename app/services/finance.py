from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import AppError
from app.db.models import Card, Employee, DailyBalance, MonthlyBalance, Transaction, LivenessSession
from app.services.calendar import is_company_workday, is_employee_working

def year_month(d) -> int:
    return d.year * 100 + d.month

@dataclass
class PaymentResult:
    subsidy_spent: int
    monthly_spent: int
    subsidy_left: int
    monthly_left: int

async def compute_subsidy_eligibility(db: AsyncSession, emp: Employee, d) -> bool:
    if emp.employee_type != "WORKER":
        return False
    if emp.status != "ACTIVE":
        return False
    if not await is_company_workday(db, d):
        return False
    if not await is_employee_working(db, emp.id, d):
        return False
    return True

async def pay(db: AsyncSession, terminal_id, card_uid: str, amount_cents: int, liveness_session_id) -> PaymentResult:
    if amount_cents <= 0:
        raise AppError("BAD_AMOUNT", "Сумма должна быть больше нуля.")
    if amount_cents > settings.MAX_MEAL_CENTS:
        raise AppError("MAX_MEAL_1000_EXCEEDED", "Сумма одного обеда не может превышать 1000 руб.")
    if amount_cents > settings.MAX_RECEIPT_CENTS:
        raise AppError("MAX_RECEIPT_500_EXCEEDED", "Сумма одного чека не может превышать 500 руб.")

    sess = (await db.execute(select(LivenessSession).where(LivenessSession.id == liveness_session_id))).scalar_one_or_none()
    if not sess or sess.status != "PASSED":
        raise AppError("LIVENESS_REQUIRED", "Liveness не пройдена или недействительна.", 403)
    if sess.used_at is not None or sess.status == "USED":
        raise AppError("LIVENESS_ALREADY_USED", "Liveness-токен уже использован.", 409)

    tz = ZoneInfo(settings.APP_TZ)
    now = datetime.now(tz=tz)
    today = now.date()
    ym = year_month(today)

    async with db.begin():
        card = (await db.execute(select(Card).where(Card.uid == card_uid).with_for_update())).scalar_one_or_none()
        if not card:
            raise AppError("CARD_NOT_FOUND", "Карта не найдена.")
        if card.status != "ACTIVE":
            raise AppError("CARD_BLOCKED", "Карта заблокирована.")

        emp = (await db.execute(select(Employee).where(Employee.id == card.employee_id).with_for_update())).scalar_one()
        if emp.status != "ACTIVE":
            raise AppError("EMPLOYEE_BLOCKED", "Сотрудник заблокирован.")

        eligible = await compute_subsidy_eligibility(db, emp, today)

        dbal = (await db.execute(
            select(DailyBalance).where(DailyBalance.employee_id == emp.id, DailyBalance.date == today).with_for_update()
        )).scalar_one_or_none()
        if not dbal:
            dbal = DailyBalance(employee_id=emp.id, date=today, used_cents=0)
            db.add(dbal)
            await db.flush()

        mbal = (await db.execute(
            select(MonthlyBalance).where(MonthlyBalance.employee_id == emp.id, MonthlyBalance.year_month == ym).with_for_update()
        )).scalar_one_or_none()
        if not mbal:
            mbal = MonthlyBalance(employee_id=emp.id, year_month=ym, limit_cents=emp.monthly_limit_cents, used_cents=0)
            db.add(mbal)
            await db.flush()

        subsidy_left = (settings.SUBSIDY_DAILY_CENTS - dbal.used_cents) if eligible else 0
        subsidy_left = max(0, subsidy_left)

        subsidy_spent = min(subsidy_left, amount_cents)
        remaining = amount_cents - subsidy_spent

        monthly_left = max(0, mbal.limit_cents - mbal.used_cents)
        if remaining > monthly_left:
            raise AppError("INSUFFICIENT_MONTHLY_LIMIT", "Недостаточно средств в месячном лимите.")

        dbal.used_cents += subsidy_spent
        mbal.used_cents += remaining

        sess.used_at = datetime.now(tz=ZoneInfo("UTC"))
        sess.status = "USED"

        tx = Transaction(
            terminal_id=terminal_id,
            employee_id=emp.id,
            card_uid=card_uid,
            amount_cents=amount_cents,
            subsidy_spent_cents=subsidy_spent,
            monthly_spent_cents=remaining,
            status="APPROVED",
            liveness_session_id=liveness_session_id,
        )
        db.add(tx)
        await db.flush()

        return PaymentResult(
            subsidy_spent=subsidy_spent,
            monthly_spent=remaining,
            subsidy_left=(settings.SUBSIDY_DAILY_CENTS - dbal.used_cents) if eligible else 0,
            monthly_left=(mbal.limit_cents - mbal.used_cents),
        )

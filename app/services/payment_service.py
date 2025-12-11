from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import PaymentError
from app.db import models
from app.services.workdays_service import is_company_workday, is_employee_workday

settings = get_settings()


def _today_date():
    return datetime.now(timezone.utc).date()


def calculate_and_apply_payment(
    db: Session,
    card_uid: str,
    canteen_id: int,
    amount_cents: int,
    liveness_token: str,
    cashier_client_id: str,
    client_ip: str,
) -> Tuple[models.Transaction, int, int]:
    if amount_cents > settings.MAX_CHECK_AMOUNT_CENTS:
        raise PaymentError("AMOUNT_TOO_LARGE", "Сумма чека не может превышать 500 руб.")

    card = (
        db.query(models.Card)
        .filter(models.Card.uid == card_uid)
        .with_for_update()
        .first()
    )
    if not card:
        raise PaymentError("CARD_NOT_FOUND", "Карта не найдена.")

    if card.status != models.CardStatus.ACTIVE:
        raise PaymentError("CARD_BLOCKED", "Карта заблокирована.")

    employee = db.query(models.Employee).get(card.employee_id)
    if not employee or employee.status != models.EmployeeStatus.ACTIVE:
        raise PaymentError("EMPLOYEE_BLOCKED", "Сотрудник заблокирован или отсутствует.")

    # Liveness
    session = (
        db.query(models.LivenessSession)
        .filter(
            models.LivenessSession.employee_id == employee.id,
            models.LivenessSession.card_id == card.id,
            models.LivenessSession.liveness_token == liveness_token,
        )
        .with_for_update()
        .first()
    )
    now = datetime.now(timezone.utc)
    if not session:
        raise PaymentError("LIVENESS_TOKEN_INVALID", "Неверный токен проверки личности.")
    if session.status != models.LivenessStatus.PASSED:
        raise PaymentError("LIVENESS_NOT_PASSED", "Проверка личности не пройдена.")
    if session.token_used:
        raise PaymentError("LIVENESS_TOKEN_USED", "Токен уже использован.")
    if session.token_expires_at and session.token_expires_at < now:
        raise PaymentError("LIVENESS_TOKEN_EXPIRED", "Срок действия токена истёк.")

    today = _today_date()

    is_company_day = is_company_workday(db, today)
    is_employee_day = is_employee_workday(db, employee.id, today)
    eligible_for_subsidy = (
        employee.type == models.EmployeeType.WORKER
        and is_company_day
        and is_employee_day
    )

    # Дотация
    subsidy_used_cents = 0
    subsidy_remaining_cents = 0
    if eligible_for_subsidy:
        daily = (
            db.query(models.DailySubsidyUsage)
            .filter_by(employee_id=employee.id, date=today)
            .with_for_update()
            .first()
        )
        if not daily:
            daily = models.DailySubsidyUsage(
                employee_id=employee.id,
                date=today,
                used_cents=0,
            )
            db.add(daily)
            db.flush()
        subsidy_remaining_cents = max(
            0, settings.DAILY_SUBSIDY_CENTS - daily.used_cents
        )
    else:
        subsidy_remaining_cents = 0

    subsidy_cents = min(amount_cents, subsidy_remaining_cents)
    salary_cents = amount_cents - subsidy_cents

    # Месячный лимит
    year = today.year
    month = today.month
    monthly = (
        db.query(models.MonthlyLimit)
        .filter_by(employee_id=employee.id, year=year, month=month)
        .with_for_update()
        .first()
    )

    monthly_limit_cents = monthly.limit_cents if monthly else 0
    monthly_used_cents = monthly.used_cents if monthly else 0
    monthly_remaining_cents = max(0, monthly_limit_cents - monthly_used_cents)

    if salary_cents > monthly_remaining_cents:
        raise PaymentError("MONTHLY_LIMIT_EXCEEDED", "Недостаточно средств в месячном лимите.")

    # Применяем
    if subsidy_cents > 0 and eligible_for_subsidy:
        daily.used_cents += subsidy_cents

    if salary_cents > 0 and monthly:
        monthly.used_cents += salary_cents

    session.token_used = True

    txn = models.Transaction(
        employee_id=employee.id,
        card_id=card.id,
        canteen_id=canteen_id,
        liveness_session_id=session.id,
        amount_total_cents=amount_cents,
        subsidy_cents=subsidy_cents,
        salary_cents=salary_cents,
        status=models.TransactionStatus.APPROVED,
        cashier_client_id=cashier_client_id,
        client_ip=client_ip,
    )
    db.add(txn)
    db.flush()

    new_subsidy_rem = subsidy_remaining_cents - subsidy_cents
    new_monthly_rem = monthly_remaining_cents - salary_cents

    return txn, new_subsidy_rem, new_monthly_rem

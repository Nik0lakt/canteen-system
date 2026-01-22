from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.models import Employee
import httpx

async def send_telegram_payment_notification(
    db: AsyncSession,
    employee_id,
    amount_cents: int,
    subsidy_spent: int,
    monthly_spent: int,
    subsidy_left: int,
    monthly_left: int
) -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    emp = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if not emp or not emp.telegram_chat_id:
        return

    text = (
        f"Оплата питания: {amount_cents/100:.2f} руб\n"
        f"Дотация: -{subsidy_spent/100:.2f} руб\n"
        f"Из лимита: -{monthly_spent/100:.2f} руб\n"
        f"Остаток дотации сегодня: {subsidy_left/100:.2f} руб\n"
        f"Остаток месячного лимита: {monthly_left/100:.2f} руб"
    )
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": emp.telegram_chat_id, "text": text}

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(url, json=payload)
    except Exception:
        return

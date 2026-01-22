from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_terminal
from app.core.errors import AppError
from app.core.security import verify_liveness_token
from app.db.models import LivenessSession, Transaction
from app.db.session import get_db
from app.services.finance import pay
from app.services.telegram import send_telegram_payment_notification

router = APIRouter()

@router.post("/api/pay")
async def api_pay(payload: dict, db: AsyncSession = Depends(get_db), terminal=Depends(get_terminal)):
    card_uid = payload.get("card_uid")
    amount_cents = payload.get("amount_cents")
    token = payload.get("liveness_token")
    if not card_uid or amount_cents is None or not token:
        raise AppError("BAD_REQUEST", "Нужны поля: card_uid, amount_cents, liveness_token.")

    claims = verify_liveness_token(token)
    if claims["tid"] != str(terminal.id):
        raise AppError("LIVENESS_TOKEN_TERMINAL_MISMATCH", "Токен liveness выдан другому терминалу.", 403)

    session_id = claims["sid"]
    sess = (await db.execute(select(LivenessSession).where(LivenessSession.id == session_id))).scalar_one_or_none()
    if not sess:
        raise AppError("LIVENESS_NOT_FOUND", "Сессия liveness не найдена.", 404)
    if sess.terminal_id != terminal.id:
        raise AppError("FORBIDDEN", "Сессия принадлежит другому терминалу.", 403)

    try:
        result = await pay(db, terminal.id, card_uid, int(amount_cents), sess.id)
    except AppError as e:
        tx = Transaction(
            terminal_id=terminal.id,
            employee_id=sess.employee_id,
            card_uid=card_uid,
            amount_cents=int(amount_cents),
            status="DECLINED",
            decline_code=e.code,
            decline_message=e.message,
            liveness_session_id=sess.id,
        )
        db.add(tx)
        await db.commit()
        return {"ok": True, "data": {"status": "DECLINED", "code": e.code, "message": e.message}}

    await send_telegram_payment_notification(
        db,
        sess.employee_id,
        int(amount_cents),
        result.subsidy_spent,
        result.monthly_spent,
        result.subsidy_left,
        result.monthly_left
    )

    return {
        "ok": True,
        "data": {
            "status": "APPROVED",
            "amount_cents": int(amount_cents),
            "subsidy_spent_cents": result.subsidy_spent,
            "monthly_spent_cents": result.monthly_spent,
            "subsidy_today_left_cents": result.subsidy_left,
            "monthly_left_cents": result.monthly_left
        }
    }

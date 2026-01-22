from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_terminal
from app.core.errors import AppError
from app.core.security import make_liveness_token
from app.db.models import LivenessSession
from app.db.session import get_db
from app.services.liveness import start_liveness, process_frame

router = APIRouter()

@router.post("/api/start_liveness")
async def api_start_liveness(payload: dict, db: AsyncSession = Depends(get_db), terminal=Depends(get_terminal)):
    card_uid = payload.get("card_uid")
    if not card_uid:
        raise AppError("BAD_REQUEST", "Не указан card_uid.")
    sess = await start_liveness(db, terminal, card_uid)
    items = sess.commands["items"]
    return {
        "ok": True,
        "data": {
            "session_id": str(sess.id),
            "commands": items,
            "expires_at": sess.expires_at.isoformat(),
            "frame_interval_ms": 150
        }
    }

@router.post("/api/liveness_frame")
async def api_liveness_frame(
    db: AsyncSession = Depends(get_db),
    terminal=Depends(get_terminal),
    session_id: str = Form(...),
    image: UploadFile = File(...)
):
    raw = await image.read()
    sess = await process_frame(db, session_id, raw)
    items = sess.commands["items"]
    hint = items[sess.current_index]["text"] if sess.status == "IN_PROGRESS" and sess.current_index < len(items) else "Проверка завершена"
    return {
        "ok": True,
        "data": {
            "status": sess.status,
            "current_index": sess.current_index,
            "hint": hint,
            "blink_seen": sess.blink_seen
        }
    }

@router.post("/api/finish_liveness")
async def api_finish_liveness(payload: dict, db: AsyncSession = Depends(get_db), terminal=Depends(get_terminal)):
    session_id = payload.get("session_id")
    if not session_id:
        raise AppError("BAD_REQUEST", "Не указан session_id.")
    sess = (await db.execute(select(LivenessSession).where(LivenessSession.id == session_id))).scalar_one_or_none()
    if not sess:
        raise AppError("LIVENESS_NOT_FOUND", "Сессия liveness не найдена.", 404)
    if sess.terminal_id != terminal.id:
        raise AppError("FORBIDDEN", "Сессия принадлежит другому терминалу.", 403)

    if sess.status == "PASSED":
        token = make_liveness_token(str(sess.employee_id), str(sess.id), str(terminal.id))
        return {"ok": True, "data": {"result": "PASSED", "liveness_token": token, "expires_in_sec": 60}}
    return {"ok": True, "data": {"result": sess.status, "reason_code": sess.fail_reason_code}}

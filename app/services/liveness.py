import random
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import AppError
from app.db.models import LivenessSession, Face, Card, Terminal
from app.services.face import decode_image, detect_single_face_and_encoding, estimate_pose_and_blink, face_match
import numpy as np

COMMANDS_POOL = [
    ("TURN_LEFT",  "Поверните голову влево"),
    ("TURN_RIGHT", "Поверните голову вправо"),
    ("TILT",       "Наклоните голову к плечу"),
]

def pick_commands():
    k = random.choice([2, 3])
    items = random.sample(COMMANDS_POOL, k=k)
    return [{"type": t, "text": txt} for (t, txt) in items]

def command_satisfied(cmd_type: str, anchor: dict, pose: dict) -> bool:
    yaw0, pitch0, roll0 = anchor["yaw"], anchor["pitch"], anchor["roll"]
    yaw, pitch, roll = pose["yaw"], pose["pitch"], pose["roll"]
    if cmd_type == "TURN_LEFT":
        return yaw <= yaw0 - 15.0
    if cmd_type == "TURN_RIGHT":
        return yaw >= yaw0 + 15.0
    if cmd_type == "TILT":
        return abs(roll - roll0) >= 12.0
    return False

async def start_liveness(db: AsyncSession, terminal: Terminal, card_uid: str) -> LivenessSession:
    card = (await db.execute(select(Card).where(Card.uid == card_uid))).scalar_one_or_none()
    if not card:
        raise AppError("CARD_NOT_FOUND", "Карта не найдена.")
    if card.status != "ACTIVE":
        raise AppError("CARD_BLOCKED", "Карта заблокирована.")

    face = (await db.execute(select(Face).where(Face.employee_id == card.employee_id, Face.is_active == True))).scalar_one_or_none()
    if not face:
        raise AppError("NO_ACTIVE_FACE", "Для сотрудника не зарегистрировано лицо.")

    now = datetime.now(timezone.utc)
    sess = LivenessSession(
        employee_id=card.employee_id,
        terminal_id=terminal.id,
        status="IN_PROGRESS",
        commands={"items": pick_commands()},
        current_index=0,
        expires_at=now + timedelta(seconds=settings.LIVENESS_SESSION_TTL_SEC),
        last_seen_at=now,
        blink_seen=False,
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)
    return sess

async def process_frame(db: AsyncSession, session_id, image_bytes: bytes) -> LivenessSession:
    sess = (await db.execute(select(LivenessSession).where(LivenessSession.id == session_id))).scalar_one_or_none()
    if not sess:
        raise AppError("LIVENESS_NOT_FOUND", "Сессия liveness не найдена.")
    now = datetime.now(timezone.utc)
    if sess.status != "IN_PROGRESS":
        raise AppError("LIVENESS_NOT_IN_PROGRESS", "Сессия liveness не активна.", 409, {"status": sess.status})
    if now >= sess.expires_at:
        sess.status = "EXPIRED"
        await db.commit()
        raise AppError("LIVENESS_EXPIRED", "Сессия liveness истекла. Повторите попытку.", 409)

    bgr = decode_image(image_bytes)
    _, emb = detect_single_face_and_encoding(bgr)
    pose, blink = estimate_pose_and_blink(bgr)

    face = (await db.execute(select(Face).where(Face.employee_id == sess.employee_id, Face.is_active == True))).scalar_one()
    stored = np.array(face.embedding, dtype=np.float32)

    ok, dist = face_match(stored, emb)
    if not ok:
        sess.status = "FAILED"
        sess.fail_reason_code = "FACE_NOT_MATCH"
        await db.commit()
        raise AppError("FACE_NOT_MATCH", "Лицо не совпадает с владельцем карты.", 403, {"dist": dist})

    sess.min_face_dist = float(dist) if sess.min_face_dist is None else float(min(sess.min_face_dist, dist))
    sess.blink_seen = bool(sess.blink_seen or blink)

    items = sess.commands["items"]
    if sess.baseline_pose is None:
        sess.baseline_pose = pose
    if sess.anchor_pose is None:
        sess.anchor_pose = pose

    if sess.current_index < len(items):
        cur_cmd = items[sess.current_index]
        if command_satisfied(cur_cmd["type"], sess.anchor_pose, pose):
            sess.current_index += 1
            sess.anchor_pose = pose

    if sess.current_index >= len(items):
        if not sess.blink_seen:
            sess.status = "FAILED"
            sess.fail_reason_code = "BLINK_NOT_DETECTED"
            await db.commit()
            raise AppError("LIVENESS_FAILED", "Не удалось подтвердить живость (моргните и повторите).", 403)
        sess.status = "PASSED"

    sess.last_seen_at = now
    await db.commit()
    await db.refresh(sess)
    return sess

import base64
from datetime import datetime, timedelta, timezone
from typing import List

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import LivenessError
from app.db import models
from app.schemas.liveness import (
    StartLivenessRequest,
    StartLivenessResponse,
    LivenessCommand,
    LivenessFrameRequest,
    LivenessFrameResponse,
    LivenessProgress,
    FinishLivenessRequest,
    FinishLivenessResponse,
)
from app.services.face_service import (
    get_active_face_embedding,
)
from app.core.config import get_settings

settings = get_settings()

COMMANDS_POOL = [
    LivenessCommand(id="TURN_LEFT", label="Поверните голову влево"),
    LivenessCommand(id="TURN_RIGHT", label="Поверните голову вправо"),
    LivenessCommand(id="TILT", label="Наклоните голову"),
    LivenessCommand(id="NOD", label="Кивните"),
    LivenessCommand(id="BLINK", label="Моргните"),
]


def _generate_commands(n: int = 3) -> List[LivenessCommand]:
    import random

    return random.sample(COMMANDS_POOL, k=n)


def start_liveness(db: Session, req: StartLivenessRequest) -> StartLivenessResponse:
    card = db.query(models.Card).filter_by(uid=req.card_uid).first()
    if not card:
        raise LivenessError("CARD_NOT_FOUND", "Карта не найдена.")

    if card.status != models.CardStatus.ACTIVE:
        raise LivenessError("CARD_BLOCKED", "Карта заблокирована.")

    employee = db.query(models.Employee).get(card.employee_id)
    if not employee or employee.status != models.EmployeeStatus.ACTIVE:
        raise LivenessError("EMPLOYEE_BLOCKED", "Сотрудник заблокирован.")

    ref_embedding = get_active_face_embedding(db, employee.id)
    if ref_embedding is None:
        raise LivenessError("FACE_NOT_ENROLLED", "Для сотрудника не зарегистрировано лицо.")

    commands = _generate_commands(3)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.LIVENESS_SESSION_TTL_SECONDS)

    session = models.LivenessSession(
        employee_id=employee.id,
        card_id=card.id,
        commands=[c.dict() for c in commands],
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return StartLivenessResponse(
        session_id=session.id,
        commands=commands,
        expires_at=session.expires_at,
    )


def _decode_image_b64(b64: str) -> np.ndarray:
    if "," in b64:
        _, b64 = b64.split(",", 1)
    img_bytes = base64.b64decode(b64)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return frame


def _dummy_pose_and_blink(frame: np.ndarray):
    """
    Упрощённый placeholder.
    В реале тут надо вызывать mediapipe FaceMesh и считать yaw/pitch/roll + глаз.
    Возвращаем фиксированные значения, чтобы код работал.
    """
    # TODO: заменить на реальную реализацию с mediapipe
    yaw, pitch, roll = 0.0, 0.0, 0.0
    blink = False
    face_found = frame is not None
    multiple_faces = False
    return face_found, multiple_faces, yaw, pitch, roll, blink


def process_liveness_frame(db: Session, req: LivenessFrameRequest) -> LivenessFrameResponse:
    session: models.LivenessSession = db.query(models.LivenessSession).get(req.session_id)
    if not session:
        raise LivenessError("LIVENESS_SESSION_NOT_FOUND", "Сессия liveness не найдена.")

    now = datetime.now(timezone.utc)
    if session.expires_at < now:
        session.status = models.LivenessStatus.EXPIRED
        session.fail_reason = "LIVENESS_SESSION_EXPIRED"
        db.commit()
        raise LivenessError("LIVENESS_SESSION_EXPIRED", "Сессия проверки личности истекла.")

    commands = [LivenessCommand(**c) for c in session.commands]
    current_cmd = commands[session.current_index]

    if current_cmd.id != req.command_id:
        raise LivenessError("INVALID_COMMAND_ORDER", "Неверный порядок команд.")

    frame = _decode_image_b64(req.image_base64)

    face_found, multiple_faces, yaw, pitch, roll, blink = _dummy_pose_and_blink(frame)

    if not face_found:
        raise LivenessError("NO_FACE_DETECTED", "Лицо не найдено. Подойдите ближе к камере.")
    if multiple_faces:
        raise LivenessError("MULTIPLE_FACES_DETECTED", "В кадре несколько лиц. Оставьте одно лицо.")

    # Проверка совпадения лица — для MVP просто доверяем liveness-сессии,
    # но можно добавить вычисление эмбеддинга и сравнение с ref_embedding.

    # Простая логика: считаем, что команда выполнена, если получено несколько кадров
    # (для MVP — просто по первому кадру считаем "PASSED").
    command_passed = True

    if command_passed:
        session.passed_commands += 1
        session.current_index += 1
        if session.passed_commands >= len(commands):
            session.status = models.LivenessStatus.PASSED
        db.commit()

    cmd_status = "PASSED" if command_passed else "IN_PROGRESS"
    overall_status = session.status.value

    return LivenessFrameResponse(
        command_status=cmd_status,
        overall_status=overall_status,
        reason=None,
        progress=LivenessProgress(
            total_commands=len(commands),
            passed_commands=session.passed_commands,
            current_command_id=current_cmd.id,
        ),
    )


def finish_liveness(db: Session, req: FinishLivenessRequest) -> FinishLivenessResponse:
    session: models.LivenessSession = db.query(models.LivenessSession).get(req.session_id)
    if not session:
        return FinishLivenessResponse(
            status="FAILED",
            liveness_token=None,
            token_expires_at=None,
            employee_id=None,
            error_code="LIVENESS_SESSION_NOT_FOUND",
            message="Сессия проверки личности не найдена.",
        )

    now = datetime.now(timezone.utc)
    if session.expires_at < now and session.status == models.LivenessStatus.PENDING:
        session.status = models.LivenessStatus.EXPIRED
        session.fail_reason = "LIVENESS_SESSION_EXPIRED"
        db.commit()

    if session.status != models.LivenessStatus.PASSED:
        return FinishLivenessResponse(
            status="FAILED",
            liveness_token=None,
            token_expires_at=None,
            employee_id=session.employee_id,
            error_code=session.fail_reason or "LIVENESS_FAILED",
            message="Проверка личности не пройдена.",
        )

    if not session.liveness_token:
        import secrets

        token = secrets.token_urlsafe(16)
        session.liveness_token = token
        session.token_expires_at = now + timedelta(seconds=settings.LIVENESS_TOKEN_TTL_SECONDS)
        db.commit()

    return FinishLivenessResponse(
        status="PASSED",
        liveness_token=session.liveness_token,
        token_expires_at=session.token_expires_at,
        employee_id=session.employee_id,
        error_code=None,
        message="Проверка личности успешно пройдена.",
    )

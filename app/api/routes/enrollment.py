from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.api.deps import get_terminal
from app.core.errors import AppError
from app.db.models import Employee, Face
from app.db.session import get_db
from app.services.face import decode_image, detect_single_face_and_encoding
import numpy as np

router = APIRouter()

@router.post("/api/enroll_face")
async def enroll_face(
    db: AsyncSession = Depends(get_db),
    terminal=Depends(get_terminal),
    employee_id: str = Form(...),
    images: list[UploadFile] = File(...)
):
    emp = (await db.execute(select(Employee).where(Employee.id == employee_id))).scalar_one_or_none()
    if not emp:
        raise AppError("EMPLOYEE_NOT_FOUND", "Сотрудник не найден.", 404)
    if not images or len(images) < 1:
        raise AppError("BAD_REQUEST", "Нужно прислать минимум 1 изображение.")

    embeddings = []
    for f in images[:10]:
        raw = await f.read()
        bgr = decode_image(raw)
        _, emb = detect_single_face_and_encoding(bgr)
        embeddings.append(emb)

    # average embedding
    avg = np.mean(np.stack(embeddings, axis=0), axis=0).astype(np.float32)
    # simple quality: more samples -> better
    quality_score = float(min(1.0, 0.5 + 0.1 * len(embeddings)))

    async with db.begin():
        # deactivate previous
        await db.execute(
            update(Face)
            .where(Face.employee_id == emp.id, Face.is_active == True)
            .values(is_active=False)
        )
        face = Face(employee_id=emp.id, embedding=avg.tolist(), quality_score=quality_score, is_active=True)
        db.add(face)

    await db.refresh(face)
    return {
        "ok": True,
        "data": {
            "employee_id": str(emp.id),
            "face_id": str(face.id),
            "quality_score": face.quality_score,
            "model": face.model
        }
    }

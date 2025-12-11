from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas.faces import EnrollFaceResponse
from app.services.face_service import compute_embedding_from_images, embedding_to_str

router = APIRouter(prefix="/api", tags=["faces"])


@router.post("/enroll_face", response_model=EnrollFaceResponse)
async def enroll_face(
    employee_id: int = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    employee = db.query(models.Employee).get(employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "EMPLOYEE_NOT_FOUND", "message": "Сотрудник не найден."},
        )

    image_bytes_list: List[bytes] = []
    for f in files:
        content = await f.read()
        image_bytes_list.append(content)

    if not image_bytes_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "NO_FILES", "message": "Не загружено ни одного файла."},
        )

    try:
        embedding = compute_embedding_from_images(image_bytes_list)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "NO_FACE_DETECTED",
                "message": "Не удалось найти одно лицо ни на одном из кадров.",
            },
        )

    emb_str = embedding_to_str(embedding)

    # деактивируем старые лица
    db.query(models.Face).filter(
        models.Face.employee_id == employee_id, models.Face.is_active == True
    ).update({models.Face.is_active: False})

    face = models.Face(employee_id=employee_id, embedding=emb_str, is_active=True)
    db.add(face)
    db.commit()
    db.refresh(face)

    return EnrollFaceResponse(status="OK", employee_id=employee_id, face_id=face.id)

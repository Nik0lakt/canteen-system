from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.errors import LivenessError
from app.schemas.liveness import (
    StartLivenessRequest,
    StartLivenessResponse,
    LivenessFrameRequest,
    LivenessFrameResponse,
    FinishLivenessRequest,
    FinishLivenessResponse,
)
from app.services import liveness_service

router = APIRouter(prefix="/api", tags=["liveness"])


@router.post("/start_liveness", response_model=StartLivenessResponse)
def start_liveness(
    req: StartLivenessRequest,
    db: Session = Depends(get_db),
):
    try:
        return liveness_service.start_liveness(db, req)
    except LivenessError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": e.code, "message": e.message},
        )


@router.post("/liveness_frame", response_model=LivenessFrameResponse)
def liveness_frame(
    req: LivenessFrameRequest,
    db: Session = Depends(get_db),
):
    try:
        return liveness_service.process_liveness_frame(db, req)
    except LivenessError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": e.code, "message": e.message},
        )


@router.post("/finish_liveness", response_model=FinishLivenessResponse)
def finish_liveness(
    req: FinishLivenessRequest,
    db: Session = Depends(get_db),
):
    return liveness_service.finish_liveness(db, req)

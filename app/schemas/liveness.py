from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class LivenessCommand(BaseModel):
    id: str
    label: str


class StartLivenessRequest(BaseModel):
    card_uid: str
    client_time: Optional[datetime]


class StartLivenessResponse(BaseModel):
    session_id: UUID
    commands: List[LivenessCommand]
    expires_at: datetime


class LivenessFrameRequest(BaseModel):
    session_id: UUID
    command_id: str
    frame_index: int = Field(ge=0)
    image_base64: str


class LivenessProgress(BaseModel):
    total_commands: int
    passed_commands: int
    current_command_id: str


class LivenessFrameResponse(BaseModel):
    command_status: str
    overall_status: str
    reason: Optional[str]
    progress: LivenessProgress


class FinishLivenessRequest(BaseModel):
    session_id: UUID


class FinishLivenessResponse(BaseModel):
    status: str
    liveness_token: Optional[str]
    token_expires_at: Optional[datetime]
    employee_id: Optional[int]
    error_code: Optional[str]
    message: Optional[str]

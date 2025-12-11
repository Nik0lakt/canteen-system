from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class PayRequest(BaseModel):
    card_uid: str
    canteen_id: int
    amount_cents: int = Field(gt=0)
    liveness_token: str


class PayResponse(BaseModel):
    status: str          # APPROVED / DECLINED
    transaction_id: Optional[UUID]
    amount_total_cents: int
    subsidy_cents: int
    salary_cents: int
    today_subsidy_remaining_cents: int
    monthly_remaining_cents: int
    error_code: Optional[str]
    message: str

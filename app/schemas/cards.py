from pydantic import BaseModel
from enum import Enum
from typing import Optional


class CardStatus(str, Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    LOST = "LOST"


class CardInfo(BaseModel):
    card_uid: str
    employee_id: int
    employee_name: str
    status: CardStatus


class EmployeeInfoForCashier(BaseModel):
    employee_id: int
    full_name: str
    photo_url: Optional[str]
    status: str
    is_worker: bool
    today_subsidy_total_cents: int
    today_subsidy_used_cents: int
    today_subsidy_remaining_cents: int
    monthly_limit_cents: int
    monthly_used_cents: int
    monthly_remaining_cents: int
    has_face: bool
    card_status: CardStatus

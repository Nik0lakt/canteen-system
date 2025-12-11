from pydantic import BaseModel
from typing import Optional
from enum import Enum


class EmployeeType(str, Enum):
    WORKER = "WORKER"
    OFFICE = "OFFICE"


class EmployeeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    TERMINATED = "TERMINATED"


class EmployeeCreate(BaseModel):
    full_name: str
    type: EmployeeType = EmployeeType.WORKER
    personnel_no: Optional[str] = None


class EmployeeRead(BaseModel):
    id: int
    full_name: str
    type: EmployeeType
    status: EmployeeStatus

    class Config:
        orm_mode = True

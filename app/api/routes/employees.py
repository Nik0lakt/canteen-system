from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas.employees import EmployeeCreate, EmployeeRead

router = APIRouter(prefix="/api/employees", tags=["employees"])


@router.post("", response_model=EmployeeRead)
def create_employee(emp: EmployeeCreate, db: Session = Depends(get_db)):
    obj = models.Employee(
        full_name=emp.full_name,
        type=models.EmployeeType(emp.type.value),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("", response_model=list[EmployeeRead])
def list_employees(db: Session = Depends(get_db)):
    return db.query(models.Employee).all()

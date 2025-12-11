from datetime import date
from sqlalchemy.orm import Session

from app.db import models


def is_company_workday(db: Session, d: date) -> bool:
    row = db.query(models.CompanyWorkday).filter_by(date=d).first()
    if row is None:
        # Допущение: по умолчанию рабочий день
        return True
    return row.is_working


def is_employee_workday(db: Session, employee_id: int, d: date) -> bool:
    # если у сотрудника есть индивидуальный выходной в этот день — нерабочий
    row = (
        db.query(models.EmployeeDayOff)
        .filter_by(employee_id=employee_id, date=d)
        .first()
    )
    if row:
        return False
    # иначе смотрим календарь предприятия
    return is_company_workday(db, d)

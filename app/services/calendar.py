from datetime import date
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import CompanyHoliday, EmployeeAbsence

async def is_company_workday(db: AsyncSession, d: date) -> bool:
    # default Mon-Fri, excluding company_holidays
    if d.weekday() >= 5:
        return False
    res = await db.execute(select(CompanyHoliday).where(CompanyHoliday.date == d))
    if res.scalar_one_or_none():
        return False
    return True

async def is_employee_working(db: AsyncSession, employee_id, d: date) -> bool:
    res = await db.execute(
        select(EmployeeAbsence).where(
            and_(
                EmployeeAbsence.employee_id == employee_id,
                EmployeeAbsence.date_from <= d,
                EmployeeAbsence.date_to >= d
            )
        )
    )
    if res.scalar_one_or_none():
        return False
    return True

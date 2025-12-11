import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    Column, BigInteger, Integer, String, Text, Enum,
    DateTime, Date, Boolean, ForeignKey, JSON, CheckConstraint,
    SmallInteger
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.sql import func

from app.db.base import Base


# ---------- Enums ----------

class EmployeeType(str, enum.Enum):
    WORKER = "WORKER"
    OFFICE = "OFFICE"


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    TERMINATED = "TERMINATED"


class CardStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    LOST = "LOST"


class CanteenType(str, enum.Enum):
    CANTEEN = "CANTEEN"
    BUFFET = "BUFFET"


class LivenessStatus(str, enum.Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class TransactionStatus(str, enum.Enum):
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


# ---------- Employees ----------

class Employee(Base):
    __tablename__ = "employees"

    id = Column(BigInteger, primary_key=True, index=True)
    personnel_no = Column(String(50), unique=True, nullable=True)
    full_name = Column(Text, nullable=False)
    type = Column(Enum(EmployeeType), nullable=False)
    status = Column(Enum(EmployeeStatus), nullable=False, default=EmployeeStatus.ACTIVE)
    position = Column(Text, nullable=True)
    department = Column(Text, nullable=True)
    telegram_id = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------- Cards ----------

class Card(Base):
    __tablename__ = "cards"

    id = Column(BigInteger, primary_key=True, index=True)
    uid = Column(String(64), unique=True, nullable=False, index=True)
    employee_id = Column(BigInteger, ForeignKey("employees.id"), nullable=True, index=True)
    status = Column(Enum(CardStatus), nullable=False, default=CardStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------- Faces ----------

class Face(Base):
    __tablename__ = "faces"

    id = Column(BigInteger, primary_key=True, index=True)
    employee_id = Column(BigInteger, ForeignKey("employees.id"), nullable=False, index=True)
    embedding = Column(String, nullable=False)  # будем хранить как base64 строки для простоты
    model_name = Column(String(64), nullable=False, default="face_recognition")
    is_active = Column(Boolean, nullable=False, default=True)
    image_path = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deactivated_at = Column(DateTime(timezone=True), nullable=True)


# ---------- Canteens ----------

class Canteen(Base):
    __tablename__ = "canteens"

    id = Column(SmallInteger, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False)
    name = Column(Text, nullable=False)
    type = Column(Enum(CanteenType), nullable=False)


# ---------- Workdays ----------

class CompanyWorkday(Base):
    __tablename__ = "company_workdays"

    date = Column(Date, primary_key=True)
    is_working = Column(Boolean, nullable=False)


class EmployeeDayOff(Base):
    __tablename__ = "employee_days_off"

    id = Column(BigInteger, primary_key=True, index=True)
    employee_id = Column(BigInteger, ForeignKey("employees.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    reason = Column(Text, nullable=True)


# ---------- Finance ----------

class DailySubsidyUsage(Base):
    __tablename__ = "daily_subsidy_usage"

    id = Column(BigInteger, primary_key=True, index=True)
    employee_id = Column(BigInteger, ForeignKey("employees.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    used_cents = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("used_cents >= 0", name="ck_used_cents_non_negative"),
        CheckConstraint("used_cents <= 10000", name="ck_used_cents_max"),
    )


class MonthlyLimit(Base):
    __tablename__ = "monthly_limits"

    id = Column(BigInteger, primary_key=True, index=True)
    employee_id = Column(BigInteger, ForeignKey("employees.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    limit_cents = Column(BigInteger, nullable=False)
    used_cents = Column(BigInteger, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------- Liveness ----------

class LivenessSession(Base):
    __tablename__ = "liveness_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(BigInteger, ForeignKey("employees.id"), nullable=False, index=True)
    card_id = Column(BigInteger, ForeignKey("cards.id"), nullable=False, index=True)
    status = Column(Enum(LivenessStatus), nullable=False, default=LivenessStatus.PENDING)
    commands = Column(JSON, nullable=False)
    current_index = Column(SmallInteger, nullable=False, default=0)
    passed_commands = Column(SmallInteger, nullable=False, default=0)
    face_match_score = Column(String, nullable=True)
    fail_reason = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    liveness_token = Column(String(64), unique=True, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    token_used = Column(Boolean, nullable=False, default=False)


# ---------- Transactions ----------

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(BigInteger, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    employee_id = Column(BigInteger, ForeignKey("employees.id"), nullable=False, index=True)
    card_id = Column(BigInteger, ForeignKey("cards.id"), nullable=False, index=True)
    canteen_id = Column(SmallInteger, ForeignKey("canteens.id"), nullable=False, index=True)
    liveness_session_id = Column(UUID(as_uuid=True), ForeignKey("liveness_sessions.id"), nullable=True)
    ts = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    amount_total_cents = Column(Integer, nullable=False)
    subsidy_cents = Column(Integer, nullable=False)
    salary_cents = Column(Integer, nullable=False)
    status = Column(Enum(TransactionStatus), nullable=False)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    cashier_client_id = Column(String(64), nullable=True)
    client_ip = Column(String(64), nullable=True)

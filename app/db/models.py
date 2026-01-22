import uuid
from sqlalchemy import (
    String, Text, Date, DateTime, Boolean, Integer, BigInteger, ForeignKey,
    CheckConstraint, JSON, func, Float
)
from sqlalchemy.dialects.postgresql import UUID, BYTEA
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

class Base(DeclarativeBase):
    pass

class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tab_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    employee_type: Mapped[str] = mapped_column(String(16), nullable=False)  # WORKER / ITR
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")  # ACTIVE/BLOCKED
    monthly_limit_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    photo_jpeg: Mapped[bytes | None] = mapped_column(BYTEA, nullable=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())

    cards = relationship("Card", back_populates="employee")
    faces = relationship("Face", back_populates="employee")

    __table_args__ = (
        CheckConstraint("employee_type in ('WORKER','ITR')", name="ck_employee_type"),
        CheckConstraint("status in ('ACTIVE','BLOCKED')", name="ck_employee_status"),
    )

class Card(Base):
    __tablename__ = "cards"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uid: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    issued_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="cards")

    __table_args__ = (CheckConstraint("status in ('ACTIVE','BLOCKED')", name="ck_card_status"),)

class Face(Base):
    __tablename__ = "faces"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(128), nullable=False)  # pgvector
    model: Mapped[str] = mapped_column(String(64), nullable=False, default="face_recognition/dlib_128")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="faces")

class DailyBalance(Base):
    __tablename__ = "daily_balance"
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True)
    date: Mapped = mapped_column(Date, primary_key=True)
    used_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

class MonthlyBalance(Base):
    __tablename__ = "monthly_balance"
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), primary_key=True)
    year_month: Mapped[int] = mapped_column(Integer, primary_key=True)  # YYYYMM
    limit_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    used_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

class Terminal(Base):
    __tablename__ = "terminals"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=True)
    api_token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("status in ('ACTIVE','BLOCKED')", name="ck_terminal_status"),)

class CompanyHoliday(Base):
    __tablename__ = "company_holidays"
    date: Mapped = mapped_column(Date, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=True)

class EmployeeAbsence(Base):
    __tablename__ = "employee_absences"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    date_from: Mapped = mapped_column(Date, nullable=False)
    date_to: Mapped = mapped_column(Date, nullable=False)
    absence_type: Mapped[str] = mapped_column(String(32), nullable=False)  # VACATION/SICK/OFF

class LivenessSession(Base):
    __tablename__ = "liveness_sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    terminal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("terminals.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="IN_PROGRESS")  # IN_PROGRESS/PASSED/FAILED/EXPIRED/USED
    commands: Mapped[dict] = mapped_column(JSON, nullable=False)  # {"items":[...]}
    current_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    baseline_pose: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    anchor_pose: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fail_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped = mapped_column(DateTime(timezone=True), nullable=True)
    min_face_dist: Mapped[float | None] = mapped_column(Float, nullable=True)
    blink_seen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    used_at: Mapped = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status in ('IN_PROGRESS','PASSED','FAILED','EXPIRED','USED')", name="ck_liveness_status"),
    )

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    terminal_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("terminals.id", ondelete="RESTRICT"))
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="RESTRICT"), index=True)

    card_uid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    subsidy_spent_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    monthly_spent_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # APPROVED/DECLINED
    decline_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decline_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    liveness_session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (CheckConstraint("status in ('APPROVED','DECLINED')", name="ck_tx_status"),)

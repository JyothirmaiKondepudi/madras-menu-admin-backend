from sqlalchemy import Column, String, DateTime, func, Boolean, text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from database import Base
from enum import StrEnum
from models.choices import CustomerStatus


def check_in(column: str, choices: type[StrEnum]) -> str:
    """SQL for a CHECK constraint limiting `column` to the enum's values."""
    values = ", ".join(f"'{choice.value}'" for choice in choices)
    return f"{column} IN ({values})"


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint(
            check_in("status", CustomerStatus),
            name="customer_status_check",
        ),
    )
    customer_id = Column(
        "customer_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_name = Column("customer_name", String, nullable=False)
    customer_email = Column("customer_email", String, unique=True, nullable=False)
    billing_email = Column(
        "billing_email",
        String,
        nullable=False,
    )
    customer_phone_number = Column("phone_number", String(10), nullable=True)
    plan = Column("plan", String, nullable=False)

    created_at = Column(
        "created_at", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    customer_disabled = Column(
        "customer_disabled", Boolean, nullable=False, server_default=text("false")
    )

    plan_start_date = Column("plan_start_date", DateTime(timezone=True), nullable=False)
    status = Column("status", String, nullable=False)
    plan_end_date = Column("plan_end_date", DateTime(timezone=True), nullable=True)
    updated_at = Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    customer_org_id = Column(
        "customer_org_id",
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

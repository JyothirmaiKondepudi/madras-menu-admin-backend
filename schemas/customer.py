from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from uuid import UUID
from datetime import datetime

from models.choices import CustomerStatus


class Customer(BaseModel):

    customer_id: UUID
    customer_name: str
    customer_email: str
    customer_phone_number: str | None = None
    billing_email: str
    status: CustomerStatus
    plan: str
    plan_start_date: datetime
    plan_end_date: datetime | None = None
    created_at: datetime
    updated_at: datetime
    customer_org_id: UUID
    customer_disabled: bool

    model_config = ConfigDict(from_attributes=True)


def _normalize_email(value: str | None) -> str | None:
    # lowercased so the UNIQUE constraint also catches "A@x.com" vs "a@x.com"
    return value.strip().lower() if value is not None else None


class CustomerCreate(BaseModel):
    """What staff type in. The server sets the id, timestamps and customer_disabled."""

    customer_name: str = Field(min_length=1)
    customer_email: str = Field(min_length=3)
    billing_email: str = Field(min_length=3)
    customer_phone_number: str | None = Field(default=None, max_length=10)
    plan: str = Field(min_length=1)
    status: CustomerStatus = CustomerStatus.TRIAL
    plan_start_date: datetime
    plan_end_date: datetime | None = None
    # the org in the customer DB; can't be checked until the internal API exists
    customer_org_id: UUID

    _emails = field_validator("customer_email", "billing_email")(_normalize_email)

    @model_validator(mode="after")
    def _end_after_start(self):
        if self.plan_end_date and self.plan_end_date < self.plan_start_date:
            raise ValueError("plan_end_date must not be before plan_start_date")
        return self


class CustomerUpdate(BaseModel):
    """Partial update: only the fields sent are changed.

    customer_org_id is left out on purpose (a customer can't move to another
    org), and customer_disabled has its own /disable and /enable endpoints.
    """

    customer_name: str | None = Field(default=None, min_length=1)
    customer_email: str | None = Field(default=None, min_length=3)
    billing_email: str | None = Field(default=None, min_length=3)
    customer_phone_number: str | None = Field(default=None, max_length=10)
    plan: str | None = Field(default=None, min_length=1)
    status: CustomerStatus | None = None
    plan_start_date: datetime | None = None
    plan_end_date: datetime | None = None

    _emails = field_validator("customer_email", "billing_email")(_normalize_email)

    @model_validator(mode="after")
    def _required_fields_not_null(self):
        # these columns are NOT NULL: sending null is a 422, leaving them out is fine
        nullable = {"customer_phone_number", "plan_end_date"}
        for name in self.model_fields_set - nullable:
            if getattr(self, name) is None:
                raise ValueError(f"{name} can't be null")
        return self

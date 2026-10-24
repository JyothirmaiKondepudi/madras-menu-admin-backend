from pydantic import BaseModel, ConfigDict
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

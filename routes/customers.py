from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from models import Customer
from models.choices import CustomerStatus
from schemas.customer import Customer as CustomerOut
from schemas.customer import CustomerCreate, CustomerUpdate

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


def _get_or_404(db: Session, customer_id: UUID) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Customer not found")
    return customer


def _commit(db: Session) -> None:
    # The UNIQUE constraint is the real duplicate check: a SELECT first would
    # still let two requests at the same moment both pass.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A customer with this email already exists"
        )


@router.get("", response_model=list[CustomerOut])
def list_customers(
    status_filter: CustomerStatus | None = Query(default=None, alias="status"),
    disabled: bool | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(Customer)
    if status_filter is not None:
        query = query.where(Customer.status == status_filter)
    if disabled is not None:
        query = query.where(Customer.customer_disabled == disabled)
    query = query.order_by(Customer.created_at.desc(), Customer.customer_id)
    return db.scalars(query.limit(limit).offset(offset)).all()


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: UUID, db: Session = Depends(get_db)):
    return _get_or_404(db, customer_id)


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerCreate, db: Session = Depends(get_db)):
    customer = Customer(**body.model_dump())
    db.add(customer)
    _commit(db)
    db.refresh(customer)
    return customer


@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: UUID, body: CustomerUpdate, db: Session = Depends(get_db)
):
    customer = _get_or_404(db, customer_id)
    for name, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, name, value)
    # checked here, not in the schema: a PATCH may send only one of the two dates
    if customer.plan_end_date and customer.plan_end_date < customer.plan_start_date:
        db.rollback()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "plan_end_date must not be before plan_start_date",
        )
    _commit(db)
    db.refresh(customer)
    return customer


# Separate from PATCH because disabling will later also call the customer
# service's internal API to set org_disabled; for now it's only recorded here.
@router.post("/{customer_id}/disable", response_model=CustomerOut)
def disable_customer(customer_id: UUID, db: Session = Depends(get_db)):
    return _set_disabled(db, customer_id, True)


@router.post("/{customer_id}/enable", response_model=CustomerOut)
def enable_customer(customer_id: UUID, db: Session = Depends(get_db)):
    return _set_disabled(db, customer_id, False)


def _set_disabled(db: Session, customer_id: UUID, disabled: bool) -> Customer:
    customer = _get_or_404(db, customer_id)
    if customer.customer_disabled != disabled:  # idempotent: no write if unchanged
        customer.customer_disabled = disabled
        db.commit()
        db.refresh(customer)
    return customer

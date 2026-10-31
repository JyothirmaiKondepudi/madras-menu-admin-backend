from fastapi import FastAPI, Depends

from sqlalchemy import select
from sqlalchemy.orm import Session


from database import get_db

from config import get_settings
from routes import customers

app = FastAPI()

settings = get_settings()

app.include_router(customers.router)


@app.get("/db/health")
def db_health_status(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@app.get("/")
def health_status():

    return {"status": "ok"}

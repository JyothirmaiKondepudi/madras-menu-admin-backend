from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


from config import database_pool_settings, database_url

DATABASE_URL = database_url()
pool = database_pool_settings()
engine = create_engine(
    DATABASE_URL,
    pool_size=pool.DB_POOL_SIZE,
    max_overflow=pool.DB_MAX_OVERFLOW,  # burst headroom on top of pool_size
    pool_timeout=pool.DB_POOL_TIMEOUT,  # fail fast instead of hanging 30s
    pool_pre_ping=True,  # detect dead connections before using them
    pool_recycle=1800,  # replace connections older than 30 min
    # don't hang if the DB is unreachable
    connect_args={"connect_timeout": pool.DB_CONNECTION_TIMEOUT},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Foreign keys without an explicit name= get the same name Postgres would
# give them (<table>_<column>_fkey), so migrations can drop and recreate them.
# "ix" is SQLAlchemy's default for index=True; it has to be repeated here
# because passing naming_convention replaces the defaults.
Base = declarative_base(
    metadata=MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "fk": "%(table_name)s_%(column_0_name)s_fkey",
        }
    )
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

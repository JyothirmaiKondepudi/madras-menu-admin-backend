"""Settings read from the environment, validated in one place.

main.py calls get_settings() at import, so the app refuses to start with a
missing or invalid setting and lists every problem at once, instead of
failing later (e.g. on the first login when SECRET_KEY is missing).

Scripts and Alembic only need the database, so database.py uses
database_url() and database_pool_settings(), and they don't need SECRET_KEY
or the other app settings.
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator


class ConfigError(RuntimeError):
    """A required setting is missing or invalid."""


class Settings(BaseModel):
    DATABASE_URL: str
    # signs login tokens; generate one with: openssl rand -hex 32
    SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    JWT_EXPIRE_MINUTES: int = Field(default=720, gt=0)
    # comma-separated in the environment
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("DATABASE_URL")
    @classmethod
    def _postgres_url(cls, value: str) -> str:
        if not value.startswith("postgresql"):
            raise ValueError("must be a postgresql:// URL")
        return value

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value):
        if isinstance(value, str):
            value = [origin.strip() for origin in value.split(",") if origin.strip()]
        for origin in value:
            if not origin.startswith(("http://", "https://")):
                raise ValueError(f"{origin!r} must start with http:// or https://")
        return value


class DatabaseSettings(BaseModel):
    """Connection pool settings, kept apart from Settings so scripts and
    Alembic can build the engine without SECRET_KEY. Per instance, at most
    DB_POOL_SIZE + DB_MAX_OVERFLOW connections are open at once."""

    DB_POOL_SIZE: int = Field(default=5, gt=0)
    DB_MAX_OVERFLOW: int = Field(default=5, ge=0)
    # seconds to wait for a free connection before giving up
    DB_POOL_TIMEOUT: int = Field(default=10, gt=0)
    # seconds to wait when opening a connection to an unreachable database
    DB_CONNECTION_TIMEOUT: int = Field(default=5, gt=0)


class PasswordSettings(BaseModel):
    """Kept apart from Settings so seed scripts can hash passwords without
    SECRET_KEY. Each step up doubles the time to hash and to check a
    password (12 is about 0.2 s): slower for an attacker trying guesses,
    and slower for every login. 4 to 31 is the range bcrypt accepts;
    the tests use 4 so they don't spend minutes hashing."""

    BCRYPT_ROUNDS: int = Field(default=12, ge=4, le=31)


def _from_environment(names) -> dict[str, str]:
    # an empty value (e.g. "SECRET_KEY=" copied from the example file) counts as unset
    return {
        name: os.environ[name] for name in names if os.environ.get(name, "").strip()
    }


def _load(model):
    try:
        return model(**_from_environment(model.model_fields))
    except ValidationError as exc:
        # messages only, never the values: SECRET_KEY must not end up in logs
        problems = "\n".join(
            f"  {'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise ConfigError(f"Invalid configuration:\n{problems}") from None


def load_settings() -> Settings:
    return _load(Settings)


@lru_cache
def get_settings() -> Settings:
    return load_settings()


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise ConfigError("Invalid configuration:\n  DATABASE_URL: Field required")
    return url


def database_pool_settings() -> DatabaseSettings:
    return _load(DatabaseSettings)


@lru_cache
def password_settings() -> PasswordSettings:
    return _load(PasswordSettings)

"""SQLAlchemy declarative base shared by every model."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Common declarative base for all ORM models."""

    pass

"""Declarative base and shared model mixins."""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model in the app."""


class TimestampMixin:
    """Adds `created_at` / `updated_at` columns, set by the database itself.

    Every domain entity in this system needs a "Date Added" / "Last Updated"
    pair (products, suppliers, purchase orders, ...). Defining it once here
    keeps that consistent instead of re-declaring two columns per model.
    """

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

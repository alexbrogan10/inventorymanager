from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    contact_person: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(50))
    address: Mapped[str] = mapped_column(Text)
    # Typical days between placing a purchase order and receiving stock -
    # feeds the reorder-point/forecasting math in later AI milestones.
    lead_time_days: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

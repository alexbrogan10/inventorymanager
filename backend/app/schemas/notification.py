from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationSeverity, NotificationType


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: NotificationType
    severity: NotificationSeverity
    title: str
    message: str
    product_id: int | None
    purchase_order_id: int | None
    is_read: bool
    created_at: datetime


class PaginatedNotifications(BaseModel):
    items: list[NotificationRead]
    total: int
    page: int
    page_size: int


class UnreadCount(BaseModel):
    count: int


class MarkAllReadResult(BaseModel):
    marked_count: int

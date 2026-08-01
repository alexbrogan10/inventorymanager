from datetime import date
from typing import Protocol

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationSeverity, NotificationType


class AbstractNotificationRepository(Protocol):
    def create(
        self,
        *,
        type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        product_id: int | None,
        purchase_order_id: int | None,
    ) -> Notification: ...

    def list_paginated(
        self, *, page: int, page_size: int, unread_only: bool
    ) -> tuple[list[Notification], int]: ...

    def get_by_id(self, notification_id: int) -> Notification | None: ...

    def count_unread(self) -> int: ...

    def mark_read(self, notification: Notification) -> Notification: ...

    def mark_all_read(self) -> int: ...

    def has_unread_of_type(self, type: NotificationType, product_id: int) -> bool: ...

    def has_notification_today(
        self, type: NotificationType, product_id: int, today: date
    ) -> bool: ...


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        type: NotificationType,
        severity: NotificationSeverity,
        title: str,
        message: str,
        product_id: int | None,
        purchase_order_id: int | None,
    ) -> Notification:
        notification = Notification(
            type=type,
            severity=severity,
            title=title,
            message=message,
            product_id=product_id,
            purchase_order_id=purchase_order_id,
        )
        self._db.add(notification)
        self._db.commit()
        self._db.refresh(notification)
        return notification

    def list_paginated(
        self, *, page: int, page_size: int, unread_only: bool
    ) -> tuple[list[Notification], int]:
        conditions = [Notification.is_read.is_(False)] if unread_only else []

        count_query = select(func.count(Notification.id)).where(*conditions)
        total = self._db.execute(count_query).scalar_one()

        page_query = (
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self._db.execute(page_query).scalars())
        return items, total

    def get_by_id(self, notification_id: int) -> Notification | None:
        return self._db.execute(
            select(Notification).where(Notification.id == notification_id)
        ).scalar_one_or_none()

    def count_unread(self) -> int:
        query = select(func.count(Notification.id)).where(Notification.is_read.is_(False))
        return self._db.execute(query).scalar_one()

    def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        self._db.commit()
        self._db.refresh(notification)
        return notification

    def mark_all_read(self) -> int:
        unread = list(
            self._db.execute(select(Notification).where(Notification.is_read.is_(False))).scalars()
        )
        for notification in unread:
            notification.is_read = True
        self._db.commit()
        return len(unread)

    def has_unread_of_type(self, type: NotificationType, product_id: int) -> bool:
        """Used to avoid re-notifying a condition (low stock, overstock)
        that's already been raised and not yet acknowledged - once the user
        marks it read, a still-ongoing condition is free to notify again."""
        query = select(Notification.id).where(
            Notification.type == type,
            Notification.product_id == product_id,
            Notification.is_read.is_(False),
        )
        return self._db.execute(query).first() is not None

    def has_notification_today(self, type: NotificationType, product_id: int, today: date) -> bool:
        """Used to cap one-off events (anomaly) at one notification per
        product per day, regardless of read state - unlike an ongoing
        threshold breach, "unusual demand today" stops being relevant once
        the day is over, so read state shouldn't let it re-fire."""
        query = select(Notification.id).where(
            Notification.type == type,
            Notification.product_id == product_id,
            cast(Notification.created_at, Date) == today,
        )
        return self._db.execute(query).first() is not None

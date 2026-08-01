"""Notifications: system-wide operational alerts (low stock, overstock,
order arrived, demand anomalies) - every authenticated user can read and
acknowledge them, since they're relevant to whoever is working the system,
not scoped to whoever triggered the underlying event. There is no create
endpoint - notifications are only ever produced as a side effect of
`SaleService`/`PurchaseOrderService` (see `NotificationService`).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.notification import Notification
from app.repositories.forecast_repository import ForecastRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import (
    MarkAllReadResult,
    NotificationRead,
    PaginatedNotifications,
    UnreadCount,
)
from app.services.notification_service import NotificationNotFoundError, NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(NotificationRepository(db), ForecastRepository(db))


@router.get("", response_model=PaginatedNotifications, dependencies=[Depends(get_current_user)])
def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    service: NotificationService = Depends(get_notification_service),
) -> PaginatedNotifications:
    return service.list_notifications(page, page_size, unread_only)


@router.get("/unread-count", response_model=UnreadCount, dependencies=[Depends(get_current_user)])
def get_unread_count(
    service: NotificationService = Depends(get_notification_service),
) -> UnreadCount:
    return UnreadCount(count=service.unread_count())


@router.patch(
    "/read-all", response_model=MarkAllReadResult, dependencies=[Depends(get_current_user)]
)
def mark_all_notifications_read(
    service: NotificationService = Depends(get_notification_service),
) -> MarkAllReadResult:
    return MarkAllReadResult(marked_count=service.mark_all_read())


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationRead,
    dependencies=[Depends(get_current_user)],
)
def mark_notification_read(
    notification_id: int, service: NotificationService = Depends(get_notification_service)
) -> Notification:
    try:
        return service.mark_read(notification_id)
    except NotificationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found."
        ) from exc

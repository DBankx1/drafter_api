import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repository.widget_repository import WidgetRepository
from app.models.dto.widget import WidgetSettingsCreate, WidgetSettingsUpdate
from app.models.entity.widget_settings import WidgetSettingsEntity

logger = logging.getLogger(__name__)


class WidgetService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.widget_repo = WidgetRepository(db)

    async def create_widget_settings(self, business_id: str, data: WidgetSettingsCreate) -> WidgetSettingsEntity:
        exists = (await self.widget_repo.get_by_business_id(business_id)) is not None

        if exists:
            raise ValueError(f"Widget settings already exist for business with id {business_id}")

        widget_settings = await self.widget_repo.create(
            business_id=business_id,
            name=data.name,
            primary_color=data.primary_color,
            secondary_color=data.secondary_color,
            position=data.position,
            logo_url=data.logo_url,
            welcome_message=data.welcome_message,
            created_at=datetime.now(timezone.utc),
        )

        logger.info(f"Created widget settings {widget_settings.id} for business {business_id}")
        return widget_settings

    async def get_widget_settings(self, business_id: str) -> WidgetSettingsEntity:
        """Returns widget settings for a business. Raises ValueError if none exist."""
        widget_settings = await self.widget_repo.get_by_business_id(business_id)

        if widget_settings is None:
            raise ValueError(f"Widget settings not found for business with id {business_id}")

        return widget_settings

    async def update_widget_settings(self, business_id: str, data: WidgetSettingsUpdate) -> WidgetSettingsEntity:
        """Partially updates widget settings for a business. Raises ValueError if none exist."""
        widget_settings = await self.widget_repo.get_by_business_id(business_id)

        if widget_settings is None:
            raise ValueError(f"Widget settings not found for business with id {business_id}")

        updates = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}

        updated = await self.widget_repo.update(widget_settings.id, **updates)

        logger.info(f"Updated widget settings {widget_settings.id} for business {business_id}")
        return updated

    async def delete_widget_settings(self, business_id: str) -> None:
        widget_settings = await self.widget_repo.get_by_business_id(business_id)

        if widget_settings is None:
            raise ValueError(f"Widget settings not found for business with id {business_id}")

        await self.widget_repo.delete(widget_settings.id)
        logger.info(f"Deleted widget settings {widget_settings.id} for business {business_id}")

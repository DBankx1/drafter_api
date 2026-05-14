import logging
from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.repository.base_repository import BaseRepository
from app.models.entity.widget_settings import WidgetSettingsEntity

logger = logging.getLogger(__name__)


class WidgetRepository(BaseRepository[WidgetSettingsEntity]):

    def __init__(self, db: AsyncSession):
        super().__init__(WidgetSettingsEntity, db)

    async def get_by_business_id(self, business_id: str) -> Optional[WidgetSettingsEntity]:
        try:
            stmt = select(WidgetSettingsEntity).where(WidgetSettingsEntity.business_id == business_id)
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving widget settings for business {business_id}: {str(e)}")
            raise

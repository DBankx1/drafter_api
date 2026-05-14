from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.middlewares.business_auth import get_user_business
from app.infrastructure.database.db import get_db
from app.models.dto.widget import WidgetSettingsCreate, WidgetSettingsResponse, WidgetSettingsUpdate
from app.models.entity.business import BusinessEntity
from app.services.widget_service import WidgetService


router = APIRouter(tags=["widget"], prefix="/widget")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_widget_settings(
    data: WidgetSettingsCreate,
    db: AsyncSession = Depends(get_db),
    business: BusinessEntity = Depends(get_user_business),
) -> WidgetSettingsResponse:
    service = WidgetService(db)
    try:
        widget_settings = await service.create_widget_settings(business.id, data)
        return WidgetSettingsResponse.model_validate(widget_settings)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("")
async def get_widget_settings(
    db: AsyncSession = Depends(get_db),
    business: BusinessEntity = Depends(get_user_business),
) -> WidgetSettingsResponse:
    service = WidgetService(db)
    try:
        widget_settings = await service.get_widget_settings(business.id)
        return WidgetSettingsResponse.model_validate(widget_settings)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("")
async def update_widget_settings(
    data: WidgetSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    business: BusinessEntity = Depends(get_user_business),
) -> WidgetSettingsResponse:
    service = WidgetService(db)
    try:
        widget_settings = await service.update_widget_settings(business.id, data)
        return WidgetSettingsResponse.model_validate(widget_settings)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget_settings(
    db: AsyncSession = Depends(get_db),
    business: BusinessEntity = Depends(get_user_business),
) -> None:
    service = WidgetService(db)
    try:
        await service.delete_widget_settings(business.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

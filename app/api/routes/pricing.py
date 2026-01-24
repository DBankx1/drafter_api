from fastapi import APIRouter

router = APIRouter(tags=["pricing"], prefix="/pricing")


@router.get("/")
async def get_pricing() -> str:
    return "OK"

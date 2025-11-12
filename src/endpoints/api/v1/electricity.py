from fastapi import APIRouter

from services.electricity_prices import get_electricity_prices

electricity_router = APIRouter(
    prefix="/electricity",
)


@electricity_router.get("/prices")
async def get_electricity_prices_endpoint():

    return await get_electricity_prices()

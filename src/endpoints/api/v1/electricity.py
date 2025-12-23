import httpx
from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from db.base import get_session
from services.electricity_prices import (
    get_electricity_prices,
    save_electricity_prices_to_db,
)
from src.models.electricity_price_models import ElectricityPriceResponse

electricity_router = APIRouter(
    prefix="/electricity",
)


@electricity_router.get("/prices")
async def get_electricity_prices_endpoint(
    req: Request, session: Session = Depends(get_session)
) -> ElectricityPriceResponse:
    """
    Fetch electricity prices from external API and save them to the database.

    :param req: Request object
    :type req: Request
    :param session: Database session
    :type session: Session
    :return: Electricity prices response
    :rtype: ElectricityPriceResponse
    """
    client: httpx.AsyncClient = req.app.state.http_client
    prices = await get_electricity_prices(client)
    await save_electricity_prices_to_db(prices, session)
    return prices

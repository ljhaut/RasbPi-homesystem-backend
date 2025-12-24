import httpx
from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from db.base import get_session
from models.electricity_price_models import ElectricityPriceResponse
from services.electricity_prices import (
    get_electricity_prices,
    save_electricity_prices_to_db,
)

electricity_router = APIRouter(
    prefix="/electricity",
)


@electricity_router.get("/prices")
async def fetch_and_save_prices(
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
    save_electricity_prices_to_db(prices, session)
    return prices

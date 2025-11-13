import httpx
import xmltodict
from sqlmodel import Session

from core.config import app_settings
from core.logging_config import setup_logger
from helpers.elec_prices_helpers import get_today_and_tomorrow_dates
from models.electricity_price_models import ElectricityPriceResponse, Point

logger = setup_logger()


async def get_electricity_prices() -> ElectricityPriceResponse:
    today, tomorrow = get_today_and_tomorrow_dates()

    payload = {
        "securityToken": app_settings.ENTSOE_API_KEY,
        "documentType": "A44",
        "in_Domain": "10YFI-1--------U",
        "out_Domain": "10YFI-1--------U",
        "periodStart": f"{today}0000",
        "periodEnd": f"{tomorrow}0000",
    }

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                app_settings.ENTSOE_API_URL, params=payload, timeout=10.0
            )

        xml_string = r.content.decode("utf-8")

        xml_dict = xmltodict.parse(xml_string)

        try:
            validated_data = ElectricityPriceResponse(**xml_dict)
            return validated_data
        except Exception as e:
            logger.error(f"Failed to validate electricity price data: {e}")
            raise

    except httpx.RequestError as e:
        logger.error(f"HTTP request failed: {e}")
        raise


async def save_electricity_prices_to_db(
    prices: ElectricityPriceResponse, session: Session
) -> None:
    document = prices.publication_market_document
    series_list = (
        document.time_series
        if isinstance(document.time_series, list)
        else [document.time_series]
    )

    for series in series_list:
        points = series.period.point
        last_valid_price_amount = None
        i = 0
        while i < len(points):
            position = int(points[i].position)
            price_amount = points[i].price_amount
            last_position = int(points[i - 1].position) if i > 0 else None
            if position - 1 != last_position:  # if there is a gap in positions
                if last_valid_price_amount is None:  # no prior valid price to use
                    logger.warning(
                        "Missing position between %s and %s but no prior price is available",
                        last_position,
                        position,
                    )
                else:
                    logger.info(
                        f"Missing position between {last_position} and {position}"
                    )
                    points.insert(  # insert a new point to fill the gap
                        i,
                        Point(
                            position=str(position - 1),
                            **{"price.amount": last_valid_price_amount},
                        ),
                    )
                    continue

            last_valid_price_amount = price_amount
            i += 1
            logger.info(f"Processed position {position} with price {price_amount}")

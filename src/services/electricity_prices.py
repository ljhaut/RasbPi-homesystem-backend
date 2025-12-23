from collections.abc import Iterable
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx
import xmltodict
from sqlmodel import Session, select

from core.config import app_settings
from core.logging_config import setup_logger
from db.models import ElectricityPrices
from helpers.elec_prices_helpers import (
    get_today_and_tomorrow_dates,
    position_to_timestamp,
)
from models.electricity_price_models import ElectricityPriceResponse, Point, TimeSeries

logger = setup_logger()


async def get_electricity_prices(client: httpx.AsyncClient) -> ElectricityPriceResponse:
    """
    Fetch electricity prices from the ENTSOE API

    :param client: HTTPX AsyncClient for making requests
    :type client: httpx.AsyncClient
    :return: Instance of ElectricityPriceResponse containing the electricity prices
    :rtype: ElectricityPriceResponse
    """
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
        r = await client.get(app_settings.ENTSOE_API_URL, params=payload, timeout=10.0)

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


def save_electricity_prices_to_db(
    prices: ElectricityPriceResponse,
    session: Session,
) -> None:
    """
    Save electricity prices to the database

    :param prices: Instance of ElectricityPriceResponse containing the electricity prices
    :type prices: ElectricityPriceResponse
    :param session: Database session for saving the prices
    :type session: Session
    """
    logger.info("Saving electricity prices to database")

    document = prices.publication_market_document
    series_list = (
        document.time_series
        if isinstance(document.time_series, list)
        else [document.time_series]
    )

    new_rows_to_db: list[ElectricityPrices] = []

    for series in series_list:
        points = series.period.point

        day = datetime.fromisoformat(
            series.period.time_interval.end.replace("Z", "+00:00")
        ).strftime("%Y%m%d")

        last_valid_price_amount = None
        i = 0
        while i < len(points):
            position = int(points[i].position)
            price_amount = points[i].price_amount
            last_position = int(points[i - 1].position) if i > 0 else None
            if i == 0 and position > 1:
                logger.warning(
                    f"First position is {position}, expected 1. This shouldn't happen, please check the data."
                )
            if (
                position - 1 != last_position and last_position is not None
            ):  # if there is a gap in positions
                if last_valid_price_amount is None:
                    logger.warning(
                        f"Missing position between {last_position} and {position}, and no last valid price to fill in."
                    )
                else:
                    logger.info(
                        f"Filling missing position between {last_position} and {position} with last valid price {last_valid_price_amount}."
                    )
                    points.insert(  # insert a new point to fill the gap
                        i,
                        Point(
                            position=str(position - 1),
                            **{"price.amount": last_valid_price_amount},
                        ),
                    )
                    continue  # re-evaluate the current index after insertion

            last_valid_price_amount = price_amount
            i += 1

            timestamp = position_to_timestamp(position, day)

            # db transactions
            price = session.exec(
                select(ElectricityPrices).where(
                    ElectricityPrices.timestamp == timestamp
                )
            ).first()
            if price:
                continue  # skip existing records

            new_rows_to_db.append(
                ElectricityPrices(
                    timestamp=timestamp,
                    price_amount_mwh_eur=price_amount,
                )
            )

    if new_rows_to_db:
        try:
            session.add_all(new_rows_to_db)
            session.commit()
            logger.info(
                f"Inserted {len(new_rows_to_db)} new electricity price records."
            )
        except Exception as e:
            session.rollback()
            raise e
    else:
        logger.info("No new electricity price records to insert.")

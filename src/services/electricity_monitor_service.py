import asyncio
from datetime import datetime, time, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

import httpx
from sqlmodel import select

from controllers.pico_controller import PicoController
from core.config import app_settings
from core.logging_config import setup_logger
from db.base import get_session
from db.models import ElectricityPrices
from helpers.common import get_current_point_index, get_current_quarter_timestamp
from models.electricity_price_models import ElectricityPriceResponse, Point
from services.electricity_prices import (
    get_electricity_prices,
    save_electricity_prices_to_db,
)

logger = setup_logger()


class ElectricityMonitorService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        pico_controller: Optional[PicoController] = None,
    ):
        self.client = client
        # self.pico_controller = pico_controller or PicoController()
        self.is_running = False
        self.current_prices: Optional[ElectricityPriceResponse] = None

    async def start(self):
        """Start the background monitoring service"""
        self.is_running = True
        logger.info("Electricity monitor service started.")

        await asyncio.gather(self._monitor_prices_task())

    async def stop(self):
        """Stop the background monitoring service"""
        self.is_running = False
        logger.info("Electricity monitor service stopped.")

    async def _monitor_prices_task(self):
        """Monitor current prices and control Pico pins"""
        while self.is_running:
            price = self._get_current_price_c_per_kwh_vat()
            if price is None:
                logger.warning(
                    "Cannot get current electricity price. Trying to fetch new prices."
                )
                await self._fetch_and_save_prices()

            await asyncio.sleep(10)  # Check every 10 seconds

    async def _fetch_and_save_prices(self):
        """Fetch electricity prices and save them to the database"""
        try:
            prices = await get_electricity_prices(self.client)
            session = next(get_session())
            await save_electricity_prices_to_db(prices, session)
        except Exception as e:
            logger.error(
                f"Failed to fetch and save electricity prices by electricity_monitor_service: {e}"
            )

    def _get_current_price_c_per_kwh_vat(self) -> Optional[float]:
        """Get the current electricity price in cents per kWh including VAT"""
        session = next(get_session())

        timestamp = get_current_quarter_timestamp()

        row = session.exec(
            select(ElectricityPrices).where(ElectricityPrices.timestamp == timestamp)
        ).first()

        logger.debug(f"Database row for timestamp {timestamp}: {row}")

        if row:
            eur_per_kwh = row.price_amount_mwh_eur / 1000.0
            eur_per_kwh_vat = eur_per_kwh * (
                1 + app_settings.FINNISH_VAT_PERCENTAGE / 100
            )
            cents_per_kwh_vat = round(eur_per_kwh_vat * 100.0, 2)
            logger.info(
                f"Current electricity price at {timestamp}: {cents_per_kwh_vat} cents/kWh (including VAT)"
            )
            return cents_per_kwh_vat
        else:
            logger.warning(f"No electricity price found for timestamp {timestamp}")
            return None

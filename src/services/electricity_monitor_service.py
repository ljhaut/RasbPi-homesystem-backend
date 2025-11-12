import asyncio
from datetime import datetime, time
from typing import List, Optional
from zoneinfo import ZoneInfo

from controllers.pico_controller import PicoController
from core.config import app_settings
from core.logging_config import setup_logger
from models.electricity_price_models import ElectricityPriceResponse, Point
from services.electricity_prices import get_electricity_prices

logger = setup_logger()


class ElectricityMonitorService:
    def __init__(self, pico_controller: Optional[PicoController] = None):
        # self.pico_controller = pico_controller or PicoController()
        self.is_running = False
        self.current_prices: Optional[ElectricityPriceResponse] = None

    async def start(self):
        """Start the background monitoring service"""
        self.is_running = True
        logger.info("Electricity monitor service started.")

        await asyncio.gather(self._fetch_prices_task(), self._monitor_prices_task())

    async def stop(self):
        """Stop the background monitoring service"""
        self.is_running = False
        logger.info("Electricity monitor service stopped.")

    async def _fetch_prices_task(self):
        while self.is_running:
            now = datetime.now(tz=ZoneInfo("Europe/Helsinki"))
            target_time = datetime.combine(
                now.date(), time(14, 0), tzinfo=ZoneInfo("Europe/Helsinki")
            )  # 14:00 today
            if now >= target_time:
                target_time = datetime.combine(
                    now.date(tz=ZoneInfo("Europe/Helsinki")).replace(day=now.day + 1),
                    time(14, 0),
                )
            if self.current_prices is None:
                try:
                    self.current_prices = await get_electricity_prices()
                    logger.info("Successfully fetched new electricity prices")
                except Exception as e:
                    logger.error(f"Error fetching electricity prices: {e}")

            seconds_until_fetch = (target_time - now).total_seconds()
            logger.info(
                f"Waiting {seconds_until_fetch} seconds until next price fetch."
            )
            await asyncio.sleep(seconds_until_fetch)

            try:
                self.current_prices = await get_electricity_prices()
                logger.info("Successfully fetched new electricity prices")
            except Exception as e:
                logger.error(f"Error fetching electricity prices: {e}")

    async def _monitor_prices_task(self):
        """Monitor current prices and control Pico pins"""
        while self.is_running:
            if self.current_prices:
                current_point = self._get_current_point_index()
                current_price = self._get_price_for_hour_or_quarter(current_point)
                logger.info(
                    f"Current electricity price for quarter-hour {current_point}: {current_price} cents/kWh"
                )
            await asyncio.sleep(10)  # Check every 10 seconds

    def _get_current_point_index(self) -> int:
        """Get the current quarter-hour index (1-96)"""
        now = datetime.now(tz=ZoneInfo("Europe/Helsinki"))
        logger.info(f"Current time: {now}")
        return now.hour * 4 + (now.minute // 15) + 1

    def _get_price_for_hour_or_quarter(
        self, point: int, quarter_hour: bool = True
    ) -> Optional[float]:
        """
        Get the electricity price for a specific hour or quarter-hour.
        Args:
            point (int): Quarter-hour index (1-96)
            quarter_hour (bool): If True, interpret point as quarter-hour index
        Returns:
            Optional[float]: Price in cents per kWh including VAT, or None if not available
        """
        if not self.current_prices:
            return None

        try:
            time_series = self.current_prices.publication_market_document.time_series
            if isinstance(time_series, list):
                points: List[Point] = time_series[0].period.point
            else:
                points: List[Point] = time_series.period.point

            if quarter_hour:
                logger.info(len(points))
                matching_point = next(
                    (p for p in points if int(p.position) == point), None
                )
                if matching_point is None:
                    logger.error(f"No price data found for point {point}")
                    return None
                eur_per_mwh = float(matching_point.price_amount)

            else:
                # TODO: Verify this logic for hourly prices
                hour = (point - 1) // 4  # Integer division to get hour (0-23)
                start_quarter = hour * 4
                quarter_prices = []
                for i in range(4):
                    quarter_index = start_quarter + i + 1
                    if quarter_index <= len(points):
                        quarter_prices.append(
                            float(points[quarter_index - 1].price_amount)
                        )

                if not quarter_prices:
                    return None

                eur_per_mwh = sum(quarter_prices) / len(quarter_prices)

            eur_per_kwh = eur_per_mwh / 1000.0
            eur_per_kwh_vat = eur_per_kwh * (
                1 + app_settings.FINNISH_VAT_PERCENTAGE / 100
            )
            cents_per_kwh_vat = eur_per_kwh_vat * 100.0
            return cents_per_kwh_vat

        except (IndexError, AttributeError) as e:
            logger.error(f"Error extracting price for hour {point}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error extracting price for hour {point}: {e}",
                exc_info=True,
            )
            return None

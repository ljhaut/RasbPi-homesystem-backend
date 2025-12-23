import asyncio
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy.exc import OperationalError
from sqlmodel import select

from controllers.pico_controller import PicoController
from core.config import app_settings
from core.logging_config import setup_logger
from db.base import get_session
from db.models import ElectricityPrices
from helpers.common import get_current_quarter_timestamp
from models.electricity_monitor_service_status import ElectricityMonitorServiceStatus
from models.electricity_price_models import ElectricityPriceResponse
from services.electricity_prices import (
    get_electricity_prices,
    save_electricity_prices_to_db,
)

logger = setup_logger()


class ElectricityPriceNotFoundError(Exception):
    """
    Exception raised when the current electricity price cannot be found in the database.
    """

    pass


class ElectricityMonitorService:
    """
    Service to monitor electricity prices and control Pico pins accordingly.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        pico_controller: Optional[PicoController] = None,
    ):
        self.client = client
        self.pico_controller = pico_controller or PicoController()
        self.status = ElectricityMonitorServiceStatus(is_running=False)

    async def start(self) -> None:
        """
        Start the background monitoring service

        :param self: Instance of ElectricityMonitorService
        """
        self.status.is_running = True
        logger.info("Electricity monitor service started.")

        await asyncio.gather(self._monitor_prices_task())

    async def stop(self) -> None:
        """
        Stop the background monitoring service

        :param self: Instance of ElectricityMonitorService
        """
        self.status.is_running = False
        logger.info("Electricity monitor service stopped.")

    async def _monitor_prices_task(self) -> None:
        """
        Background task to monitor electricity prices and control Pico pins

        :param self: Instance of ElectricityMonitorService
        """
        while self.status.is_running:
            try:
                price, timestamp = self._get_current_price_c_per_kwh_vat()
                if price is not None and price != self.status.current_price:
                    logger.info(
                        f"Current electricity price: {price} cents/kWh (including VAT) at {timestamp}"
                    )
                    # If price is not same as last known price, update control logic
                    await self._pico_control_logic(price)
                    self.status.current_price = price
                else:
                    logger.debug(
                        "Current price is the same as last known price. No action taken."
                    )

            except ElectricityPriceNotFoundError:
                logger.warning(
                    "Cannot get current electricity price. Trying to fetch new prices."
                )
                try:
                    await self._fetch_and_save_prices()
                except httpx.HTTPError as e:
                    logger.error(f"Failed to fetch prices from API: {e}")
                except OperationalError as e:
                    logger.error(f"Failed to save prices to DB: {e}")
                except Exception as e:
                    logger.error(
                        f"Unexpected error while fetching and saving prices: {e}"
                    )

            await asyncio.sleep(10)  # Check every 10 seconds

    async def _fetch_and_save_prices(self) -> None:
        """
        Fetch electricity prices from the API and save them to the database

        :param self: Instance of ElectricityMonitorService
        """
        prices = await get_electricity_prices(self.client)
        gen = get_session()
        session = next(gen)
        try:
            save_electricity_prices_to_db(prices, session)
        finally:
            # close the generator to exit the session context
            gen.close()

    def _get_current_price_c_per_kwh_vat(self) -> tuple[float, datetime]:
        """
        Get the current electricity price in cents per kWh including VAT

        :param self: Instance of ElectricityMonitorService
        :return: Current electricity price in cents per kWh including VAT and the timestamp
        :rtype: tuple[float, datetime]
        """
        # Acquire a session from the get_session() generator and ensure it is closed
        try:
            gen = get_session()
            session = next(gen)
        except Exception as e:
            logger.error(f"Failed to acquire DB session: {e}")
            raise ElectricityPriceNotFoundError(
                "Could not acquire database session"
            ) from e

        timestamp = get_current_quarter_timestamp()

        try:
            row = session.exec(
                select(ElectricityPrices).where(
                    ElectricityPrices.timestamp == timestamp
                )
            ).first()
        except OperationalError as oe:
            logger.error(
                f"Database OperationalError while querying current price: {oe}"
            )
            raise ElectricityPriceNotFoundError(f"DB error: {oe}") from oe
        except Exception as e:
            logger.error(f"Unexpected error while querying current price: {e}")
            raise ElectricityPriceNotFoundError(f"Unexpected error: {e}") from e
        finally:
            try:
                gen.close()
            except Exception:
                pass

        logger.debug(f"Database row for timestamp {timestamp}: {row}")

        if row:
            eur_per_kwh = row.price_amount_mwh_eur / 1000.0
            eur_per_kwh_vat = eur_per_kwh * (
                1 + app_settings.FINNISH_VAT_PERCENTAGE / 100
            )
            cents_per_kwh_vat = round(eur_per_kwh_vat * 100.0, 2)
            return cents_per_kwh_vat, timestamp
        else:
            logger.warning(f"No electricity price found for timestamp {timestamp}")
            raise ElectricityPriceNotFoundError(
                f"No electricity price found for timestamp {timestamp}"
            )

    async def _pico_control_logic(self, price_c: float) -> None:
        """
        Control Pico pins based on the current electricity price

        :param self: Instance of ElectricityMonitorService
        :param price_c: Current electricity price in cents per kWh including VAT
        """
        await self._car_charge_logic(price_c)

    async def _car_charge_logic(self, price_c: float):
        """
        Control car charging based on the current electricity price

        :param self: Instance of ElectricityMonitorService
        :param price_c: Current electricity price in cents per kWh including VAT
        """
        if price_c < 8.0:
            if self.status.car_charging:
                return  # Already charging
            logger.info(
                f"Electricity price {price_c} c/kWh is below threshold. Enabling car charging."
            )
            await self.pico_controller.turn_on_all_pins(talker_id=1)
        else:
            if not self.status.car_charging:
                return  # Already not charging
            logger.info(
                f"Electricity price {price_c} c/kWh is above threshold. Disabling car charging."
            )
            await self.pico_controller.turn_off_all_pins(talker_id=1)

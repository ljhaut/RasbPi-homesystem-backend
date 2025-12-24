import asyncio
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

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
from services.electricity_prices import (
    check_if_tomorrow_prices_exist,
    get_electricity_prices,
    save_electricity_prices_to_db,
)

logger = setup_logger()


class ElectricityPriceNotFoundError(Exception):
    """
    Exception raised when the current electricity price cannot be found in the database.
    """


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
        await self.pico_controller.clean_up()
        logger.info("Electricity monitor service stopped.")

    async def _monitor_prices_task(self) -> None:
        """
        Background task to monitor electricity prices and control Pico pins

        :param self: Instance of ElectricityMonitorService
        """
        while self.status.is_running:
            self._new_data_status_check()
            if not self.status.latest_data_fetched:
                if self.status.new_data_should_be_available:
                    try:
                        gen = get_session()
                        session = next(gen)
                        if not check_if_tomorrow_prices_exist(session):
                            try:
                                await self._fetch_and_save_prices()
                                self.status.latest_data_fetched = True
                                self.status.new_data_should_be_available = False
                                logger.debug("Fetched and saved tomorrow's prices.")
                            except httpx.HTTPError as e:
                                logger.error(f"Failed to fetch prices from API: {e}")
                            except OperationalError as e:
                                logger.error(f"Failed to save prices to DB: {e}")
                            except Exception as e:
                                logger.error(
                                    f"Unexpected error while fetching and saving prices: {e}"
                                )
                        else:
                            logger.debug(
                                "Tomorrow's prices already exist in the database."
                            )
                            self.status.latest_data_fetched = True
                            self.status.new_data_should_be_available = False
                    finally:
                        gen.close()
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
            except Exception as e:
                logger.error(f"Unexpected error in monitoring task: {e}")

            logger.debug(f"Monitor status: {self.status}")
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

    def _new_data_status_check(self) -> None:
        """
        If current time is the first quarter of the day, set latest_data_fetched to False.
        If current time is after 14:00, set new_data_should_be_available to True.
        """
        current_time = datetime.now(ZoneInfo("Europe/Helsinki"))
        if current_time.hour == 0 and current_time.minute < 15:
            self.status.latest_data_fetched = False
            self.status.new_data_should_be_available = False

        if (
            current_time.hour >= 14
            and not self.status.latest_data_fetched
            and not self.status.new_data_should_be_available
        ):
            self.status.new_data_should_be_available = True

    async def _pico_control_logic(self, price_c: float) -> None:
        """
        Control Pico pins based on the current electricity price

        :param self: Instance of ElectricityMonitorService
        :param price_c: Current electricity price in cents per kWh including VAT
        """
        await self._car_charge_logic(price_c)

    async def _car_charge_logic(self, price_c: float) -> None:
        """
        Control car charging based on the current electricity price

        :param self: Instance of ElectricityMonitorService
        :param price_c: Current electricity price in cents per kWh including VAT
        """
        if price_c < app_settings.CAR_CHARGE_THRESHOLD_C:
            if self.status.car_charging:
                return  # Already charging
            logger.info(
                f"Electricity price {price_c} c/kWh is below threshold. Enabling car charging."
            )
            await self.pico_controller.turn_on_all_pins(talker_id=1)
            self.status.car_charging = True
        else:
            if not self.status.car_charging:
                return  # Already not charging
            logger.info(
                f"Electricity price {price_c} c/kWh is above threshold. Disabling car charging."
            )
            await self.pico_controller.turn_off_all_pins(talker_id=1)
            self.status.car_charging = False

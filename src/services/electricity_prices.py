import httpx
import xmltodict

from core.config import app_settings
from core.logging_config import setup_logger
from helpers.elec_prices_helpers import get_today_and_tomorrow_dates
from models.electricity_price_models import ElectricityPriceResponse

logger = setup_logger()


async def get_electricity_prices() -> ElectricityPriceResponse:
    today, tomorrow = get_today_and_tomorrow_dates()

    payload = {
        "securityToken": app_settings.ENTSOE_API_KEY,
        "documentType": "A44",
        "in_Domain": "10YFI-1--------U",
        "out_Domain": "10YFI-1--------U",
        "periodStart": f"202511100000",
        "periodEnd": f"202511110000",
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

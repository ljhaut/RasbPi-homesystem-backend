from pydantic import BaseModel


class ElectricityMonitorServiceStatus(BaseModel):
    is_running: bool
    current_price: float | None = None
    new_data_should_be_available: bool = False
    latest_data_fetched: bool = False
    car_charging: bool | None = None

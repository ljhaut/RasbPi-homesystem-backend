from pydantic import BaseModel


class ElectricityMonitorServiceStatus(BaseModel):
    is_running: bool
    current_price: float | None = None
    car_charging: bool | None = None

from datetime import date

from sqlmodel import Field, SQLModel


class ElectricityPrices(SQLModel, table=True):
    __tablename__ = "electricity_prices"

    id: int | None = Field(default=None, primary_key=True)
    price_amount_mwh_eur: float = Field(index=True, nullable=False)
    timestamp: date = Field(index=True, nullable=False)

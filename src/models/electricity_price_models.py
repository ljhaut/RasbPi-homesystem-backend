from typing import List, Union

from pydantic import BaseModel, Field


class Point(BaseModel):
    position: str
    price_amount: str = Field(alias="price.amount")


class TimeInterval(BaseModel):
    start: str
    end: str


class Period(BaseModel):
    time_interval: TimeInterval = Field(alias="timeInterval")
    resolution: str
    point: List[Point] = Field(alias="Point")


class MarketParticipantMRID(BaseModel):
    coding_scheme: str = Field(alias="@codingScheme")
    text: str = Field(alias="#text")


class DomainMRID(BaseModel):
    coding_scheme: str = Field(alias="@codingScheme")
    text: str = Field(alias="#text")


class TimeSeries(BaseModel):
    mrid: str = Field(alias="mRID")
    auction_type: str = Field(alias="auction.type")
    business_type: str = Field(alias="businessType")
    in_domain_mrid: DomainMRID = Field(alias="in_Domain.mRID")
    out_domain_mrid: DomainMRID = Field(alias="out_Domain.mRID")
    contract_market_agreement_type: str = Field(alias="contract_MarketAgreement.type")
    currency_unit_name: str = Field(alias="currency_Unit.name")
    price_measure_unit_name: str = Field(alias="price_Measure_Unit.name")
    curve_type: str = Field(alias="curveType")
    period: Period = Field(alias="Period")


class PublicationMarketDocument(BaseModel):
    xmlns: str = Field(alias="@xmlns")
    mrid: str = Field(alias="mRID")
    revision_number: str = Field(alias="revisionNumber")
    type: str
    sender_market_participant_mrid: MarketParticipantMRID = Field(
        alias="sender_MarketParticipant.mRID"
    )
    sender_market_participant_role_type: str = Field(
        alias="sender_MarketParticipant.marketRole.type"
    )
    receiver_market_participant_mrid: MarketParticipantMRID = Field(
        alias="receiver_MarketParticipant.mRID"
    )
    receiver_market_participant_role_type: str = Field(
        alias="receiver_MarketParticipant.marketRole.type"
    )
    created_date_time: str = Field(alias="createdDateTime")
    period_time_interval: TimeInterval = Field(alias="period.timeInterval")
    time_series: Union[List[TimeSeries], TimeSeries] = Field(alias="TimeSeries")

    class Config:
        populate_by_name = True


class ElectricityPriceResponse(BaseModel):
    publication_market_document: PublicationMarketDocument = Field(
        alias="Publication_MarketDocument"
    )

    class Config:
        populate_by_name = True

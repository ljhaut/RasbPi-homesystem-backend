# tests/unit/helpers/test_elec_prices_helpers.py
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from src.helpers import elec_prices_helpers as helpers


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        base = datetime(2023, 9, 15, tzinfo=ZoneInfo("Europe/Helsinki"))
        return base.astimezone(tz) if tz else base


def test_position_one_starts_at_second_hour(monkeypatch):
    monkeypatch.setattr(helpers, "datetime", FrozenDatetime)
    result = helpers.position_to_timestamp(1)
    assert result == datetime(2023, 9, 15, 1, 0, tzinfo=ZoneInfo("Europe/Helsinki"))


@pytest.mark.parametrize(
    "position,expected",
    [
        (4, datetime(2023, 9, 15, 1, 45, tzinfo=ZoneInfo("Europe/Helsinki"))),
        (92, datetime(2023, 9, 15, 22, 45, tzinfo=ZoneInfo("Europe/Helsinki"))),
        (93, datetime(2023, 9, 16, 0, 0, tzinfo=ZoneInfo("Europe/Helsinki"))),
    ],
)
def test_position_to_timestamp_conversion(monkeypatch, position, expected):
    monkeypatch.setattr(helpers, "datetime", FrozenDatetime)
    assert helpers.position_to_timestamp(position) == expected

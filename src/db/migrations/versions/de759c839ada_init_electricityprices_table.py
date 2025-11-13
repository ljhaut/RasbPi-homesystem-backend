"""Init electricityPrices table

Revision ID: de759c839ada
Revises:
Create Date: 2025-11-13 21:00:41.348297

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "de759c839ada"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "electricity_prices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("price_amount_mwh_eur", sa.Float(), nullable=False, index=True),
        sa.Column("timestamp", sa.Date(), nullable=False, index=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("electricity_prices")

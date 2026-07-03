from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "56457597e097"
down_revision: Union[str, None] = "e724f8c813de"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "riders",
        sa.Column(
            "shift_start_time",
            sa.DateTime(timezone=True),
            nullable=True
        )
    )


def downgrade() -> None:
    op.drop_column("riders", "shift_start_time")
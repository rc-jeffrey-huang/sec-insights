"""empty message

Revision ID: 27585363bd94
Revises: 873c0c4616ea
Create Date: 2023-09-15 14:13:21.491990

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "27585363bd94"
down_revision = "873c0c4616ea"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_document_id", table_name="document")
    op.drop_constraint(
        "conversationdocument_document_id_fkey",
        "conversationdocument",
        type_="foreignkey",
    )
    op.drop_table("document")
    op.drop_index(
        "ix_conversationdocument_document_id", table_name="conversationdocument"
    )
    op.drop_column("conversationdocument", "document_id")
    op.add_column(
        "conversationdocument", sa.Column("document_id", sa.String(), nullable=True)
    )

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key(
        "conversationdocument_document_id_fkey",
        "conversationdocument",
        "document",
        ["document_id"],
        ["id"],
    )
    op.create_index(
        "ix_conversationdocument_document_id",
        "conversationdocument",
        ["document_id"],
        unique=False,
    )
    op.create_table(
        "document",
        sa.Column("url", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            "metadata_map",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="document_pkey"),
        sa.UniqueConstraint("url", name="document_url_key"),
    )
    op.create_index("ix_document_id", "document", ["id"], unique=False)
    # ### end Alembic commands ###

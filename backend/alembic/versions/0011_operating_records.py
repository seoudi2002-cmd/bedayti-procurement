"""append-only operating records (rent, vehicles, overtime)

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-03 23:10:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('op_record',
    sa.Column('dataset_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('module_id', sa.String(length=32), nullable=False),
    sa.Column('kind', sa.String(length=24), nullable=False),
    sa.Column('entity_key', sa.String(length=300), nullable=False),
    sa.Column('entity_label', sa.String(length=300), nullable=True),
    sa.Column('period', sa.String(length=7), nullable=True),
    sa.Column('source_ref', sa.String(length=80), nullable=True),
    sa.Column('values', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('personal', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('flags', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.ForeignKeyConstraint(['dataset_id'], ['analysis_dataset.id'], name=op.f('fk_op_record_dataset_id_analysis_dataset'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_op_record'))
    )
    op.create_index('ix_op_record_lookup', 'op_record', ['module_id', 'kind', 'entity_key', 'period'], unique=False)
    op.create_index('ix_op_record_dataset', 'op_record', ['dataset_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_op_record_dataset', table_name='op_record')
    op.drop_index('ix_op_record_lookup', table_name='op_record')
    op.drop_table('op_record')

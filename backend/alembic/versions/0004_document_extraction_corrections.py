"""document extraction, corrections, line allocation

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-02 21:59:22.579599
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('data_override',
    sa.Column('entity_type', sa.String(length=40), nullable=False),
    sa.Column('entity_key', sa.String(length=120), nullable=False),
    sa.Column('field', sa.String(length=60), nullable=False),
    sa.Column('value_type', sa.String(length=10), nullable=False),
    sa.Column('original_value', sa.Text(), nullable=True),
    sa.Column('corrected_value', sa.Text(), nullable=True),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('proposed_by', sa.String(length=200), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('reviewed_by', sa.String(length=200), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('review_note', sa.Text(), nullable=True),
    sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_data_override'))
    )
    op.create_index('ix_data_override_target', 'data_override', ['entity_type', 'entity_key', 'field'], unique=False)
    op.create_table('extraction_job',
    sa.Column('file_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('engine', sa.String(length=40), nullable=True),
    sa.Column('engine_version', sa.String(length=80), nullable=True),
    sa.Column('languages', sa.String(length=40), nullable=True),
    sa.Column('page_count', sa.SmallInteger(), nullable=True),
    sa.Column('params', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('summary', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.String(length=200), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['file_id'], ['document_file.id'], name=op.f('fk_extraction_job_file_id_document_file')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_extraction_job'))
    )
    op.create_table('extracted_page',
    sa.Column('job_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('page_no', sa.SmallInteger(), nullable=False),
    sa.Column('text_source', sa.String(length=14), nullable=False),
    sa.Column('rotation', sa.SmallInteger(), nullable=False),
    sa.Column('mean_confidence', sa.Numeric(precision=5, scale=3), nullable=True),
    sa.Column('word_count', sa.Integer(), nullable=False),
    sa.Column('raw_text', sa.Text(), nullable=False),
    sa.Column('doc_type_guess', sa.String(length=40), nullable=True),
    sa.Column('doc_type_confidence', sa.Numeric(precision=4, scale=3), nullable=True),
    sa.Column('image_path', sa.String(length=1000), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['extraction_job.id'], name=op.f('fk_extracted_page_job_id_extraction_job'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_extracted_page'))
    )
    op.create_index('ix_extracted_page_job', 'extracted_page', ['job_id', 'page_no'], unique=True)
    op.create_table('extracted_document',
    sa.Column('job_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('seq', sa.SmallInteger(), nullable=False),
    sa.Column('doc_type', sa.String(length=40), nullable=False),
    sa.Column('page_from', sa.SmallInteger(), nullable=False),
    sa.Column('page_to', sa.SmallInteger(), nullable=False),
    sa.Column('status', sa.String(length=14), nullable=False),
    sa.Column('confidence', sa.Numeric(precision=4, scale=3), nullable=True),
    sa.Column('header', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('flags', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('po_header_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('link_method', sa.String(length=40), nullable=True),
    sa.Column('procurement_document_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('reviewed_by', sa.String(length=200), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('review_note', sa.Text(), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['extraction_job.id'], name=op.f('fk_extracted_document_job_id_extraction_job'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['po_header_id'], ['po_header.id'], name=op.f('fk_extracted_document_po_header_id_po_header')),
    sa.ForeignKeyConstraint(['procurement_document_id'], ['procurement_document.id'], name=op.f('fk_extracted_document_procurement_document_id_procurement_document')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_extracted_document'))
    )
    op.create_table('po_line_allocation',
    sa.Column('po_line_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('branch_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=True),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('source_ref', sa.String(length=300), nullable=True),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('decided_by', sa.String(length=200), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['branch_id'], ['dim_branch.id'], name=op.f('fk_po_line_allocation_branch_id_dim_branch')),
    sa.ForeignKeyConstraint(['po_line_id'], ['fact_po_line.id'], name=op.f('fk_po_line_allocation_po_line_id_fact_po_line'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_po_line_allocation'))
    )
    op.create_index('ix_po_line_allocation_line', 'po_line_allocation', ['po_line_id'], unique=False)
    op.create_table('extracted_line',
    sa.Column('extracted_document_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('line_no', sa.SmallInteger(), nullable=False),
    sa.Column('page_no', sa.SmallInteger(), nullable=True),
    sa.Column('bbox', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('description_raw', sa.Text(), nullable=True),
    sa.Column('quantity_raw', sa.String(length=60), nullable=True),
    sa.Column('unit_price_raw', sa.String(length=60), nullable=True),
    sa.Column('line_total_raw', sa.String(length=60), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('unit_description', sa.String(length=200), nullable=True),
    sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=True),
    sa.Column('unit_price', sa.Numeric(precision=18, scale=5), nullable=True),
    sa.Column('line_total', sa.Numeric(precision=18, scale=5), nullable=True),
    sa.Column('price_basis', sa.String(length=10), nullable=True),
    sa.Column('field_confidence', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('confidence', sa.Numeric(precision=4, scale=3), nullable=True),
    sa.Column('flags', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('branch_source_text', sa.String(length=600), nullable=True),
    sa.Column('branch_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('branch_attribution_method', sa.String(length=40), nullable=True),
    sa.Column('branch_attribution_status', sa.String(length=20), nullable=True),
    sa.Column('po_line_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['branch_id'], ['dim_branch.id'], name=op.f('fk_extracted_line_branch_id_dim_branch')),
    sa.ForeignKeyConstraint(['extracted_document_id'], ['extracted_document.id'], name=op.f('fk_extracted_line_extracted_document_id_extracted_document'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['po_line_id'], ['fact_po_line.id'], name=op.f('fk_extracted_line_po_line_id_fact_po_line')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_extracted_line'))
    )
    op.create_index('ix_extracted_line_doc', 'extracted_line', ['extracted_document_id', 'line_no'], unique=False)
    op.add_column('document_file', sa.Column('source_kind', sa.String(length=14), nullable=True))
    op.add_column('fact_po_line', sa.Column('source_kind', sa.String(length=20), server_default='import', nullable=False))
    op.add_column('fact_po_line', sa.Column('extracted_line_id', sa.Integer(), nullable=True))
    op.add_column('fact_po_line', sa.Column('price_basis', sa.String(length=10), nullable=True))
    op.add_column('fact_po_line', sa.Column('branch_source_text', sa.String(length=600), nullable=True))
    op.add_column('fact_po_line', sa.Column('branch_attribution_method', sa.String(length=40), nullable=True))
    op.add_column('fact_po_line', sa.Column('branch_attribution_status', sa.String(length=20), nullable=True))
    op.add_column('po_header', sa.Column('lines_total', sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column('procurement_document', sa.Column('page_from', sa.SmallInteger(), nullable=True))
    op.add_column('procurement_document', sa.Column('page_to', sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column('procurement_document', 'page_to')
    op.drop_column('procurement_document', 'page_from')
    op.drop_column('po_header', 'lines_total')
    op.drop_column('fact_po_line', 'branch_attribution_status')
    op.drop_column('fact_po_line', 'branch_attribution_method')
    op.drop_column('fact_po_line', 'branch_source_text')
    op.drop_column('fact_po_line', 'price_basis')
    op.drop_column('fact_po_line', 'extracted_line_id')
    op.drop_column('fact_po_line', 'source_kind')
    op.drop_column('document_file', 'source_kind')
    op.drop_index('ix_extracted_line_doc', table_name='extracted_line')
    op.drop_table('extracted_line')
    op.drop_index('ix_po_line_allocation_line', table_name='po_line_allocation')
    op.drop_table('po_line_allocation')
    op.drop_table('extracted_document')
    op.drop_index('ix_extracted_page_job', table_name='extracted_page')
    op.drop_table('extracted_page')
    op.drop_table('extraction_job')
    op.drop_index('ix_data_override_target', table_name='data_override')
    op.drop_table('data_override')

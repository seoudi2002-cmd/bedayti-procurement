"""po header, procurement documents, load tracking

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-02 20:33:41.545319
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('document_file',
    sa.Column('file_name', sa.String(length=500), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('storage_path', sa.String(length=1000), nullable=True),
    sa.Column('content_type', sa.String(length=100), nullable=True),
    sa.Column('pages', sa.SmallInteger(), nullable=True),
    sa.Column('uploaded_by', sa.String(length=200), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_document_file')),
    sa.UniqueConstraint('sha256', name=op.f('uq_document_file_sha256'))
    )
    op.create_table('procurement_case',
    sa.Column('case_key', sa.String(length=100), nullable=False),
    sa.Column('fiscal_year', sa.SmallInteger(), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=True),
    sa.Column('cost_center_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('opened_on', sa.Date(), nullable=True),
    sa.Column('attrs', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['cost_center_id'], ['dim_cost_center.id'], name=op.f('fk_procurement_case_cost_center_id_dim_cost_center')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_procurement_case')),
    sa.UniqueConstraint('case_key', name=op.f('uq_procurement_case_case_key'))
    )
    op.create_table('po_header',
    sa.Column('fiscal_year', sa.SmallInteger(), nullable=False),
    sa.Column('po_number', sa.String(length=64), nullable=False),
    sa.Column('po_date', sa.Date(), nullable=False),
    sa.Column('approval_date', sa.Date(), nullable=True),
    sa.Column('period', sa.Date(), nullable=False),
    sa.Column('supplier_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('cost_center_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('branch_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('requisition_no', sa.String(length=64), nullable=True),
    sa.Column('purchase_method', sa.String(length=50), nullable=True),
    sa.Column('delivery_days', sa.Integer(), nullable=True),
    sa.Column('payment_days', sa.Integer(), nullable=True),
    sa.Column('payment_terms', sa.String(length=300), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('total_amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=True),
    sa.Column('case_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('batch_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('terms', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('attrs', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], name=op.f('fk_po_header_batch_id_import_batch'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['branch_id'], ['dim_branch.id'], name=op.f('fk_po_header_branch_id_dim_branch')),
    sa.ForeignKeyConstraint(['case_id'], ['procurement_case.id'], name=op.f('fk_po_header_case_id_procurement_case')),
    sa.ForeignKeyConstraint(['cost_center_id'], ['dim_cost_center.id'], name=op.f('fk_po_header_cost_center_id_dim_cost_center')),
    sa.ForeignKeyConstraint(['period'], ['dim_period.period'], name=op.f('fk_po_header_period_dim_period')),
    sa.ForeignKeyConstraint(['supplier_id'], ['dim_supplier.id'], name=op.f('fk_po_header_supplier_id_dim_supplier')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_po_header')),
    sa.UniqueConstraint('fiscal_year', 'po_number', name='uq_po_header_fy_number')
    )
    op.create_index('ix_po_header_requisition', 'po_header', ['fiscal_year', 'requisition_no'], unique=False)
    op.create_index('ix_po_header_supplier_period', 'po_header', ['supplier_id', 'period'], unique=False)
    op.create_table('procurement_document',
    sa.Column('case_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('po_header_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('parent_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('relation', sa.String(length=30), nullable=True),
    sa.Column('doc_type', sa.String(length=40), nullable=False),
    sa.Column('doc_number', sa.String(length=100), nullable=True),
    sa.Column('doc_date', sa.Date(), nullable=True),
    sa.Column('fiscal_year', sa.SmallInteger(), nullable=True),
    sa.Column('supplier_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=True),
    sa.Column('file_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('batch_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('attrs', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], name=op.f('fk_procurement_document_batch_id_import_batch'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['case_id'], ['procurement_case.id'], name=op.f('fk_procurement_document_case_id_procurement_case')),
    sa.ForeignKeyConstraint(['file_id'], ['document_file.id'], name=op.f('fk_procurement_document_file_id_document_file')),
    sa.ForeignKeyConstraint(['parent_id'], ['procurement_document.id'], name=op.f('fk_procurement_document_parent_id_procurement_document')),
    sa.ForeignKeyConstraint(['po_header_id'], ['po_header.id'], name=op.f('fk_procurement_document_po_header_id_po_header')),
    sa.ForeignKeyConstraint(['supplier_id'], ['dim_supplier.id'], name=op.f('fk_procurement_document_supplier_id_dim_supplier')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_procurement_document'))
    )
    op.create_index('ix_procurement_document_case', 'procurement_document', ['case_id'], unique=False)
    op.create_index('ix_procurement_document_po', 'procurement_document', ['po_header_id'], unique=False)
    op.create_index('ix_procurement_document_type_number', 'procurement_document', ['doc_type', 'doc_number'], unique=False)
    op.add_column('fact_cost', sa.Column('source_ref', sa.String(length=64), nullable=True))
    op.create_index('uq_fact_cost_source', 'fact_cost', ['module_id', 'source_ref'], unique=True)
    op.add_column('fact_po_line', sa.Column('po_header_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True))
    op.add_column('fact_po_line', sa.Column('fiscal_year', sa.SmallInteger(), nullable=True))
    op.add_column('fact_po_line', sa.Column('vat_rate', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('fact_po_line', sa.Column('vat_amount', sa.Numeric(precision=18, scale=2), nullable=True))
    op.create_unique_constraint('uq_fact_po_line_header_line', 'fact_po_line', ['po_header_id', 'line_number'])
    op.create_foreign_key(op.f('fk_fact_po_line_po_header_id_po_header'), 'fact_po_line', 'po_header', ['po_header_id'], ['id'])
    op.add_column('import_batch', sa.Column('rows_loaded', sa.Integer(), server_default='0', nullable=False))
    op.add_column('import_batch', sa.Column('rows_held', sa.Integer(), server_default='0', nullable=False))
    op.drop_constraint(op.f('uq_import_batch_module_file'), 'import_batch', type_='unique')
    op.create_index('uq_import_batch_module_file', 'import_batch', ['module_id', 'file_hash'], unique=True, postgresql_where=sa.text("status <> 'rolled_back'"), sqlite_where=sa.text("status <> 'rolled_back'"))


def downgrade() -> None:
    op.drop_index('uq_import_batch_module_file', table_name='import_batch', postgresql_where=sa.text("status <> 'rolled_back'"), sqlite_where=sa.text("status <> 'rolled_back'"))
    op.create_unique_constraint(op.f('uq_import_batch_module_file'), 'import_batch', ['module_id', 'file_hash'], postgresql_nulls_not_distinct=False)
    op.drop_column('import_batch', 'rows_held')
    op.drop_column('import_batch', 'rows_loaded')
    op.drop_constraint(op.f('fk_fact_po_line_po_header_id_po_header'), 'fact_po_line', type_='foreignkey')
    op.drop_constraint('uq_fact_po_line_header_line', 'fact_po_line', type_='unique')
    op.drop_column('fact_po_line', 'vat_amount')
    op.drop_column('fact_po_line', 'vat_rate')
    op.drop_column('fact_po_line', 'fiscal_year')
    op.drop_column('fact_po_line', 'po_header_id')
    op.drop_index('uq_fact_cost_source', table_name='fact_cost')
    op.drop_column('fact_cost', 'source_ref')
    op.drop_index('ix_procurement_document_type_number', table_name='procurement_document')
    op.drop_index('ix_procurement_document_po', table_name='procurement_document')
    op.drop_index('ix_procurement_document_case', table_name='procurement_document')
    op.drop_table('procurement_document')
    op.drop_index('ix_po_header_supplier_period', table_name='po_header')
    op.drop_index('ix_po_header_requisition', table_name='po_header')
    op.drop_table('po_header')
    op.drop_table('procurement_case')
    op.drop_table('document_file')

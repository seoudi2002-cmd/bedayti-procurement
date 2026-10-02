"""reference data, registers, exceptions, branch attribution

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-02 21:10:55.373219
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('dim_department',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('source', sa.String(length=100), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_dim_department')),
    sa.UniqueConstraint('name', name=op.f('uq_dim_department_name'))
    )
    op.create_table('dim_region',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_dim_region')),
    sa.UniqueConstraint('name', name=op.f('uq_dim_region_name'))
    )
    op.create_table('supplier_contact',
    sa.Column('supplier_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('contact_name_source', sa.String(length=300), nullable=True),
    sa.Column('phone_source', sa.String(length=100), nullable=True),
    sa.Column('email', sa.String(length=200), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['supplier_id'], ['dim_supplier.id'], name=op.f('fk_supplier_contact_supplier_id_dim_supplier')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_supplier_contact')),
    sa.UniqueConstraint('supplier_id', name=op.f('uq_supplier_contact_supplier_id'))
    )
    op.create_table('data_exception',
    sa.Column('module_id', sa.String(length=64), nullable=True),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('severity', sa.String(length=10), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('entity_type', sa.String(length=30), nullable=False),
    sa.Column('entity_key', sa.String(length=100), nullable=False),
    sa.Column('batch_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('details', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('decided_by', sa.String(length=200), nullable=True),
    sa.Column('decision_note', sa.Text(), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], name=op.f('fk_data_exception_batch_id_import_batch'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_data_exception')),
    sa.UniqueConstraint('code', 'entity_type', 'entity_key', name='uq_data_exception_key')
    )
    op.create_index('ix_data_exception_status', 'data_exception', ['status', 'severity'], unique=False)
    op.create_table('dim_employee',
    sa.Column('employee_code', sa.Integer(), nullable=False),
    sa.Column('full_name', sa.String(length=300), nullable=False),
    sa.Column('hire_date', sa.Date(), nullable=True),
    sa.Column('position_source', sa.String(length=200), nullable=True),
    sa.Column('branch_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('branch_source_text', sa.String(length=300), nullable=True),
    sa.Column('branch_match_method', sa.String(length=30), nullable=True),
    sa.Column('governorate_source', sa.String(length=100), nullable=True),
    sa.Column('governorate_issue', sa.String(length=50), nullable=True),
    sa.Column('department_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('cost_center_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('manager_employee_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('missing_fields', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('source_batch_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['branch_id'], ['dim_branch.id'], name=op.f('fk_dim_employee_branch_id_dim_branch')),
    sa.ForeignKeyConstraint(['cost_center_id'], ['dim_cost_center.id'], name=op.f('fk_dim_employee_cost_center_id_dim_cost_center')),
    sa.ForeignKeyConstraint(['department_id'], ['dim_department.id'], name=op.f('fk_dim_employee_department_id_dim_department')),
    sa.ForeignKeyConstraint(['manager_employee_id'], ['dim_employee.id'], name=op.f('fk_dim_employee_manager_employee_id_dim_employee')),
    sa.ForeignKeyConstraint(['source_batch_id'], ['import_batch.id'], name=op.f('fk_dim_employee_source_batch_id_import_batch'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_dim_employee')),
    sa.UniqueConstraint('employee_code', name=op.f('uq_dim_employee_employee_code'))
    )
    op.create_table('branch_contact',
    sa.Column('branch_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=False),
    sa.Column('branch_manager_name_source', sa.String(length=300), nullable=True),
    sa.Column('branch_phone', sa.String(length=100), nullable=True),
    sa.Column('manager_phone_1', sa.String(length=100), nullable=True),
    sa.Column('manager_phone_2', sa.String(length=100), nullable=True),
    sa.Column('region_manager_name_source', sa.String(length=300), nullable=True),
    sa.Column('region_manager_phone', sa.String(length=200), nullable=True),
    sa.Column('email', sa.String(length=200), nullable=True),
    sa.Column('notes_source', sa.String(length=500), nullable=True),
    sa.Column('manager_employee_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('manager_reconciliation_status', sa.String(length=30), nullable=True),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['branch_id'], ['dim_branch.id'], name=op.f('fk_branch_contact_branch_id_dim_branch')),
    sa.ForeignKeyConstraint(['manager_employee_id'], ['dim_employee.id'], name=op.f('fk_branch_contact_manager_employee_id_dim_employee')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_branch_contact')),
    sa.UniqueConstraint('branch_id', name=op.f('uq_branch_contact_branch_id'))
    )
    op.create_table('requisition',
    sa.Column('fiscal_year', sa.SmallInteger(), nullable=False),
    sa.Column('req_number', sa.String(length=64), nullable=False),
    sa.Column('number_source', sa.String(length=64), nullable=False),
    sa.Column('source_seq', sa.Integer(), nullable=True),
    sa.Column('request_date', sa.Date(), nullable=True),
    sa.Column('department_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('department_source', sa.String(length=200), nullable=True),
    sa.Column('description_source', sa.Text(), nullable=True),
    sa.Column('priority_source', sa.String(length=50), nullable=True),
    sa.Column('status_source', sa.String(length=100), nullable=True),
    sa.Column('notes_source', sa.Text(), nullable=True),
    sa.Column('case_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('attrs', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('batch_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('raw_row_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], name=op.f('fk_requisition_batch_id_import_batch'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['case_id'], ['procurement_case.id'], name=op.f('fk_requisition_case_id_procurement_case')),
    sa.ForeignKeyConstraint(['department_id'], ['dim_department.id'], name=op.f('fk_requisition_department_id_dim_department')),
    sa.ForeignKeyConstraint(['raw_row_id'], ['raw_row.id'], name=op.f('fk_requisition_raw_row_id_raw_row'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_requisition')),
    sa.UniqueConstraint('fiscal_year', 'req_number', name='uq_requisition_fy_number')
    )
    op.create_table('finance_handover',
    sa.Column('memo_no', sa.Integer(), nullable=False),
    sa.Column('memo_type', sa.String(length=10), nullable=False),
    sa.Column('memo_type_source', sa.String(length=50), nullable=False),
    sa.Column('sent_date', sa.Date(), nullable=True),
    sa.Column('po_number_source', sa.String(length=64), nullable=True),
    sa.Column('po_header_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('supplier_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('supplier_name_source', sa.String(length=300), nullable=True),
    sa.Column('supplier_category_source', sa.String(length=200), nullable=True),
    sa.Column('subject_source', sa.Text(), nullable=True),
    sa.Column('purchase_category_source', sa.String(length=200), nullable=True),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('period', sa.Date(), nullable=True),
    sa.Column('attrs', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('batch_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('raw_row_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.ForeignKeyConstraint(['batch_id'], ['import_batch.id'], name=op.f('fk_finance_handover_batch_id_import_batch'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['period'], ['dim_period.period'], name=op.f('fk_finance_handover_period_dim_period')),
    sa.ForeignKeyConstraint(['po_header_id'], ['po_header.id'], name=op.f('fk_finance_handover_po_header_id_po_header')),
    sa.ForeignKeyConstraint(['raw_row_id'], ['raw_row.id'], name=op.f('fk_finance_handover_raw_row_id_raw_row'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['supplier_id'], ['dim_supplier.id'], name=op.f('fk_finance_handover_supplier_id_dim_supplier')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_finance_handover')),
    sa.UniqueConstraint('memo_no', name='uq_finance_handover_memo_no')
    )
    op.create_index('ix_finance_handover_po', 'finance_handover', ['po_header_id'], unique=False)
    op.create_index('ix_finance_handover_type_date', 'finance_handover', ['memo_type', 'sent_date'], unique=False)
    op.add_column('dim_branch', sa.Column('system_key', sa.String(length=32), nullable=True))
    op.add_column('dim_branch', sa.Column('source_seq', sa.Integer(), nullable=True))
    op.add_column('dim_branch', sa.Column('region_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True))
    op.add_column('dim_branch', sa.Column('address', sa.String(length=600), nullable=True))
    op.alter_column('dim_branch', 'code',
               existing_type=sa.VARCHAR(length=32),
               nullable=True)
    op.create_unique_constraint(op.f('uq_dim_branch_system_key'), 'dim_branch', ['system_key'])
    op.create_foreign_key(op.f('fk_dim_branch_region_id_dim_region'), 'dim_branch', 'dim_region', ['region_id'], ['id'])
    op.alter_column('dim_cost_center', 'code',
               existing_type=sa.VARCHAR(length=32),
               nullable=True)
    op.add_column('dim_supplier', sa.Column('register_no', sa.Integer(), nullable=True))
    op.add_column('dim_supplier', sa.Column('commercial_reg_no', sa.String(length=60), nullable=True))
    op.add_column('dim_supplier', sa.Column('address', sa.String(length=600), nullable=True))
    op.add_column('dim_supplier', sa.Column('category_source', sa.String(length=200), nullable=True))
    op.add_column('dim_supplier', sa.Column('services_source', sa.String(length=300), nullable=True))
    op.add_column('dim_supplier', sa.Column('notes_source', sa.String(length=500), nullable=True))
    op.alter_column('dim_supplier', 'code',
               existing_type=sa.VARCHAR(length=32),
               nullable=True)
    op.add_column('entity_alias', sa.Column('method', sa.String(length=30), nullable=True))
    op.add_column('import_batch', sa.Column('profile', sa.String(length=30), server_default='default', nullable=False))
    op.add_column('import_batch', sa.Column('column_map', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True))
    op.add_column('import_batch', sa.Column('warnings', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), server_default='[]', nullable=False))
    op.add_column('import_batch', sa.Column('rows_skipped', sa.Integer(), server_default='0', nullable=False))
    op.add_column('po_header', sa.Column('number_source', sa.String(length=64), nullable=True))
    op.add_column('po_header', sa.Column('po_date_source', sa.String(length=50), nullable=True))
    op.add_column('po_header', sa.Column('supplier_name_source', sa.String(length=300), nullable=True))
    op.add_column('po_header', sa.Column('supplier_register_no_source', sa.Integer(), nullable=True))
    op.add_column('po_header', sa.Column('branch_source_text', sa.String(length=600), nullable=True))
    op.add_column('po_header', sa.Column('branch_attribution_method', sa.String(length=40), nullable=True))
    op.add_column('po_header', sa.Column('branch_attribution_status', sa.String(length=20), nullable=True))
    op.add_column('po_header', sa.Column('requisition_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True))
    op.add_column('po_header', sa.Column('granularity', sa.String(length=12), server_default='lines', nullable=False))
    op.add_column('po_header', sa.Column('description_source', sa.Text(), nullable=True))
    op.add_column('po_header', sa.Column('po_category_source', sa.String(length=200), nullable=True))
    op.add_column('po_header', sa.Column('supplier_category_source', sa.String(length=200), nullable=True))
    op.add_column('po_header', sa.Column('issuance_status_source', sa.String(length=100), nullable=True))
    op.add_column('po_header', sa.Column('order_status_source', sa.String(length=100), nullable=True))
    op.add_column('po_header', sa.Column('finance_handover_amount_register', sa.Numeric(precision=18, scale=2), nullable=True))
    op.add_column('po_header', sa.Column('remaining_register', sa.Numeric(precision=18, scale=2), nullable=True))
    op.alter_column('po_header', 'po_date',
               existing_type=sa.DATE(),
               nullable=True)
    op.alter_column('po_header', 'period',
               existing_type=sa.DATE(),
               nullable=True)
    op.alter_column('po_header', 'supplier_id',
               existing_type=sa.BIGINT(),
               nullable=True)
    op.alter_column('po_header', 'total_amount',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               nullable=True)
    op.create_foreign_key(op.f('fk_po_header_requisition_id_requisition'), 'po_header', 'requisition', ['requisition_id'], ['id'])
    op.add_column('procurement_document', sa.Column('ref_table', sa.String(length=40), nullable=True))
    op.add_column('procurement_document', sa.Column('ref_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('procurement_document', 'ref_id')
    op.drop_column('procurement_document', 'ref_table')
    op.drop_constraint(op.f('fk_po_header_requisition_id_requisition'), 'po_header', type_='foreignkey')
    op.alter_column('po_header', 'total_amount',
               existing_type=sa.NUMERIC(precision=18, scale=2),
               nullable=False)
    op.alter_column('po_header', 'supplier_id',
               existing_type=sa.BIGINT(),
               nullable=False)
    op.alter_column('po_header', 'period',
               existing_type=sa.DATE(),
               nullable=False)
    op.alter_column('po_header', 'po_date',
               existing_type=sa.DATE(),
               nullable=False)
    op.drop_column('po_header', 'remaining_register')
    op.drop_column('po_header', 'finance_handover_amount_register')
    op.drop_column('po_header', 'order_status_source')
    op.drop_column('po_header', 'issuance_status_source')
    op.drop_column('po_header', 'supplier_category_source')
    op.drop_column('po_header', 'po_category_source')
    op.drop_column('po_header', 'description_source')
    op.drop_column('po_header', 'granularity')
    op.drop_column('po_header', 'requisition_id')
    op.drop_column('po_header', 'branch_attribution_status')
    op.drop_column('po_header', 'branch_attribution_method')
    op.drop_column('po_header', 'branch_source_text')
    op.drop_column('po_header', 'supplier_register_no_source')
    op.drop_column('po_header', 'supplier_name_source')
    op.drop_column('po_header', 'po_date_source')
    op.drop_column('po_header', 'number_source')
    op.drop_column('import_batch', 'rows_skipped')
    op.drop_column('import_batch', 'warnings')
    op.drop_column('import_batch', 'column_map')
    op.drop_column('import_batch', 'profile')
    op.drop_column('entity_alias', 'method')
    op.alter_column('dim_supplier', 'code',
               existing_type=sa.VARCHAR(length=32),
               nullable=False)
    op.drop_column('dim_supplier', 'notes_source')
    op.drop_column('dim_supplier', 'services_source')
    op.drop_column('dim_supplier', 'category_source')
    op.drop_column('dim_supplier', 'address')
    op.drop_column('dim_supplier', 'commercial_reg_no')
    op.drop_column('dim_supplier', 'register_no')
    op.alter_column('dim_cost_center', 'code',
               existing_type=sa.VARCHAR(length=32),
               nullable=False)
    op.drop_constraint(op.f('fk_dim_branch_region_id_dim_region'), 'dim_branch', type_='foreignkey')
    op.drop_constraint(op.f('uq_dim_branch_system_key'), 'dim_branch', type_='unique')
    op.alter_column('dim_branch', 'code',
               existing_type=sa.VARCHAR(length=32),
               nullable=False)
    op.drop_column('dim_branch', 'address')
    op.drop_column('dim_branch', 'region_id')
    op.drop_column('dim_branch', 'source_seq')
    op.drop_column('dim_branch', 'system_key')
    op.drop_index('ix_finance_handover_type_date', table_name='finance_handover')
    op.drop_index('ix_finance_handover_po', table_name='finance_handover')
    op.drop_table('finance_handover')
    op.drop_table('requisition')
    op.drop_table('branch_contact')
    op.drop_table('dim_employee')
    op.drop_index('ix_data_exception_status', table_name='data_exception')
    op.drop_table('data_exception')
    op.drop_table('supplier_contact')
    op.drop_table('dim_region')
    op.drop_table('dim_department')

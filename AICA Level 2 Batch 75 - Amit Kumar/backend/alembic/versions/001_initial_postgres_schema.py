"""initial postgres schema

Revision ID: 001_initial_postgres_schema
Revises: 
Create Date: 2026-08-13 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial_postgres_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Clients
    op.create_table(
        'clients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=True),
        sa.Column('reporting_period', sa.String(), nullable=True),
        sa.Column('previous_year_period', sa.String(), nullable=True),
        sa.Column('currency', sa.String(), nullable=True),
        sa.Column('accounting_framework', sa.String(), nullable=True),
        sa.Column('schedule_format', sa.String(), nullable=True),
        sa.Column('prepared_by', sa.String(), nullable=True),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clients_id'), 'clients', ['id'], unique=False)
    op.create_index(op.f('ix_clients_name'), 'clients', ['name'], unique=False)
    op.create_index(op.f('ix_clients_entity_type'), 'clients', ['entity_type'], unique=False)
    op.create_index(op.f('ix_clients_created_at'), 'clients', ['created_at'], unique=False)
    op.create_index('idx_clients_name_entity', 'clients', ['name', 'entity_type'], unique=False)

    # 2. Users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
    op.create_index('idx_users_role_active', 'users', ['role', 'is_active'], unique=False)

    # 3. Engagements
    op.create_table(
        'engagements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('reporting_period', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('partner_in_charge', sa.String(), nullable=True),
        sa.Column('manager_in_charge', sa.String(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_engagements_id'), 'engagements', ['id'], unique=False)
    op.create_index(op.f('ix_engagements_client_id'), 'engagements', ['client_id'], unique=False)
    op.create_index(op.f('ix_engagements_title'), 'engagements', ['title'], unique=False)
    op.create_index(op.f('ix_engagements_reporting_period'), 'engagements', ['reporting_period'], unique=False)
    op.create_index(op.f('ix_engagements_status'), 'engagements', ['status'], unique=False)
    op.create_index('idx_engagements_client_period', 'engagements', ['client_id', 'reporting_period'], unique=False)

    # 4. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)
    op.create_index('idx_audit_logs_client_action', 'audit_logs', ['client_id', 'action'], unique=False)

    # 5. Uploaded Files
    op.create_table(
        'uploaded_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('original_filename', sa.String(), nullable=False),
        sa.Column('stored_filepath', sa.String(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_uploaded_files_id'), 'uploaded_files', ['id'], unique=False)
    op.create_index(op.f('ix_uploaded_files_client_id'), 'uploaded_files', ['client_id'], unique=False)
    op.create_index(op.f('ix_uploaded_files_file_type'), 'uploaded_files', ['file_type'], unique=False)
    op.create_index('idx_uploaded_files_client_type', 'uploaded_files', ['client_id', 'file_type'], unique=False)

    # 6. Generated Reports
    op.create_table(
        'generated_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('report_type', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_generated_reports_id'), 'generated_reports', ['id'], unique=False)
    op.create_index(op.f('ix_generated_reports_client_id'), 'generated_reports', ['client_id'], unique=False)
    op.create_index(op.f('ix_generated_reports_report_type'), 'generated_reports', ['report_type'], unique=False)
    op.create_index('idx_reports_client_type', 'generated_reports', ['client_id', 'report_type'], unique=False)

    # 7. Notes
    op.create_table(
        'notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('note_number', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('suggested_content', sa.Text(), nullable=False),
        sa.Column('table_json', sa.Text(), nullable=True),
        sa.Column('is_modified', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notes_id'), 'notes', ['id'], unique=False)
    op.create_index(op.f('ix_notes_client_id'), 'notes', ['client_id'], unique=False)
    op.create_index(op.f('ix_notes_note_number'), 'notes', ['note_number'], unique=False)
    op.create_index('idx_notes_client_num', 'notes', ['client_id', 'note_number'], unique=False)

    # 8. Trial Balance Lines
    op.create_table(
        'trial_balance_lines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('ledger_code', sa.String(), nullable=True),
        sa.Column('ledger_name', sa.String(), nullable=False),
        sa.Column('original_group', sa.String(), nullable=True),
        sa.Column('cy_amount', sa.Float(), nullable=True),
        sa.Column('py_amount', sa.Float(), nullable=True),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('suggested_classification', sa.String(), nullable=True),
        sa.Column('final_classification', sa.String(), nullable=True),
        sa.Column('financial_statement', sa.String(), nullable=True),
        sa.Column('note_number', sa.String(), nullable=True),
        sa.Column('current_non_current', sa.String(), nullable=True),
        sa.Column('user_override', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trial_balance_lines_id'), 'trial_balance_lines', ['id'], unique=False)
    op.create_index(op.f('ix_trial_balance_lines_client_id'), 'trial_balance_lines', ['client_id'], unique=False)
    op.create_index('idx_tb_client_cls', 'trial_balance_lines', ['client_id', 'final_classification'], unique=False)

    # 9. Mapping Rules
    op.create_table(
        'mapping_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pattern', sa.String(), nullable=False),
        sa.Column('target_classification', sa.String(), nullable=False),
        sa.Column('target_statement', sa.String(), nullable=False),
        sa.Column('note_number', sa.String(), nullable=True),
        sa.Column('current_non_current', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mapping_rules_id'), 'mapping_rules', ['id'], unique=False)

    # 10. Accounting Policies
    op.create_table(
        'accounting_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('policy_number', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('suggested_content', sa.Text(), nullable=False),
        sa.Column('is_applicable', sa.Boolean(), nullable=True),
        sa.Column('is_modified', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_accounting_policies_id'), 'accounting_policies', ['id'], unique=False)

    # 11. Cash Flow Adjustments
    op.create_table(
        'cash_flow_adjustments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('adjustment_type', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=True),
        sa.Column('py_amount', sa.Float(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('remarks', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cash_flow_adjustments_id'), 'cash_flow_adjustments', ['id'], unique=False)
    op.create_index('idx_cf_client_cat', 'cash_flow_adjustments', ['client_id', 'category'], unique=False)

def downgrade() -> None:
    op.drop_table('cash_flow_adjustments')
    op.drop_table('accounting_policies')
    op.drop_table('mapping_rules')
    op.drop_table('trial_balance_lines')
    op.drop_table('notes')
    op.drop_table('generated_reports')
    op.drop_table('uploaded_files')
    op.drop_table('audit_logs')
    op.drop_table('engagements')
    op.drop_table('users')
    op.drop_table('clients')

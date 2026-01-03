"""Add transactions and updated loans tables

Revision ID: a1b2c3d4e5f6
Revises: 20251219_1205_budgeting
Create Date: 2026-01-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '20251219_1205_budgeting'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # Transaction Fee Configuration Table
    # ============================================================
    op.create_table('transaction_fees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_type', sa.Enum('credit', 'debit', 'transfer', 'p2p', 'qr_payment', 'bill_payment', 'mobile_money', 'international', 'card_payment', 'merchant_payment', 'loan_disbursement', 'loan_repayment', 'fee', 'refund', 'reversal', name='transactiontype'), nullable=False),
        sa.Column('currency', sa.Enum('USD', 'EUR', 'GBP', 'KES', 'NGN', 'ZAR', 'RWF', 'UGX', 'TZS', name='transaction_currency'), nullable=False),
        sa.Column('flat_fee', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('percentage_fee', sa.Numeric(precision=5, scale=4), nullable=False, server_default='0.0000'),
        sa.Column('min_fee', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('max_fee', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('min_amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('max_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transaction_fees_id'), 'transaction_fees', ['id'], unique=False)

    # ============================================================
    # Transactions Table
    # ============================================================
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reference_code', sa.String(length=50), nullable=False),
        sa.Column('external_reference', sa.String(length=100), nullable=True),
        # Source Account
        sa.Column('source_account_id', sa.Integer(), nullable=True),
        sa.Column('source_account_number', sa.String(length=20), nullable=True),
        # Destination Account
        sa.Column('destination_account_id', sa.Integer(), nullable=True),
        sa.Column('destination_account_number', sa.String(length=20), nullable=True),
        sa.Column('destination_bank_code', sa.String(length=20), nullable=True),
        sa.Column('destination_bank_name', sa.String(length=100), nullable=True),
        # Beneficiary Details
        sa.Column('beneficiary_name', sa.String(length=200), nullable=True),
        sa.Column('beneficiary_phone', sa.String(length=20), nullable=True),
        sa.Column('beneficiary_email', sa.String(length=255), nullable=True),
        # Amount Details
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.Enum('USD', 'EUR', 'GBP', 'KES', 'NGN', 'ZAR', 'RWF', 'UGX', 'TZS', name='transaction_currency'), nullable=False),
        # FX Details
        sa.Column('original_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('original_currency', sa.Enum('USD', 'EUR', 'GBP', 'KES', 'NGN', 'ZAR', 'RWF', 'UGX', 'TZS', name='transaction_currency'), nullable=True),
        sa.Column('exchange_rate', sa.Numeric(precision=15, scale=6), nullable=True),
        # Fees
        sa.Column('fee_amount', sa.Numeric(precision=15, scale=2), nullable=False, server_default='0.00'),
        sa.Column('fee_currency', sa.Enum('USD', 'EUR', 'GBP', 'KES', 'NGN', 'ZAR', 'RWF', 'UGX', 'TZS', name='transaction_currency'), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        # Transaction Details
        sa.Column('transaction_type', sa.Enum('credit', 'debit', 'transfer', 'p2p', 'qr_payment', 'bill_payment', 'mobile_money', 'international', 'card_payment', 'merchant_payment', 'loan_disbursement', 'loan_repayment', 'fee', 'refund', 'reversal', name='transactiontype'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', 'cancelled', 'reversed', 'on_hold', name='transactionstatus'), nullable=False),
        sa.Column('channel', sa.Enum('web', 'mobile_app', 'api', 'ussd', 'whatsapp', 'telegram', 'atm', 'pos', 'branch', name='transactionchannel'), nullable=False),
        # Description
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('narration', sa.String(length=200), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        # QR Payment
        sa.Column('qr_code', sa.String(length=500), nullable=True),
        sa.Column('merchant_id', sa.String(length=50), nullable=True),
        sa.Column('merchant_name', sa.String(length=200), nullable=True),
        # Bill Payment
        sa.Column('biller_code', sa.String(length=50), nullable=True),
        sa.Column('biller_name', sa.String(length=200), nullable=True),
        sa.Column('bill_reference', sa.String(length=100), nullable=True),
        # Mobile Money
        sa.Column('mobile_money_provider', sa.String(length=50), nullable=True),
        sa.Column('mobile_number', sa.String(length=20), nullable=True),
        # International Transfer
        sa.Column('swift_code', sa.String(length=11), nullable=True),
        sa.Column('iban', sa.String(length=34), nullable=True),
        sa.Column('routing_number', sa.String(length=9), nullable=True),
        sa.Column('purpose_code', sa.String(length=10), nullable=True),
        # Processing Dates
        sa.Column('initiated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        # Balance Tracking
        sa.Column('source_balance_before', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('source_balance_after', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('destination_balance_before', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('destination_balance_after', sa.Numeric(precision=15, scale=2), nullable=True),
        # Security
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('device_fingerprint', sa.String(length=255), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('location', sa.String(length=200), nullable=True),
        # Flags
        sa.Column('is_recurring', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_scheduled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        # Linked
        sa.Column('parent_transaction_id', sa.Integer(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['destination_account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['parent_transaction_id'], ['transactions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transactions_id'), 'transactions', ['id'], unique=False)
    op.create_index(op.f('ix_transactions_reference_code'), 'transactions', ['reference_code'], unique=True)
    op.create_index(op.f('ix_transactions_source_account_id'), 'transactions', ['source_account_id'], unique=False)
    op.create_index(op.f('ix_transactions_destination_account_id'), 'transactions', ['destination_account_id'], unique=False)

    # ============================================================
    # QR Codes Table
    # ============================================================
    op.create_table('qr_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('qr_code_data', sa.Text(), nullable=False),
        sa.Column('qr_code_image_url', sa.String(length=500), nullable=True),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('currency', sa.Enum('USD', 'EUR', 'GBP', 'KES', 'NGN', 'ZAR', 'RWF', 'UGX', 'TZS', name='transaction_currency'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scan_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_scanned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_qr_codes_id'), 'qr_codes', ['id'], unique=False)
    op.create_index(op.f('ix_qr_codes_account_id'), 'qr_codes', ['account_id'], unique=False)

    # ============================================================
    # Loan Products Table
    # ============================================================
    op.create_table('loan_products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('loan_type', sa.Enum('personal', 'auto', 'home', 'education', 'business', 'emergency', 'salary_advance', 'overdraft', name='loantype'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('min_interest_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('max_interest_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('default_interest_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('min_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('max_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('min_term_months', sa.Integer(), nullable=False),
        sa.Column('max_term_months', sa.Integer(), nullable=False),
        sa.Column('processing_fee_percentage', sa.Numeric(precision=5, scale=4), nullable=True, server_default='0'),
        sa.Column('processing_fee_flat', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('late_payment_fee', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('early_repayment_fee_percentage', sa.Numeric(precision=5, scale=4), nullable=True, server_default='0'),
        sa.Column('requires_collateral', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('collateral_types', sa.String(length=200), nullable=True),
        sa.Column('min_credit_score', sa.Integer(), nullable=True),
        sa.Column('min_income', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('repayment_frequency', sa.Enum('weekly', 'bi_weekly', 'monthly', 'quarterly', name='repaymentfrequency'), nullable=True, server_default="'monthly'"),
        sa.Column('grace_period_days', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_loan_products_id'), 'loan_products', ['id'], unique=False)

    # ============================================================
    # Loans Table (Drop old and recreate)
    # ============================================================
    op.drop_table('loans')
    
    op.create_table('loans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reference_number', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('loan_type', sa.Enum('personal', 'auto', 'home', 'education', 'business', 'emergency', 'salary_advance', 'overdraft', name='loantype'), nullable=False),
        sa.Column('purpose', sa.Text(), nullable=True),
        # Amounts
        sa.Column('requested_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('approved_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('disbursed_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True, server_default="'USD'"),
        # Terms
        sa.Column('interest_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('term_months', sa.Integer(), nullable=False),
        sa.Column('repayment_frequency', sa.Enum('weekly', 'bi_weekly', 'monthly', 'quarterly', name='repaymentfrequency'), nullable=True, server_default="'monthly'"),
        # Calculated
        sa.Column('total_interest', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_repayment', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('monthly_payment', sa.Numeric(precision=15, scale=2), nullable=True),
        # Balance Tracking
        sa.Column('principal_paid', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('interest_paid', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('fees_paid', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('total_paid', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('outstanding_balance', sa.Numeric(precision=15, scale=2), nullable=True),
        # Fees
        sa.Column('processing_fee', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('late_fees_accrued', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        # Status
        sa.Column('status', sa.Enum('draft', 'submitted', 'under_review', 'pending_documents', 'approved', 'rejected', 'disbursed', 'active', 'overdue', 'defaulted', 'paid_off', 'cancelled', 'written_off', name='loanstatus'), nullable=False, server_default="'draft'"),
        # Collateral
        sa.Column('collateral_type', sa.Enum('property', 'vehicle', 'savings', 'stocks', 'guarantor', 'salary', 'none', name='collateraltype'), nullable=True),
        sa.Column('collateral_description', sa.Text(), nullable=True),
        sa.Column('collateral_value', sa.Numeric(precision=15, scale=2), nullable=True),
        # Employment
        sa.Column('employer_name', sa.String(length=200), nullable=True),
        sa.Column('monthly_income', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('employment_duration_months', sa.Integer(), nullable=True),
        # Dates
        sa.Column('application_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('disbursed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('first_payment_date', sa.Date(), nullable=True),
        sa.Column('maturity_date', sa.Date(), nullable=True),
        sa.Column('paid_off_at', sa.DateTime(timezone=True), nullable=True),
        # Review
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('approval_notes', sa.Text(), nullable=True),
        # Tracking
        sa.Column('next_payment_date', sa.Date(), nullable=True),
        sa.Column('payments_made', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('payments_remaining', sa.Integer(), nullable=True),
        sa.Column('days_overdue', sa.Integer(), nullable=True, server_default='0'),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['loan_products.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reference_number')
    )
    op.create_index(op.f('ix_loans_id'), 'loans', ['id'], unique=False)
    op.create_index(op.f('ix_loans_user_id'), 'loans', ['user_id'], unique=False)
    op.create_index(op.f('ix_loans_reference_number'), 'loans', ['reference_number'], unique=True)

    # ============================================================
    # Loan Payments Table
    # ============================================================
    op.create_table('loan_payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('loan_id', sa.Integer(), nullable=False),
        sa.Column('payment_number', sa.Integer(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('scheduled_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('principal_component', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('interest_component', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('paid_amount', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('paid_principal', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('paid_interest', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('late_fee', sa.Numeric(precision=15, scale=2), nullable=True, server_default='0'),
        sa.Column('status', sa.Enum('scheduled', 'pending', 'paid', 'partial', 'overdue', 'waived', name='paymentstatus'), nullable=True, server_default="'scheduled'"),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('balance_after', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('transaction_id', sa.Integer(), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['loan_id'], ['loans.id'], ),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_loan_payments_id'), 'loan_payments', ['id'], unique=False)
    op.create_index(op.f('ix_loan_payments_loan_id'), 'loan_payments', ['loan_id'], unique=False)

    # ============================================================
    # Loan Documents Table
    # ============================================================
    op.create_table('loan_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('loan_id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('document_name', sa.String(length=200), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['loan_id'], ['loans.id'], ),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_loan_documents_id'), 'loan_documents', ['id'], unique=False)
    op.create_index(op.f('ix_loan_documents_loan_id'), 'loan_documents', ['loan_id'], unique=False)


def downgrade() -> None:
    # Drop new tables
    op.drop_index(op.f('ix_loan_documents_loan_id'), table_name='loan_documents')
    op.drop_index(op.f('ix_loan_documents_id'), table_name='loan_documents')
    op.drop_table('loan_documents')
    
    op.drop_index(op.f('ix_loan_payments_loan_id'), table_name='loan_payments')
    op.drop_index(op.f('ix_loan_payments_id'), table_name='loan_payments')
    op.drop_table('loan_payments')
    
    op.drop_index(op.f('ix_loans_reference_number'), table_name='loans')
    op.drop_index(op.f('ix_loans_user_id'), table_name='loans')
    op.drop_index(op.f('ix_loans_id'), table_name='loans')
    op.drop_table('loans')
    
    # Recreate old loans table
    op.create_table('loans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('interest_rate', sa.Float(), server_default='5.0'),
        sa.Column('term_months', sa.Integer(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=True),
        sa.Column('status', sa.String(), server_default='pending'),
        sa.Column('remaining_balance', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_loans_id'), 'loans', ['id'], unique=False)
    
    op.drop_index(op.f('ix_loan_products_id'), table_name='loan_products')
    op.drop_table('loan_products')
    
    op.drop_index(op.f('ix_qr_codes_account_id'), table_name='qr_codes')
    op.drop_index(op.f('ix_qr_codes_id'), table_name='qr_codes')
    op.drop_table('qr_codes')
    
    op.drop_index(op.f('ix_transactions_destination_account_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_source_account_id'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_reference_code'), table_name='transactions')
    op.drop_index(op.f('ix_transactions_id'), table_name='transactions')
    op.drop_table('transactions')
    
    op.drop_index(op.f('ix_transaction_fees_id'), table_name='transaction_fees')
    op.drop_table('transaction_fees')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS transactiontype")
    op.execute("DROP TYPE IF EXISTS transactionstatus")
    op.execute("DROP TYPE IF EXISTS transactionchannel")
    op.execute("DROP TYPE IF EXISTS transaction_currency")
    op.execute("DROP TYPE IF EXISTS loantype")
    op.execute("DROP TYPE IF EXISTS loanstatus")
    op.execute("DROP TYPE IF EXISTS repaymentfrequency")
    op.execute("DROP TYPE IF EXISTS paymentstatus")
    op.execute("DROP TYPE IF EXISTS collateraltype")

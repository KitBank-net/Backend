"""add budgeting tables

Revision ID: 20251219_1205_budgeting
Revises: 20251219_1200_notifications
Create Date: 2025-12-19 12:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251219_1205_budgeting'
down_revision = '20251219_1200_notifications'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create spending_categories table
    op.create_table(
        'spending_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category_type', sa.Enum('food_dining', 'transportation', 'shopping', 'entertainment', 
                                           'bills_utilities', 'healthcare', 'education', 'travel',
                                           'groceries', 'personal_care', 'investments', 'transfers',
                                           'income', 'other', name='categorytype'), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_spending_categories_id'), 'spending_categories', ['id'], unique=False)
    op.create_index(op.f('ix_spending_categories_user_id'), 'spending_categories', ['user_id'], unique=False)

    # Create budgets table
    op.create_table(
        'budgets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('period', sa.Enum('weekly', 'monthly', 'yearly', name='budgetperiod'), nullable=False),
        sa.Column('spent_amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('period_start_date', sa.Date(), nullable=False),
        sa.Column('period_end_date', sa.Date(), nullable=False),
        sa.Column('alert_threshold', sa.Float(), nullable=False, server_default='80'),
        sa.Column('alert_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['spending_categories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_budgets_id'), 'budgets', ['id'], unique=False)
    op.create_index(op.f('ix_budgets_user_id'), 'budgets', ['user_id'], unique=False)

    # Create savings_goals table
    op.create_table(
        'savings_goals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_amount', sa.Float(), nullable=False),
        sa.Column('current_amount', sa.Float(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('active', 'completed', 'cancelled', 'paused', name='goalstatus'), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('auto_save_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_save_amount', sa.Float(), nullable=True),
        sa.Column('auto_save_frequency', sa.Enum('weekly', 'monthly', 'yearly', name='budgetperiod'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_savings_goals_id'), 'savings_goals', ['id'], unique=False)
    op.create_index(op.f('ix_savings_goals_user_id'), 'savings_goals', ['user_id'], unique=False)

    # Create spending_insights table
    op.create_table(
        'spending_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('insight_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_dismissed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['category_id'], ['spending_categories.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_spending_insights_id'), 'spending_insights', ['id'], unique=False)
    op.create_index(op.f('ix_spending_insights_user_id'), 'spending_insights', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop spending_insights
    op.drop_index(op.f('ix_spending_insights_user_id'), table_name='spending_insights')
    op.drop_index(op.f('ix_spending_insights_id'), table_name='spending_insights')
    op.drop_table('spending_insights')

    # Drop savings_goals
    op.drop_index(op.f('ix_savings_goals_user_id'), table_name='savings_goals')
    op.drop_index(op.f('ix_savings_goals_id'), table_name='savings_goals')
    op.drop_table('savings_goals')

    # Drop budgets
    op.drop_index(op.f('ix_budgets_user_id'), table_name='budgets')
    op.drop_index(op.f('ix_budgets_id'), table_name='budgets')
    op.drop_table('budgets')

    # Drop spending_categories
    op.drop_index(op.f('ix_spending_categories_user_id'), table_name='spending_categories')
    op.drop_index(op.f('ix_spending_categories_id'), table_name='spending_categories')
    op.drop_table('spending_categories')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS goalstatus')
    op.execute('DROP TYPE IF EXISTS budgetperiod')
    op.execute('DROP TYPE IF EXISTS categorytype')

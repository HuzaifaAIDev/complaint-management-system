"""remove residence ID feature, add agent_categories table

Revision ID: d4e8f1a2b3c5
Revises: b3f7a1c9d2e4
Create Date: 2026-08-24 09:00:00.000000

Removes the Residence ID feature entirely (customers.residence_id column,
its FK/unique constraint, and the residence_ids table) and adds the new
agent_categories many-to-many table that links agents to the service
categories/skills they can be assigned complaints in.

This migration does not touch or destroy any customer, service request,
or complaint data - only the residence-verification columns/table, which
are dropped because the feature they supported no longer exists anywhere
in the application.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e8f1a2b3c5'
down_revision = 'b3f7a1c9d2e4'
branch_labels = None
depends_on = None


def upgrade():
    # --- Drop the residence_id FK/unique constraint and column from customers ---
    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.drop_constraint('fk_customers_residence_id', type_='foreignkey')
        batch_op.drop_constraint('uq_customers_residence_id', type_='unique')
        batch_op.drop_column('residence_id')

    # --- Drop the now-unused residence_ids table ---
    with op.batch_alter_table('residence_ids', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_residence_ids_code'))
    op.drop_table('residence_ids')

    # --- New table: agent_categories (agent <-> service_category skills) ---
    op.create_table(
        'agent_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['users.id']),
        sa.ForeignKeyConstraint(['category_id'], ['service_categories.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agent_id', 'category_id', name='uq_agent_category'),
    )


def downgrade():
    op.drop_table('agent_categories')

    op.create_table(
        'residence_ids',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=40), nullable=False),
        sa.Column('label', sa.String(length=120), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=False),
        sa.Column('used_by_customer_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['used_by_customer_id'], ['customers.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('residence_ids', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_residence_ids_code'), ['code'], unique=True)

    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('residence_id', sa.String(length=40), nullable=True))
        batch_op.create_unique_constraint('uq_customers_residence_id', ['residence_id'])
        batch_op.create_foreign_key('fk_customers_residence_id', 'residence_ids', ['residence_id'], ['code'])

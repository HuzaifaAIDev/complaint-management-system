"""add residence_ids table and customers.residence_id column

Revision ID: 7c1e9b2a5df0
Revises: af8a57f03679
Create Date: 2026-08-19 08:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c1e9b2a5df0'
down_revision = 'af8a57f03679'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('residence_ids',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=40), nullable=False),
    sa.Column('label', sa.String(length=120), nullable=True),
    sa.Column('is_used', sa.Boolean(), nullable=False),
    sa.Column('used_by_customer_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['used_by_customer_id'], ['customers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('residence_ids', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_residence_ids_code'), ['code'], unique=True)

    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('residence_id', sa.String(length=40), nullable=True))
        batch_op.create_unique_constraint('uq_customers_residence_id', ['residence_id'])
        batch_op.create_foreign_key('fk_customers_residence_id', 'residence_ids', ['residence_id'], ['code'])


def downgrade():
    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.drop_constraint('fk_customers_residence_id', type_='foreignkey')
        batch_op.drop_constraint('uq_customers_residence_id', type_='unique')
        batch_op.drop_column('residence_id')

    with op.batch_alter_table('residence_ids', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_residence_ids_code'))

    op.drop_table('residence_ids')

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE flags (
            key               text PRIMARY KEY,
            enabled           boolean NOT NULL DEFAULT true,
            variations        jsonb NOT NULL DEFAULT '[false, true]',
            default_variation int NOT NULL DEFAULT 0,
            rules             jsonb NOT NULL DEFAULT '[]',
            rollout           jsonb,
            updated_at        timestamptz NOT NULL DEFAULT now()
        )
    """)


def downgrade():
    op.execute("DROP TABLE flags")

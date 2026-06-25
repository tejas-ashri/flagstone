from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE sdk_keys (
            key_hash   text PRIMARY KEY,
            label      text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            revoked_at timestamptz
        )
    """)


def downgrade():
    op.execute("DROP TABLE sdk_keys")

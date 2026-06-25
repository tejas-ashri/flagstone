from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE events (
            id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            flag_key       text NOT NULL REFERENCES flags(key) ON DELETE CASCADE,
            event_type     text NOT NULL CHECK (event_type IN ('exposure', 'conversion')),
            variation_index int NOT NULL,
            user_id        text NOT NULL,
            attributes     jsonb NOT NULL DEFAULT '{}',
            received_at    timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_events_flag_key_type ON events (flag_key, event_type, received_at)
    """)


def downgrade():
    op.execute("DROP TABLE events")

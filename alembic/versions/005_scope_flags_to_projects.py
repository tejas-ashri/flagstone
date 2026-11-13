import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def _run(sql: str) -> None:
    # asyncpg runs each execute() as a prepared statement, which allows only one
    # command, so send the statements one at a time.
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def upgrade():
    # Existing flags, events and SDK keys all move into the Default project.
    _run("""
        ALTER TABLE flags ADD COLUMN project_id text NOT NULL DEFAULT 'default'
            REFERENCES projects(id) ON DELETE CASCADE;
        ALTER TABLE events ADD COLUMN project_id text NOT NULL DEFAULT 'default';

        ALTER TABLE events DROP CONSTRAINT events_flag_key_fkey;
        ALTER TABLE flags DROP CONSTRAINT flags_pkey;
        ALTER TABLE flags ADD PRIMARY KEY (project_id, key);
        ALTER TABLE events ADD CONSTRAINT events_project_flag_fkey
            FOREIGN KEY (project_id, flag_key) REFERENCES flags(project_id, key) ON DELETE CASCADE;

        ALTER TABLE flags ALTER COLUMN project_id DROP DEFAULT;
        ALTER TABLE events ALTER COLUMN project_id DROP DEFAULT;

        DROP INDEX ix_events_flag_key_type;
        CREATE INDEX ix_events_project_flag_type
            ON events (project_id, flag_key, event_type, received_at);

        ALTER TABLE sdk_keys
            ADD COLUMN project_id text NOT NULL DEFAULT 'default'
                REFERENCES projects(id) ON DELETE CASCADE,
            ADD COLUMN prefix text NOT NULL DEFAULT '',
            ADD COLUMN last_used_at timestamptz;
        ALTER TABLE sdk_keys ALTER COLUMN project_id DROP DEFAULT;
        CREATE INDEX ix_sdk_keys_project_id ON sdk_keys (project_id)
    """)


def downgrade():
    # Flag keys are only unique per project, so going back to a single global
    # key space would lose or collide data. Refuse instead of deleting it.
    bind = op.get_bind()
    other = bind.execute(sa.text("""
        SELECT (SELECT count(*) FROM flags WHERE project_id <> 'default')
             + (SELECT count(*) FROM sdk_keys WHERE project_id <> 'default')
    """)).scalar()
    if other:
        raise RuntimeError(
            "Cannot downgrade: flags or SDK keys exist outside the Default project. "
            "Delete those projects first."
        )
    _run("""
        DROP INDEX ix_sdk_keys_project_id;
        ALTER TABLE sdk_keys DROP COLUMN last_used_at, DROP COLUMN prefix, DROP COLUMN project_id;

        DROP INDEX ix_events_project_flag_type;
        CREATE INDEX ix_events_flag_key_type ON events (flag_key, event_type, received_at);

        ALTER TABLE events DROP CONSTRAINT events_project_flag_fkey;
        ALTER TABLE flags DROP CONSTRAINT flags_pkey;
        ALTER TABLE flags ADD PRIMARY KEY (key);
        ALTER TABLE events ADD CONSTRAINT events_flag_key_fkey
            FOREIGN KEY (flag_key) REFERENCES flags(key) ON DELETE CASCADE;

        ALTER TABLE events DROP COLUMN project_id;
        ALTER TABLE flags DROP COLUMN project_id
    """)

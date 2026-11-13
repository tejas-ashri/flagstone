from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def _run(sql: str) -> None:
    # asyncpg runs each execute() as a prepared statement, which allows only one
    # command, so send the statements one at a time.
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def upgrade():
    _run("""
        CREATE TABLE projects (
            id         text PRIMARY KEY,
            name       text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        INSERT INTO projects (id, name) VALUES ('default', 'Default');

        CREATE TABLE users (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email         text NOT NULL UNIQUE,
            name          text NOT NULL DEFAULT '',
            avatar_url    text,
            created_at    timestamptz NOT NULL DEFAULT now(),
            last_login_at timestamptz
        );

        CREATE TABLE identities (
            provider         text NOT NULL,
            provider_user_id text NOT NULL,
            user_id          uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY (provider, provider_user_id)
        );
        CREATE INDEX ix_identities_user_id ON identities (user_id);

        CREATE TABLE memberships (
            project_id text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role       text NOT NULL CHECK (role IN ('admin', 'viewer')),
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (project_id, user_id)
        );

        CREATE TABLE invitations (
            project_id text NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            email      text NOT NULL,
            role       text NOT NULL CHECK (role IN ('admin', 'viewer')),
            invited_by uuid REFERENCES users(id) ON DELETE SET NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (project_id, email)
        );

        CREATE TABLE sessions (
            token_hash text PRIMARY KEY,
            user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at timestamptz NOT NULL DEFAULT now(),
            expires_at timestamptz NOT NULL
        );
        CREATE INDEX ix_sessions_user_id ON sessions (user_id)
    """)


def downgrade():
    _run("""
        DROP TABLE sessions;
        DROP TABLE invitations;
        DROP TABLE memberships;
        DROP TABLE identities;
        DROP TABLE users;
        DROP TABLE projects
    """)

import sqlite3
from apps.api.migrations import MIGRATIONS, migrate, current_version


def test_fresh_and_idempotent():
    c = sqlite3.connect(":memory:", isolation_level=None)
    assert migrate(c) == MIGRATIONS[-1][0]
    assert migrate(c) == MIGRATIONS[-1][0]
    assert c.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == len(MIGRATIONS)
    c.execute("SELECT * FROM triage")


def test_adopts_pre_migration_db_without_data_loss():
    c = sqlite3.connect(":memory:", isolation_level=None)
    c.execute("CREATE TABLE users(id TEXT PRIMARY KEY, email TEXT UNIQUE, pw TEXT, persona TEXT, created REAL)")
    c.execute("INSERT INTO users VALUES ('u1','a@b.c','x','p',0)")
    migrate(c)
    assert c.execute("SELECT email FROM users").fetchone()[0] == "a@b.c"
    assert current_version(c) == MIGRATIONS[-1][0]

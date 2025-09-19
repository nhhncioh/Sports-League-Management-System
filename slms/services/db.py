from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Union

from flask import g
from sqlalchemy import text

from slms.extensions import db
from sqlalchemy import text as _text, inspect

ParamType = Union[Sequence[Any], Mapping[str, Any], Any]


class DatabaseWrapper:
    """Lightweight helper that mimics the previous DB-API connection pattern."""

    def __init__(self) -> None:
        self._session = db.session

    def cursor(self) -> "SessionCursor":
        return SessionCursor(self._session)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    def close(self) -> None:
        self._session.close()


class SessionCursor:
    def __init__(self, session) -> None:
        self._session = session
        self._result = None

    def execute(self, query: str, params: ParamType = None):
        statement, bind_params = _prepare_statement(query, params)
        self._result = self._session.execute(statement, bind_params)
        return self._result

    def fetchone(self):
        if self._result is None:
            return None
        return self._result.fetchone()

    def fetchall(self):
        if self._result is None:
            return []
        return self._result.fetchall()

    def fetchmany(self, size: int | None = None):
        if self._result is None:
            return []
        return self._result.fetchmany(size)

    def close(self) -> None:
        self._result = None


def _prepare_statement(query: str, params: ParamType = None):
    if params is None:
        return text(query), {}

    if isinstance(params, Mapping):
        bind_params: Dict[str, Any] = {}
        new_query = query
        for key, value in params.items():
            placeholder = f"%({key})s"
            new_query = new_query.replace(placeholder, f":{key}")
            bind_params[key] = value
        return text(new_query), bind_params

    if not isinstance(params, Sequence) or isinstance(params, (str, bytes)):
        params = (params,)

    parts = query.split("%s")
    if len(parts) - 1 != len(params):
        raise ValueError("Mismatched placeholders and parameters in query.")

    bind_params = {f"param_{idx}": value for idx, value in enumerate(params)}
    new_query = "".join(
        part + (f":param_{idx}" if idx < len(params) else "")
        for idx, part in enumerate(parts)
    )
    return text(new_query), bind_params


def get_db() -> DatabaseWrapper:
    if "db" not in g:
        g.db = DatabaseWrapper()
    return g.db


def close_db(_: Exception | None = None) -> None:
    wrapper = g.pop("db", None)
    if wrapper is not None:
        wrapper.close()
    db.session.remove()


__all__ = ["get_db", "close_db", "DatabaseWrapper"]



def ensure_minimum_schema() -> None:
    """Ensure critical columns/tables exist for the ORM models used at login.

    This is a pragmatic guard to prevent developer 500s when the DB was
    initialized from legacy schema without Alembic migrations applied.
    Currently ensures:
      - user.two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE
    """
    try:
        engine = db.engine
        dialect = engine.dialect.name
        with engine.begin() as conn:
            if dialect == "postgresql":
                exists = conn.execute(
                    _text(
                        """
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'user' AND column_name = 'two_factor_enabled'
                        """
                    )
                ).scalar()
                if not exists:
                    conn.execute(_text('ALTER TABLE "user" ADD COLUMN two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE'))

                exists_active = conn.execute(
                    _text(
                        """
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'user' AND column_name = 'is_active'
                        """
                    )
                ).scalar()
                if not exists_active:
                    conn.execute(_text('ALTER TABLE "user" ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE'))

                league_columns = {
                    'primary_color': "ALTER TABLE leagues ADD COLUMN primary_color TEXT",
                    'secondary_color': "ALTER TABLE leagues ADD COLUMN secondary_color TEXT",
                    'accent_color': "ALTER TABLE leagues ADD COLUMN accent_color TEXT",
                    'text_color': "ALTER TABLE leagues ADD COLUMN text_color TEXT",
                    'logo_url': "ALTER TABLE leagues ADD COLUMN logo_url TEXT",
                    'hero_image_url': "ALTER TABLE leagues ADD COLUMN hero_image_url TEXT",
                    'homepage_title': "ALTER TABLE leagues ADD COLUMN homepage_title TEXT",
                    'homepage_subtitle': "ALTER TABLE leagues ADD COLUMN homepage_subtitle TEXT",
                    'homepage_background_url': "ALTER TABLE leagues ADD COLUMN homepage_background_url TEXT",
                    'homepage_cta_text': "ALTER TABLE leagues ADD COLUMN homepage_cta_text TEXT",
                    'homepage_cta_url': "ALTER TABLE leagues ADD COLUMN homepage_cta_url TEXT",
                    'homepage_highlights_json': "ALTER TABLE leagues ADD COLUMN homepage_highlights_json TEXT"
                }
                for column, statement in league_columns.items():
                    exists_column = conn.execute(_text(
                        """
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'leagues' AND column_name = :column
                        """
                    ), {'column': column}).scalar()
                    if not exists_column:
                        conn.execute(_text(statement))

                conn.execute(_text("""
                    CREATE TABLE IF NOT EXISTS league_fee_plans (
                        plan_id SERIAL PRIMARY KEY,
                        league_id INTEGER UNIQUE REFERENCES leagues(league_id) ON DELETE CASCADE,
                        total_fee_cents INTEGER NOT NULL DEFAULT 0,
                        deposit_cents INTEGER,
                        currency TEXT DEFAULT 'USD',
                        notes TEXT,
                        installments_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                        installment_count INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
                conn.execute(_text("""
                    CREATE TABLE IF NOT EXISTS league_fee_installments (
                        installment_id SERIAL PRIMARY KEY,
                        plan_id INTEGER REFERENCES league_fee_plans(plan_id) ON DELETE CASCADE,
                        label TEXT NOT NULL,
                        due_date DATE,
                        amount_cents INTEGER NOT NULL DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        notes TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
                conn.execute(_text("""
                    CREATE TABLE IF NOT EXISTS league_installment_status (
                        status_id SERIAL PRIMARY KEY,
                        installment_id INTEGER REFERENCES league_fee_installments(installment_id) ON DELETE CASCADE,
                        team_id INTEGER REFERENCES teams(team_id) ON DELETE CASCADE,
                        status TEXT DEFAULT 'pending',
                        amount_paid_cents INTEGER,
                        paid_at TIMESTAMPTZ,
                        notes TEXT,
                        UNIQUE(installment_id, team_id)
                    )
                """))

            elif dialect == "sqlite":
                rows = conn.execute(_text("PRAGMA table_info('user')")).fetchall()
                names = {r[1] for r in rows} if rows else set()
                if "two_factor_enabled" not in names:
                    conn.execute(_text("ALTER TABLE user ADD COLUMN two_factor_enabled BOOLEAN NOT NULL DEFAULT 0"))
                if "is_active" not in names:
                    conn.execute(_text("ALTER TABLE user ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))

                league_columns_sqlite = {
                    'primary_color': "ALTER TABLE leagues ADD COLUMN primary_color TEXT",
                    'secondary_color': "ALTER TABLE leagues ADD COLUMN secondary_color TEXT",
                    'accent_color': "ALTER TABLE leagues ADD COLUMN accent_color TEXT",
                    'text_color': "ALTER TABLE leagues ADD COLUMN text_color TEXT",
                    'logo_url': "ALTER TABLE leagues ADD COLUMN logo_url TEXT",
                    'hero_image_url': "ALTER TABLE leagues ADD COLUMN hero_image_url TEXT",
                    'homepage_title': "ALTER TABLE leagues ADD COLUMN homepage_title TEXT",
                    'homepage_subtitle': "ALTER TABLE leagues ADD COLUMN homepage_subtitle TEXT",
                    'homepage_background_url': "ALTER TABLE leagues ADD COLUMN homepage_background_url TEXT",
                    'homepage_cta_text': "ALTER TABLE leagues ADD COLUMN homepage_cta_text TEXT",
                    'homepage_cta_url': "ALTER TABLE leagues ADD COLUMN homepage_cta_url TEXT",
                    'homepage_highlights_json': "ALTER TABLE leagues ADD COLUMN homepage_highlights_json TEXT"
                }
                for column, statement in league_columns_sqlite.items():
                    if column not in names:
                        conn.execute(_text(statement))

                conn.execute(_text("""
                    CREATE TABLE IF NOT EXISTS league_fee_plans (
                        plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        league_id INTEGER UNIQUE REFERENCES leagues(league_id) ON DELETE CASCADE,
                        total_fee_cents INTEGER NOT NULL DEFAULT 0,
                        deposit_cents INTEGER,
                        currency TEXT DEFAULT 'USD',
                        notes TEXT,
                        installments_enabled INTEGER NOT NULL DEFAULT 0,
                        installment_count INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.execute(_text("""
                    CREATE TABLE IF NOT EXISTS league_fee_installments (
                        installment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plan_id INTEGER REFERENCES league_fee_plans(plan_id) ON DELETE CASCADE,
                        label TEXT NOT NULL,
                        due_date TEXT,
                        amount_cents INTEGER NOT NULL DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        notes TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.execute(_text("""
                    CREATE TABLE IF NOT EXISTS league_installment_status (
                        status_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        installment_id INTEGER REFERENCES league_fee_installments(installment_id) ON DELETE CASCADE,
                        team_id INTEGER REFERENCES teams(team_id) ON DELETE CASCADE,
                        status TEXT DEFAULT 'pending',
                        amount_paid_cents INTEGER,
                        paid_at TEXT,
                        notes TEXT,
                        UNIQUE(installment_id, team_id)
                    )
                """))
    except Exception:
        # Never block app startup if this safety net fails
        pass

def ensure_core_tables() -> None:
    """Ensure core ORM tables exist. If missing (e.g., fresh DB without migrations), create them.

    This is a development convenience so the app can run without manual Alembic steps.
    """
    try:
        engine = db.engine
        inspector = inspect(engine)
        required_tables = {
            'organization', 'user', 'league', 'season', 'team', 'venue', 'game'
        }
        existing = set(inspector.get_table_names())
        if not required_tables.issubset(existing):
            db.create_all()
    except Exception:
        # Do not block startup on errors here
        pass


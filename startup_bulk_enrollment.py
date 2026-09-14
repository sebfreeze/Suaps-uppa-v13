"""Execute the private bulk-enrollment payload without requiring a Streamlit session.

Personal identifiers are supplied only through ``SUAPS_BULK_ENROLL_JSON`` at
runtime. This module contains no production student data.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from bulk_enrollment import apply_bulk_enrollment_json


def run_startup_bulk_enrollment(*, raw_payload, db_factory, use_postgres=False, logger=print):
    raw = str(raw_payload or "").strip()
    if not raw:
        return None

    try:
        result = apply_bulk_enrollment_json(
            db_factory,
            raw,
            use_postgres=bool(use_postgres),
        )
    except Exception as exc:
        logger(f"[SUAPS_BULK_ENROLL_STARTUP] status=error type={type(exc).__name__}")
        return {"status": "error"}

    status = str(result.get("status") or "unknown")
    if status == "ok":
        logger(
            "[SUAPS_BULK_ENROLL_STARTUP] "
            f"status=ok enrolled={int(result.get('enrolled') or 0)} "
            f"created={int(result.get('created') or 0)} "
            f"updated={int(result.get('updated') or 0)} "
            f"offer_id={result.get('offer_id')}"
        )
    elif status == "missing_students":
        logger(
            "[SUAPS_BULK_ENROLL_STARTUP] "
            f"status=missing_students count={len(result.get('missing') or [])}"
        )
    elif status == "ambiguous_students":
        logger(
            "[SUAPS_BULK_ENROLL_STARTUP] "
            f"status=ambiguous_students count={len(result.get('ambiguous') or [])}"
        )
    else:
        logger(f"[SUAPS_BULK_ENROLL_STARTUP] status={status}")
    return result


class _PostgresCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    @staticmethod
    def _sql(sql):
        return str(sql).replace("?", "%s")

    def execute(self, sql, params=()):
        self._cursor.execute(self._sql(sql), tuple(params or ()))
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class _PostgresConnection:
    def __init__(self, raw):
        self._raw = raw

    def cursor(self):
        return _PostgresCursor(self._raw.cursor())

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()


def _postgres_factory(database_url):
    import psycopg
    from psycopg.rows import dict_row

    def factory():
        raw = psycopg.connect(database_url, row_factory=dict_row)
        return _PostgresConnection(raw)

    return factory


def _sqlite_factory(path):
    path = Path(path)

    def factory():
        conn = sqlite3.connect(path, check_same_thread=False, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    return factory


def run_from_environment(*, logger=print):
    raw = os.getenv("SUAPS_BULK_ENROLL_JSON", "").strip()
    if not raw:
        return None

    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        try:
            import psycopg  # noqa: F401
        except Exception:
            logger("[SUAPS_BULK_ENROLL_STARTUP] status=deferred dependency=psycopg")
            return {"status": "deferred"}
        return run_startup_bulk_enrollment(
            raw_payload=raw,
            db_factory=_postgres_factory(database_url),
            use_postgres=True,
            logger=logger,
        )

    db_path = os.getenv("SUAPS_SQLITE_DB", "suaps_v14.db")
    return run_startup_bulk_enrollment(
        raw_payload=raw,
        db_factory=_sqlite_factory(db_path),
        use_postgres=False,
        logger=logger,
    )

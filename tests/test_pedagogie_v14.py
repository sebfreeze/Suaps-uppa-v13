import os

import pytest

from pedagogie_v14 import (
    QmarkConnection,
    create_v14_session,
    init_v14_pedagogy,
    resource_connection_factory,
)


class FakeRaw:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))
        return self

    def commit(self):
        pass

    def close(self):
        pass


def test_qmark_connection_translates_placeholders():
    raw = FakeRaw()
    conn = QmarkConnection(raw)
    conn.execute("SELECT * FROM x WHERE a=? AND b=?", (1, 2))
    assert raw.calls == [("SELECT * FROM x WHERE a=%s AND b=%s", (1, 2))]


def test_resource_connection_factory_uses_sqlite_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    marker = object()
    factory, use_postgres = resource_connection_factory(lambda: marker)
    assert use_postgres is False
    assert factory() is marker


def test_init_v14_pedagogy_uses_detected_backend_for_seance_migration(monkeypatch):
    legacy_factory = lambda: object()
    postgres_factory = lambda: object()
    calls = []

    monkeypatch.setattr(
        "pedagogie_v14.resource_connection_factory",
        lambda factory: (postgres_factory, True),
    )
    monkeypatch.setattr(
        "pedagogie_v14.resources.init_pedagogy_schema",
        lambda factory, use_postgres: calls.append(("schema", factory, use_postgres)),
    )
    monkeypatch.setattr(
        "pedagogie_v14.seed_official_resources",
        lambda factory, use_postgres: calls.append(("seed", factory, use_postgres)),
    )
    monkeypatch.setattr(
        "pedagogie_v14.resources.ensure_seance_resource_column",
        lambda factory, use_postgres: calls.append(("seances", factory, use_postgres)),
    )

    init_v14_pedagogy(legacy_factory)

    assert calls[-1] == ("seances", postgres_factory, True)


def test_create_v14_session_resolves_offer_and_links_resource():
    calls = []

    def one(sql, params=()):
        assert "FROM offres" in sql
        assert params[0] == "Natation"
        return {"id": 42, "intitule": "Natation tous niveaux"}

    def exe(sql, params=()):
        calls.append((sql, params))
        return 99

    rid = create_v14_session(
        exe,
        one,
        {"id": 7, "activite": "Natation", "titre": "Crawl : coordination complète"},
        "2026-09-14",
        "Natation tous niveaux",
    )
    assert rid == 99
    assert calls == [(
        "INSERT INTO seances(offre_id,date_seance,theme,ressource_id,qr_ouvert) VALUES(?,?,?,?,0)",
        (42, "2026-09-14", "Crawl : coordination complète", 7),
    )]


def test_create_v14_session_rejects_unknown_offer():
    with pytest.raises(ValueError, match="créneau"):
        create_v14_session(
            lambda *args: None,
            lambda *args: None,
            {"id": 7, "activite": "Natation", "titre": "Crawl"},
            "2026-09-14",
            "Groupe inconnu",
        )

from collections import Counter

from pedagogie_resources import init_pedagogy_schema, list_resources
from pedagogie_seed import OFFICIAL_SESSIONS, seed_official_resources


EXPECTED = {
    "Natation": 10,
    "Rugby": 10,
    "Sauvetage / SSA": 10,
    "Course à pied": 10,
    "Pelote Basque": 10,
    "Surf": 5,
}


def sqlite_factory(tmp_path):
    import sqlite3

    db_path = tmp_path / "seed.sqlite"

    def get_conn():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    return get_conn


def test_official_catalog_has_exactly_55_complete_sessions():
    assert len(OFFICIAL_SESSIONS) == 55
    assert Counter(s["activite"] for s in OFFICIAL_SESSIONS) == EXPECTED
    assert len({s["seed_key"] for s in OFFICIAL_SESSIONS}) == 55
    required = {
        "seed_key", "activite", "numero", "titre", "objectif", "competences",
        "materiel", "echauffement", "situations", "variables",
        "criteres_reussite", "securite", "retour_bilan",
    }
    for session in OFFICIAL_SESSIONS:
        assert required <= set(session)
        assert session["objectif"].strip()
        assert session["echauffement"].strip()
        assert session["retour_bilan"].strip()
        for key in ("competences", "materiel", "situations", "variables", "criteres_reussite", "securite"):
            assert session[key], f"{session['seed_key']} has empty {key}"
        assert len(session["situations"]) >= 2
        assert len(session["variables"]) >= 2
        assert len(session["criteres_reussite"]) >= 2
        assert len(session["securite"]) >= 2


def test_seed_is_idempotent_and_creates_only_official_resources(tmp_path):
    get_conn = sqlite_factory(tmp_path)
    init_pedagogy_schema(get_conn, False)
    assert seed_official_resources(get_conn, False) == 55
    assert seed_official_resources(get_conn, False) == 0
    rows = list_resources(get_conn)
    assert len(rows) == 55
    assert all(r["officiel_suaps"] == 1 for r in rows)
    assert all(r["visible_etudiants"] == 0 for r in rows)
    assert Counter(r["activite"] for r in rows) == EXPECTED

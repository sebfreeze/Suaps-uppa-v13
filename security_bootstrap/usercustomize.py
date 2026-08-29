"""Bootstrap complémentaire de migration PostgreSQL pour l'application SUAPS.

Ce module est chargé automatiquement après security_bootstrap/sitecustomize.py
sur Render. Il conserve les injections historiques de usercustomize.py, crée de
façon idempotente le schéma PostgreSQL complet et journalise un audit non
sensible des volumes. Aucun secret ni donnée nominative n'est écrit dans les
logs.
"""
from __future__ import annotations

import builtins
import importlib.util
import os
from pathlib import Path


# Conserver les injections historiques Compétition / Pédagogie.
_root = Path(__file__).resolve().parents[1]
_legacy = _root / "usercustomize.py"
if _legacy.exists():
    try:
        _spec = importlib.util.spec_from_file_location("suaps_legacy_usercustomize", _legacy)
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
    except Exception as exc:
        print(f"[SUAPS_BOOTSTRAP] legacy_usercustomize_error={type(exc).__name__}")


# Corrige l'initialisation des semestres : un créneau déjà rattaché uniquement
# au S2 ne doit plus être automatiquement réajouté au S1 à chaque redémarrage.
_previous_compile = builtins.compile


def _patch_semester_seed(source):
    if not isinstance(source, str):
        return source
    old = '_c_sem.execute("INSERT OR IGNORE INTO offre_semestres(offre_id,semestre) SELECT id,\'Semestre 1 — 2026/2027\' FROM offres")'
    new = '_c_sem.execute("INSERT OR IGNORE INTO offre_semestres(offre_id,semestre) SELECT o.id,\'Semestre 1 — 2026/2027\' FROM offres o WHERE NOT EXISTS (SELECT 1 FROM offre_semestres os WHERE os.offre_id=o.id)")'
    if old in source:
        source = source.replace(old, new, 1)
    return source


def _compile(source, filename, mode, *args, **kwargs):
    return _previous_compile(_patch_semester_seed(source), filename, mode, *args, **kwargs)


builtins.compile = _compile


SCHEMA_DDL = [
    """CREATE TABLE IF NOT EXISTS utilisateurs(
        id BIGSERIAL PRIMARY KEY, profil TEXT NOT NULL, nom TEXT NOT NULL,
        prenom TEXT NOT NULL, email TEXT NOT NULL UNIQUE, identifiant TEXT,
        composante TEXT, actif INTEGER DEFAULT 1)""",
    """CREATE TABLE IF NOT EXISTS offres(
        id BIGSERIAL PRIMARY KEY, activite TEXT NOT NULL, intitule TEXT NOT NULL,
        jour_horaire TEXT, lieu TEXT, capacite INTEGER DEFAULT 20,
        public TEXT DEFAULT 'Tous', ouverte INTEGER DEFAULT 1)""",
    """CREATE TABLE IF NOT EXISTS inscriptions(
        id BIGSERIAL PRIMARY KEY, utilisateur_id BIGINT NOT NULL,
        offre_id BIGINT NOT NULL, modalite TEXT NOT NULL,
        statut TEXT DEFAULT 'Inscrit', date_inscription TEXT NOT NULL,
        UNIQUE(utilisateur_id,offre_id))""",
    """CREATE TABLE IF NOT EXISTS seances(
        id BIGSERIAL PRIMARY KEY, offre_id BIGINT NOT NULL,
        date_seance TEXT NOT NULL, theme TEXT, qr_token TEXT,
        qr_ouvert INTEGER DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS presences(
        id BIGSERIAL PRIMARY KEY, seance_id BIGINT NOT NULL,
        utilisateur_id BIGINT NOT NULL, statut TEXT DEFAULT 'Présent',
        mode_validation TEXT DEFAULT 'Manuel', commentaire TEXT,
        UNIQUE(seance_id,utilisateur_id))""",
    """CREATE TABLE IF NOT EXISTS evaluations(
        id BIGSERIAL PRIMARY KEY, utilisateur_id BIGINT NOT NULL,
        activite TEXT NOT NULL, intitule TEXT NOT NULL, note REAL,
        bareme REAL DEFAULT 20, coefficient REAL DEFAULT 1,
        commentaire TEXT, date_eval TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS performances(
        id BIGSERIAL PRIMARY KEY, utilisateur_id BIGINT NOT NULL,
        activite TEXT NOT NULL, intitule TEXT NOT NULL, valeur REAL,
        unite TEXT, commentaire TEXT, date_perf TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS competences(
        id BIGSERIAL PRIMARY KEY, activite TEXT NOT NULL, code TEXT NOT NULL,
        libelle TEXT NOT NULL, UNIQUE(activite,code))""",
    """CREATE TABLE IF NOT EXISTS acquisitions(
        id BIGSERIAL PRIMARY KEY, utilisateur_id BIGINT NOT NULL,
        competence_id BIGINT NOT NULL, niveau TEXT DEFAULT 'Non évalué',
        commentaire TEXT, date_validation TEXT,
        UNIQUE(utilisateur_id,competence_id))""",
    """CREATE TABLE IF NOT EXISTS baremes(
        id BIGSERIAL PRIMARY KEY, activite TEXT NOT NULL, nom TEXT NOT NULL,
        description TEXT, unite TEXT DEFAULT 'points', valeur_0 REAL DEFAULT 0,
        valeur_20 REAL DEFAULT 20, actif INTEGER DEFAULT 1)""",
    """CREATE TABLE IF NOT EXISTS actualites(
        id BIGSERIAL PRIMARY KEY, categorie TEXT NOT NULL, titre TEXT NOT NULL,
        contenu TEXT NOT NULL, date_publication TEXT NOT NULL, lien TEXT,
        actif INTEGER DEFAULT 1)""",
    """CREATE TABLE IF NOT EXISTS evaluations_finales(
        id BIGSERIAL PRIMARY KEY, utilisateur_id BIGINT NOT NULL,
        activite TEXT NOT NULL, performance REAL DEFAULT 0,
        competences REAL DEFAULT 0, presences REAL DEFAULT 0,
        projet REAL DEFAULT 0, total REAL DEFAULT 0, commentaire TEXT,
        date_evaluation TEXT, UNIQUE(utilisateur_id,activite))""",
    """CREATE TABLE IF NOT EXISTS offre_semestres(
        offre_id BIGINT NOT NULL, semestre TEXT NOT NULL,
        PRIMARY KEY(offre_id,semestre))""",
    """CREATE TABLE IF NOT EXISTS equipes(
        id BIGSERIAL PRIMARY KEY, nom TEXT NOT NULL, activite TEXT NOT NULL,
        couleur TEXT, capitaine_id BIGINT, date_creation TEXT, photo BYTEA)""",
    """CREATE TABLE IF NOT EXISTS equipe_joueurs(
        id BIGSERIAL PRIMARY KEY, equipe_id BIGINT NOT NULL,
        utilisateur_id BIGINT NOT NULL, numero TEXT, poste TEXT,
        titulaire INTEGER DEFAULT 1, photo BYTEA,
        UNIQUE(equipe_id,utilisateur_id))""",
    """CREATE TABLE IF NOT EXISTS tournois(
        id BIGSERIAL PRIMARY KEY, nom TEXT NOT NULL, activite TEXT NOT NULL,
        formule TEXT NOT NULL, date_tournoi TEXT, lieu TEXT,
        statut TEXT DEFAULT 'Préparation')""",
    """CREATE TABLE IF NOT EXISTS tournoi_equipes(
        id BIGSERIAL PRIMARY KEY, tournoi_id BIGINT NOT NULL,
        equipe_id BIGINT NOT NULL, poule TEXT DEFAULT 'A',
        UNIQUE(tournoi_id,equipe_id))""",
    """CREATE TABLE IF NOT EXISTS matchs(
        id BIGSERIAL PRIMARY KEY, activite TEXT NOT NULL,
        equipe_a_id BIGINT NOT NULL, equipe_b_id BIGINT NOT NULL,
        tournoi_id BIGINT, phase TEXT, date_match TEXT, heure TEXT, lieu TEXT,
        arbitre TEXT, score_a INTEGER, score_b INTEGER,
        statut TEXT DEFAULT 'Prévu', observations TEXT)""",
    """CREATE TABLE IF NOT EXISTS suaps_migration_meta(
        cle TEXT PRIMARY KEY, valeur TEXT NOT NULL,
        maj TIMESTAMPTZ NOT NULL DEFAULT NOW())""",
    "CREATE INDEX IF NOT EXISTS ix_ins_u ON inscriptions(utilisateur_id,statut)",
    "CREATE INDEX IF NOT EXISTS ix_ins_o ON inscriptions(offre_id,statut)",
    "CREATE INDEX IF NOT EXISTS ix_pre_u ON presences(utilisateur_id,statut)",
    "CREATE INDEX IF NOT EXISTS ix_sea_o ON seances(offre_id,id)",
]

AUDIT_TABLES = [
    "utilisateurs", "offres", "inscriptions", "seances", "presences",
    "evaluations", "performances", "competences", "acquisitions", "baremes",
    "actualites", "evaluations_finales", "offre_semestres", "equipes",
    "equipe_joueurs", "tournois", "tournoi_equipes", "matchs",
]


def _ensure_postgres_schema_and_audit():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print("[SUAPS_DB_AUDIT] engine=sqlite fallback=active")
        return

    try:
        import psycopg

        counts = {}
        with psycopg.connect(database_url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                for ddl in SCHEMA_DDL:
                    cur.execute(ddl)
                cur.execute(
                    """INSERT INTO suaps_migration_meta(cle,valeur,maj)
                       VALUES('schema_version','2026-08-29-pg1',NOW())
                       ON CONFLICT(cle) DO UPDATE
                       SET valeur=EXCLUDED.valeur, maj=EXCLUDED.maj"""
                )
                for table in AUDIT_TABLES:
                    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                    counts[table] = int(cur.fetchone()[0])
            conn.commit()
        summary = ",".join(f"{k}={v}" for k, v in counts.items())
        print(f"[SUAPS_DB_AUDIT] engine=postgres schema=2026-08-29-pg1 {summary}")
    except Exception as exc:
        print(f"[SUAPS_DB_AUDIT] error={type(exc).__name__}:{exc}")


_ensure_postgres_schema_and_audit()

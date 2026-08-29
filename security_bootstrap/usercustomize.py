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


_previous_compile = builtins.compile


def _patch_generated_source(source):
    if not isinstance(source, str):
        return source

    # Le S2 ne doit pas être réinjecté en S1 à chaque redémarrage.
    old = '_c_sem.execute("INSERT OR IGNORE INTO offre_semestres(offre_id,semestre) SELECT id,\'Semestre 1 — 2026/2027\' FROM offres")'
    new = '_c_sem.execute("INSERT OR IGNORE INTO offre_semestres(offre_id,semestre) SELECT o.id,\'Semestre 1 — 2026/2027\' FROM offres o WHERE NOT EXISTS (SELECT 1 FROM offre_semestres os WHERE os.offre_id=o.id)")'
    if old in source:
        source = source.replace(old, new, 1)

    # Garde-fou CSV : le correctif historique ajoute pandas dans une couche
    # suivante. Le code ci-dessous s'exécute donc avec pd déjà importé.
    if "def _suaps_safe_read_csv" not in source and "st.set_page_config(" in source:
        csv_guard = '''\n# Garde-fou SUAPS sur les imports CSV administratifs.\n_pd_read_csv_original = pd.read_csv\ndef _suaps_safe_read_csv(file_obj,*args,**kwargs):\n    size=None\n    try:\n        if hasattr(file_obj,"getbuffer"):\n            size=len(file_obj.getbuffer())\n        elif hasattr(file_obj,"size"):\n            size=int(file_obj.size)\n    except Exception:\n        size=None\n    if size is not None and size > 5*1024*1024:\n        raise ValueError("Fichier CSV trop volumineux : maximum 5 Mo.")\n    try:\n        if hasattr(file_obj,"seek"):\n            file_obj.seek(0)\n    except Exception:\n        pass\n    df=_pd_read_csv_original(file_obj,*args,**kwargs)\n    if len(df) > 5000:\n        raise ValueError("Import refusé : maximum 5 000 lignes par fichier.")\n    if len(df.columns) > 30:\n        raise ValueError("Import refusé : maximum 30 colonnes.")\n    for col in df.columns:\n        if str(col).lower().strip() == "profil":\n            vals={str(v).strip() for v in df[col].dropna().tolist()}\n            allowed={"Étudiant","Etudiant","Personnel"}\n            bad=sorted(v for v in vals if v and v not in allowed)\n            if bad:\n                raise ValueError("Profil non autorisé dans le CSV : "+", ".join(bad)+". Seuls Étudiant et Personnel sont importables.")\n    obj_cols=list(df.select_dtypes(include=["object"]).columns)\n    for col in obj_cols:\n        too_long=df[col].dropna().astype(str).map(len).gt(500)\n        if bool(too_long.any()):\n            raise ValueError(f"Valeur trop longue dans la colonne {col} (maximum 500 caractères).")\n    return df\npd.read_csv=_suaps_safe_read_csv\n'''
        idx = source.find("st.set_page_config(")
        line_end = source.find("\n", idx)
        if line_end != -1:
            source = source[:line_end + 1] + csv_guard + source[line_end + 1:]

    # Helper de sauvegarde complète, restaurable et vérifiable par SHA256.
    if "def _suaps_make_backup_zip" not in source and "for k,v in {" in source:
        helper = '''\ndef _suaps_make_backup_zip():\n    import base64 as _b64\n    import hashlib as _hashlib\n    import io as _io\n    import json as _json\n    import zipfile as _zipfile\n    from datetime import datetime as _dt, timezone as _tz\n\n    _tables=[\n        "utilisateurs","offres","inscriptions","seances","presences",\n        "evaluations","performances","competences","acquisitions","baremes",\n        "actualites","evaluations_finales","offre_semestres","equipes",\n        "equipe_joueurs","tournois","tournoi_equipes","matchs","suaps_migration_meta"\n    ]\n    _stamp=_dt.now(_tz.utc).strftime("%Y%m%dT%H%M%SZ")\n    _manifest={\n        "application":"SUAPS UPPA",\n        "format":"suaps-json-backup-v1",\n        "created_utc":_stamp,\n        "database":"postgresql" if os.getenv("DATABASE_URL","").strip() else "sqlite",\n        "tables":{}\n    }\n    _buf=_io.BytesIO()\n    with _zipfile.ZipFile(_buf,"w",compression=_zipfile.ZIP_DEFLATED) as _zf:\n        for _table in _tables:\n            try:\n                _records=rows(f'SELECT * FROM "{_table}" ORDER BY 1')\n            except Exception:\n                _records=[]\n            _clean=[]\n            for _record in _records:\n                _d=dict(_record)\n                for _k,_v in list(_d.items()):\n                    if isinstance(_v,memoryview):\n                        _v=_v.tobytes()\n                    if isinstance(_v,(bytes,bytearray)):\n                        _d[_k]={"__suaps_type__":"bytes","base64":_b64.b64encode(bytes(_v)).decode("ascii")}\n                    elif _v is not None and not isinstance(_v,(str,int,float,bool)):\n                        _d[_k]=str(_v)\n                _clean.append(_d)\n            _raw=_json.dumps(_clean,ensure_ascii=False,indent=2,sort_keys=True).encode("utf-8")\n            _name=f"tables/{_table}.json"\n            _zf.writestr(_name,_raw)\n            _manifest["tables"][_table]={\n                "rows":len(_clean),\n                "sha256":_hashlib.sha256(_raw).hexdigest(),\n                "file":_name\n            }\n        _readme=(\n            "SAUVEGARDE SUAPS UPPA\\n"\n            "=====================\\n"\n            "Cette archive contient des données personnelles et potentiellement des photos.\\n"\n            "Conservez-la dans un espace institutionnel sécurisé et ne la déposez pas dans un dépôt Git public.\\n"\n            "Le fichier manifest.json fournit les compteurs et empreintes SHA256 de chaque table.\\n"\n        )\n        _zf.writestr("README.txt",_readme.encode("utf-8"))\n        _manifest_raw=_json.dumps(_manifest,ensure_ascii=False,indent=2,sort_keys=True).encode("utf-8")\n        _zf.writestr("manifest.json",_manifest_raw)\n    return _buf.getvalue(),f"suaps_backup_{_stamp}.zip",_manifest\n'''
        source = source.replace("for k,v in {", helper + "\nfor k,v in {", 1)

    # Ajoute Sauvegardes avant Actualités. Les autres couches pourront ensuite
    # ajouter Compétition/Pédagogie puis Semestres & CSV sans collision.
    radio_old = 'sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")'
    radio_new = 'sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Sauvegardes","Actualités"],horizontal=True,key="admin_section")'
    if radio_old in source:
        source = source.replace(radio_old, radio_new, 1)

    actualites_anchor = '    else:\n        st.markdown("### 📰 Gestion des Infos Live")'
    if actualites_anchor in source and 'elif sec=="Sauvegardes":' not in source:
        backup_block = '''    elif sec=="Sauvegardes":\n        st.markdown("### 🛡️ Sauvegardes PostgreSQL")\n        st.warning("La sauvegarde contient des données personnelles. Télécharge-la uniquement depuis un poste de confiance et stocke-la dans un espace institutionnel sécurisé.")\n        st.caption("L'archive ZIP contient toutes les tables au format JSON, un manifeste avec les volumes et une empreinte SHA256 pour contrôler l'intégrité.")\n        _bcols=st.columns(4)\n        for _col,_table,_label in zip(_bcols,["utilisateurs","inscriptions","presences","evaluations"],["Profils","Inscriptions","Présences","Évaluations"]):\n            try:\n                _n=one(f'SELECT COUNT(*) n FROM "{_table}"')\n                _col.metric(_label,int(_n["n"]) if _n else 0)\n            except Exception:\n                _col.metric(_label,"—")\n        if st.button("🔐 Préparer une sauvegarde complète",type="primary",key="prepare_full_backup"):\n            try:\n                _zip,_filename,_manifest=_suaps_make_backup_zip()\n                st.session_state["suaps_backup_zip"]=_zip\n                st.session_state["suaps_backup_name"]=_filename\n                st.session_state["suaps_backup_manifest"]=_manifest\n                st.success("Sauvegarde prête. Télécharge-la maintenant et conserve-la hors de Render.")\n            except Exception as _e:\n                st.error(f"Impossible de préparer la sauvegarde : {_e}")\n        if st.session_state.get("suaps_backup_zip"):\n            st.download_button(\n                "⬇️ Télécharger la sauvegarde ZIP",\n                data=st.session_state["suaps_backup_zip"],\n                file_name=st.session_state.get("suaps_backup_name","suaps_backup.zip"),\n                mime="application/zip",\n                use_container_width=True,\n                key="download_full_backup",\n            )\n            _m=st.session_state.get("suaps_backup_manifest",{})\n            if _m:\n                _total=sum(int(v.get("rows",0)) for v in _m.get("tables",{}).values())\n                st.caption(f"Archive contrôlée : {_total} enregistrement(s) réparti(s) dans {len(_m.get('tables',{}))} table(s).")\n    else:\n        st.markdown("### 📰 Gestion des Infos Live")'''
        source = source.replace(actualites_anchor, backup_block, 1)

    return source


def _compile(source, filename, mode, *args, **kwargs):
    return _previous_compile(_patch_generated_source(source), filename, mode, *args, **kwargs)


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
                       VALUES('schema_version','2026-08-29-pg2',NOW())
                       ON CONFLICT(cle) DO UPDATE
                       SET valeur=EXCLUDED.valeur, maj=EXCLUDED.maj"""
                )
                for table in AUDIT_TABLES:
                    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                    counts[table] = int(cur.fetchone()[0])
            conn.commit()
        summary = ",".join(f"{k}={v}" for k, v in counts.items())
        print(f"[SUAPS_DB_AUDIT] engine=postgres schema=2026-08-29-pg2 {summary}")
    except Exception as exc:
        print(f"[SUAPS_DB_AUDIT] error={type(exc).__name__}:{exc}")


_ensure_postgres_schema_and_audit()

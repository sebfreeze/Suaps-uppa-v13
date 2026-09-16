"""Adaptateur des ressources pédagogiques pour le point d'entrée V14/V17 live.

Le live Render historique utilise ``db/rows/one/exe`` et une table ``seances``
rattachée aux ``offres``. Ce module adapte le module générique sans modifier ce
schéma historique. Les ressources utilisent PostgreSQL via ``DATABASE_URL``
quand il est disponible, avec repli SQLite pour ne jamais empêcher le démarrage.
"""
from __future__ import annotations

import os
from datetime import date
from threading import RLock

import pedagogie_resources as resources
from pedagogie_seed import seed_official_resources

_FORCE_SQLITE = False
_STORAGE_WARNING = ""
_INIT_CACHE = {}
_INIT_LOCK = RLock()


class QmarkConnection:
    """Expose l'API ``execute(..., ? placeholders)`` au-dessus de psycopg."""

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=()):
        return self._raw.execute(str(sql).replace("?", "%s"), params)

    def commit(self):
        return self._raw.commit()

    def close(self):
        return self._raw.close()


def _postgres_factory(database_url: str):
    def factory():
        import psycopg
        from psycopg.rows import dict_row

        raw = psycopg.connect(database_url, row_factory=dict_row, connect_timeout=6)
        return QmarkConnection(raw)

    return factory


def _main_app_uses_postgres(factory) -> bool:
    """Détecte le backend déjà configuré par la couche sécurité du live."""
    try:
        return bool(getattr(factory, "__globals__", {}).get("USE_POSTGRES"))
    except Exception:
        return False


def resource_connection_factory(sqlite_factory):
    """Retourne ``(factory, use_postgres)`` pour les ressources pédagogiques.

    En production, ``sqlite_factory`` est en réalité la fonction ``db`` du live,
    déjà transformée par la couche sécurité pour utiliser le pool PostgreSQL.
    La réutiliser évite une nouvelle connexion réseau de test à chaque rerun.
    """
    global _FORCE_SQLITE, _STORAGE_WARNING

    if _main_app_uses_postgres(sqlite_factory):
        _STORAGE_WARNING = ""
        return sqlite_factory, True

    database_url = os.getenv("DATABASE_URL", "").strip()
    if _FORCE_SQLITE or not database_url:
        return sqlite_factory, False

    # Repli de compatibilité si le module est utilisé hors du live principal.
    pg_factory = _postgres_factory(database_url)
    try:
        probe = pg_factory()
        probe.close()
        _STORAGE_WARNING = ""
        return pg_factory, True
    except Exception:  # disponibilité externe : le live doit rester accessible
        _FORCE_SQLITE = True
        _STORAGE_WARNING = (
            "Le stockage PostgreSQL des ressources est momentanément indisponible ; "
            "les ressources utilisent le stockage local de secours pour cette instance."
        )
        return sqlite_factory, False


def storage_warning() -> str:
    return _STORAGE_WARNING


def init_v14_pedagogy(sqlite_factory) -> tuple[object, bool]:
    """Initialise ressources + seed officiel une seule fois par processus/backend."""
    factory, use_postgres = resource_connection_factory(sqlite_factory)
    app_globals = getattr(sqlite_factory, "__globals__", {})
    backend_key = (
        "postgres" if use_postgres else "sqlite",
        str(os.getenv("DATABASE_URL", "") if use_postgres else ""),
        id(app_globals),
    )

    with _INIT_LOCK:
        cached = _INIT_CACHE.get(backend_key)
        if cached is not None:
            return cached

        resources.init_pedagogy_schema(factory, use_postgres)
        seed_official_resources(factory, use_postgres)
        # La migration de seances doit utiliser le backend réellement détecté.
        resources.ensure_seance_resource_column(factory, use_postgres)
        result = (factory, use_postgres)
        _INIT_CACHE[backend_key] = result
        return result


def create_v14_session(exe, one, resource: dict, date_seance: str, group_label: str) -> int:
    """Crée une séance V14 à partir d'une ressource en la rattachant à une offre/créneau."""
    if not resource or not resource.get("id"):
        raise ValueError("Ressource invalide.")
    try:
        date.fromisoformat(str(date_seance))
    except ValueError as exc:
        raise ValueError("Date de séance invalide.") from exc

    activity = str(resource.get("activite") or "").strip()
    group = (group_label or "").strip()
    if group:
        offer = one(
            "SELECT id,intitule FROM offres WHERE activite=? AND intitule=? ORDER BY id LIMIT 1",
            (activity, group),
        )
    else:
        offer = one(
            "SELECT id,intitule FROM offres WHERE activite=? ORDER BY id LIMIT 1",
            (activity,),
        )
    if not offer:
        raise ValueError("Aucun créneau correspondant à cette activité et à ce groupe.")

    return exe(
        "INSERT INTO seances(offre_id,date_seance,theme,ressource_id,qr_ouvert) VALUES(?,?,?,?,0)",
        (
            int(offer["id"]),
            str(date_seance),
            str(resource.get("titre") or "Séance pédagogique"),
            int(resource["id"]),
        ),
    )


def _session_exec_adapter(exe, one):
    """Traduit uniquement l'INSERT générique de séance vers le schéma V14."""

    def adapted(sql, params=()):
        normalized = " ".join(str(sql).split())
        signature = "INSERT INTO seances(activite,date_seance,groupe,theme,ressource_id) VALUES(?,?,?,?,?)"
        if normalized == signature:
            activity, date_seance, group, title, resource_id = params
            return create_v14_session(
                exe,
                one,
                {
                    "id": int(resource_id),
                    "activite": str(activity),
                    "titre": str(title),
                },
                str(date_seance),
                str(group or ""),
            )
        return exe(sql, params)

    return adapted


def _prefill_session_groups(st, rows, resource_rows) -> None:
    """Préremplit le champ Groupe du module générique avec un vrai créneau V14."""
    offers = rows("SELECT id,activite,intitule FROM offres ORDER BY activite,intitule,id")
    first_by_activity = {}
    for offer in offers:
        activity = str(offer["activite"])
        first_by_activity.setdefault(activity, str(offer["intitule"]))
    for resource in resource_rows:
        default_group = first_by_activity.get(str(resource.get("activite") or ""))
        if not default_group:
            continue
        key = f"ses_group_{resource['id']}"
        if key not in st.session_state:
            st.session_state[key] = default_group


def render_v14_teacher_resources(st, db, rows, one, exe, activities) -> None:
    """Affiche l'interface enseignant générique avec les adaptations du live V14."""
    factory, use_postgres = resource_connection_factory(db)
    if storage_warning():
        st.warning(storage_warning())
    elif use_postgres:
        st.caption("🗄️ Ressources enregistrées dans la base PostgreSQL persistante.")
    else:
        st.caption("🗄️ Ressources enregistrées dans la base locale de l'application.")

    resource_rows = resources.list_resources(factory)
    _prefill_session_groups(st, rows, resource_rows)
    resources.render_teacher_resources(
        st,
        get_conn=factory,
        use_postgres=use_postgres,
        exec_sql=_session_exec_adapter(exe, one),
        activities=activities,
        admin_code_value=os.getenv("PEDAGOGY_ADMIN_CODE", "").strip(),
    )


def render_v14_student_resources(st, db) -> None:
    """Vue étudiant, strictement en lecture seule, branchée sur le même stockage."""
    factory, _use_postgres = resource_connection_factory(db)
    resources.render_student_resources(st, get_conn=factory)

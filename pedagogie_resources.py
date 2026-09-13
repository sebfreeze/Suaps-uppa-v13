"""Ressources pédagogiques partagées du SUAPS UPPA.

Le module garde la logique de données et l'interface Streamlit hors de ``app.py``.
Il fonctionne avec sqlite3 en local et avec la couche CompatConnection de l'app
quand PostgreSQL est activé.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

MAX_FILE_BYTES = 5 * 1024 * 1024
PBKDF2_ITERATIONS = 200_000
RESOURCE_TYPES = ("Progression", "Séance", "Compétences / barèmes", "Document", "Vidéo / lien")
ALLOWED_FILES = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    ".pptx": {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/octet-stream",
    },
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    },
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
}
_UNSET = object()


def _cursor_description(cursor):
    raw = getattr(cursor, "_cursor", cursor)
    return getattr(raw, "description", None)


def _row_to_dict(row, cursor=None):
    if row is None:
        return None
    if hasattr(row, "keys"):
        return dict(row)
    description = _cursor_description(cursor) if cursor is not None else None
    if description:
        names = []
        for d in description:
            names.append(getattr(d, "name", None) or d[0])
        return dict(zip(names, row))
    raise TypeError("Impossible de convertir la ligne SQL en dictionnaire.")


def _close(conn):
    try:
        conn.close()
    except Exception:
        pass


def _fetchone(conn, sql, params=()):
    cur = conn.execute(sql, params)
    return _row_to_dict(cur.fetchone(), cur)


def _fetchall(conn, sql, params=()):
    cur = conn.execute(sql, params)
    return [_row_to_dict(row, cur) for row in cur.fetchall()]


def hash_edit_code(code: str) -> str:
    cleaned = (code or "").strip()
    if len(cleaned) < 6:
        raise ValueError("Le code de modification doit contenir au moins 6 caractères.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", cleaned.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_edit_code(code: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = (stored or "").split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            (code or "").strip().encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def validate_external_url(url: str) -> str:
    cleaned = (url or "").strip()
    if not cleaned:
        return ""
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Le lien doit être une adresse HTTP ou HTTPS valide.")
    return cleaned


def validate_upload(filename: str, mime_type: str, data: bytes) -> tuple[str, str, int]:
    safe_name = Path(filename or "").name.strip()
    if not safe_name:
        raise ValueError("Le nom du fichier est invalide.")
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_FILES:
        raise ValueError("Type de fichier non autorisé.")
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise ValueError("Le contenu du fichier est invalide.")
    size = len(data)
    if size > MAX_FILE_BYTES:
        raise ValueError("Fichier trop volumineux : 5 Mo maximum.")
    normalized_mime = (mime_type or "application/octet-stream").strip().lower()
    if normalized_mime not in ALLOWED_FILES[suffix]:
        raise ValueError("Le type MIME ne correspond pas à un fichier autorisé.")
    return safe_name, normalized_mime, size


def init_pedagogy_schema(get_conn, use_postgres: bool) -> None:
    conn = get_conn()
    try:
        if use_postgres:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ressources_pedagogiques(
                    id SERIAL PRIMARY KEY,
                    seed_key TEXT UNIQUE,
                    activite TEXT NOT NULL,
                    type_ressource TEXT NOT NULL,
                    titre TEXT NOT NULL,
                    description TEXT,
                    contenu_json TEXT,
                    auteur TEXT NOT NULL,
                    auteur_code_hash TEXT,
                    date_creation TEXT NOT NULL,
                    date_modification TEXT NOT NULL,
                    visible_etudiants INTEGER NOT NULL DEFAULT 0,
                    officiel_suaps INTEGER NOT NULL DEFAULT 0,
                    lien_externe TEXT,
                    nom_fichier TEXT,
                    mime_type TEXT,
                    taille_fichier INTEGER,
                    fichier_data BYTEA
                )
                """
            )
        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ressources_pedagogiques(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    seed_key TEXT UNIQUE,
                    activite TEXT NOT NULL,
                    type_ressource TEXT NOT NULL,
                    titre TEXT NOT NULL,
                    description TEXT,
                    contenu_json TEXT,
                    auteur TEXT NOT NULL,
                    auteur_code_hash TEXT,
                    date_creation TEXT NOT NULL,
                    date_modification TEXT NOT NULL,
                    visible_etudiants INTEGER NOT NULL DEFAULT 0,
                    officiel_suaps INTEGER NOT NULL DEFAULT 0,
                    lien_externe TEXT,
                    nom_fichier TEXT,
                    mime_type TEXT,
                    taille_fichier INTEGER,
                    fichier_data BLOB
                )
                """
            )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ressources_pedagogiques_filters
            ON ressources_pedagogiques(activite, type_ressource, officiel_suaps, visible_etudiants)
            """
        )
        conn.commit()
    finally:
        _close(conn)


def _validate_resource_fields(activity, resource_type, title, author, official):
    activity = (activity or "").strip()
    resource_type = (resource_type or "").strip()
    title = (title or "").strip()
    author = (author or "").strip()
    if not activity:
        raise ValueError("L'activité est obligatoire.")
    if resource_type not in RESOURCE_TYPES:
        raise ValueError("Type de ressource invalide.")
    if not title:
        raise ValueError("Le titre est obligatoire.")
    if not author:
        raise ValueError("L'auteur est obligatoire.")
    return activity, resource_type, title, author


def create_resource(
    get_conn,
    *,
    activity: str,
    resource_type: str,
    title: str,
    author: str,
    description: str = "",
    content=None,
    author_code: str | None = None,
    visible_students: bool = False,
    official: bool = False,
    external_url: str = "",
    filename: str | None = None,
    mime_type: str | None = None,
    file_data: bytes | None = None,
    seed_key: str | None = None,
) -> bool:
    activity, resource_type, title, author = _validate_resource_fields(
        activity, resource_type, title, author, official
    )
    link = validate_external_url(external_url)
    content_json = json.dumps(content or {}, ensure_ascii=False)
    author_hash = None if official else hash_edit_code(author_code or "")
    file_name = file_mime = None
    file_size = None
    blob = None
    if file_data is not None or filename or mime_type:
        if file_data is None or not filename:
            raise ValueError("Le fichier est incomplet.")
        file_name, file_mime, file_size = validate_upload(filename, mime_type or "", file_data)
        blob = bytes(file_data)
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_conn()
    try:
        if seed_key:
            exists = _fetchone(conn, "SELECT id FROM ressources_pedagogiques WHERE seed_key=?", (seed_key,))
            if exists:
                return False
        conn.execute(
            """
            INSERT INTO ressources_pedagogiques(
                seed_key, activite, type_ressource, titre, description, contenu_json,
                auteur, auteur_code_hash, date_creation, date_modification,
                visible_etudiants, officiel_suaps, lien_externe,
                nom_fichier, mime_type, taille_fichier, fichier_data
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                seed_key,
                activity,
                resource_type,
                title,
                (description or "").strip(),
                content_json,
                author,
                author_hash,
                now,
                now,
                1 if visible_students else 0,
                1 if official else 0,
                link,
                file_name,
                file_mime,
                file_size,
                blob,
            ),
        )
        conn.commit()
        return True
    finally:
        _close(conn)


def _decode_resource(row):
    if row is None:
        return None
    result = dict(row)
    try:
        result["contenu"] = json.loads(result.get("contenu_json") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        result["contenu"] = {}
    return result


def list_resources(
    get_conn,
    *,
    student_only: bool = False,
    activity: str | None = None,
    resource_type: str | None = None,
    author: str | None = None,
    query: str | None = None,
    official: bool | None = None,
    student_visible: bool | None = None,
):
    sql = """
        SELECT id, seed_key, activite, type_ressource, titre, description, contenu_json,
               auteur, auteur_code_hash, date_creation, date_modification,
               visible_etudiants, officiel_suaps, lien_externe,
               nom_fichier, mime_type, taille_fichier
        FROM ressources_pedagogiques
        WHERE 1=1
    """
    params = []
    if student_only:
        sql += " AND visible_etudiants=1"
    if activity:
        sql += " AND activite=?"
        params.append(activity)
    if resource_type:
        sql += " AND type_ressource=?"
        params.append(resource_type)
    if author:
        sql += " AND LOWER(auteur)=LOWER(?)"
        params.append(author.strip())
    if official is not None:
        sql += " AND officiel_suaps=?"
        params.append(1 if official else 0)
    if student_visible is not None:
        sql += " AND visible_etudiants=?"
        params.append(1 if student_visible else 0)
    if query and query.strip():
        sql += " AND (LOWER(titre) LIKE LOWER(?) OR LOWER(COALESCE(description,'')) LIKE LOWER(?) OR LOWER(auteur) LIKE LOWER(?))"
        needle = f"%{query.strip()}%"
        params.extend([needle, needle, needle])
    sql += " ORDER BY activite, type_ressource, titre, id"
    conn = get_conn()
    try:
        return [_decode_resource(r) for r in _fetchall(conn, sql, tuple(params))]
    finally:
        _close(conn)


def get_resource(get_conn, resource_id: int):
    conn = get_conn()
    try:
        row = _fetchone(
            conn,
            """
            SELECT id, seed_key, activite, type_ressource, titre, description, contenu_json,
                   auteur, auteur_code_hash, date_creation, date_modification,
                   visible_etudiants, officiel_suaps, lien_externe,
                   nom_fichier, mime_type, taille_fichier
            FROM ressources_pedagogiques WHERE id=?
            """,
            (int(resource_id),),
        )
        return _decode_resource(row)
    finally:
        _close(conn)


def get_resource_file(get_conn, resource_id: int):
    conn = get_conn()
    try:
        row = _fetchone(
            conn,
            "SELECT nom_fichier, mime_type, fichier_data FROM ressources_pedagogiques WHERE id=?",
            (int(resource_id),),
        )
        if not row or row.get("fichier_data") is None:
            return None
        return row.get("nom_fichier") or "document", row.get("mime_type") or "application/octet-stream", bytes(row["fichier_data"])
    finally:
        _close(conn)


def update_resource(
    get_conn,
    resource_id: int,
    *,
    activity: str,
    resource_type: str,
    title: str,
    description: str = "",
    content=None,
    visible_students: bool = False,
    external_url: str = "",
    author: str | None = None,
    author_code: str | None = None,
    filename=_UNSET,
    mime_type=_UNSET,
    file_data=_UNSET,
) -> None:
    current = get_resource(get_conn, resource_id)
    if current is None:
        raise ValueError("Ressource introuvable.")
    new_author = (author if author is not None else current["auteur"]).strip()
    activity, resource_type, title, new_author = _validate_resource_fields(
        activity, resource_type, title, new_author, bool(current["officiel_suaps"])
    )
    link = validate_external_url(external_url)
    content_json = json.dumps(content or {}, ensure_ascii=False)
    author_hash = current.get("auteur_code_hash")
    if author_code:
        author_hash = hash_edit_code(author_code)
    set_file = file_data is not _UNSET or filename is not _UNSET or mime_type is not _UNSET
    conn = get_conn()
    try:
        if set_file:
            if file_data in (_UNSET, None):
                file_name = file_mime = None
                file_size = None
                blob = None
            else:
                file_name, file_mime, file_size = validate_upload(
                    "" if filename is _UNSET else filename,
                    "" if mime_type is _UNSET else mime_type,
                    file_data,
                )
                blob = bytes(file_data)
            conn.execute(
                """
                UPDATE ressources_pedagogiques
                SET activite=?, type_ressource=?, titre=?, description=?, contenu_json=?,
                    auteur=?, auteur_code_hash=?, date_modification=?, visible_etudiants=?,
                    lien_externe=?, nom_fichier=?, mime_type=?, taille_fichier=?, fichier_data=?
                WHERE id=?
                """,
                (
                    activity, resource_type, title, (description or "").strip(), content_json,
                    new_author, author_hash, datetime.now().isoformat(timespec="seconds"),
                    1 if visible_students else 0, link, file_name, file_mime, file_size, blob,
                    int(resource_id),
                ),
            )
        else:
            conn.execute(
                """
                UPDATE ressources_pedagogiques
                SET activite=?, type_ressource=?, titre=?, description=?, contenu_json=?,
                    auteur=?, auteur_code_hash=?, date_modification=?, visible_etudiants=?,
                    lien_externe=? WHERE id=?
                """,
                (
                    activity, resource_type, title, (description or "").strip(), content_json,
                    new_author, author_hash, datetime.now().isoformat(timespec="seconds"),
                    1 if visible_students else 0, link, int(resource_id),
                ),
            )
        conn.commit()
    finally:
        _close(conn)


def delete_resource(get_conn, resource_id: int) -> None:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM ressources_pedagogiques WHERE id=?", (int(resource_id),))
        conn.commit()
    finally:
        _close(conn)


def can_edit_resource(resource: dict, author: str, author_code: str, admin_code: str, configured_admin_code: str) -> bool:
    if configured_admin_code and admin_code and hmac.compare_digest(admin_code, configured_admin_code):
        return True
    if bool(resource.get("officiel_suaps")):
        return False
    return (
        (author or "").strip().casefold() == str(resource.get("auteur") or "").strip().casefold()
        and verify_edit_code(author_code or "", resource.get("auteur_code_hash") or "")
    )


def ensure_seance_resource_column(get_conn, use_postgres: bool) -> None:
    conn = get_conn()
    try:
        if use_postgres:
            row = _fetchone(
                conn,
                """
                SELECT 1 AS present
                FROM information_schema.columns
                WHERE table_schema='public' AND table_name='seances' AND column_name='ressource_id'
                """,
            )
            if not row:
                conn.execute("ALTER TABLE seances ADD COLUMN ressource_id INTEGER")
        else:
            cur = conn.execute("PRAGMA table_info(seances)")
            cols = {r[1] if not hasattr(r, "keys") else r["name"] for r in cur.fetchall()}
            if "ressource_id" not in cols:
                conn.execute("ALTER TABLE seances ADD COLUMN ressource_id INTEGER")
        conn.commit()
    finally:
        _close(conn)


def create_seance_from_resource(exec_sql, resource: dict, date_seance: str, groupe: str) -> None:
    if not resource or not resource.get("id"):
        raise ValueError("Ressource invalide.")
    try:
        date.fromisoformat(str(date_seance))
    except ValueError as exc:
        raise ValueError("Date de séance invalide.") from exc
    exec_sql(
        "INSERT INTO seances(activite,date_seance,groupe,theme,ressource_id) VALUES(?,?,?,?,?)",
        (
            str(resource["activite"]),
            str(date_seance),
            (groupe or "").strip(),
            str(resource["titre"]),
            int(resource["id"]),
        ),
    )


def resource_card_summary(resource: dict) -> dict:
    return {
        "title": resource["titre"],
        "subtitle": f'{resource["activite"]} • {resource["type_ressource"]}',
        "author": resource["auteur"],
        "official": bool(resource.get("officiel_suaps")),
        "student_visible": bool(resource.get("visible_etudiants")),
    }


def duplicate_payload(resource: dict, new_author: str) -> dict:
    return {
        "activite": resource["activite"],
        "type_ressource": resource["type_ressource"],
        "titre": f'Copie — {resource["titre"]}',
        "description": resource.get("description") or "",
        "contenu": resource.get("contenu") or {},
        "auteur": (new_author or "").strip(),
        "visible_etudiants": 0,
        "officiel_suaps": 0,
    }


def _split_lines(value: str) -> list[str]:
    return [line.strip(" •-\t") for line in (value or "").splitlines() if line.strip(" •-\t")]


def _join_lines(values) -> str:
    return "\n".join(str(v) for v in (values or []))


def _session_editor_fields(st, prefix: str, defaults: dict | None = None) -> dict:
    defaults = defaults or {}
    objectif = st.text_area("Objectif principal", value=str(defaults.get("objectif") or ""), key=f"{prefix}_objectif")
    competences = st.text_area("Compétences visées — une par ligne", value=_join_lines(defaults.get("competences")), key=f"{prefix}_competences")
    materiel = st.text_area("Matériel — un élément par ligne", value=_join_lines(defaults.get("materiel")), key=f"{prefix}_materiel")
    echauffement = st.text_area("Échauffement / mise en route", value=str(defaults.get("echauffement") or ""), key=f"{prefix}_echauffement")
    situations = st.text_area("Situations d’apprentissage — une par ligne", value=_join_lines(defaults.get("situations")), key=f"{prefix}_situations")
    variables = st.text_area("Variables de difficulté — une par ligne", value=_join_lines(defaults.get("variables")), key=f"{prefix}_variables")
    criteres = st.text_area("Critères de réussite — un par ligne", value=_join_lines(defaults.get("criteres_reussite")), key=f"{prefix}_criteres")
    securite = st.text_area("Consignes de sécurité — une par ligne", value=_join_lines(defaults.get("securite")), key=f"{prefix}_securite")
    retour = st.text_area("Retour au calme / bilan", value=str(defaults.get("retour_bilan") or ""), key=f"{prefix}_retour")
    return {
        "objectif": objectif.strip(),
        "competences": _split_lines(competences),
        "materiel": _split_lines(materiel),
        "echauffement": echauffement.strip(),
        "situations": _split_lines(situations),
        "variables": _split_lines(variables),
        "criteres_reussite": _split_lines(criteres),
        "securite": _split_lines(securite),
        "retour_bilan": retour.strip(),
    }


def _render_session_content(st, content: dict):
    if not content:
        return
    if content.get("objectif"):
        st.markdown(f"**🎯 Objectif :** {content['objectif']}")
    sections = [
        ("🧩 Compétences", "competences"),
        ("🎒 Matériel", "materiel"),
        ("🔥 Échauffement / mise en route", "echauffement"),
        ("🏃 Situations d’apprentissage", "situations"),
        ("🔁 Variables", "variables"),
        ("✅ Critères de réussite", "criteres_reussite"),
        ("🛟 Sécurité", "securite"),
        ("🧘 Retour au calme / bilan", "retour_bilan"),
    ]
    for label, key in sections:
        value = content.get(key)
        if not value:
            continue
        with st.expander(label, expanded=key in {"situations", "securite"}):
            if isinstance(value, list):
                for item in value:
                    st.markdown(f"- {item}")
            else:
                st.write(value)


def render_teacher_resources(st, *, get_conn, use_postgres, exec_sql, activities, admin_code_value) -> None:
    """Interface complète de consultation et contribution pour les enseignants."""
    st.markdown("## 📚 Ressources pédagogiques")
    all_rows = list_resources(get_conn)
    st.caption(f"{len(all_rows)} ressources partagées entre les enseignants • fonds officiel SUAPS inclus")

    with st.expander("🔎 Filtres et recherche", expanded=False):
        c1, c2, c3 = st.columns(3)
        act_options = ["Toutes"] + sorted({r["activite"] for r in all_rows} | set(activities or []))
        typ_options = ["Tous"] + list(RESOURCE_TYPES)
        authors = ["Tous"] + sorted({r["auteur"] for r in all_rows})
        activity = c1.selectbox("Activité", act_options, key="ped_filter_act")
        resource_type = c2.selectbox("Type", typ_options, key="ped_filter_type")
        author = c3.selectbox("Auteur", authors, key="ped_filter_author")
        c4, c5 = st.columns(2)
        origin = c4.selectbox("Origine", ["Toutes", "Officiel SUAPS", "Enseignants"], key="ped_filter_origin")
        visibility = c5.selectbox("Partage étudiant", ["Toutes", "Visible", "Non visible"], key="ped_filter_vis")
        query = st.text_input("Rechercher", placeholder="titre, description ou auteur…", key="ped_filter_query")

    rows = list_resources(
        get_conn,
        activity=None if activity == "Toutes" else activity,
        resource_type=None if resource_type == "Tous" else resource_type,
        author=None if author == "Tous" else author,
        query=query,
        official=None if origin == "Toutes" else origin == "Officiel SUAPS",
        student_visible=None if visibility == "Toutes" else visibility == "Visible",
    )

    with st.expander("➕ Ajouter une ressource", expanded=False):
        create_type = st.selectbox("Type de ressource à créer", RESOURCE_TYPES, key="ped_create_type")
        with st.form("ped_create_form", clear_on_submit=False):
            activity_new = st.selectbox("Activité", list(activities or []) or sorted({r["activite"] for r in all_rows}), key="ped_create_act")
            title = st.text_input("Titre")
            description = st.text_area("Description")
            author_new = st.text_input("Nom et prénom de l’enseignant")
            edit_code = st.text_input("Code personnel de modification (6 caractères minimum)", type="password")
            visible = st.checkbox("Partager aussi avec les étudiants", value=False)
            external_url = st.text_input("Lien externe / vidéo (facultatif)")
            uploaded = st.file_uploader("PDF / DOCX / PPTX / XLSX / image — 5 Mo maximum", type=["pdf", "docx", "pptx", "xlsx", "png", "jpg", "jpeg"])
            content = _session_editor_fields(st, "ped_create_session") if create_type == "Séance" else {}
            submitted = st.form_submit_button("Enregistrer la ressource", type="primary", use_container_width=True)
            if submitted:
                try:
                    file_data = uploaded.getvalue() if uploaded is not None else None
                    create_resource(
                        get_conn,
                        activity=activity_new,
                        resource_type=create_type,
                        title=title,
                        description=description,
                        content=content,
                        author=author_new,
                        author_code=edit_code,
                        visible_students=visible,
                        external_url=external_url,
                        filename=uploaded.name if uploaded is not None else None,
                        mime_type=uploaded.type if uploaded is not None else None,
                        file_data=file_data,
                    )
                    st.success("Ressource ajoutée : elle est immédiatement visible par tous les enseignants.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error("Impossible d’enregistrer la ressource pour le moment.")

    if not rows:
        st.info("Aucune ressource ne correspond aux filtres.")
        return

    st.markdown(f"### Ressources ({len(rows)})")
    labels = {}
    for r in rows:
        badge = "🏛️ " if r["officiel_suaps"] else "👤 "
        student = " • 🎓" if r["visible_etudiants"] else ""
        labels[r["id"]] = f'{badge}{r["activite"]} — {r["titre"]}{student}'
    selected_id = st.selectbox("Ouvrir une ressource", list(labels), format_func=lambda x: labels[x], key="ped_selected")
    resource = get_resource(get_conn, selected_id)
    if not resource:
        st.warning("Cette ressource n’existe plus.")
        return

    official_badge = " • 🏛️ Officiel SUAPS" if resource["officiel_suaps"] else ""
    student_badge = " • 🎓 Visible étudiants" if resource["visible_etudiants"] else ""
    st.markdown(f"### {resource['titre']}")
    st.caption(f"{resource['activite']} • {resource['type_ressource']} • {resource['auteur']}{official_badge}{student_badge}")
    if resource.get("description"):
        st.write(resource["description"])
    if resource["type_ressource"] == "Séance":
        _render_session_content(st, resource.get("contenu") or {})
    elif resource.get("contenu"):
        for key, value in resource["contenu"].items():
            if value:
                st.write(f"**{key.replace('_', ' ').title()} :**", value)

    if resource.get("lien_externe"):
        try:
            st.link_button("🔗 Ouvrir le lien", resource["lien_externe"], use_container_width=True)
        except AttributeError:
            st.markdown(f"[🔗 Ouvrir le lien]({resource['lien_externe']})")
    if resource.get("nom_fichier"):
        file_tuple = get_resource_file(get_conn, int(resource["id"]))
        if file_tuple:
            file_name, mime, file_bytes = file_tuple
            st.download_button("⬇️ Télécharger le document", data=file_bytes, file_name=file_name, mime=mime, use_container_width=True, key=f"ped_dl_{resource['id']}")

    a1, a2 = st.columns(2)
    with a1.expander("🧬 Dupliquer", expanded=False):
        with st.form(f"ped_dup_{resource['id']}"):
            dup_author = st.text_input("Votre nom/prénom", key=f"dup_author_{resource['id']}")
            dup_code = st.text_input("Nouveau code de modification", type="password", key=f"dup_code_{resource['id']}")
            if st.form_submit_button("Créer ma copie", use_container_width=True):
                try:
                    payload = duplicate_payload(resource, dup_author)
                    create_resource(
                        get_conn,
                        activity=payload["activite"], resource_type=payload["type_ressource"],
                        title=payload["titre"], description=payload["description"], content=payload["contenu"],
                        author=payload["auteur"], author_code=dup_code, visible_students=False,
                        external_url=resource.get("lien_externe") or "",
                    )
                    st.success("Copie créée. Elle est modifiable avec votre code.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    with a2.expander("📅 Créer une séance de présence", expanded=False):
        with st.form(f"ped_to_session_{resource['id']}"):
            session_date = st.date_input("Date", value=date.today(), key=f"ses_date_{resource['id']}")
            group = st.text_input("Groupe", key=f"ses_group_{resource['id']}")
            if st.form_submit_button("Créer la séance", type="primary", use_container_width=True):
                try:
                    create_seance_from_resource(exec_sql, resource, str(session_date), group)
                    st.success("Séance créée : elle est disponible dans Présences / QR-NFC.")
                except ValueError as exc:
                    st.error(str(exc))

    auth_key = f"ped_authorized_{resource['id']}"
    with st.expander("✏️ Modifier / supprimer", expanded=False):
        if not st.session_state.get(auth_key):
            st.caption("Auteur : utilisez votre nom et votre code. Une ressource officielle exige le code administrateur.")
            if not admin_code_value:
                st.caption("Administration globale non configurée.")
            with st.form(f"ped_auth_{resource['id']}"):
                auth_author = st.text_input("Auteur", key=f"auth_author_{resource['id']}")
                auth_code = st.text_input("Code auteur", type="password", key=f"auth_code_{resource['id']}")
                admin_try = st.text_input("Code administrateur (facultatif)", type="password", key=f"admin_try_{resource['id']}") if admin_code_value else ""
                if st.form_submit_button("Déverrouiller", use_container_width=True):
                    if can_edit_resource(resource, auth_author, auth_code, admin_try, admin_code_value):
                        st.session_state[auth_key] = True
                        st.rerun()
                    else:
                        st.error("Autorisation refusée.")
        else:
            edit_type = st.selectbox("Type", RESOURCE_TYPES, index=RESOURCE_TYPES.index(resource["type_ressource"]), key=f"edit_type_{resource['id']}")
            with st.form(f"ped_edit_{resource['id']}"):
                activity_values = list(dict.fromkeys(list(activities or []) + [resource["activite"]]))
                edit_activity = st.selectbox("Activité", activity_values, index=activity_values.index(resource["activite"]), key=f"edit_act_{resource['id']}")
                edit_title = st.text_input("Titre", value=resource["titre"], key=f"edit_title_{resource['id']}")
                edit_desc = st.text_area("Description", value=resource.get("description") or "", key=f"edit_desc_{resource['id']}")
                edit_visible = st.checkbox("Visible aux étudiants", value=bool(resource["visible_etudiants"]), key=f"edit_visible_{resource['id']}")
                edit_link = st.text_input("Lien externe", value=resource.get("lien_externe") or "", key=f"edit_link_{resource['id']}")
                edit_content = _session_editor_fields(st, f"ped_edit_session_{resource['id']}", resource.get("contenu") or {}) if edit_type == "Séance" else resource.get("contenu") or {}
                replace_file = st.file_uploader("Remplacer le document (facultatif)", type=["pdf", "docx", "pptx", "xlsx", "png", "jpg", "jpeg"], key=f"edit_file_{resource['id']}")
                remove_file = st.checkbox("Supprimer le document actuel", value=False, key=f"remove_file_{resource['id']}") if resource.get("nom_fichier") else False
                csave, cdelete = st.columns(2)
                save = csave.form_submit_button("Enregistrer", type="primary", use_container_width=True)
                delete = cdelete.form_submit_button("Supprimer", use_container_width=True)
                if save:
                    try:
                        kwargs = {}
                        if replace_file is not None:
                            kwargs.update(filename=replace_file.name, mime_type=replace_file.type, file_data=replace_file.getvalue())
                        elif remove_file:
                            kwargs.update(filename=None, mime_type=None, file_data=None)
                        update_resource(
                            get_conn, int(resource["id"]), activity=edit_activity, resource_type=edit_type,
                            title=edit_title, description=edit_desc, content=edit_content,
                            visible_students=edit_visible, external_url=edit_link, **kwargs,
                        )
                        st.session_state.pop(auth_key, None)
                        st.success("Ressource mise à jour.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error("Impossible de mettre à jour la ressource.")
                if delete:
                    delete_resource(get_conn, int(resource["id"]))
                    st.session_state.pop(auth_key, None)
                    st.success("Ressource supprimée.")
                    st.rerun()


def render_student_resources(st, *, get_conn) -> None:
    """Vue lecture seule des seules ressources explicitement partagées aux étudiants."""
    st.markdown("## 📚 Ressources pédagogiques")
    shared = list_resources(get_conn, student_only=True)
    if not shared:
        st.info("Aucune ressource n’est actuellement partagée avec les étudiants.")
        return
    c1, c2 = st.columns(2)
    activities = ["Toutes"] + sorted({r["activite"] for r in shared})
    types = ["Tous"] + sorted({r["type_ressource"] for r in shared})
    activity = c1.selectbox("Activité", activities, key="student_ped_act")
    resource_type = c2.selectbox("Type", types, key="student_ped_type")
    query = st.text_input("Rechercher une ressource", key="student_ped_query")
    rows = list_resources(
        get_conn,
        student_only=True,
        activity=None if activity == "Toutes" else activity,
        resource_type=None if resource_type == "Tous" else resource_type,
        query=query,
    )
    if not rows:
        st.info("Aucune ressource ne correspond à votre recherche.")
        return
    labels = {r["id"]: f'{r["activite"]} — {r["titre"]}' for r in rows}
    selected = st.selectbox("Consulter", list(labels), format_func=lambda x: labels[x], key="student_ped_selected")
    resource = get_resource(get_conn, selected)
    if not resource or not resource.get("visible_etudiants"):
        st.warning("Cette ressource n’est plus disponible.")
        return
    st.markdown(f"### {resource['titre']}")
    st.caption(f"{resource['activite']} • {resource['type_ressource']} • {resource['auteur']}")
    if resource.get("description"):
        st.write(resource["description"])
    if resource["type_ressource"] == "Séance":
        _render_session_content(st, resource.get("contenu") or {})
    if resource.get("lien_externe"):
        try:
            st.link_button("🔗 Ouvrir le lien", resource["lien_externe"], use_container_width=True)
        except AttributeError:
            st.markdown(f"[🔗 Ouvrir le lien]({resource['lien_externe']})")
    if resource.get("nom_fichier"):
        file_tuple = get_resource_file(get_conn, int(resource["id"]))
        if file_tuple:
            file_name, mime, file_bytes = file_tuple
            st.download_button("⬇️ Télécharger le document", data=file_bytes, file_name=file_name, mime=mime, use_container_width=True, key=f"student_ped_dl_{resource['id']}")

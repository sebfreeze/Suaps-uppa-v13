"""Carnet enseignant SUAPS : appel, notes et compétences dans un écran compact.

Le module ajoute une vue de travail inspirée des carnets de classe numériques :
tableaux éditables, actions de groupe, synthèses immédiates et fiche étudiant.
Il réutilise le schéma V13 existant afin de ne pas casser les données historiques.
"""

from datetime import date as _date, datetime as _datetime, timedelta as _timedelta
from io import BytesIO as _BytesIO
import secrets as _secrets
import unicodedata as _unicodedata

import pandas as pd


WORKBOOK_MENU_LABEL = "📘 Carnet enseignant"
ATTENDANCE_STATUSES = ["Présent", "Absent", "Justifié", "Dispensé"]
COMPETENCE_LEVELS = [
    "Non évalué",
    "En cours d’acquisition",
    "Acquis",
    "Maîtrisé",
]

ATTENDANCE_ICONS = {
    "Présent": "✅",
    "Absent": "❌",
    "Justifié": "🟠",
    "Dispensé": "🔵",
}

COMPETENCE_ICONS = {
    "Non évalué": "⚪",
    "En cours d’acquisition": "🟠",
    "Acquis": "🟢",
    "Maîtrisé": "🔵",
}

SUAPS_RUBRIC_COMPONENTS = (
    ("SUAPS • Projet / performance", "Projet / performance", 7.0),
    ("SUAPS • Maîtrise / compétences", "Maîtrise / compétences", 7.0),
    ("SUAPS • Assiduité / investissement / engagement", "Assiduité / investissement / engagement", 6.0),
)
SUAPS_RUBRIC_TITLES = {title for title, _, _ in SUAPS_RUBRIC_COMPONENTS}
WORKBOOK_ACTIVITIES = [
    "Natation",
    "Sauvetage",
    "Surf",
    "Rugby",
    "Course à pied",
    "Pelote Basque",
]


def _student_import_template():
    """Modèle complet : étudiants + création automatique des créneaux."""
    return pd.DataFrame(
        [
            {
                "nom": "DUPONT",
                "prenom": "Emma",
                "email": "",
                "numero_etudiant": "20260001",
                "groupe": "NAT-A",
                "activite": "Natation",
                "creneau": "Natation tous niveaux",
                "jour_horaire": "Lundi 18h00",
                "lieu": "Piscine universitaire",
                "UET": "X",
                "UECF": "",
                "Non noté": "",
            },
            {
                "nom": "MARTIN",
                "prenom": "Lucas",
                "email": "lucas.martin@exemple.fr",
                "numero_etudiant": "20260002",
                "groupe": "RUG-B",
                "activite": "Rugby",
                "creneau": "Rugby tous niveaux",
                "jour_horaire": "Jeudi 18h00",
                "lieu": "Stade universitaire",
                "UET": "",
                "UECF": "",
                "Non noté": "X",
            },
        ]
    )


def _canonical_import_key(value):
    text = str(value or "").strip().lower()
    text = "".join(
        char
        for char in _unicodedata.normalize("NFKD", text)
        if not _unicodedata.combining(char)
    )
    for char in (" ", "-", "/", "\\", "°", "'", "’"):
        text = text.replace(char, "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def _normalize_student_import_frame(frame):
    """Normalise les colonnes des modèles récents et historiques SUAPS."""
    imported = frame.copy()
    aliases = {}
    mapping = {
        "nom": "nom",
        "prenom": "prenom",
        "mail": "email",
        "e_mail": "email",
        "email": "email",
        "numero_etudiant": "numero_etudiant",
        "numero": "numero_etudiant",
        "n_etudiant": "numero_etudiant",
        "num_etudiant": "numero_etudiant",
        "identifiant": "numero_etudiant",
        "ine": "numero_etudiant",
        "groupe": "groupe",
        "group": "groupe",
        "activite": "activite",
        "creneau": "creneau",
        "jour_horaire": "jour_horaire",
        "jour_horaire_": "jour_horaire",
        "horaire": "jour_horaire",
        "lieu": "lieu",
        "uet": "uet",
        "uecf": "uecf",
        "non_note": "non_note",
        "non_notee": "non_note",
        "modalite": "modalite",
    }
    for column in imported.columns:
        key = _canonical_import_key(column)
        if key in mapping:
            aliases[column] = mapping[key]
    return imported.rename(columns=aliases)


def _clean_import_value(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _is_import_marked(value):
    text = _canonical_import_key(_clean_import_value(value))
    if text in {"", "0", "non", "no", "false", "faux", "nan"}:
        return False
    return True


def _import_modality(row):
    explicit = _canonical_import_key(_clean_import_value(row.get("modalite", "")))
    explicit_map = {
        "uet": "UET",
        "uecf": "UECF",
        "non_note": "Non noté",
        "non_notee": "Non noté",
    }
    if explicit in explicit_map:
        return explicit_map[explicit]
    if _is_import_marked(row.get("uet", "")):
        return "UET"
    if _is_import_marked(row.get("uecf", "")):
        return "UECF"
    if _is_import_marked(row.get("non_note", "")):
        return "Non noté"
    return "Non noté"


def _offer_import_values(row):
    activity = _clean_import_value(row.get("activite", ""))
    title = _clean_import_value(row.get("creneau", ""))
    if not activity and not title:
        return None
    if not activity:
        activity = title
    if not title:
        title = activity
    return {
        "activite": activity,
        "intitule": title,
        "groupe": _clean_import_value(row.get("groupe", "")),
        "jour_horaire": _clean_import_value(row.get("jour_horaire", "")),
        "lieu": _clean_import_value(row.get("lieu", "")),
    }


def _render_workbook_quick_actions(st, qdf, exec_sql):
    """Raccourcis terrain vers les tâches administratives les plus fréquentes."""
    st.markdown("### ⚡ Accès rapides")
    st.caption(
        "Créer un créneau d’inscription, importer un groupe et récupérer le modèle sans quitter le carnet."
    )

    with st.expander("➕ Créer un créneau", expanded=False):
        st.caption("Créneau d’inscription étudiant • UET, UECF ou Non noté")
        with st.form("workbook_create_offer"):
            c1, c2 = st.columns(2)
            activity = c1.selectbox(
                "Activité",
                WORKBOOK_ACTIVITIES,
                key="workbook_offer_activity",
            )
            title = c2.text_input(
                "Intitulé",
                placeholder="Ex. Natation perfectionnement",
            )
            c3, c4 = st.columns(2)
            group = c3.text_input(
                "Groupe / niveau",
                placeholder="Ex. NAT-A, débutant…",
            )
            capacity = c4.number_input(
                "Capacité (0 = illimitée)",
                min_value=0,
                value=24,
                step=1,
            )
            schedule = st.text_input(
                "Jour / horaire",
                placeholder="Ex. Mardi 18h00–19h30",
            )
            location = st.text_input(
                "Lieu",
                placeholder="Ex. Piscine universitaire",
            )
            c5, c6 = st.columns(2)
            start = c5.date_input(
                "Ouverture des inscriptions",
                value=_date.today(),
                key="workbook_offer_start",
            )
            end = c6.date_input(
                "Fermeture des inscriptions",
                value=_date.today() + _timedelta(days=30),
                key="workbook_offer_end",
            )
            create = st.form_submit_button(
                "Créer le créneau",
                type="primary",
                use_container_width=True,
            )
        if create:
            if not _clean(title):
                st.error("Renseigne un intitulé pour le créneau.")
            else:
                token = _secrets.token_urlsafe(20)
                exec_sql(
                    """
                    INSERT INTO offres_inscription(
                        activite,intitule,groupe,jour_horaire,lieu,capacite,
                        ouverte,date_debut,date_fin,token
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        activity,
                        _clean(title),
                        _clean(group),
                        _clean(schedule),
                        _clean(location),
                        int(capacity),
                        1,
                        str(start),
                        str(end),
                        token,
                    ),
                )
                st.success("Créneau créé. Il est aussi visible dans « Inscriptions en ligne ».")
                st.rerun()

        recent_offers = qdf(
            """
            SELECT id, activite, intitule, groupe, jour_horaire, lieu, capacite, ouverte
            FROM offres_inscription
            ORDER BY id DESC
            LIMIT 5
            """
        )
        if not recent_offers.empty:
            st.markdown("**Derniers créneaux**")
            st.dataframe(
                recent_offers,
                hide_index=True,
                use_container_width=True,
            )

    with st.expander("🗑️ Supprimer un créneau / une séance", expanded=False):
        st.warning(
            "Suppression définitive. Un créneau supprimé retire ses inscriptions "
            "mais ne supprime pas les étudiants. Une séance supprimée retire ses présences."
        )
        delete_offer_tab, delete_session_tab = st.tabs(
            ["Créneaux", "Séances"]
        )

        with delete_offer_tab:
            offers_to_delete = qdf(
                """
                SELECT o.id, o.activite, o.intitule, o.jour_horaire,
                       COUNT(i.id) AS nb_inscrits
                FROM offres_inscription o
                LEFT JOIN inscriptions i ON i.offre_id=o.id
                GROUP BY o.id, o.activite, o.intitule, o.jour_horaire
                ORDER BY o.activite, o.intitule, o.id
                """
            )
            if offers_to_delete.empty:
                st.info("Aucun créneau à supprimer.")
            else:
                offer_labels = {}
                for _, offer in offers_to_delete.iterrows():
                    label = (
                        f"#{int(offer['id'])} • {offer['activite']} — "
                        f"{offer['intitule']} • {offer['jour_horaire'] or 'horaire non renseigné'} "
                        f"• {int(offer['nb_inscrits'] or 0)} inscrit(s)"
                    )
                    offer_labels[label] = int(offer["id"])

                selected_offer_label = st.selectbox(
                    "Créneau à supprimer",
                    list(offer_labels.keys()),
                    key="workbook_delete_offer_select",
                )
                confirm_offer = st.checkbox(
                    "Je confirme la suppression de ce créneau et de ses inscriptions.",
                    key="workbook_delete_offer_confirm",
                )
                if st.button(
                    "🗑️ Supprimer ce créneau",
                    disabled=not confirm_offer,
                    use_container_width=True,
                    key="workbook_delete_offer_button",
                ):
                    exec_sql(
                        "DELETE FROM offres_inscription WHERE id=?",
                        (offer_labels[selected_offer_label],),
                    )
                    st.success("Créneau supprimé. Les étudiants sont conservés.")
                    st.rerun()

        with delete_session_tab:
            sessions_to_delete = qdf(
                """
                SELECT s.id, s.activite, s.groupe, s.date_seance, s.theme,
                       COUNT(p.id) AS nb_presences
                FROM seances s
                LEFT JOIN presences p ON p.seance_id=s.id
                GROUP BY s.id, s.activite, s.groupe, s.date_seance, s.theme
                ORDER BY s.date_seance DESC, s.id DESC
                """
            )
            if sessions_to_delete.empty:
                st.info("Aucune séance à supprimer.")
            else:
                session_labels = {}
                for _, session_row in sessions_to_delete.iterrows():
                    label = (
                        f"#{int(session_row['id'])} • {session_row['date_seance']} • "
                        f"{session_row['activite']} • "
                        f"{session_row['groupe'] or 'sans groupe'} • "
                        f"{session_row['theme'] or 'sans thème'} "
                        f"• {int(session_row['nb_presences'] or 0)} présence(s)"
                    )
                    session_labels[label] = int(session_row["id"])

                selected_session_label = st.selectbox(
                    "Séance à supprimer",
                    list(session_labels.keys()),
                    key="workbook_delete_session_select",
                )
                confirm_session = st.checkbox(
                    "Je confirme la suppression de cette séance et de ses présences.",
                    key="workbook_delete_session_confirm",
                )
                if st.button(
                    "🗑️ Supprimer cette séance",
                    disabled=not confirm_session,
                    use_container_width=True,
                    key="workbook_delete_session_button",
                ):
                    exec_sql(
                        "DELETE FROM seances WHERE id=?",
                        (session_labels[selected_session_label],),
                    )
                    st.success("Séance supprimée avec ses présences.")
                    st.rerun()

    with st.expander("📥 Importer CSV / Excel", expanded=False):
        st.caption(
            "Nom et Prénom sont obligatoires. Si activite + creneau sont présents, "
            "le créneau est créé automatiquement s’il n’existe pas et l’étudiant y est inscrit."
        )
        st.caption(
            "Compatibilité ancien modèle : identifiant, activite, creneau, jour_horaire, "
            "UET, UECF et Non noté."
        )
        uploaded = st.file_uploader(
            "Fichier étudiants",
            type=["xlsx", "csv"],
            key="workbook_student_import",
        )
        if uploaded is not None:
            try:
                raw = (
                    pd.read_csv(uploaded)
                    if uploaded.name.lower().endswith(".csv")
                    else pd.read_excel(uploaded)
                )
                imported = _normalize_student_import_frame(raw)
                st.dataframe(
                    imported.head(20),
                    hide_index=True,
                    use_container_width=True,
                )
                if "nom" not in imported.columns or "prenom" not in imported.columns:
                    st.error("Le fichier doit contenir au minimum les colonnes Nom et Prénom.")
                else:
                    slot_rows = [
                        _offer_import_values(row)
                        for _, row in imported.iterrows()
                    ]
                    slot_keys = {
                        (
                            item["activite"].casefold(),
                            item["intitule"].casefold(),
                        )
                        for item in slot_rows
                        if item is not None
                    }
                    if slot_keys:
                        st.info(
                            f"{len(slot_keys)} créneau(x) détecté(s) dans le fichier. "
                            "Ils seront créés uniquement s’ils n’existent pas déjà."
                        )

                if (
                    "nom" in imported.columns
                    and "prenom" in imported.columns
                    and st.button(
                        "Importer étudiants + créneaux",
                        type="primary",
                        use_container_width=True,
                        key="workbook_import_students_button",
                    )
                ):
                    added = 0
                    updated = 0
                    ignored = 0
                    offers_created = 0
                    registrations = 0

                    for _, row in imported.iterrows():
                        name = _clean_import_value(row.get("nom", ""))
                        firstname = _clean_import_value(row.get("prenom", ""))
                        if not name or not firstname:
                            ignored += 1
                            continue

                        email = _clean_import_value(row.get("email", ""))
                        number = _clean_import_value(row.get("numero_etudiant", ""))
                        group_value = _clean_import_value(row.get("groupe", ""))

                        existing = (
                            qdf(
                                """
                                SELECT id, email, numero_etudiant, groupe
                                FROM etudiants
                                WHERE numero_etudiant=?
                                """,
                                (number,),
                            )
                            if number
                            else pd.DataFrame()
                        )
                        if existing.empty:
                            existing = qdf(
                                """
                                SELECT id, email, numero_etudiant, groupe
                                FROM etudiants
                                WHERE lower(nom)=lower(?) AND lower(prenom)=lower(?)
                                ORDER BY id
                                LIMIT 1
                                """,
                                (name, firstname),
                            )

                        if not existing.empty:
                            old = existing.iloc[0]
                            student_id = int(old["id"])
                            exec_sql(
                                """
                                UPDATE etudiants
                                SET nom=?, prenom=?, email=?, numero_etudiant=?,
                                    groupe=?, actif=1
                                WHERE id=?
                                """,
                                (
                                    name,
                                    firstname,
                                    email or _clean_import_value(old.get("email", "")),
                                    number or _clean_import_value(old.get("numero_etudiant", "")) or None,
                                    group_value or _clean_import_value(old.get("groupe", "")),
                                    student_id,
                                ),
                            )
                            updated += 1
                        else:
                            exec_sql(
                                """
                                INSERT INTO etudiants(
                                    nom,prenom,email,numero_etudiant,groupe
                                ) VALUES(?,?,?,?,?)
                                """,
                                (
                                    name,
                                    firstname,
                                    email,
                                    number or None,
                                    group_value,
                                ),
                            )
                            added += 1
                            created_student = (
                                qdf(
                                    """
                                    SELECT id FROM etudiants
                                    WHERE numero_etudiant=?
                                    ORDER BY id DESC LIMIT 1
                                    """,
                                    (number,),
                                )
                                if number
                                else qdf(
                                    """
                                    SELECT id FROM etudiants
                                    WHERE lower(nom)=lower(?) AND lower(prenom)=lower(?)
                                    ORDER BY id DESC LIMIT 1
                                    """,
                                    (name, firstname),
                                )
                            )
                            if created_student.empty:
                                ignored += 1
                                continue
                            student_id = int(created_student.iloc[0]["id"])

                        offer_values = _offer_import_values(row)
                        if offer_values is None:
                            continue

                        offer = qdf(
                            """
                            SELECT id, groupe, jour_horaire, lieu
                            FROM offres_inscription
                            WHERE lower(activite)=lower(?) AND lower(intitule)=lower(?)
                            ORDER BY id
                            LIMIT 1
                            """,
                            (
                                offer_values["activite"],
                                offer_values["intitule"],
                            ),
                        )

                        if offer.empty:
                            exec_sql(
                                """
                                INSERT INTO offres_inscription(
                                    activite,intitule,groupe,jour_horaire,lieu,
                                    capacite,ouverte,date_debut,date_fin,token
                                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                                """,
                                (
                                    offer_values["activite"],
                                    offer_values["intitule"],
                                    offer_values["groupe"],
                                    offer_values["jour_horaire"],
                                    offer_values["lieu"],
                                    0,
                                    1,
                                    None,
                                    None,
                                    _secrets.token_urlsafe(20),
                                ),
                            )
                            offers_created += 1
                            offer = qdf(
                                """
                                SELECT id, groupe, jour_horaire, lieu
                                FROM offres_inscription
                                WHERE lower(activite)=lower(?) AND lower(intitule)=lower(?)
                                ORDER BY id DESC
                                LIMIT 1
                                """,
                                (
                                    offer_values["activite"],
                                    offer_values["intitule"],
                                ),
                            )
                        else:
                            old_offer = offer.iloc[0]
                            new_group = (
                                _clean_import_value(old_offer.get("groupe", ""))
                                or offer_values["groupe"]
                            )
                            new_schedule = (
                                _clean_import_value(old_offer.get("jour_horaire", ""))
                                or offer_values["jour_horaire"]
                            )
                            new_location = (
                                _clean_import_value(old_offer.get("lieu", ""))
                                or offer_values["lieu"]
                            )
                            exec_sql(
                                """
                                UPDATE offres_inscription
                                SET groupe=?, jour_horaire=?, lieu=?
                                WHERE id=?
                                """,
                                (
                                    new_group,
                                    new_schedule,
                                    new_location,
                                    int(old_offer["id"]),
                                ),
                            )

                        if offer.empty:
                            ignored += 1
                            continue

                        offer_id = int(offer.iloc[0]["id"])
                        modality = _import_modality(row)
                        exec_sql(
                            """
                            INSERT INTO inscriptions(
                                offre_id,etudiant_id,modalite,date_inscription,
                                statut,commentaire
                            ) VALUES(?,?,?,?,?,?)
                            ON CONFLICT(offre_id,etudiant_id)
                            DO UPDATE SET
                                modalite=excluded.modalite,
                                date_inscription=excluded.date_inscription,
                                statut='Inscrit',
                                commentaire=excluded.commentaire
                            """,
                            (
                                offer_id,
                                student_id,
                                modality,
                                _datetime.now().isoformat(timespec="seconds"),
                                "Inscrit",
                                "Import CSV/Excel — Carnet enseignant",
                            ),
                        )
                        registrations += 1

                    st.success(
                        "Import terminé : "
                        f"{added} étudiant(s) ajouté(s), "
                        f"{updated} mis à jour, "
                        f"{offers_created} créneau(x) créé(s), "
                        f"{registrations} inscription(s) traitée(s), "
                        f"{ignored} ligne(s) ignorée(s)."
                    )
                    st.rerun()
            except Exception as exc:
                st.error(f"Erreur d’import : {exc}")

    with st.expander("📄 Télécharger le modèle", expanded=False):
        template = _student_import_template()
        st.caption(
            "Email facultatif • Nom et Prénom obligatoires • "
            "activite + creneau = création/inscription automatique"
        )
        st.dataframe(template, hide_index=True, use_container_width=True)
        output = _BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            template.to_excel(writer, index=False, sheet_name="Etudiants")
        st.download_button(
            "⬇️ Modèle Excel",
            data=output.getvalue(),
            file_name="modele_import_etudiants_SUAPS.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="workbook_download_excel_template",
        )
        st.download_button(
            "⬇️ Modèle CSV",
            data=template.to_csv(index=False).encode("utf-8-sig"),
            file_name="modele_import_etudiants_SUAPS.csv",
            mime="text/csv",
            use_container_width=True,
            key="workbook_download_csv_template",
        )


def _attendance_display(status):
    status = _clean(status) or "Non renseigné"
    return f"{ATTENDANCE_ICONS.get(status, '⚪')} {status}"


def _competence_display(level):
    level = _clean(level) or "Non évalué"
    return f"{COMPETENCE_ICONS.get(level, '⚪')} {level}"


def _advance_index(index, total, step=1):
    if total <= 0:
        return 0
    return max(0, min(int(index) + int(step), int(total) - 1))


def _float_or_none(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalized_note_20(note, bareme):
    note = _float_or_none(note)
    bareme = _float_or_none(bareme)
    if note is None or bareme is None or bareme <= 0:
        return None
    return note / bareme * 20.0


def _weighted_average_20(items):
    """Moyenne pondérée normalisée /20 de tuples (note, barème, coefficient)."""
    total = 0.0
    weights = 0.0
    for note, bareme, coefficient in items:
        normalized = _normalized_note_20(note, bareme)
        coefficient = _float_or_none(coefficient)
        if normalized is None or coefficient is None or coefficient <= 0:
            continue
        total += normalized * coefficient
        weights += coefficient
    return (total / weights) if weights else None


def _note_changed(old_note, new_note):
    old_note = _float_or_none(old_note)
    new_note = _float_or_none(new_note)
    if old_note is None or new_note is None:
        return old_note != new_note
    return abs(old_note - new_note) > 1e-9


def _clamp_score(value, maximum):
    value = _float_or_none(value)
    if value is None:
        return None
    return max(0.0, min(float(maximum), value))


def _score_from_20(value, maximum):
    value = _float_or_none(value)
    if value is None:
        return None
    return round(_clamp_score(value / 20.0 * float(maximum), maximum), 2)


def _competence_score_7(levels):
    weights = {
        "Non évalué": 0.0,
        "En cours d’acquisition": 1.0 / 3.0,
        "Acquis": 2.0 / 3.0,
        "Maîtrisé": 1.0,
    }
    values = [weights.get(_clean(level), 0.0) for level in levels]
    if not values:
        return None
    return round(sum(values) / len(values) * 7.0, 2)


def _attendance_score_6(statuses):
    relevant = [
        _clean(status)
        for status in statuses
        if _clean(status) in {"Présent", "Absent"}
    ]
    if not relevant:
        return None
    present = sum(status == "Présent" for status in relevant)
    return round(present / len(relevant) * 6.0, 2)


def _rubric_total_20(values):
    cleaned = [_float_or_none(value) for value in values]
    if any(value is None for value in cleaned):
        return None
    return round(sum(cleaned), 2)


def _is_suaps_rubric_title(title):
    return _clean(title) in SUAPS_RUBRIC_TITLES


def _evaluation_identity(row):
    return (_clean(row.get("date_eval")), _clean(row.get("intitule")))


def _gradebook_assessments(evaluations):
    """Déduit les colonnes d'évaluation sans créer de nouvelle table."""
    if evaluations is None or evaluations.empty:
        return []
    work = evaluations.copy()
    if "id" in work.columns:
        work = work.sort_values(
            ["date_eval", "id"],
            ascending=[False, False],
            kind="stable",
        )
    else:
        work = work.sort_values("date_eval", ascending=False, kind="stable")

    result = []
    seen = set()
    for _, row in work.iterrows():
        identity = _evaluation_identity(row)
        if identity in seen:
            continue
        seen.add(identity)
        bareme = _float_or_none(row.get("bareme"))
        coefficient = _float_or_none(row.get("coefficient"))
        result.append(
            {
                "identity": identity,
                "date_eval": identity[0],
                "intitule": identity[1] or "Évaluation",
                "bareme": bareme if bareme and bareme > 0 else 20.0,
                "coefficient": (
                    coefficient if coefficient and coefficient > 0 else 1.0
                ),
            }
        )
    for idx, item in enumerate(result, start=1):
        item["column"] = f"eval_{idx}"
    return result


def inject_workbook_navigation(options):
    """Ajoute le Carnet uniquement dans la navigation enseignant."""
    original_is_tuple = isinstance(options, tuple)
    items = list(options)
    teacher_navigation = (
        "Présences" in items
        and ("Cahier de notes" in items or "Compétences" in items)
    )
    if not teacher_navigation or WORKBOOK_MENU_LABEL in items:
        return options

    if "Présences" in items:
        items.insert(items.index("Présences"), WORKBOOK_MENU_LABEL)
    else:
        items.append(WORKBOOK_MENU_LABEL)
    return tuple(items) if original_is_tuple else items


def _clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def _students_for_session(qdf, session):
    """Retourne le roster de la séance sans mélanger les activités.

    Priorité aux inscriptions en ligne liées à l'activité et, si renseigné,
    au groupe/intitulé du créneau. Le comportement historique n'est utilisé
    qu'en absence totale d'inscriptions dans l'application.
    """
    activity = _clean(session.get("activite"))
    group = _clean(session.get("groupe"))

    if activity:
        if group:
            registered = qdf(
                """
                SELECT DISTINCT e.id, e.nom, e.prenom, e.numero_etudiant, e.groupe
                FROM etudiants e
                JOIN inscriptions i ON i.etudiant_id=e.id
                JOIN offres_inscription o ON o.id=i.offre_id
                WHERE e.actif=1
                  AND i.statut='Inscrit'
                  AND lower(o.activite)=lower(?)
                  AND (
                      lower(coalesce(o.groupe,''))=lower(?)
                      OR lower(o.intitule)=lower(?)
                  )
                ORDER BY e.nom, e.prenom
                """,
                (activity, group, group),
            )
        else:
            registered = qdf(
                """
                SELECT DISTINCT e.id, e.nom, e.prenom, e.numero_etudiant, e.groupe
                FROM etudiants e
                JOIN inscriptions i ON i.etudiant_id=e.id
                JOIN offres_inscription o ON o.id=i.offre_id
                WHERE e.actif=1
                  AND i.statut='Inscrit'
                  AND lower(o.activite)=lower(?)
                ORDER BY e.nom, e.prenom
                """,
                (activity,),
            )
        if not registered.empty:
            return registered

    if group:
        legacy_group = qdf(
            """
            SELECT id, nom, prenom, numero_etudiant, groupe
            FROM etudiants
            WHERE actif=1 AND lower(coalesce(groupe,''))=lower(?)
            ORDER BY nom, prenom
            """,
            (group,),
        )
        if not legacy_group.empty:
            return legacy_group

    registrations = qdf(
        "SELECT COUNT(*) AS n FROM inscriptions WHERE statut='Inscrit'"
    )
    if not registrations.empty and int(registrations.iloc[0]["n"] or 0) > 0:
        return pd.DataFrame(
            columns=["id", "nom", "prenom", "numero_etudiant", "groupe"]
        )

    return qdf(
        """
        SELECT id, nom, prenom, numero_etudiant, groupe
        FROM etudiants
        WHERE actif=1
        ORDER BY nom, prenom
        """
    )


def _attendance_source(row):
    if row is None:
        return "—"
    comment = _clean(row.get("commentaire"))
    if "QR" in comment.upper() or "NFC" in comment.upper():
        return "QR/NFC"
    return "Manuel"


def _presence_comment_for_save(old_row, new_status, observation):
    """Préserve la trace QR/NFC tant que l'enseignant ne modifie pas la présence."""
    observation = _clean(observation)
    if observation:
        return observation
    if old_row is None:
        return ""
    old_status = _clean(old_row.get("statut"))
    old_comment = _clean(old_row.get("commentaire"))
    if (
        new_status == old_status
        and ("QR" in old_comment.upper() or "NFC" in old_comment.upper())
    ):
        return old_comment
    return ""


def _express_presence_comment(old_row, new_status, observation):
    """Commentaire d'appel express en conservant la provenance QR/NFC."""
    observation = _clean(observation)
    if observation:
        return observation
    preserved = _presence_comment_for_save(old_row, new_status, "")
    if preserved:
        return preserved
    return "Appel express — Carnet enseignant"



def _matching_offers_for_session(qdf, session):
    """Créneaux d'inscription correspondant à la séance affichée dans le carnet."""
    activity = _clean(session.get("activite"))
    group = _clean(session.get("groupe"))
    if not activity:
        return pd.DataFrame()

    if group:
        return qdf(
            """
            SELECT id, activite, intitule, groupe, jour_horaire, lieu, capacite, ouverte
            FROM offres_inscription
            WHERE lower(activite)=lower(?)
              AND (
                  lower(coalesce(groupe,''))=lower(?)
                  OR lower(intitule)=lower(?)
              )
            ORDER BY ouverte DESC, id DESC
            """,
            (activity, group, group),
        )

    return qdf(
        """
        SELECT id, activite, intitule, groupe, jour_horaire, lieu, capacite, ouverte
        FROM offres_inscription
        WHERE lower(activite)=lower(?)
        ORDER BY ouverte DESC, id DESC
        """,
        (activity,),
    )


def _ensure_offer_for_session(qdf, exec_sql, session):
    """Retourne un créneau lié à la séance, ou crée un créneau interne fermé."""
    offers = _matching_offers_for_session(qdf, session)
    if not offers.empty:
        return int(offers.iloc[0]["id"])

    activity = _clean(session.get("activite")) or "Activité"
    group = _clean(session.get("groupe"))
    title = group or f"{activity} — Carnet"
    exec_sql(
        """
        INSERT INTO offres_inscription(
            activite,intitule,groupe,jour_horaire,lieu,capacite,
            ouverte,date_debut,date_fin,token
        ) VALUES(?,?,?,?,?,?,?,?,?,?)
        """,
        (
            activity,
            title,
            group,
            "",
            "",
            0,
            0,
            None,
            None,
            _secrets.token_urlsafe(20),
        ),
    )
    created = _matching_offers_for_session(qdf, session)
    if created.empty:
        return None
    return int(created.iloc[0]["id"])


def _offer_default_modality(qdf, offer_id):
    if not offer_id:
        return "Non noté"
    modes = qdf(
        """
        SELECT modalite, COUNT(*) AS n
        FROM inscriptions
        WHERE offre_id=? AND statut='Inscrit'
        GROUP BY modalite
        ORDER BY n DESC
        LIMIT 1
        """,
        (int(offer_id),),
    )
    if modes.empty:
        return "Non noté"
    value = _clean(modes.iloc[0]["modalite"])
    return value if value in {"UET", "UECF", "Non noté"} else "Non noté"


def _register_student_in_offer(qdf, exec_sql, offer_id, student_id, modality):
    """Inscrit l'étudiant dans le créneau en protégeant la capacité définie."""
    offer = qdf(
        "SELECT id, capacite FROM offres_inscription WHERE id=?",
        (int(offer_id),),
    )
    if offer.empty:
        return False, "Créneau introuvable."

    already = qdf(
        """
        SELECT id FROM inscriptions
        WHERE offre_id=? AND etudiant_id=? AND statut='Inscrit'
        """,
        (int(offer_id), int(student_id)),
    )
    if already.empty:
        capacity = int(offer.iloc[0]["capacite"] or 0)
        if capacity > 0:
            count = qdf(
                """
                SELECT COUNT(*) AS n
                FROM inscriptions
                WHERE offre_id=? AND statut='Inscrit'
                """,
                (int(offer_id),),
            )
            enrolled = int(count.iloc[0]["n"] or 0) if not count.empty else 0
            if enrolled >= capacity:
                return False, f"Créneau complet ({enrolled}/{capacity})."

    exec_sql(
        """
        INSERT INTO inscriptions(
            offre_id,etudiant_id,modalite,date_inscription,statut,commentaire
        ) VALUES(?,?,?,?,?,?)
        ON CONFLICT(offre_id,etudiant_id)
        DO UPDATE SET
            modalite=excluded.modalite,
            date_inscription=excluded.date_inscription,
            statut='Inscrit',
            commentaire=excluded.commentaire
        """,
        (
            int(offer_id),
            int(student_id),
            modality,
            _datetime.now().isoformat(timespec="seconds"),
            "Inscrit",
            "Ajout manuel — Carnet enseignant",
        ),
    )
    return True, "Étudiant ajouté au créneau."


def _render_add_student_to_session(st, qdf, exec_sql, session):
    """Ajout direct d'un étudiant dans le créneau actuellement sélectionné."""
    sid = int(session["id"])
    activity = _clean(session.get("activite")) or "Activité"
    group = _clean(session.get("groupe"))
    offers = _matching_offers_for_session(qdf, session)

    with st.expander("➕ Ajouter un étudiant à ce créneau", expanded=False):
        st.caption(
            f"Créneau sélectionné : {activity}"
            + (f" • {group}" if group else "")
            + ". L'étudiant apparaîtra immédiatement dans le carnet."
        )

        offer_id = None
        if offers.empty:
            st.info(
                "Aucun créneau d'inscription correspondant : un créneau interne fermé "
                "sera créé automatiquement lors du premier ajout."
            )
        elif len(offers) == 1:
            offer_id = int(offers.iloc[0]["id"])
            offer = offers.iloc[0]
            st.caption(
                f"Inscription liée à : {offer['intitule']}"
                + (f" • {offer['jour_horaire']}" if _clean(offer.get("jour_horaire")) else "")
            )
        else:
            offer_labels = {
                int(row["id"]): (
                    f"{row['intitule']}"
                    + (f" • {row['jour_horaire']}" if _clean(row.get("jour_horaire")) else "")
                )
                for _, row in offers.iterrows()
            }
            offer_id = st.selectbox(
                "Créneau d'inscription associé",
                list(offer_labels.keys()),
                format_func=lambda value: offer_labels[value],
                key=f"workbook_add_offer_{sid}",
            )

        current_students = _students_for_session(qdf, session)
        current_ids = (
            {int(x) for x in current_students["id"].tolist()}
            if not current_students.empty
            else set()
        )
        all_students = qdf(
            """
            SELECT id, nom, prenom, numero_etudiant, groupe
            FROM etudiants
            WHERE actif=1
            ORDER BY nom, prenom
            """
        )
        available = (
            all_students[~all_students["id"].astype(int).isin(current_ids)]
            if not all_students.empty
            else all_students
        )

        st.markdown("**Étudiant déjà dans la base**")
        if available.empty:
            st.info("Tous les étudiants actifs sont déjà dans ce créneau, ou la base est vide.")
        else:
            student_labels = {}
            for _, student in available.iterrows():
                eid = int(student["id"])
                details = []
                if _clean(student.get("numero_etudiant")):
                    details.append(f"N° {_clean(student.get('numero_etudiant'))}")
                if _clean(student.get("groupe")):
                    details.append(_clean(student.get("groupe")))
                suffix = f" • {' • '.join(details)}" if details else ""
                student_labels[eid] = f"{student['nom']} {student['prenom']}{suffix}"

            with st.form(f"workbook_add_existing_student_{sid}"):
                student_id = st.selectbox(
                    "Rechercher / sélectionner l'étudiant",
                    list(student_labels.keys()),
                    format_func=lambda value: student_labels[value],
                    key=f"workbook_add_existing_select_{sid}",
                )
                add_existing = st.form_submit_button(
                    "➕ Ajouter au créneau",
                    type="primary",
                    use_container_width=True,
                )

            if add_existing:
                target_offer = int(offer_id) if offer_id else _ensure_offer_for_session(
                    qdf, exec_sql, session
                )
                if target_offer is None:
                    st.error("Impossible de créer le lien avec ce créneau.")
                else:
                    modality = _offer_default_modality(qdf, target_offer)
                    ok, message = _register_student_in_offer(
                        qdf, exec_sql, target_offer, int(student_id), modality
                    )
                    if ok:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

        st.markdown("**Nouvel étudiant**")
        with st.form(f"workbook_create_and_add_student_{sid}"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Nom", key=f"workbook_new_name_{sid}")
            firstname = c2.text_input("Prénom", key=f"workbook_new_firstname_{sid}")
            c3, c4 = st.columns(2)
            number = c3.text_input("N° étudiant", key=f"workbook_new_number_{sid}")
            email = c4.text_input("Email", key=f"workbook_new_email_{sid}")
            student_group = st.text_input(
                "Groupe",
                value=group,
                key=f"workbook_new_group_{sid}",
            )
            create_and_add = st.form_submit_button(
                "Créer et ajouter au créneau",
                use_container_width=True,
            )

        if create_and_add:
            name = _clean(name)
            firstname = _clean(firstname)
            number = _clean(number)
            email = _clean(email)
            student_group = _clean(student_group)
            if not name or not firstname:
                st.error("Le nom et le prénom sont obligatoires.")
            else:
                existing = (
                    qdf(
                        "SELECT id FROM etudiants WHERE numero_etudiant=? ORDER BY id LIMIT 1",
                        (number,),
                    )
                    if number
                    else pd.DataFrame()
                )
                if existing.empty:
                    existing = qdf(
                        """
                        SELECT id FROM etudiants
                        WHERE lower(nom)=lower(?) AND lower(prenom)=lower(?)
                        ORDER BY id LIMIT 1
                        """,
                        (name, firstname),
                    )

                if existing.empty:
                    exec_sql(
                        """
                        INSERT INTO etudiants(
                            nom,prenom,email,numero_etudiant,groupe,actif
                        ) VALUES(?,?,?,?,?,1)
                        """,
                        (name, firstname, email, number or None, student_group),
                    )
                    existing = (
                        qdf(
                            "SELECT id FROM etudiants WHERE numero_etudiant=? ORDER BY id DESC LIMIT 1",
                            (number,),
                        )
                        if number
                        else qdf(
                            """
                            SELECT id FROM etudiants
                            WHERE lower(nom)=lower(?) AND lower(prenom)=lower(?)
                            ORDER BY id DESC LIMIT 1
                            """,
                            (name, firstname),
                        )
                    )

                if existing.empty:
                    st.error("Impossible de créer l'étudiant.")
                else:
                    student_id = int(existing.iloc[0]["id"])
                    exec_sql(
                        """
                        UPDATE etudiants
                        SET nom=?, prenom=?, email=?, groupe=?, actif=1
                        WHERE id=?
                        """,
                        (name, firstname, email, student_group, student_id),
                    )
                    target_offer = int(offer_id) if offer_id else _ensure_offer_for_session(
                        qdf, exec_sql, session
                    )
                    if target_offer is None:
                        st.error("Impossible de créer le lien avec ce créneau.")
                    else:
                        modality = _offer_default_modality(qdf, target_offer)
                        ok, message = _register_student_in_offer(
                            qdf, exec_sql, target_offer, student_id, modality
                        )
                        if ok:
                            st.success("Étudiant créé/identifié et ajouté au créneau.")
                            st.rerun()
                        else:
                            st.error(message)

def _render_header(st, session, students):
    activity = _clean(session.get("activite")) or "Activité"
    group = _clean(session.get("groupe")) or "Tous"
    theme = _clean(session.get("theme")) or "Séance"
    session_date = _clean(session.get("date_seance"))

    st.markdown(
        f"""
        <div style="
            border:1px solid rgba(12,60,120,.12);
            border-radius:18px;
            padding:14px 16px;
            margin:4px 0 14px 0;
            background:rgba(255,255,255,.84);
        ">
          <div style="font-size:1.08rem;font-weight:750;">{activity} • {theme}</div>
          <div style="opacity:.78;margin-top:4px;">📅 {session_date} &nbsp;•&nbsp; 👥 {group} &nbsp;•&nbsp; {len(students)} étudiant(s)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_attendance(st, qdf, upsert_presence, session, students):
    sid = int(session["id"])
    existing = qdf(
        "SELECT * FROM presences WHERE seance_id=?",
        (sid,),
    )
    pmap = {int(row["etudiant_id"]): row for _, row in existing.iterrows()}

    current_statuses = [
        _clean(row.get("statut"))
        for _, row in existing.iterrows()
        if _clean(row.get("statut")) in ATTENDANCE_STATUSES
    ]
    completed = len(current_statuses)
    total_students = len(students)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ Présents", current_statuses.count("Présent"))
    c2.metric("❌ Absents", current_statuses.count("Absent"))
    c3.metric("🟠 Justifiés", current_statuses.count("Justifié"))
    c4.metric("🔵 Dispensés", current_statuses.count("Dispensé"))

    if total_students:
        st.progress(min(1.0, completed / total_students))
        st.caption(f"Appel renseigné : {completed}/{total_students} étudiant(s)")

    st.markdown("#### ✅ Présence en 1 clic")
    st.caption(
        "Un clic coche l'étudiant présent ; un second clic le repasse absent. "
        "Les statuts Justifié et Dispensé restent disponibles dans la grille complète."
    )

    def _toggle_quick_presence(student_id, state_key):
        old = pmap.get(int(student_id))
        target = "Présent" if st.session_state.get(state_key, False) else "Absent"
        upsert_presence(
            sid,
            int(student_id),
            target,
            _presence_comment_for_save(old, target, ""),
        )

    quick_cols = st.columns(2)
    for index, (_, student) in enumerate(students.iterrows()):
        eid = int(student["id"])
        old = pmap.get(eid)
        current_status = _clean(old.get("statut")) if old is not None else ""
        state_key = f"workbook_one_click_present_{sid}_{eid}"
        expected = current_status == "Présent"
        if state_key not in st.session_state or st.session_state[state_key] != expected:
            st.session_state[state_key] = expected

        label = f"{student['nom']} {student['prenom']}"
        if _clean(student.get("numero_etudiant")):
            label += f" • {_clean(student.get('numero_etudiant'))}"
        quick_cols[index % 2].checkbox(
            label,
            key=state_key,
            on_change=_toggle_quick_presence,
            args=(eid, state_key),
        )

    st.divider()

    b1, b2 = st.columns(2)
    if b1.button(
        "✅ Tous présents",
        key=f"workbook_all_present_{sid}",
        use_container_width=True,
        type="primary",
    ):
        for _, student in students.iterrows():
            eid = int(student["id"])
            old = pmap.get(eid)
            upsert_presence(
                sid,
                eid,
                "Présent",
                _presence_comment_for_save(old, "Présent", ""),
            )
        st.success("Tous les étudiants ont été marqués présents.")
        st.rerun()

    if b2.button(
        "⬜ Absents si non renseignés",
        key=f"workbook_missing_absent_{sid}",
        use_container_width=True,
    ):
        existing_ids = set(pmap)
        for _, student in students.iterrows():
            eid = int(student["id"])
            if eid not in existing_ids:
                upsert_presence(
                    sid,
                    eid,
                    "Absent",
                    "Appel manuel — Carnet enseignant",
                )
        st.success("Les étudiants non renseignés ont été marqués absents.")
        st.rerun()

    tab_fast, tab_grid = st.tabs(["⚡ Appel express", "📋 Grille complète"])

    with tab_fast:
        ids = [int(x) for x in students["id"].tolist()]
        labels = {
            int(row["id"]): f"{row['nom']} {row['prenom']}"
            for _, row in students.iterrows()
        }
        cursor_key = f"workbook_attendance_cursor_{sid}"
        cursor = int(st.session_state.get(cursor_key, 0))
        cursor = _advance_index(cursor, len(ids), 0)
        st.session_state[cursor_key] = cursor

        eid = ids[cursor]
        student = students[students["id"] == eid].iloc[0]
        old = pmap.get(eid)
        current_status = _clean(old.get("statut")) if old is not None else ""
        source = _attendance_source(old)

        st.markdown(f"### {cursor + 1}/{len(ids)} • {student['nom']} {student['prenom']}")
        if _clean(student.get("numero_etudiant")):
            st.caption(
                f"N° {_clean(student.get('numero_etudiant'))} • "
                f"{_clean(student.get('groupe')) or 'sans groupe'}"
            )
        st.info(
            f"Statut actuel : {_attendance_display(current_status)}"
            f" • origine : {source}"
        )

        system_comments = {
            "Auto-validation QR/NFC",
            "Appel manuel smartphone",
            "Appel manuel — Carnet enseignant",
            "Appel express — Carnet enseignant",
        }
        old_comment = _clean(old.get("commentaire")) if old is not None else ""
        observation_default = "" if old_comment in system_comments else old_comment
        observation = st.text_input(
            "Observation",
            value=observation_default,
            placeholder="Optionnel : retard, motif, information utile…",
            key=f"workbook_fast_obs_{sid}_{eid}",
        )

        r1c1, r1c2 = st.columns(2)
        r2c1, r2c2 = st.columns(2)

        clicked_status = None
        if r1c1.button(
            "✅ Présent",
            key=f"fast_present_{sid}_{eid}",
            use_container_width=True,
            type="primary" if current_status == "Présent" else "secondary",
        ):
            clicked_status = "Présent"
        if r1c2.button(
            "❌ Absent",
            key=f"fast_absent_{sid}_{eid}",
            use_container_width=True,
            type="primary" if current_status == "Absent" else "secondary",
        ):
            clicked_status = "Absent"
        if r2c1.button(
            "🟠 Justifié",
            key=f"fast_justified_{sid}_{eid}",
            use_container_width=True,
            type="primary" if current_status == "Justifié" else "secondary",
        ):
            clicked_status = "Justifié"
        if r2c2.button(
            "🔵 Dispensé",
            key=f"fast_exempt_{sid}_{eid}",
            use_container_width=True,
            type="primary" if current_status == "Dispensé" else "secondary",
        ):
            clicked_status = "Dispensé"

        if clicked_status:
            upsert_presence(
                sid,
                eid,
                clicked_status,
                _express_presence_comment(old, clicked_status, observation),
            )
            if cursor < len(ids) - 1:
                st.session_state[cursor_key] = _advance_index(cursor, len(ids), 1)
            st.rerun()

        n1, n2 = st.columns(2)
        if n1.button(
            "← Précédent",
            key=f"fast_prev_{sid}_{eid}",
            use_container_width=True,
            disabled=cursor == 0,
        ):
            st.session_state[cursor_key] = _advance_index(cursor, len(ids), -1)
            st.rerun()
        if n2.button(
            "Suivant →",
            key=f"fast_next_{sid}_{eid}",
            use_container_width=True,
            disabled=cursor >= len(ids) - 1,
        ):
            st.session_state[cursor_key] = _advance_index(cursor, len(ids), 1)
            st.rerun()

        if cursor == len(ids) - 1 and current_status in ATTENDANCE_STATUSES:
            st.success("Dernier étudiant de la liste : l’appel peut être vérifié dans la grille complète.")

    with tab_grid:
        table_rows = []
        for _, student in students.iterrows():
            eid = int(student["id"])
            old = pmap.get(eid)
            status = _clean(old.get("statut")) if old is not None else "Absent"
            if status not in ATTENDANCE_STATUSES:
                status = "Absent"
            comment = _clean(old.get("commentaire")) if old is not None else ""
            if comment in {
                "Auto-validation QR/NFC",
                "Appel manuel smartphone",
                "Appel manuel — Carnet enseignant",
                "Appel express — Carnet enseignant",
            }:
                comment = ""
            table_rows.append(
                {
                    "etudiant_id": eid,
                    "Étudiant": f"{student['nom']} {student['prenom']}",
                    "Repère": _attendance_display(status),
                    "Statut": status,
                    "Source": _attendance_source(old),
                    "Observation": comment,
                }
            )

        frame = pd.DataFrame(table_rows)
        with st.form(f"workbook_attendance_form_{sid}"):
            edited = st.data_editor(
                frame,
                hide_index=True,
                use_container_width=True,
                height=min(760, 42 + 36 * max(1, len(frame))),
                disabled=["etudiant_id", "Étudiant", "Repère", "Source"],
                column_config={
                    "etudiant_id": None,
                    "Étudiant": st.column_config.TextColumn(
                        "Étudiant", width="medium", pinned=True
                    ),
                    "Repère": st.column_config.TextColumn(
                        "Repère", width="small"
                    ),
                    "Statut": st.column_config.SelectboxColumn(
                        "Présence",
                        options=ATTENDANCE_STATUSES,
                        required=True,
                        width="small",
                    ),
                    "Source": st.column_config.TextColumn("Origine", width="small"),
                    "Observation": st.column_config.TextColumn(
                        "Observation", width="medium"
                    ),
                },
                key=f"workbook_attendance_grid_{sid}",
            )
            save = st.form_submit_button(
                "💾 Enregistrer l’appel",
                type="primary",
                use_container_width=True,
            )

        if save:
            for _, row in edited.iterrows():
                eid = int(row["etudiant_id"])
                status = _clean(row["Statut"]) or "Absent"
                upsert_presence(
                    sid,
                    eid,
                    status,
                    _presence_comment_for_save(
                        pmap.get(eid),
                        status,
                        row["Observation"],
                    ),
                )
            st.success("Appel enregistré.")
            st.rerun()


def _render_suaps_rubric(st, qdf, exec_sql, session, students):
    sid = int(session["id"])
    activity = _clean(session.get("activite"))
    student_ids = [int(x) for x in students["id"].tolist()]
    student_id_set = set(student_ids)

    st.markdown("### 🎯 Barème SUAPS commun /20")
    c1, c2, c3 = st.columns(3)
    c1.metric("Projet / performance", "7 pts")
    c2.metric("Maîtrise / compétences", "7 pts")
    c3.metric("Assiduité / investissement / engagement", "6 pts")
    st.caption(
        "Même structure pour toutes les activités. Les valeurs proposées sont "
        "préremplies automatiquement et restent modifiables par l’enseignant."
    )

    evaluations = qdf(
        "SELECT * FROM evaluations WHERE activite=? ORDER BY id DESC",
        (activity,),
    )
    saved = {}
    ordinary_items = {eid: [] for eid in student_ids}
    seen = set()
    if not evaluations.empty:
        for _, row in evaluations.iterrows():
            eid = int(row["etudiant_id"])
            if eid not in student_id_set:
                continue
            title = _clean(row.get("intitule"))
            if title in SUAPS_RUBRIC_TITLES:
                if (eid, title) not in saved:
                    saved[(eid, title)] = row
                continue
            identity = (eid, _evaluation_identity(row))
            if identity not in seen:
                seen.add(identity)
                ordinary_items[eid].append(
                    (row.get("note"), row.get("bareme"), row.get("coefficient"))
                )

    performances = qdf(
        """
        SELECT id, etudiant_id, note_calculee
        FROM performances
        WHERE activite=?
        ORDER BY date_perf DESC, id DESC
        """,
        (activity,),
    )
    latest_perf = {}
    if not performances.empty:
        for _, row in performances.iterrows():
            eid = int(row["etudiant_id"])
            note20 = _float_or_none(row.get("note_calculee"))
            if eid in student_id_set and eid not in latest_perf and note20 is not None:
                latest_perf[eid] = note20

    comps = qdf(
        "SELECT id FROM competences WHERE activite=? ORDER BY id",
        (activity,),
    )
    comp_ids = [int(x) for x in comps["id"].tolist()] if not comps.empty else []
    acquisitions = qdf(
        """
        SELECT a.etudiant_id, a.competence_id, a.niveau
        FROM acquisitions a
        JOIN competences c ON c.id=a.competence_id
        WHERE c.activite=?
        """,
        (activity,),
    )
    acq_map = {}
    if not acquisitions.empty:
        for _, row in acquisitions.iterrows():
            acq_map[(int(row["etudiant_id"]), int(row["competence_id"]))] = _clean(
                row.get("niveau")
            )

    presences = qdf(
        """
        SELECT p.etudiant_id, p.statut
        FROM presences p
        JOIN seances s ON s.id=p.seance_id
        WHERE s.activite=?
        """,
        (activity,),
    )
    statuses = {eid: [] for eid in student_ids}
    if not presences.empty:
        for _, row in presences.iterrows():
            eid = int(row["etudiant_id"])
            if eid in student_id_set:
                statuses[eid].append(_clean(row.get("statut")))

    rows = []
    for _, student in students.iterrows():
        eid = int(student["id"])
        levels = [acq_map.get((eid, cid), "Non évalué") for cid in comp_ids]

        perf_default = _score_from_20(latest_perf.get(eid), 7.0)
        if perf_default is None:
            perf_default = _score_from_20(
                _weighted_average_20(ordinary_items[eid]),
                7.0,
            )
        comp_default = _competence_score_7(levels)
        engage_default = _attendance_score_6(statuses[eid])

        defaults = (perf_default, comp_default, engage_default)
        scores = []
        for (title, _, maximum), default in zip(SUAPS_RUBRIC_COMPONENTS, defaults):
            old = saved.get((eid, title))
            scores.append(
                _clamp_score(old.get("note"), maximum)
                if old is not None
                else default
            )

        rows.append(
            {
                "etudiant_id": eid,
                "Étudiant": f"{student['nom']} {student['prenom']}",
                "Projet / performance /7": scores[0],
                "Maîtrise / compétences /7": scores[1],
                "Assiduité / investissement / engagement /6": scores[2],
                "Total /20": _rubric_total_20(scores),
            }
        )

    frame = pd.DataFrame(rows)
    totals = pd.to_numeric(frame["Total /20"], errors="coerce").dropna()
    if len(totals):
        m1, m2, m3 = st.columns(3)
        m1.metric("Moyenne groupe", f"{totals.mean():.2f}/20")
        m2.metric("Plus basse", f"{totals.min():.2f}/20")
        m3.metric("Plus haute", f"{totals.max():.2f}/20")

    with st.form(f"suaps_rubric_form_{sid}_{activity}"):
        edited = st.data_editor(
            frame,
            hide_index=True,
            use_container_width=True,
            height=min(780, 42 + 36 * max(1, len(frame))),
            disabled=["etudiant_id", "Étudiant", "Total /20"],
            column_config={
                "etudiant_id": None,
                "Étudiant": st.column_config.TextColumn(
                    "Étudiant", width="medium", pinned=True
                ),
                "Projet / performance /7": st.column_config.NumberColumn(
                    "Projet / performance /7",
                    min_value=0.0, max_value=7.0, step=0.25, format="%.2f",
                ),
                "Maîtrise / compétences /7": st.column_config.NumberColumn(
                    "Maîtrise / compétences /7",
                    min_value=0.0, max_value=7.0, step=0.25, format="%.2f",
                ),
                "Assiduité / investissement / engagement /6": st.column_config.NumberColumn(
                    "Assiduité / investissement / engagement /6",
                    min_value=0.0, max_value=6.0, step=0.25, format="%.2f",
                ),
                "Total /20": st.column_config.NumberColumn(
                    "Total /20", min_value=0.0, max_value=20.0, format="%.2f",
                ),
            },
            key=f"suaps_rubric_grid_{sid}_{activity}",
        )
        save = st.form_submit_button(
            "💾 Enregistrer le barème SUAPS 7 + 7 + 6",
            type="primary",
            use_container_width=True,
        )

    if save:
        columns = (
            "Projet / performance /7",
            "Maîtrise / compétences /7",
            "Assiduité / investissement / engagement /6",
        )
        changes = 0
        today = str(_date.today())
        for _, row in edited.iterrows():
            eid = int(row["etudiant_id"])
            for column, (title, _, maximum) in zip(columns, SUAPS_RUBRIC_COMPONENTS):
                value = _clamp_score(row[column], maximum)
                if value is None:
                    continue
                old = saved.get((eid, title))
                old_value = _float_or_none(old.get("note")) if old is not None else None
                if not _note_changed(old_value, value):
                    continue
                if old is not None:
                    exec_sql(
                        """
                        UPDATE evaluations
                        SET note=?, bareme=?, coefficient=?, date_eval=?, commentaire=?
                        WHERE id=?
                        """,
                        (
                            value, maximum, 1.0, today,
                            "Barème SUAPS commun 7/7/6",
                            int(old["id"]),
                        ),
                    )
                else:
                    exec_sql(
                        """
                        INSERT INTO evaluations(
                            etudiant_id, activite, intitule, date_eval,
                            note, bareme, coefficient, commentaire
                        ) VALUES(?,?,?,?,?,?,?,?)
                        """,
                        (
                            eid, activity, title, today,
                            value, maximum, 1.0,
                            "Barème SUAPS commun 7/7/6",
                        ),
                    )
                changes += 1
        st.success(f"{changes} composante(s) du barème mise(s) à jour.")
        st.rerun()

    with st.expander("ℹ️ Suggestions automatiques"):
        st.markdown(
            """
- **Projet / performance /7** : dernière performance /20 convertie sur 7 ; à défaut, moyenne des évaluations convertie sur 7.
- **Maîtrise / compétences /7** : progression des niveaux Non évalué → En cours → Acquis → Maîtrisé.
- **Assiduité / investissement / engagement /6** : suggestion issue des présences ; les absences justifiées et dispenses sont neutres. L’enseignant ajuste la note pour l’investissement et l’engagement.
            """
        )


def _render_gradebook_class(st, qdf, exec_sql, session, students):
    sid = int(session["id"])
    activity = _clean(session.get("activite"))
    evaluations = qdf(
        """
        SELECT *
        FROM evaluations
        WHERE activite=?
        ORDER BY date_eval DESC, id DESC
        """,
        (activity,),
    )
    if not evaluations.empty:
        evaluations = evaluations[
            ~evaluations["intitule"].astype(str).isin(SUAPS_RUBRIC_TITLES)
        ].copy()
    if evaluations.empty:
        st.info(
            "Aucune évaluation classique pour cette activité. "
            "Le barème SUAPS 7/7/6 reste disponible dans son onglet."
        )
        return

    all_assessments = _gradebook_assessments(evaluations)
    total_assessments = len(all_assessments)
    count_options = sorted(
        {
            min(total_assessments, value)
            for value in (5, 8, 12)
            if min(total_assessments, value) > 0
        }
    )
    if total_assessments not in count_options:
        count_options.append(total_assessments)

    visible_count = st.selectbox(
        "Évaluations visibles",
        count_options,
        index=len(count_options) - 1 if total_assessments <= 8 else min(1, len(count_options) - 1),
        format_func=lambda value: (
            f"Toutes ({value})" if value == total_assessments else f"{value} dernières"
        ),
        key=f"gradebook_visible_count_{sid}_{activity}",
    )
    assessments = all_assessments[: int(visible_count)]

    student_ids = [int(x) for x in students["id"].tolist()]
    student_id_set = set(student_ids)

    ordered_evaluations = evaluations.sort_values("id", ascending=False, kind="stable")
    eval_map = {}
    for _, row in ordered_evaluations.iterrows():
        eid = int(row["etudiant_id"])
        if eid not in student_id_set:
            continue
        key = (eid, _evaluation_identity(row))
        if key not in eval_map:
            eval_map[key] = row

    all_eval_items = {eid: [] for eid in student_ids}
    seen_student_assessments = set()
    for _, row in ordered_evaluations.iterrows():
        eid = int(row["etudiant_id"])
        if eid not in student_id_set:
            continue
        identity = _evaluation_identity(row)
        unique_key = (eid, identity)
        if unique_key in seen_student_assessments:
            continue
        seen_student_assessments.add(unique_key)
        all_eval_items[eid].append(
            (
                row.get("note"),
                row.get("bareme"),
                row.get("coefficient"),
            )
        )

    performances = qdf(
        """
        SELECT id, etudiant_id, intitule, date_perf, valeur, unite, note_calculee
        FROM performances
        WHERE activite=?
        ORDER BY date_perf DESC, id DESC
        """,
        (activity,),
    )
    performance_map = {}
    if not performances.empty:
        for _, row in performances.iterrows():
            eid = int(row["etudiant_id"])
            if eid not in student_id_set or eid in performance_map:
                continue
            if _float_or_none(row.get("note_calculee")) is not None:
                performance_map[eid] = row

    comps = qdf(
        "SELECT id, code, libelle FROM competences WHERE activite=? ORDER BY code",
        (activity,),
    )
    acquisitions = qdf(
        """
        SELECT a.etudiant_id, a.competence_id, a.niveau
        FROM acquisitions a
        JOIN competences c ON c.id=a.competence_id
        WHERE c.activite=?
        """,
        (activity,),
    )
    total_competences = len(comps)
    acquired_count = {eid: 0 for eid in student_ids}
    if not acquisitions.empty:
        for _, row in acquisitions.iterrows():
            eid = int(row["etudiant_id"])
            if (
                eid in student_id_set
                and _clean(row.get("niveau")) in {"Acquis", "Maîtrisé"}
            ):
                acquired_count[eid] += 1

    table_rows = []
    for _, student in students.iterrows():
        eid = int(student["id"])
        item = {
            "etudiant_id": eid,
            "Étudiant": f"{student['nom']} {student['prenom']}",
        }
        for assessment in assessments:
            old = eval_map.get((eid, assessment["identity"]))
            item[assessment["column"]] = (
                _float_or_none(old.get("note")) if old is not None else None
            )
        item["Moyenne /20"] = _weighted_average_20(all_eval_items[eid])
        perf = performance_map.get(eid)
        item["Perf. /20"] = (
            _float_or_none(perf.get("note_calculee")) if perf is not None else None
        )
        item["Compétences %"] = (
            round((acquired_count[eid] / total_competences) * 100)
            if total_competences
            else None
        )
        table_rows.append(item)

    frame = pd.DataFrame(table_rows)

    averages = pd.to_numeric(frame["Moyenne /20"], errors="coerce").dropna()
    perf_values = pd.to_numeric(frame["Perf. /20"], errors="coerce").dropna()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Évaluations", total_assessments)
    c2.metric(
        "Moyenne groupe /20",
        f"{averages.mean():.2f}" if len(averages) else "—",
    )
    c3.metric(
        "Performance groupe /20",
        f"{perf_values.mean():.2f}" if len(perf_values) else "—",
    )
    comp_values = pd.to_numeric(frame["Compétences %"], errors="coerce").dropna()
    c4.metric(
        "Compétences acquises",
        f"{comp_values.mean():.0f}%" if len(comp_values) else "—",
    )

    st.caption(
        "La moyenne /20 tient compte de toutes les évaluations de l’activité "
        "et de leurs coefficients. Les colonnes affichent les évaluations les plus récentes."
    )

    config = {
        "etudiant_id": None,
        "Étudiant": st.column_config.TextColumn(
            "Étudiant", width="medium", pinned=True
        ),
        "Moyenne /20": st.column_config.NumberColumn(
            "Moy. /20", format="%.2f", width="small"
        ),
        "Perf. /20": st.column_config.NumberColumn(
            "Perf. /20", format="%.2f", width="small"
        ),
        "Compétences %": st.column_config.ProgressColumn(
            "Comp. %",
            min_value=0,
            max_value=100,
            format="%d%%",
            width="small",
        ),
    }
    for assessment in assessments:
        date_label = assessment["date_eval"]
        if len(date_label) >= 10:
            date_label = f"{date_label[8:10]}/{date_label[5:7]}"
        config[assessment["column"]] = st.column_config.NumberColumn(
            f"{date_label} • {assessment['intitule']}",
            help=(
                f"Barème : /{assessment['bareme']:g} • "
                f"Coefficient : {assessment['coefficient']:g}"
            ),
            min_value=0.0,
            max_value=float(assessment["bareme"]),
            step=0.25,
            format="%.2f",
            width="small",
        )

    disabled = [
        "etudiant_id",
        "Étudiant",
        "Moyenne /20",
        "Perf. /20",
        "Compétences %",
    ]

    with st.form(f"gradebook_class_form_{sid}_{activity}"):
        edited = st.data_editor(
            frame,
            hide_index=True,
            use_container_width=True,
            height=min(780, 42 + 36 * max(1, len(frame))),
            disabled=disabled,
            column_config=config,
            key=f"gradebook_class_grid_{sid}_{activity}_{visible_count}",
        )
        save = st.form_submit_button(
            "💾 Enregistrer le cahier de notes",
            type="primary",
            use_container_width=True,
        )

    if save:
        changes = 0
        for _, row in edited.iterrows():
            eid = int(row["etudiant_id"])
            for assessment in assessments:
                col = assessment["column"]
                new_note = _float_or_none(row[col])
                old = eval_map.get((eid, assessment["identity"]))
                old_note = (
                    _float_or_none(old.get("note")) if old is not None else None
                )
                if not _note_changed(old_note, new_note):
                    continue
                if old is not None:
                    exec_sql(
                        "UPDATE evaluations SET note=? WHERE id=?",
                        (new_note, int(old["id"])),
                    )
                elif new_note is not None:
                    exec_sql(
                        """
                        INSERT INTO evaluations(
                            etudiant_id, activite, intitule, date_eval,
                            note, bareme, coefficient, commentaire
                        ) VALUES(?,?,?,?,?,?,?,?)
                        """,
                        (
                            eid,
                            activity,
                            assessment["intitule"],
                            assessment["date_eval"],
                            new_note,
                            float(assessment["bareme"]),
                            float(assessment["coefficient"]),
                            "",
                        ),
                    )
                changes += 1
        st.success(f"{changes} note(s) mise(s) à jour.")
        st.rerun()

    st.markdown("#### 🔗 Lecture croisée étudiant")
    focus_eid = st.selectbox(
        "Étudiant à examiner",
        student_ids,
        format_func=lambda value: next(
            (
                f"{r['nom']} {r['prenom']}"
                for _, r in students.iterrows()
                if int(r["id"]) == int(value)
            ),
            str(value),
        ),
        key=f"gradebook_focus_{sid}_{activity}",
    )

    focus_average = _weighted_average_20(all_eval_items.get(int(focus_eid), []))
    focus_perf = performance_map.get(int(focus_eid))
    focus_perf_note = (
        _float_or_none(focus_perf.get("note_calculee"))
        if focus_perf is not None
        else None
    )
    focus_comp = (
        round((acquired_count[int(focus_eid)] / total_competences) * 100)
        if total_competences
        else None
    )

    f1, f2, f3 = st.columns(3)
    f1.metric(
        "Notes",
        f"{focus_average:.2f}/20" if focus_average is not None else "—",
    )
    f2.metric(
        "Performance",
        f"{focus_perf_note:.2f}/20" if focus_perf_note is not None else "—",
    )
    f3.metric(
        "Compétences",
        f"{focus_comp}%" if focus_comp is not None else "—",
    )
    if focus_perf is not None:
        detail = (
            f"Dernière performance : {_clean(focus_perf.get('intitule'))}"
            f" • {_clean(focus_perf.get('date_perf'))}"
        )
        value = _float_or_none(focus_perf.get("valeur"))
        unit = _clean(focus_perf.get("unite"))
        if value is not None:
            detail += f" • {value:g} {unit}".rstrip()
        st.caption(detail)

    if st.button(
        "👤 Préparer la fiche étudiant",
        key=f"gradebook_open_student_{sid}_{activity}",
        use_container_width=True,
    ):
        st.session_state[f"workbook_student_card_{sid}"] = int(focus_eid)
        st.success(
            "Étudiant sélectionné. Ouvre l’onglet « Fiche étudiant » "
            "pour retrouver son historique complet."
        )


def _render_single_evaluation(st, qdf, exec_sql, session, students):
    sid = int(session["id"])
    activity = _clean(session.get("activite"))
    session_date = _clean(session.get("date_seance"))
    default_title = _clean(session.get("theme")) or f"Évaluation du {session_date}"

    c1, c2, c3 = st.columns([2.4, 1, 1])
    title = c1.text_input(
        "Évaluation",
        value=default_title,
        key=f"workbook_eval_title_{sid}",
    ).strip() or default_title
    bareme = c2.number_input(
        "Barème",
        min_value=1.0,
        value=20.0,
        step=1.0,
        key=f"workbook_bareme_{sid}",
    )
    coefficient = c3.number_input(
        "Coefficient",
        min_value=0.1,
        value=1.0,
        step=0.1,
        key=f"workbook_coef_{sid}",
    )

    evaluations = qdf(
        """
        SELECT *
        FROM evaluations
        WHERE activite=? AND intitule=? AND date_eval=?
        ORDER BY id DESC
        """,
        (activity, title, session_date),
    )
    emap = {}
    for _, row in evaluations.iterrows():
        eid = int(row["etudiant_id"])
        if eid not in emap:
            emap[eid] = row

    table_rows = []
    for _, student in students.iterrows():
        eid = int(student["id"])
        old = emap.get(eid)
        note = None
        comment = ""
        if old is not None:
            if not pd.isna(old["note"]):
                note = float(old["note"])
            comment = _clean(old.get("commentaire"))
        table_rows.append(
            {
                "etudiant_id": eid,
                "Étudiant": f"{student['nom']} {student['prenom']}",
                "Note": note,
                "Observation": comment,
            }
        )

    frame = pd.DataFrame(table_rows)
    valid_notes = pd.to_numeric(frame["Note"], errors="coerce").dropna()
    completion = len(valid_notes) / len(frame) if len(frame) else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Saisies", f"{len(valid_notes)}/{len(frame)}")
    m2.metric(
        "Moyenne",
        f"{valid_notes.mean():.2f}/{float(bareme):g}" if len(valid_notes) else "—",
    )
    m3.metric(
        "Plus basse",
        f"{valid_notes.min():.2f}" if len(valid_notes) else "—",
    )
    m4.metric(
        "Plus haute",
        f"{valid_notes.max():.2f}" if len(valid_notes) else "—",
    )
    st.progress(min(1.0, completion))

    with st.form(f"workbook_notes_form_{sid}"):
        edited = st.data_editor(
            frame,
            hide_index=True,
            use_container_width=True,
            height=min(760, 42 + 36 * max(1, len(frame))),
            disabled=["etudiant_id", "Étudiant"],
            column_config={
                "etudiant_id": None,
                "Étudiant": st.column_config.TextColumn(
                    "Étudiant", width="medium", pinned=True
                ),
                "Note": st.column_config.NumberColumn(
                    f"Note / {float(bareme):g}",
                    min_value=0.0,
                    max_value=float(bareme),
                    step=0.25,
                    width="small",
                ),
                "Observation": st.column_config.TextColumn(
                    "Observation", width="large"
                ),
            },
            key=f"workbook_notes_grid_{sid}",
        )
        save = st.form_submit_button(
            "💾 Enregistrer les notes",
            type="primary",
            use_container_width=True,
        )

    if save:
        for _, row in edited.iterrows():
            raw_note = row["Note"]
            if pd.isna(raw_note):
                continue
            eid = int(row["etudiant_id"])
            note = float(raw_note)
            comment = _clean(row["Observation"])
            old = emap.get(eid)
            if old is not None:
                exec_sql(
                    """
                    UPDATE evaluations
                    SET note=?, bareme=?, coefficient=?, commentaire=?
                    WHERE id=?
                    """,
                    (
                        note,
                        float(bareme),
                        float(coefficient),
                        comment,
                        int(old["id"]),
                    ),
                )
            else:
                exec_sql(
                    """
                    INSERT INTO evaluations(
                        etudiant_id, activite, intitule, date_eval,
                        note, bareme, coefficient, commentaire
                    ) VALUES(?,?,?,?,?,?,?,?)
                    """,
                    (
                        eid,
                        activity,
                        title,
                        session_date,
                        note,
                        float(bareme),
                        float(coefficient),
                        comment,
                    ),
                )
        st.success("Notes enregistrées.")
        st.rerun()


def _render_notes(st, qdf, exec_sql, session, students):
    tab_rubric, tab_class, tab_single = st.tabs(
        ["🎯 Barème SUAPS 7/7/6", "📊 Vue classe", "✍️ Saisie évaluation"]
    )
    with tab_rubric:
        _render_suaps_rubric(st, qdf, exec_sql, session, students)
    with tab_class:
        _render_gradebook_class(st, qdf, exec_sql, session, students)
    with tab_single:
        _render_single_evaluation(st, qdf, exec_sql, session, students)


def _render_competences(st, qdf, upsert_acquisition, session, students):
    activity_rows = qdf(
        "SELECT DISTINCT activite FROM competences ORDER BY activite"
    )
    activities = (
        activity_rows["activite"].dropna().astype(str).tolist()
        if not activity_rows.empty
        else []
    )
    if not activities:
        st.info("Aucune compétence n’est encore définie.")
        return

    session_activity = _clean(session.get("activite"))
    default_index = activities.index(session_activity) if session_activity in activities else 0
    activity = st.selectbox(
        "Activité évaluée",
        activities,
        index=default_index,
        key=f"workbook_comp_activity_{int(session['id'])}",
    )

    comps = qdf(
        "SELECT id, code, libelle FROM competences WHERE activite=? ORDER BY code",
        (activity,),
    )
    if comps.empty:
        st.info("Aucune compétence pour cette activité.")
        return

    ids = [int(x) for x in students["id"].tolist()]
    if not ids:
        st.info("Aucun étudiant dans ce groupe.")
        return

    acquisitions = qdf(
        """
        SELECT a.etudiant_id, a.competence_id, a.niveau, a.commentaire
        FROM acquisitions a
        JOIN competences c ON c.id=a.competence_id
        WHERE c.activite=?
        """,
        (activity,),
    )
    amap = {
        (int(row["etudiant_id"]), int(row["competence_id"])): row
        for _, row in acquisitions.iterrows()
        if int(row["etudiant_id"]) in ids
    }

    code_to_id = {
        str(row["code"]): int(row["id"])
        for _, row in comps.iterrows()
    }
    labels = {
        str(row["code"]): str(row["libelle"])
        for _, row in comps.iterrows()
    }

    matrix_rows = []
    for _, student in students.iterrows():
        eid = int(student["id"])
        item = {
            "etudiant_id": eid,
            "Étudiant": f"{student['nom']} {student['prenom']}",
        }
        for code, cid in code_to_id.items():
            old = amap.get((eid, cid))
            level = _clean(old.get("niveau")) if old is not None else "Non évalué"
            if level not in COMPETENCE_LEVELS:
                level = "Non évalué"
            item[code] = level
        matrix_rows.append(item)

    matrix = pd.DataFrame(matrix_rows)

    flat_levels = []
    for code in code_to_id:
        flat_levels.extend(matrix[code].tolist())
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("⚪ Non évalué", flat_levels.count("Non évalué"))
    k2.metric("🟠 En cours", flat_levels.count("En cours d’acquisition"))
    k3.metric("🟢 Acquis", flat_levels.count("Acquis"))
    k4.metric("🔵 Maîtrisé", flat_levels.count("Maîtrisé"))

    config = {
        "etudiant_id": None,
        "Étudiant": st.column_config.TextColumn(
            "Étudiant", width="medium", pinned=True
        ),
    }
    for code in code_to_id:
        config[code] = st.column_config.SelectboxColumn(
            code,
            help=labels[code],
            options=COMPETENCE_LEVELS,
            required=True,
            width="small",
        )

    st.caption(
        "Chaque colonne correspond à une compétence. "
        "Touchez une cellule pour changer rapidement son niveau."
    )

    with st.form(f"workbook_comp_grid_form_{int(session['id'])}_{activity}"):
        edited = st.data_editor(
            matrix,
            hide_index=True,
            use_container_width=True,
            height=min(780, 42 + 36 * max(1, len(matrix))),
            disabled=["etudiant_id", "Étudiant"],
            column_config=config,
            key=f"workbook_comp_grid_{int(session['id'])}_{activity}",
        )
        save = st.form_submit_button(
            "💾 Enregistrer la grille de compétences",
            type="primary",
            use_container_width=True,
        )

    if save:
        changes = 0
        for _, row in edited.iterrows():
            eid = int(row["etudiant_id"])
            for code, cid in code_to_id.items():
                new_level = _clean(row[code]) or "Non évalué"
                old = amap.get((eid, cid))
                old_level = _clean(old.get("niveau")) if old is not None else "Non évalué"
                if new_level == old_level:
                    continue
                old_comment = _clean(old.get("commentaire")) if old is not None else ""
                validation_date = (
                    str(_date.today())
                    if new_level in {"Acquis", "Maîtrisé"}
                    else None
                )
                upsert_acquisition(
                    eid,
                    cid,
                    new_level,
                    validation_date,
                    old_comment,
                )
                changes += 1
        st.success(f"{changes} niveau(x) de compétence mis à jour.")
        st.rerun()

    with st.expander("👁️ Vue synthétique", expanded=False):
        visual = matrix.drop(columns=["etudiant_id"]).copy()
        for code in code_to_id:
            visual[code] = visual[code].map(_competence_display)
        st.caption("⚪ Non évalué • 🟠 En cours • 🟢 Acquis • 🔵 Maîtrisé")
        st.dataframe(
            visual,
            hide_index=True,
            use_container_width=True,
            height=min(680, 42 + 36 * max(1, len(visual))),
        )

    st.markdown("#### Action de groupe")
    c1, c2, c3 = st.columns([2, 1.4, 2])
    chosen_code = c1.selectbox(
        "Compétence",
        list(code_to_id.keys()),
        format_func=lambda code: f"{code} — {labels[code]}",
        key=f"workbook_bulk_comp_{activity}",
    )
    bulk_level = c2.selectbox(
        "Niveau",
        COMPETENCE_LEVELS[1:],
        key=f"workbook_bulk_level_{activity}",
    )
    selected_ids = c3.multiselect(
        "Étudiants",
        options=ids,
        format_func=lambda eid: next(
            (
                f"{r['nom']} {r['prenom']}"
                for _, r in students.iterrows()
                if int(r["id"]) == int(eid)
            ),
            str(eid),
        ),
        key=f"workbook_bulk_students_{activity}",
    )
    if st.button(
        "Appliquer aux étudiants sélectionnés",
        key=f"workbook_bulk_apply_{activity}",
        use_container_width=True,
    ):
        cid = code_to_id[chosen_code]
        validation_date = (
            str(_date.today()) if bulk_level in {"Acquis", "Maîtrisé"} else None
        )
        for eid in selected_ids:
            old = amap.get((int(eid), cid))
            old_comment = _clean(old.get("commentaire")) if old is not None else ""
            upsert_acquisition(
                int(eid),
                int(cid),
                bulk_level,
                validation_date,
                old_comment,
            )
        st.success(f"{len(selected_ids)} étudiant(s) mis à jour.")
        st.rerun()

    progress_rows = []
    for _, student in students.iterrows():
        eid = int(student["id"])
        levels = []
        for cid in code_to_id.values():
            old = amap.get((eid, cid))
            levels.append(_clean(old.get("niveau")) if old is not None else "Non évalué")
        acquired = sum(level in {"Acquis", "Maîtrisé"} for level in levels)
        progress_rows.append(
            {
                "Étudiant": f"{student['nom']} {student['prenom']}",
                "Validées": acquired,
                "Total": len(code_to_id),
                "Progression": round((acquired / len(code_to_id)) * 100) if code_to_id else 0,
            }
        )
    st.markdown("#### Progression du groupe")
    st.dataframe(
        pd.DataFrame(progress_rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Progression": st.column_config.ProgressColumn(
                "Progression",
                min_value=0,
                max_value=100,
                format="%d%%",
            )
        },
    )


def _render_student_card(st, qdf, session, students):
    if students.empty:
        return
    student_ids = [int(x) for x in students["id"].tolist()]
    labels = {
        int(row["id"]): f"{row['nom']} {row['prenom']}"
        for _, row in students.iterrows()
    }
    eid = st.selectbox(
        "Étudiant",
        student_ids,
        format_func=lambda value: labels[value],
        key=f"workbook_student_card_{int(session['id'])}",
    )
    student = students[students["id"] == eid].iloc[0]

    st.markdown(f"### 👤 {student['nom']} {student['prenom']}")
    st.caption(
        f"N° {_clean(student.get('numero_etudiant')) or '—'} • "
        f"Groupe : {_clean(student.get('groupe')) or '—'}"
    )

    pres = qdf(
        """
        SELECT s.date_seance, s.activite, s.theme, p.statut
        FROM presences p
        JOIN seances s ON s.id=p.seance_id
        WHERE p.etudiant_id=?
        ORDER BY s.date_seance DESC, s.id DESC
        """,
        (eid,),
    )
    evals = qdf(
        """
        SELECT activite, intitule, date_eval, note, bareme, coefficient, commentaire
        FROM evaluations
        WHERE etudiant_id=?
        ORDER BY date_eval DESC, id DESC
        """,
        (eid,),
    )
    acq = qdf(
        """
        SELECT c.activite, c.code, c.libelle,
               COALESCE(a.niveau,'Non évalué') AS niveau
        FROM competences c
        LEFT JOIN acquisitions a
          ON a.competence_id=c.id AND a.etudiant_id=?
        ORDER BY c.activite, c.code
        """,
        (eid,),
    )

    attendance_rate = None
    if not pres.empty:
        attendance_rate = round(float(pres["statut"].eq("Présent").mean()) * 100)

    weighted_average = None
    suaps_total = None
    if not evals.empty:
        session_activity = _clean(session.get("activite"))
        rubric_values = []
        for title, _, _ in SUAPS_RUBRIC_COMPONENTS:
            rows = evals[
                (evals["activite"].astype(str) == session_activity)
                & (evals["intitule"].astype(str) == title)
            ]
            rubric_values.append(
                _float_or_none(rows.iloc[0]["note"]) if not rows.empty else None
            )
        suaps_total = _rubric_total_20(rubric_values)

        valid = evals[
            ~evals["intitule"].astype(str).isin(SUAPS_RUBRIC_TITLES)
        ].dropna(subset=["note", "bareme", "coefficient"]).copy()
        valid = valid[valid["bareme"].astype(float) > 0]
        if not valid.empty and float(valid["coefficient"].astype(float).sum()) > 0:
            normalized = (
                valid["note"].astype(float)
                / valid["bareme"].astype(float)
                * 20.0
            )
            weights = valid["coefficient"].astype(float)
            weighted_average = float((normalized * weights).sum() / weights.sum())

    competence_rate = None
    if not acq.empty:
        session_activity = _clean(session.get("activite"))
        activity_acq = acq[acq["activite"].astype(str) == session_activity]
        metric_source = activity_acq if not activity_acq.empty else acq
        competence_rate = round(
            float(metric_source["niveau"].isin(["Acquis", "Maîtrisé"]).mean()) * 100
        )

    c1, c2, c3 = st.columns(3)
    c1.metric("Présence", f"{attendance_rate}%" if attendance_rate is not None else "—")
    c2.metric(
        "Note SUAPS /20" if suaps_total is not None else "Moyenne /20",
        f"{suaps_total:.2f}"
        if suaps_total is not None
        else (f"{weighted_average:.2f}" if weighted_average is not None else "—"),
    )
    c3.metric("Compétences validées", f"{competence_rate}%" if competence_rate is not None else "—")

    st.markdown("#### Dernières évaluations")
    if evals.empty:
        st.info("Aucune évaluation.")
    else:
        display_evals = evals.head(8).copy()
        display_evals["note_sur_20"] = (
            display_evals["note"].astype(float)
            / display_evals["bareme"].astype(float)
            * 20.0
        ).round(2)
        st.dataframe(
            display_evals[
                ["date_eval", "activite", "intitule", "note", "bareme", "note_sur_20", "commentaire"]
            ],
            hide_index=True,
            use_container_width=True,
        )

    st.markdown("#### Compétences")
    if acq.empty:
        st.info("Aucune compétence.")
    else:
        display_acq = acq.copy()
        display_acq["Niveau"] = display_acq["niveau"].map(_competence_display)
        st.dataframe(
            display_acq[["activite", "code", "libelle", "Niveau"]],
            hide_index=True,
            use_container_width=True,
        )

    st.markdown("#### Présences récentes")
    if pres.empty:
        st.info("Aucune présence.")
    else:
        display_pres = pres.head(10).copy()
        display_pres["Présence"] = display_pres["statut"].map(_attendance_display)
        st.dataframe(
            display_pres[["date_seance", "activite", "theme", "Présence"]],
            hide_index=True,
            use_container_width=True,
        )


def render_teacher_workbook(
    st,
    qdf,
    exec_sql,
    upsert_presence,
    upsert_acquisition,
):
    """Rend le carnet enseignant sans modifier le schéma historique."""
    st.markdown("## 📘 Carnet enseignant")
    st.caption(
        "Appel, notes et compétences dans une même vue • optimisé smartphone et tablette"
    )

    st.markdown(
        """
        <style>
        div[data-testid="stDataFrame"] {border-radius:14px; overflow:hidden;}
        div[data-testid="stDataEditor"] {border-radius:14px; overflow:hidden;}
        [data-testid="stMetric"] {
          border:1px solid rgba(12,60,120,.10);
          border-radius:14px;
          padding:10px;
          background:rgba(255,255,255,.68);
        }
        @media (max-width: 768px){
          div[data-testid="stDataEditor"] {font-size:.92rem;}
          [data-testid="stMetricValue"] {font-size:1.25rem;}
          .stButton button {
            min-height:52px;
            font-weight:700;
            border-radius:14px;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _render_workbook_quick_actions(st, qdf, exec_sql)

    sessions = qdf(
        "SELECT * FROM seances ORDER BY date_seance DESC, id DESC"
    )
    if sessions.empty:
        st.info("Crée d’abord une séance dans le menu Présences.")
        return

    activities = ["Toutes"] + sorted(
        {
            _clean(value)
            for value in sessions["activite"].tolist()
            if _clean(value)
        }
    )
    f1, f2 = st.columns([1, 2])
    activity_filter = f1.selectbox(
        "Filtrer par activité",
        activities,
        key="workbook_activity_filter",
    )
    filtered = sessions
    if activity_filter != "Toutes":
        filtered = sessions[sessions["activite"].astype(str) == activity_filter]

    session_ids = [int(x) for x in filtered["id"].tolist()]
    label_map = {}
    for _, row in filtered.iterrows():
        sid = int(row["id"])
        label_map[sid] = (
            f"{_clean(row['date_seance'])} — {_clean(row['activite'])} — "
            f"{_clean(row.get('groupe')) or 'Tous'} — {_clean(row.get('theme')) or 'Séance'}"
        )

    sid = f2.selectbox(
        "Séance",
        session_ids,
        format_func=lambda value: label_map[value],
        key="workbook_session",
    )
    session = filtered[filtered["id"] == sid].iloc[0]

    _render_add_student_to_session(st, qdf, exec_sql, session)
    students = _students_for_session(qdf, session)
    if students.empty:
        st.warning(
            "Aucun étudiant actif n’est rattaché à cette séance. "
            "Utilise « Ajouter un étudiant à ce créneau » ci-dessus."
        )
        return

    _render_header(st, session, students)

    tab_att, tab_notes, tab_comp, tab_student = st.tabs(
        ["✅ Appel", "📝 Notes", "🎯 Compétences", "👤 Fiche étudiant"]
    )
    with tab_att:
        _render_attendance(st, qdf, upsert_presence, session, students)
    with tab_notes:
        _render_notes(st, qdf, exec_sql, session, students)
    with tab_comp:
        _render_competences(st, qdf, upsert_acquisition, session, students)
    with tab_student:
        _render_student_card(st, qdf, session, students)

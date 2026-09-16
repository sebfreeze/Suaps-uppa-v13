from datetime import date
from pathlib import Path

import streamlit as st

from presence_note_service import (
    COMBINED_MENU_LABEL,
    evaluation_title,
    inject_combined_navigation,
    save_rows,
)


COMPETITION_MENU_LABEL = "Compétition"


# Conserve l'application V13 intacte et ajoute seulement les entrées complémentaires
# dans la navigation enseignant.
_original_sidebar_radio = st.sidebar.radio


def _inject_competition_navigation(options):
    original_is_tuple = isinstance(options, tuple)
    items = list(options)

    # La navigation étudiant ne contient que Accueil / Portail étudiant :
    # on ne lui ajoute pas la rubrique de gestion des compétitions.
    teacher_navigation = any(
        marker in items
        for marker in ("Tableau de bord", "Étudiants", "Présences", "Cahier de notes")
    )
    if not teacher_navigation or COMPETITION_MENU_LABEL in items:
        return options

    if "Compétences" in items:
        items.insert(items.index("Compétences"), COMPETITION_MENU_LABEL)
    elif "Exports" in items:
        items.insert(items.index("Exports"), COMPETITION_MENU_LABEL)
    else:
        items.append(COMPETITION_MENU_LABEL)

    return tuple(items) if original_is_tuple else items


def _sidebar_radio_with_additions(label, options, *args, **kwargs):
    if label == "Navigation":
        options = inject_combined_navigation(options)
        options = _inject_competition_navigation(options)
    return _original_sidebar_radio(label, options, *args, **kwargs)


st.sidebar.radio = _sidebar_radio_with_additions
try:
    legacy_path = Path(__file__).with_name("app_legacy.py")
    legacy_code = legacy_path.read_text(encoding="utf-8")
    exec(compile(legacy_code, str(legacy_path), "exec"), globals(), globals())
finally:
    st.sidebar.radio = _original_sidebar_radio


def _competition_sql(sql):
    """Adapte le module Compétition historique au schéma V13 actuel."""
    adapted = sql.replace("utilisateurs", "etudiants")
    adapted = adapted.replace("profil='Étudiant' AND ", "")
    if globals().get("USE_POSTGRES"):
        adapted = adapted.replace(" BLOB", " BYTEA")
    return adapted


def _competition_rows(sql, params=()):
    frame = qdf(_competition_sql(sql), params)
    return frame.to_dict(orient="records")


def _competition_one(sql, params=()):
    data = _competition_rows(sql, params)
    return data[0] if data else None


def _competition_exec(sql, params=()):
    return exec_sql(_competition_sql(sql), params)


def _render_competition():
    from sports_co_module import init_sports_co_db, render_sports_co

    st.markdown("## 🏆 Compétition")
    st.caption(
        "Sports collectifs • Badminton • Pelote Basque • équipes • matchs • tournois"
    )
    st.link_button(
        "🔗 My Sport U — compte, licence et compétitions",
        "https://sport-u.com/mysportu/",
        use_container_width=True,
    )

    init_sports_co_db(_competition_exec)
    render_sports_co(
        st,
        _competition_rows,
        _competition_one,
        _competition_exec,
        date,
    )


def _teacher_observation(presence_row, evaluation_row):
    if evaluation_row is not None:
        value = evaluation_row.get("commentaire")
        if value:
            return str(value)
    if presence_row is None:
        return ""
    value = presence_row.get("commentaire")
    if not value:
        return ""
    value = str(value)
    if value in {"Auto-validation QR/NFC", "Appel manuel smartphone"}:
        return ""
    return value


def _render_presence_note_evaluation():
    st.subheader(COMBINED_MENU_LABEL)
    st.caption(
        "Présence, note et observation sur la même feuille. "
        "Les présences validées par QR code sont reprises automatiquement."
    )

    sessions = qdf("SELECT * FROM seances ORDER BY date_seance DESC, id DESC")
    if sessions.empty:
        st.info("Crée d’abord une séance dans le menu Présences.")
        return

    labels = {
        int(row["id"]): (
            f'{row["date_seance"]} — {row["activite"]} — '
            f'{row["groupe"] or "Tous"} — {row["theme"] or ""}'
        )
        for _, row in sessions.iterrows()
    }
    sid = st.selectbox(
        "Séance",
        list(labels.keys()),
        format_func=lambda value: labels[value],
        key="combined_presence_note_session",
    )
    session = sessions[sessions.id == sid].iloc[0]
    activity = str(session["activite"])
    date_eval = str(session["date_seance"])
    group = session["groupe"] or ""

    c1, c2, c3 = st.columns([2.5, 1, 1])
    title = c1.text_input(
        "Évaluation",
        value=evaluation_title(session["theme"], date_eval),
        key=f"combined_title_{sid}",
    ).strip()
    bareme = c2.number_input(
        "Barème",
        min_value=1.0,
        value=20.0,
        step=1.0,
        key=f"combined_bareme_{sid}",
    )
    coefficient = c3.number_input(
        "Coefficient",
        min_value=0.1,
        value=1.0,
        step=0.1,
        key=f"combined_coeff_{sid}",
    )
    title = evaluation_title(title, date_eval)

    if group:
        students = qdf(
            "SELECT * FROM etudiants WHERE actif=1 AND groupe=? ORDER BY nom, prenom",
            (group,),
        )
    else:
        students = qdf("SELECT * FROM etudiants WHERE actif=1 ORDER BY nom, prenom")

    if students.empty:
        st.warning("Aucun étudiant n’est rattaché à cette séance.")
        return

    presences = qdf("SELECT * FROM presences WHERE seance_id=?", (sid,))
    presence_map = {
        int(row["etudiant_id"]): row
        for _, row in presences.iterrows()
    }

    evaluations = qdf(
        """
        SELECT *
        FROM evaluations
        WHERE activite=? AND intitule=? AND date_eval=?
        ORDER BY id DESC
        """,
        (activity, title, date_eval),
    )
    evaluation_map = {}
    for _, row in evaluations.iterrows():
        student_id = int(row["etudiant_id"])
        if student_id not in evaluation_map:
            evaluation_map[student_id] = row

    st.caption(
        f"{len(students)} étudiant(s) • {activity} • "
        f"{group or 'tous les groupes'} • note sur {bareme:g}"
    )

    statuses = ["Présent", "Absent", "Justifié", "Dispensé"]
    with st.form(f"combined_presence_note_form_{sid}"):
        h1, h2, h3, h4 = st.columns([2.2, 1.3, 1, 2.8])
        h1.markdown("**Étudiant**")
        h2.markdown("**Présence**")
        h3.markdown("**Note**")
        h4.markdown("**Observation**")

        rows = []
        invalid_note = False
        for _, student in students.iterrows():
            student_id = int(student["id"])
            old_presence = presence_map.get(student_id)
            old_evaluation = evaluation_map.get(student_id)

            old_status = (
                str(old_presence["statut"])
                if old_presence is not None
                else "Présent"
            )
            if old_status not in statuses:
                old_status = "Présent"

            old_note = None
            if old_evaluation is not None and not pd.isna(old_evaluation["note"]):
                old_note = float(old_evaluation["note"])

            old_observation = _teacher_observation(old_presence, old_evaluation)

            c_name, c_status, c_note, c_obs = st.columns([2.2, 1.3, 1, 2.8])
            c_name.markdown(f'**{student["nom"]} {student["prenom"]}**')
            if student["numero_etudiant"]:
                c_name.caption(f'N° {student["numero_etudiant"]}')

            status = c_status.selectbox(
                "Présence",
                statuses,
                index=statuses.index(old_status),
                key=f"combined_status_{sid}_{student_id}",
                label_visibility="collapsed",
            )
            note = c_note.number_input(
                "Note",
                min_value=0.0,
                value=old_note,
                step=0.25,
                key=f"combined_note_{sid}_{student_id}",
                label_visibility="collapsed",
                placeholder="—",
            )
            observation = c_obs.text_input(
                "Observation",
                value=old_observation,
                key=f"combined_obs_{sid}_{student_id}",
                label_visibility="collapsed",
                placeholder="Observation facultative",
            )

            if note is not None and float(note) > float(bareme):
                invalid_note = True

            rows.append(
                {
                    "student_id": student_id,
                    "status": status,
                    "note": note,
                    "observation": observation,
                }
            )

        save = st.form_submit_button(
            "💾 Enregistrer la séance",
            type="primary",
            use_container_width=True,
        )

    if save:
        if invalid_note:
            st.error(f"Une note dépasse le barème de {bareme:g}. Corrige-la avant d’enregistrer.")
            return

        conn = get_conn()
        try:
            save_rows(
                conn,
                session_id=int(sid),
                activity=activity,
                date_eval=date_eval,
                title=title,
                bareme=float(bareme),
                coefficient=float(coefficient),
                rows=rows,
            )
        finally:
            conn.close()

        st.success("Présences, notes et observations enregistrées.")
        st.rerun()


if globals().get("menu") == COMPETITION_MENU_LABEL:
    if st.session_state.get("role") == "Enseignant":
        _render_competition()
    else:
        st.error("Cette page est réservée aux enseignants.")
elif globals().get("menu") == COMBINED_MENU_LABEL:
    if st.session_state.get("role") == "Enseignant":
        _render_presence_note_evaluation()
    else:
        st.error("Cette page est réservée aux enseignants.")

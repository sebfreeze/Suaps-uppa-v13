"""Carnet enseignant SUAPS : appel, notes et compétences dans un écran compact.

Le module ajoute une vue de travail inspirée des carnets de classe numériques :
tableaux éditables, actions de groupe, synthèses immédiates et fiche étudiant.
Il réutilise le schéma V13 existant afin de ne pas casser les données historiques.
"""

from datetime import date as _date

import pandas as pd


WORKBOOK_MENU_LABEL = "📘 Carnet enseignant"
ATTENDANCE_STATUSES = ["Présent", "Absent", "Justifié", "Dispensé"]
COMPETENCE_LEVELS = [
    "Non évalué",
    "En cours d’acquisition",
    "Acquis",
    "Maîtrisé",
]


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
    group = _clean(session.get("groupe"))
    if group:
        return qdf(
            "SELECT id, nom, prenom, numero_etudiant, groupe "
            "FROM etudiants WHERE actif=1 AND groupe=? ORDER BY nom, prenom",
            (group,),
        )
    return qdf(
        "SELECT id, nom, prenom, numero_etudiant, groupe "
        "FROM etudiants WHERE actif=1 ORDER BY nom, prenom"
    )


def _attendance_source(row):
    if row is None:
        return "—"
    comment = _clean(row.get("commentaire"))
    if "QR" in comment.upper() or "NFC" in comment.upper():
        return "QR/NFC"
    return "Manuel"


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
        if _clean(row.get("statut"))
    ]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Présents", current_statuses.count("Présent"))
    c2.metric("Absents", current_statuses.count("Absent"))
    c3.metric("Justifiés", current_statuses.count("Justifié"))
    c4.metric("Dispensés", current_statuses.count("Dispensé"))

    b1, b2 = st.columns(2)
    if b1.button(
        "✅ Tous présents",
        key=f"workbook_all_present_{sid}",
        use_container_width=True,
        type="primary",
    ):
        for _, student in students.iterrows():
            upsert_presence(
                sid,
                int(student["id"]),
                "Présent",
                "Appel manuel — Carnet enseignant",
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

    table_rows = []
    for _, student in students.iterrows():
        eid = int(student["id"])
        old = pmap.get(eid)
        status = _clean(old.get("statut")) if old is not None else "Absent"
        if status not in ATTENDANCE_STATUSES:
            status = "Absent"
        comment = _clean(old.get("commentaire")) if old is not None else ""
        if comment in {"Auto-validation QR/NFC", "Appel manuel smartphone", "Appel manuel — Carnet enseignant"}:
            comment = ""
        table_rows.append(
            {
                "etudiant_id": eid,
                "Étudiant": f"{student['nom']} {student['prenom']}",
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
            disabled=["etudiant_id", "Étudiant", "Source"],
            column_config={
                "etudiant_id": None,
                "Étudiant": st.column_config.TextColumn(
                    "Étudiant", width="medium", pinned=True
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
            upsert_presence(
                sid,
                int(row["etudiant_id"]),
                _clean(row["Statut"]) or "Absent",
                _clean(row["Observation"]),
            )
        st.success("Appel enregistré.")
        st.rerun()


def _render_notes(st, qdf, exec_sql, session, students):
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
    if len(valid_notes):
        st.caption(
            f"Moyenne actuelle : {valid_notes.mean():.2f}/{float(bareme):g} • "
            f"{len(valid_notes)}/{len(frame)} note(s) saisie(s)"
        )
    else:
        st.caption("Aucune note encore saisie pour cette évaluation.")

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
    st.dataframe(pd.DataFrame(progress_rows), hide_index=True, use_container_width=True)


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
    if not evals.empty:
        valid = evals.dropna(subset=["note", "bareme", "coefficient"]).copy()
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
        competence_rate = round(
            float(acq["niveau"].isin(["Acquis", "Maîtrisé"]).mean()) * 100
        )

    c1, c2, c3 = st.columns(3)
    c1.metric("Présence", f"{attendance_rate}%" if attendance_rate is not None else "—")
    c2.metric("Moyenne /20", f"{weighted_average:.2f}" if weighted_average is not None else "—")
    c3.metric("Compétences validées", f"{competence_rate}%" if competence_rate is not None else "—")

    st.markdown("#### Dernières évaluations")
    if evals.empty:
        st.info("Aucune évaluation.")
    else:
        st.dataframe(evals.head(8), hide_index=True, use_container_width=True)

    st.markdown("#### Compétences")
    if acq.empty:
        st.info("Aucune compétence.")
    else:
        st.dataframe(acq, hide_index=True, use_container_width=True)

    st.markdown("#### Présences récentes")
    if pres.empty:
        st.info("Aucune présence.")
    else:
        st.dataframe(pres.head(10), hide_index=True, use_container_width=True)


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
        @media (max-width: 768px){
          div[data-testid="stDataEditor"] {font-size:.92rem;}
          [data-testid="stMetricValue"] {font-size:1.35rem;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

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
    students = _students_for_session(qdf, session)
    if students.empty:
        st.warning("Aucun étudiant actif n’est rattaché à cette séance.")
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

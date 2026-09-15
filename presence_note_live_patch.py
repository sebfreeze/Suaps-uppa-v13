"""Injection ciblée de la feuille combinée présence / note dans le live V14/V17."""

SENTINEL = "# --- presence note evaluation integration ---"

NAV_OLD = '    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")'
NAV_NEW = '    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Présence / Note évaluation","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")'
EVAL_MARKER = '    elif sec=="Évaluations":\n'

COMBINED_BLOCK = '''    # --- presence note evaluation integration ---
    elif sec=="Présence / Note évaluation":
        st.markdown("### ✅ Présence / Note évaluation")
        st.caption("Tableau du groupe : Nom / Prénom, Présence, Note et Observation. Les présences QR déjà validées sont pré-cochées automatiquement.")
        _sessions=rows("SELECT s.id,s.offre_id,s.date_seance,s.theme,o.activite,o.intitule FROM seances s JOIN offres o ON o.id=s.offre_id ORDER BY s.date_seance DESC,s.id DESC")
        if not _sessions:
            st.info("Crée d'abord une séance dans la rubrique Présences.")
        else:
            _session=st.selectbox("Séance",_sessions,format_func=lambda r:f"{r['date_seance']} — {r['activite']} — {r['intitule']} — {r['theme'] or ''}",key="combined_session")
            _default_title=(_session["theme"] or "").strip() or f"Évaluation du {_session['date_seance']}"
            _c1,_c2,_c3=st.columns([2.4,1,1])
            _eval_title=_c1.text_input("Évaluation",value=_default_title,key=f"combined_title_{_session['id']}").strip() or _default_title
            _bareme=_c2.number_input("Barème",min_value=1.0,value=20.0,step=1.0,key=f"combined_bareme_{_session['id']}")
            _coef=_c3.number_input("Coefficient",min_value=0.1,value=1.0,step=0.1,key=f"combined_coef_{_session['id']}")
            _students=rows("SELECT u.id,u.nom,u.prenom,u.identifiant,i.modalite FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id WHERE i.offre_id=? AND i.statut='Inscrit' AND u.actif=1 ORDER BY u.nom,u.prenom",(_session["offre_id"],))
            if not _students:
                st.info("Aucun étudiant inscrit sur ce créneau.")
            else:
                import pandas as pd
                _presences=rows("SELECT * FROM presences WHERE seance_id=?",(_session["id"],))
                _pmap={int(r["utilisateur_id"]):r for r in _presences}
                _evaluations=rows("SELECT * FROM evaluations WHERE activite=? AND intitule=? AND date_eval=? ORDER BY id DESC",(_session["activite"],_eval_title,_session["date_seance"]))
                _emap={}
                for _ev in _evaluations:
                    _uid=int(_ev["utilisateur_id"])
                    if _uid not in _emap: _emap[_uid]=_ev
                st.caption(f"{len(_students)} étudiant(s) • {_session['activite']} • note sur {_bareme:g}")
                _table_rows=[]
                for _student in _students:
                    _uid=int(_student["id"]); _old_p=_pmap.get(_uid); _old_e=_emap.get(_uid)
                    _old_status=_old_p["statut"] if _old_p else "Absent"
                    _old_note=float(_old_e["note"]) if _old_e and _old_e["note"] is not None else None
                    _old_obs=""
                    if _old_e and _old_e.get("commentaire"): _old_obs=str(_old_e["commentaire"])
                    elif _old_p and _old_p.get("commentaire"): _old_obs=str(_old_p["commentaire"])
                    _table_rows.append({"utilisateur_id":_uid,"Nom / Prénom":f"{_student['nom']} {_student['prenom']}","Présence":_old_status=="Présent","Note":_old_note,"Observation":_old_obs})
                _table_df=pd.DataFrame(_table_rows).set_index("utilisateur_id")
                with st.form(f"combined_presence_note_{_session['id']}"):
                    _edited_table=st.data_editor(
                        _table_df,
                        hide_index=True,
                        use_container_width=True,
                        column_order=["Nom / Prénom","Présence","Note","Observation"],
                        disabled=["Nom / Prénom"],
                        height=min(720,44+36*len(_students)),
                        column_config={
                            "Nom / Prénom":st.column_config.TextColumn("Nom / Prénom",width=145,pinned=True),
                            "Présence":st.column_config.CheckboxColumn("Présence",help="Coche si l'étudiant est présent",width=75),
                            "Note":st.column_config.NumberColumn("Note",min_value=0.0,max_value=float(_bareme),step=0.25,required=False,width=70),
                            "Observation":st.column_config.TextColumn("Observation",width=160),
                        },
                        key=f"combined_table_{_session['id']}",
                    )
                    _save_combined=st.form_submit_button("💾 Enregistrer la séance",type="primary",use_container_width=True)
                if _save_combined:
                    _combined_rows=[]; _combined_invalid=False
                    for _uid,_row in _edited_table.iterrows():
                        _note_value=_row["Note"]
                        _note=None if pd.isna(_note_value) else float(_note_value)
                        _obs_value=_row["Observation"]
                        _obs="" if pd.isna(_obs_value) else str(_obs_value).strip()
                        if _note is not None and _note>float(_bareme): _combined_invalid=True
                        _combined_rows.append({"utilisateur_id":int(_uid),"statut":"Présent" if bool(_row["Présence"]) else "Absent","note":_note,"observation":_obs})
                    if _combined_invalid:
                        st.error(f"Une note dépasse le barème de {_bareme:g}. Corrige-la avant d'enregistrer.")
                    else:
                        for _item in _combined_rows:
                            _presence=one("SELECT id FROM presences WHERE seance_id=? AND utilisateur_id=?",(_session["id"],_item["utilisateur_id"]))
                            if _presence:
                                exe("UPDATE presences SET statut=?,mode_validation=?,commentaire=? WHERE id=?",(_item["statut"],"Manuel",(_item["observation"] or "").strip(),_presence["id"]))
                            else:
                                exe("INSERT INTO presences(seance_id,utilisateur_id,statut,mode_validation,commentaire) VALUES(?,?,?,?,?)",(_session["id"],_item["utilisateur_id"],_item["statut"],"Manuel",(_item["observation"] or "").strip()))
                            if _item["note"] is not None:
                                _existing_eval=one("SELECT id FROM evaluations WHERE utilisateur_id=? AND activite=? AND intitule=? AND date_eval=? ORDER BY id DESC LIMIT 1",(_item["utilisateur_id"],_session["activite"],_eval_title,_session["date_seance"]))
                                if _existing_eval:
                                    exe("UPDATE evaluations SET note=?,bareme=?,coefficient=?,commentaire=? WHERE id=?",(float(_item["note"]),float(_bareme),float(_coef),(_item["observation"] or "").strip(),_existing_eval["id"]))
                                else:
                                    exe("INSERT INTO evaluations(utilisateur_id,activite,intitule,note,bareme,coefficient,commentaire,date_eval) VALUES(?,?,?,?,?,?,?,?)",(_item["utilisateur_id"],_session["activite"],_eval_title,float(_item["note"]),float(_bareme),float(_coef),(_item["observation"] or "").strip(),_session["date_seance"]))
                        st.success("Présences, notes et observations enregistrées.")
                        st.rerun()
'''


def patch_app_source(source: str) -> str:
    if SENTINEL in source:
        return source
    if NAV_OLD not in source:
        raise RuntimeError("Navigation enseignant live introuvable pour Présence / Note évaluation.")
    if EVAL_MARKER not in source:
        raise RuntimeError("Point d'insertion Évaluations live introuvable.")
    source = source.replace(NAV_OLD, NAV_NEW, 1)
    source = source.replace(EVAL_MARKER, COMBINED_BLOCK + EVAL_MARKER, 1)
    return source

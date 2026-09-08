# Ajoute Compétition, Pédagogie, présence manuelle, Présences & Notes et contrôles d'accès.
import builtins

_previous_compile = builtins.compile


def _inject_modules(source):
    if not isinstance(source, str):
        return source
    if 'def admin()' not in source or 'key="admin_section"' not in source:
        return source

    # Codes d'accès : requis uniquement lors de la création d'un nouveau profil.
    if 'key="student_access_code"' not in source:
        if 'import os\n' not in source:
            source = source.replace('import sqlite3\n', 'import sqlite3\nimport os\n', 1)
        old_signup = '''            mail=st.text_input("E-mail UPPA"); ident=st.text_input("Numéro étudiant / identifiant"); comp=st.text_input("Formation / service")
            ok=st.form_submit_button("Créer mon profil",type="primary")
        if ok:
            if not nom or not pre or not mail: st.warning("Nom, prénom et e-mail sont obligatoires.")
            else:
                try:
                    st.session_state.user_id=exe("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,composante) VALUES(?,?,?,?,?,?)",(prof,nom.strip(),pre.strip(),mail.strip(),ident.strip(),comp.strip())); go("Mon espace")
                except sqlite3.IntegrityError: st.error("Cette adresse e-mail est déjà enregistrée.")'''
        new_signup = '''            mail=st.text_input("E-mail UPPA"); ident=st.text_input("Numéro étudiant / identifiant"); comp=st.text_input("Formation / service")
            student_access_code=st.text_input("Code d'accès étudiant",type="password",key="student_access_code") if prof=="Étudiant" else ""
            personnel_access_code=st.text_input("Code d'accès Personnel UPPA",type="password",key="personnel_access_code") if prof=="Personnel" else ""
            if prof=="Étudiant":
                st.caption("Ce code est communiqué par le SUAPS pour autoriser la création d'un profil étudiant.")
            elif prof=="Personnel":
                st.caption("Ce code est communiqué par le SUAPS pour autoriser la création d'un profil Personnel UPPA.")
            ok=st.form_submit_button("Créer mon profil",type="primary")
        if ok:
            _expected_access_code=os.getenv("STUDENT_ACCESS_CODE","").strip()
            if prof=="Étudiant" and (not _expected_access_code or student_access_code.strip()!=_expected_access_code):
                st.error("Code d'accès étudiant incorrect.")
            elif prof=="Personnel" and (not _expected_access_code or personnel_access_code.strip()!=_expected_access_code):
                st.error("Code d'accès Personnel UPPA incorrect.")
            elif not nom or not pre or not mail: st.warning("Nom, prénom et e-mail sont obligatoires.")
            else:
                try:
                    st.session_state.user_id=exe("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,composante) VALUES(?,?,?,?,?,?)",(prof,nom.strip(),pre.strip(),mail.strip(),ident.strip(),comp.strip())); go("Mon espace")
                except sqlite3.IntegrityError: st.error("Cette adresse e-mail est déjà enregistrée.")'''
        if old_signup in source:
            source = source.replace(old_signup, new_signup, 1)

    if '"Compétition"' not in source:
        if '"Sports collectifs"' in source:
            source = source.replace('"Sports collectifs"', '"Compétition"')
        elif '"Évaluation /20","Compétences"' in source:
            source = source.replace('"Évaluation /20","Compétences"', '"Évaluation /20","Compétition","Compétences"', 1)

    if '"Pédagogie"' not in source:
        source = source.replace('"Compétition","Compétences"', '"Compétition","Pédagogie","Compétences"', 1)

    anchor = '    elif sec=="Compétences":\n'
    if anchor in source and 'elif sec=="Compétition":' not in source:
        competition = '''    elif sec=="Compétition":
        st.markdown("## 🏆 Compétition")
        st.caption("Sports collectifs • Badminton • Pelote Basque")
        st.info("Équipes / joueurs • Composer • Matchs • Feuilles de match • Tournois • Classements")
        from sports_co_module import init_sports_co_db, render_sports_co
        init_sports_co_db(exe)
        render_sports_co(st, rows, one, exe, date)
    elif sec=="Compétences":
'''
        source = source.replace(anchor, competition, 1)

    anchor = '    elif sec=="Compétences":\n'
    if anchor in source and 'elif sec=="Pédagogie":' not in source:
        pedagogie = '''    elif sec=="Pédagogie":
        st.markdown("## 🎓 Pédagogie")
        st.caption("Un suivi simple de la séance à la progression de l'étudiant")
        ptab=st.radio("Suivi pédagogique",["Séances","Progression","Bilans"],horizontal=True,key="pedagogie_tab")
        if ptab=="Séances":
            st.markdown("### 🎯 Objectifs de séance")
            st.info("Choisis 2 ou 3 objectifs prioritaires et relie-les aux compétences travaillées.")
            st.multiselect("Objectifs",["Technique / maîtrise gestuelle","Tactique / prise de décision","Engagement / intensité","Autonomie","Coopération","Sécurité","Condition physique"],max_selections=3,key="pedago_objectifs")
            st.text_area("Observation rapide de la séance",placeholder="Points réussis, points à renforcer, consigne pour la prochaine séance…",key="pedago_obs")
        elif ptab=="Progression":
            st.markdown("### ⭐ Progression des compétences")
            st.info("Lecture simple : Non évalué → À renforcer → Acquis → Maîtrisé. Les validations détaillées restent dans la rubrique Compétences.")
            st.progress(0,text="Sélectionne ou évalue les compétences pour visualiser progressivement le parcours de l'étudiant.")
        else:
            st.markdown("### 👤 Bilan étudiant")
            st.info("Le bilan regroupe les éléments déjà présents dans l'application : présences, compétences, performances et note /20.")
            st.markdown("**Repères de bilan** : assiduité • progression • acquis • points à renforcer • investissement")
            st.text_area("Commentaire de bilan",placeholder="Bilan synthétique de fin de période ou de semestre…",key="pedago_bilan")
    elif sec=="Compétences":
'''
        source = source.replace(anchor, pedagogie, 1)

    if 'key="manual_presence_pick"' not in source:
        old_presence = '''            if ok: exe("UPDATE seances SET qr_ouvert=0 WHERE offre_id=?",(oid,)); exe("INSERT INTO seances(offre_id,date_seance,theme,qr_token,qr_ouvert) VALUES(?,?,?,?,1)",(oid,str(d),theme,tok)); st.success(f"Code : {tok}"); st.rerun()
    elif sec=="Évaluations":'''
        new_presence = '''            if ok: exe("UPDATE seances SET qr_ouvert=0 WHERE offre_id=?",(oid,)); exe("INSERT INTO seances(offre_id,date_seance,theme,qr_token,qr_ouvert) VALUES(?,?,?,?,1)",(oid,str(d),theme,tok)); st.success(f"Code : {tok}"); st.rerun()
            _sessions=rows("SELECT * FROM seances WHERE offre_id=? ORDER BY date_seance DESC,id DESC",(oid,))
            if _sessions:
                st.markdown("### ✅ Appel manuel sur smartphone")
                _sess=st.selectbox("Séance à gérer",_sessions,format_func=lambda r:f"{r['date_seance']} — {r['theme'] or 'Séance'} — {r['qr_token'] or 'sans code'}",key="manual_presence_pick")
                _regs=rows("SELECT u.id,u.nom,u.prenom,p.statut,p.mode_validation FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id LEFT JOIN presences p ON p.utilisateur_id=u.id AND p.seance_id=? WHERE i.offre_id=? AND i.statut='Inscrit' AND u.actif=1 ORDER BY u.nom,u.prenom",(_sess["id"],oid))
                if not _regs:
                    st.info("Aucun inscrit sur ce créneau.")
                else:
                    _reg_by_id={r["id"]:r for r in _regs}
                    _present_default=[r["id"] for r in _regs if r.get("statut")=="Présent"]
                    _selected=st.multiselect("Étudiants présents",list(_reg_by_id),default=_present_default,format_func=lambda uid:f"{_reg_by_id[uid]['nom']} {_reg_by_id[uid]['prenom']}",key=f"manual_present_{_sess['id']}")
                    st.caption(f"{len(_selected)} présent(s) sur {len(_regs)} inscrit(s). Décoche un nom pour le noter absent.")
                    if st.button("💾 Enregistrer l'appel",type="primary",key=f"save_manual_presence_{_sess['id']}"):
                        _selected_set=set(_selected)
                        for _uid,_r in _reg_by_id.items():
                            _status="Présent" if _uid in _selected_set else "Absent"
                            _old=one("SELECT id,statut,mode_validation FROM presences WHERE seance_id=? AND utilisateur_id=?",(_sess["id"],_uid))
                            if _old:
                                if _old.get("mode_validation")=="QR" and _old.get("statut")=="Présent" and _status=="Présent":
                                    continue
                                exe("UPDATE presences SET statut=?,mode_validation='Manuel' WHERE id=?",(_status,_old["id"]))
                            else:
                                exe("INSERT INTO presences(seance_id,utilisateur_id,statut,mode_validation) VALUES(?,?,?,'Manuel')",(_sess["id"],_uid,_status))
                        st.success("Appel enregistré.")
                        st.rerun()
    elif sec=="Évaluations":'''
        if old_presence in source:
            source = source.replace(old_presence, new_presence, 1)

    if '"Présences & Notes"' not in source:
        source = source.replace('"Présences","Évaluations"', '"Présences","Présences & Notes","Évaluations"', 1)

    if 'elif sec=="Présences & Notes":' not in source:
        if 'import pandas as pd\n' not in source:
            source = source.replace('import streamlit as st\n', 'import streamlit as st\nimport pandas as pd\n', 1)
        eval_anchor = '    elif sec=="Évaluations":\n'
        combined = '''    elif sec=="Présences & Notes":
        st.markdown("## 📝 Présences & Notes")
        st.caption("Une seule page pour faire l'appel et saisir les notes du groupe.")
        _offs=rows("SELECT * FROM offres ORDER BY activite,intitule")
        if not _offs:
            st.info("Aucun créneau disponible.")
        else:
            _omap={f"{o['activite']} — {o['intitule']}":o for o in _offs}
            _olab=st.selectbox("Créneau / groupe",list(_omap),key="pn_offer")
            _off=_omap[_olab]
            _oid=_off["id"]
            with st.expander("➕ Créer une nouvelle séance"):
                with st.form("pn_new_session"):
                    _d=st.date_input("Date",date.today(),key="pn_new_date")
                    _theme=st.text_input("Thème",key="pn_new_theme")
                    _tok=st.text_input("Code QR / présence",value=f"SUAPS-{datetime.now().strftime('%H%M%S')}",key="pn_new_tok")
                    _create=st.form_submit_button("Créer et ouvrir la séance",type="primary")
                if _create:
                    exe("UPDATE seances SET qr_ouvert=0 WHERE offre_id=?",(_oid,))
                    exe("INSERT INTO seances(offre_id,date_seance,theme,qr_token,qr_ouvert) VALUES(?,?,?,?,1)",(_oid,str(_d),_theme,_tok))
                    st.success("Séance créée.")
                    st.rerun()
            _sessions=rows("SELECT * FROM seances WHERE offre_id=? ORDER BY date_seance DESC,id DESC",(_oid,))
            if not _sessions:
                st.info("Crée d'abord une séance pour ce créneau.")
            else:
                _sess=st.selectbox("Séance",_sessions,format_func=lambda r:f"{r['date_seance']} — {r['theme'] or 'Séance'}",key="pn_session")
                _regs=rows("SELECT u.id,u.nom,u.prenom,p.statut,p.mode_validation FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id LEFT JOIN presences p ON p.utilisateur_id=u.id AND p.seance_id=? WHERE i.offre_id=? AND i.statut='Inscrit' AND u.actif=1 ORDER BY u.nom,u.prenom",(_sess["id"],_oid))
                if not _regs:
                    st.info("Aucun étudiant inscrit sur ce créneau.")
                else:
                    _c1,_c2,_c3=st.columns(3)
                    _intitule=_c1.text_input("Évaluation / test",value=f"{_sess['date_seance']} — {_sess['theme'] or _off['activite']}",key="pn_eval_title")
                    _bareme=_c2.number_input("Barème",min_value=1.0,max_value=100.0,value=20.0,step=1.0,key="pn_bareme")
                    _coef=_c3.number_input("Coefficient",min_value=0.1,max_value=20.0,value=1.0,step=0.1,key="pn_coef")
                    _all=st.checkbox("✅ Précocher tous les inscrits présents",value=False,key=f"pn_all_{_sess['id']}")
                    _grid=[]
                    for _r in _regs:
                        _ev=one("SELECT id,note,commentaire,bareme,coefficient FROM evaluations WHERE utilisateur_id=? AND activite=? AND intitule=? AND date_eval=? ORDER BY id DESC LIMIT 1",(_r["id"],_off["activite"],_intitule,_sess["date_seance"]))
                        _grid.append({
                            "id":_r["id"],
                            "Étudiant":f"{_r['nom']} {_r['prenom']}",
                            "Présent":True if _all else (_r.get("statut")=="Présent"),
                            "Note":float(_ev["note"]) if _ev and _ev.get("note") is not None else None,
                            "Commentaire":(_ev.get("commentaire") or "") if _ev else "",
                            "Origine":_r.get("mode_validation") or ""
                        })
                    _df=pd.DataFrame(_grid)
                    _edited=st.data_editor(
                        _df,
                        use_container_width=True,
                        hide_index=True,
                        disabled=["id","Étudiant","Origine"],
                        column_config={
                            "id":None,
                            "Étudiant":st.column_config.TextColumn("Étudiant",width="medium"),
                            "Présent":st.column_config.CheckboxColumn("Présent"),
                            "Note":st.column_config.NumberColumn(f"Note / {_bareme:g}",min_value=0.0,max_value=float(_bareme),step=0.25),
                            "Commentaire":st.column_config.TextColumn("Commentaire",width="large"),
                            "Origine":st.column_config.TextColumn("Origine",help="QR ou saisie manuelle",width="small"),
                        },
                        key=f"pn_grid_{_sess['id']}_{_intitule}"
                    )
                    _np=int(_edited["Présent"].sum())
                    st.caption(f"✅ {_np} présent(s) • ❌ {len(_edited)-_np} absent(s) • Une note vide n'est pas enregistrée.")
                    if st.button("💾 Enregistrer la séance",type="primary",use_container_width=True,key=f"pn_save_{_sess['id']}"):
                        _notes=0
                        for _,_row in _edited.iterrows():
                            _uid=int(_row["id"])
                            _status="Présent" if bool(_row["Présent"]) else "Absent"
                            _old=one("SELECT id,statut,mode_validation FROM presences WHERE seance_id=? AND utilisateur_id=?",(_sess["id"],_uid))
                            if _old:
                                if not (_old.get("mode_validation")=="QR" and _old.get("statut")=="Présent" and _status=="Présent"):
                                    exe("UPDATE presences SET statut=?,mode_validation='Manuel' WHERE id=?",(_status,_old["id"]))
                            else:
                                exe("INSERT INTO presences(seance_id,utilisateur_id,statut,mode_validation) VALUES(?,?,?,'Manuel')",(_sess["id"],_uid,_status))
                            _note=_row["Note"]
                            if _note is not None and not pd.isna(_note):
                                _comment="" if pd.isna(_row["Commentaire"]) else str(_row["Commentaire"]).strip()
                                _existing=one("SELECT id FROM evaluations WHERE utilisateur_id=? AND activite=? AND intitule=? AND date_eval=? ORDER BY id DESC LIMIT 1",(_uid,_off["activite"],_intitule,_sess["date_seance"]))
                                if _existing:
                                    exe("UPDATE evaluations SET note=?,bareme=?,coefficient=?,commentaire=? WHERE id=?",(float(_note),float(_bareme),float(_coef),_comment,_existing["id"]))
                                else:
                                    exe("INSERT INTO evaluations(utilisateur_id,activite,intitule,note,bareme,coefficient,commentaire,date_eval) VALUES(?,?,?,?,?,?,?,?)",(_uid,_off["activite"],_intitule,float(_note),float(_bareme),float(_coef),_comment,_sess["date_seance"]))
                                _notes+=1
                        st.success(f"Séance enregistrée : {_np} présent(s), {_notes} note(s).")
                        st.rerun()
    elif sec=="Évaluations":
'''
        if eval_anchor in source:
            source = source.replace(eval_anchor, combined, 1)

    return source


def _compile(source, filename, mode, flags=0, dont_inherit=False, optimize=-1, **kwargs):
    try:
        if str(filename).endswith("v14_core.py"):
            source = _inject_modules(source)
    except Exception:
        pass
    return _previous_compile(source, filename, mode, flags, dont_inherit, optimize, **kwargs)


builtins.compile = _compile

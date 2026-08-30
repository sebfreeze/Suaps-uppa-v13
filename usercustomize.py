"""Ajoute les modules Compétition, Pédagogie, présence manuelle et contrôles d'accès à l'application générée."""
import builtins

_previous_compile = builtins.compile


def _inject_modules(source):
    if not isinstance(source, str):
        return source
    if 'def admin()' not in source or 'key="admin_section"' not in source:
        return source

    # Codes d'accès : requis uniquement lors de la création d'un nouveau profil.
    # La valeur est lue côté serveur et n'est jamais inscrite dans le dépôt.
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

    # Compétition : sports collectifs + badminton + Pelote Basque.
    if '"Compétition"' not in source:
        if '"Sports collectifs"' in source:
            source = source.replace('"Sports collectifs"', '"Compétition"')
        elif '"Évaluation /20","Compétences"' in source:
            source = source.replace('"Évaluation /20","Compétences"', '"Évaluation /20","Compétition","Compétences"', 1)

    # Ajoute Pédagogie juste avant Compétences.
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
        ptab = st.radio("Suivi pédagogique", ["Séances", "Progression", "Bilans"], horizontal=True, key="pedagogie_tab")
        if ptab == "Séances":
            st.markdown("### 🎯 Objectifs de séance")
            st.info("Choisis 2 ou 3 objectifs prioritaires et relie-les aux compétences travaillées.")
            st.multiselect("Objectifs", ["Technique / maîtrise gestuelle", "Tactique / prise de décision", "Engagement / intensité", "Autonomie", "Coopération", "Sécurité", "Condition physique"], max_selections=3, key="pedago_objectifs")
            st.text_area("Observation rapide de la séance", placeholder="Points réussis, points à renforcer, consigne pour la prochaine séance…", key="pedago_obs")
        elif ptab == "Progression":
            st.markdown("### ⭐ Progression des compétences")
            st.info("Lecture simple : Non évalué → À renforcer → Acquis → Maîtrisé. Les validations détaillées restent dans la rubrique Compétences.")
            st.progress(0, text="Sélectionne ou évalue les compétences pour visualiser progressivement le parcours de l'étudiant.")
        else:
            st.markdown("### 👤 Bilan étudiant")
            st.info("Le bilan regroupe les éléments déjà présents dans l'application : présences, compétences, performances et note /20.")
            st.markdown("**Repères de bilan** : assiduité • progression • acquis • points à renforcer • investissement")
            st.text_area("Commentaire de bilan", placeholder="Bilan synthétique de fin de période ou de semestre…", key="pedago_bilan")
    elif sec=="Compétences":
'''
        source = source.replace(anchor, pedagogie, 1)

    # Présences : appel manuel rapide, adapté au smartphone de l'enseignant.
    # Il complète QR/NFC sans supprimer les validations déjà enregistrées.
    if 'key="manual_presence_pick"' not in source:
        old_presence = '''            if ok: exe("UPDATE seances SET qr_ouvert=0 WHERE offre_id=?",(oid,)); exe("INSERT INTO seances(offre_id,date_seance,theme,qr_token,qr_ouvert) VALUES(?,?,?,?,1)",(oid,str(d),theme,tok)); st.success(f"Code : {tok}"); st.rerun()
    elif sec=="Évaluations":'''
        new_presence = '''            if ok: exe("UPDATE seances SET qr_ouvert=0 WHERE offre_id=?",(oid,)); exe("INSERT INTO seances(offre_id,date_seance,theme,qr_token,qr_ouvert) VALUES(?,?,?,?,1)",(oid,str(d),theme,tok)); st.success(f"Code : {tok}"); st.rerun()
            _sessions=rows("SELECT * FROM seances WHERE offre_id=? ORDER BY date_seance DESC,id DESC",(oid,))
            if _sessions:
                st.markdown("### ✅ Appel manuel sur smartphone")
                _sess=st.selectbox("Séance à gérer",_sessions,format_func=lambda r:f"{r['date_seance']} — {r['theme'] or 'Séance'} — {r['qr_token'] or 'sans code'}",key="manual_presence_pick")
                _regs=rows("SELECT u.id,u.nom,u.prenom,p.statut FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id LEFT JOIN presences p ON p.utilisateur_id=u.id AND p.seance_id=? WHERE i.offre_id=? AND i.statut='Inscrit' AND u.actif=1 ORDER BY u.nom,u.prenom",(_sess["id"],oid))
                if not _regs:
                    st.info("Aucun inscrit sur ce créneau.")
                else:
                    _reg_by_id={r["id"]:r for r in _regs}
                    _present_default=[r["id"] for r in _regs if r.get("statut")=="Présent"]
                    _selected=st.multiselect("Étudiants présents",list(_reg_by_id),default=_present_default,format_func=lambda uid:f"{_reg_by_id[uid]['nom']} {_reg_by_id[uid]['prenom']}",key=f"manual_present_{_sess['id']}")
                    st.caption(f"{len(_selected)} présent(s) sur {len(_regs)} inscrit(s). Décoche un nom pour le noter absent.")
                    if st.button("💾 Enregistrer l'appel",type="primary",key=f"save_manual_presence_{_sess['id']}"):
                        _selected_set=set(_selected)
                        for _uid in _reg_by_id:
                            _status="Présent" if _uid in _selected_set else "Absent"
                            _old=one("SELECT id FROM presences WHERE seance_id=? AND utilisateur_id=?",(_sess["id"],_uid))
                            if _old:
                                exe("UPDATE presences SET statut=?,mode_validation='Manuel' WHERE id=?",(_status,_old["id"]))
                            else:
                                exe("INSERT INTO presences(seance_id,utilisateur_id,statut,mode_validation) VALUES(?,?,?,'Manuel')",(_sess["id"],_uid,_status))
                        st.success("Appel enregistré.")
                        st.rerun()
    elif sec=="Évaluations":'''
        if old_presence in source:
            source = source.replace(old_presence, new_presence, 1)

    return source


def _compile(source, filename, mode, flags=0, dont_inherit=False, optimize=-1, **kwargs):
    try:
        if str(filename).endswith("v14_core.py"):
            source = _inject_modules(source)
    except Exception:
        pass
    return _previous_compile(source, filename, mode, flags, dont_inherit, optimize, **kwargs)


builtins.compile = _compile

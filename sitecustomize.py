"""Correctifs de démarrage, semestres/CSV et identité visuelle SUAPS."""

try:
    import builtins
    _original_compile = builtins.compile

    def _patch_suaps_generated_app(source):
        if not isinstance(source, str):
            return source

        # Correctif historique de la chaîne SQL CSV générée.
        if "export_rows=rows(\"\"\"SELECT u.nom AS 'Nom'" in source:
            source = source.replace(
                "export_rows=rows(\"\"\"SELECT u.nom AS 'Nom'",
                "export_rows=rows(\"SELECT u.nom AS 'Nom'",
            )
            source = source.replace(
                "ORDER BY u.nom,u.prenom\"\"\",(o[\"id\"],))",
                "ORDER BY u.nom,u.prenom\",(o[\"id\"],))",
            )

        if "def inscriptions():" not in source or "Enseignant / Admin" not in source:
            return source

        if "import pandas as pd" not in source:
            source = source.replace("import streamlit as st", "import streamlit as st\nimport pandas as pd", 1)

        # Rattachement des créneaux aux semestres 2026/2027.
        marker = "init_db()\n\ndef rows(sql,p=()):"
        migration = '''init_db()\n\ntry:\n    _c_sem=db()\n    _c_sem.execute("CREATE TABLE IF NOT EXISTS offre_semestres(offre_id INTEGER NOT NULL,semestre TEXT NOT NULL,PRIMARY KEY(offre_id,semestre))")\n    _c_sem.execute("INSERT OR IGNORE INTO offre_semestres(offre_id,semestre) SELECT id,'Semestre 1 — 2026/2027' FROM offres")\n    _c_sem.commit(); _c_sem.close()\nexcept Exception:\n    pass\n\ndef rows(sql,p=()):'''
        if marker in source and "CREATE TABLE IF NOT EXISTS offre_semestres" not in source:
            source = source.replace(marker, migration, 1)

        # Choix du semestre côté étudiant.
        old_ins = '''    fam=st.selectbox("Famille d’activités",[x[1] for x in FAMILLES])\n    acts=FAMILY_MAP.get(fam,[])\n    data=rows("SELECT o.*,COUNT(CASE WHEN i.statut='Inscrit' THEN 1 END) n FROM offres o LEFT JOIN inscriptions i ON i.offre_id=o.id WHERE o.ouverte=1 GROUP BY o.id ORDER BY o.activite,o.intitule")'''
        new_ins = '''    semestre=st.radio("Année 2026/2027",["Semestre 1 — 2026/2027","Semestre 2 — 2026/2027"],horizontal=True,key="ins_semestre")\n    fam=st.selectbox("Famille d’activités",[x[1] for x in FAMILLES])\n    acts=FAMILY_MAP.get(fam,[])\n    data=rows("SELECT o.*,COUNT(CASE WHEN i.statut='Inscrit' THEN 1 END) n FROM offres o JOIN offre_semestres os ON os.offre_id=o.id AND os.semestre=? LEFT JOIN inscriptions i ON i.offre_id=o.id WHERE o.ouverte=1 GROUP BY o.id ORDER BY o.activite,o.intitule",(semestre,))'''
        if old_ins in source and "key=\"ins_semestre\"" not in source:
            source = source.replace(old_ins, new_ins, 1)

        old_radio = 'sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")'
        new_radio = 'sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités","Semestres & CSV"],horizontal=True,key="admin_section")'
        source = source.replace(old_radio, new_radio)

        source = source.replace(
            '    else:\n        st.markdown("### 📰 Gestion des Infos Live")',
            '    elif sec=="Actualités":\n        st.markdown("### 📰 Gestion des Infos Live")',
            1,
        )

        tail = '''            if supprimer: exe("DELETE FROM actualites WHERE id=?",(n["id"],)); st.success("Information supprimée."); st.rerun()\n    if st.button("← Accueil"): go("Accueil")'''
        semester_block = '''            if supprimer: exe("DELETE FROM actualites WHERE id=?",(n["id"],)); st.success("Information supprimée."); st.rerun()\n    else:\n        st.markdown("### 📅 Semestres 2026/2027")\n        st.caption("Affecte chaque créneau au Semestre 1, au Semestre 2 ou aux deux.")\n        offs_sem=rows("SELECT * FROM offres ORDER BY activite,intitule,jour_horaire")\n        if offs_sem:\n            off_sem=st.selectbox("Créneau à paramétrer",offs_sem,format_func=lambda r:f"{r['activite']} — {r['intitule']} — {r['jour_horaire'] or 'horaire à définir'}",key="semester_offer")\n            linked={r["semestre"] for r in rows("SELECT semestre FROM offre_semestres WHERE offre_id=?",(off_sem["id"],))}\n            s1=st.checkbox("Semestre 1 — 2026/2027","Semestre 1 — 2026/2027" in linked,key="semester_s1")\n            s2=st.checkbox("Semestre 2 — 2026/2027","Semestre 2 — 2026/2027" in linked,key="semester_s2")\n            if st.button("Enregistrer les semestres",type="primary",key="save_semesters"):\n                exe("DELETE FROM offre_semestres WHERE offre_id=?",(off_sem["id"],))\n                if s1: exe("INSERT OR IGNORE INTO offre_semestres(offre_id,semestre) VALUES(?,?)",(off_sem["id"],"Semestre 1 — 2026/2027"))\n                if s2: exe("INSERT OR IGNORE INTO offre_semestres(offre_id,semestre) VALUES(?,?)",(off_sem["id"],"Semestre 2 — 2026/2027"))\n                st.success("Semestres du créneau enregistrés."); st.rerun()\n\n        st.markdown("### 📥 Import CSV / Excel étudiants et inscriptions")\n        st.caption("Import global possible : chaque étudiant est automatiquement réparti dans son activité et son créneau.")\n        st.info("Colonnes obligatoires : nom, prenom, email, numero_etudiant, activite, creneau. Pour la modalité, mettre X dans une seule colonne : UET, UECF ou Non noté. Recommandées : semestre, jour_horaire. Facultatives : composante, profil, responsable, co_responsable.")\n        modele=pd.DataFrame([{\n            "nom":"DUPONT","prenom":"Paul","email":"paul.dupont@etu.univ-pau.fr","numero_etudiant":"12345678","composante":"STAPS","profil":"Étudiant",\n            "semestre":"Semestre 1 — 2026/2027","UET":"X","UECF":"","Non noté":"","activite":"Natation","creneau":"Natation tous niveaux","jour_horaire":"Lundi 18h00","responsable":"","co_responsable":""\n        }])\n        guide_modele=pd.DataFrame([\n            {"colonne":"nom","statut":"Obligatoire","type / valeurs":"Texte","exemple":"DUPONT"},\n            {"colonne":"prenom","statut":"Obligatoire","type / valeurs":"Texte","exemple":"Paul"},\n            {"colonne":"email","statut":"Obligatoire","type / valeurs":"Adresse e-mail","exemple":"paul.dupont@etu.univ-pau.fr"},\n            {"colonne":"numero_etudiant","statut":"Obligatoire","type / valeurs":"Numéro étudiant","exemple":"12345678"},\n            {"colonne":"composante","statut":"Facultatif","type / valeurs":"Texte","exemple":"STAPS"},\n            {"colonne":"profil","statut":"Facultatif","type / valeurs":"Étudiant ou Personnel","exemple":"Étudiant"},\n            {"colonne":"semestre","statut":"Recommandé","type / valeurs":"Semestre 1 — 2026/2027 ou Semestre 2 — 2026/2027","exemple":"Semestre 1 — 2026/2027"},\n            {"colonne":"UET","statut":"Modalité","type / valeurs":"Mettre X si l'étudiant est inscrit en UET","exemple":"X"},\n            {"colonne":"UECF","statut":"Modalité","type / valeurs":"Mettre X si l'étudiant est inscrit en UECF","exemple":""},\n            {"colonne":"Non noté","statut":"Modalité","type / valeurs":"Mettre X si l'inscription n'est pas notée","exemple":""},\n            {"colonne":"activite","statut":"Obligatoire","type / valeurs":"Nom exact de l’activité dans l’application","exemple":"Natation"},\n            {"colonne":"creneau","statut":"Obligatoire","type / valeurs":"Intitulé exact du créneau","exemple":"Natation tous niveaux"},\n            {"colonne":"jour_horaire","statut":"Recommandé","type / valeurs":"Texte ; utile si plusieurs créneaux identiques","exemple":"Lundi 18h00"},\n            {"colonne":"responsable","statut":"Facultatif / information","type / valeurs":"Nom du responsable enregistré sur le créneau","exemple":"Sébastien"},\n            {"colonne":"co_responsable","statut":"Facultatif / information","type / valeurs":"Nom du co-responsable éventuel","exemple":""}\n        ])\n        _xlsx=__import__("io").BytesIO()\n        with pd.ExcelWriter(_xlsx,engine="openpyxl") as _writer:\n            modele.to_excel(_writer,index=False,sheet_name="Import")\n            guide_modele.to_excel(_writer,index=False,sheet_name="Guide")\n            _ws=_writer.book["Import"]; _ws.freeze_panes="A2"; _ws.auto_filter.ref=_ws.dimensions\n            _wg=_writer.book["Guide"]; _wg.freeze_panes="A2"; _wg.auto_filter.ref=_wg.dimensions\n            for _col,_width in {"A":16,"B":16,"C":32,"D":16,"E":18,"F":16,"G":28,"H":10,"I":10,"J":12,"K":22,"L":28,"M":22,"N":18,"O":18}.items(): _ws.column_dimensions[_col].width=_width\n            for _col,_width in {"A":18,"B":16,"C":52,"D":34}.items(): _wg.column_dimensions[_col].width=_width\n        _xlsx.seek(0)\n        mt1,mt2=st.columns(2)\n        mt1.download_button("📗 Télécharger le modèle Excel",_xlsx.getvalue(),file_name="modele_import_suaps_2026_2027.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key="download_import_template_xlsx",use_container_width=True)\n        mt2.download_button("⬇️ Télécharger le modèle CSV",modele.to_csv(index=False).encode("utf-8-sig"),file_name="modele_import_suaps_2026_2027.csv",mime="text/csv",key="download_import_template_csv",use_container_width=True)\n        import_file=st.file_uploader("Choisir le fichier CSV ou Excel",type=["csv","xlsx"],key="import_users_file")\n        if import_file is not None:\n            try:\n                imp=pd.read_excel(import_file,sheet_name="Import") if import_file.name.lower().endswith(".xlsx") else pd.read_csv(import_file,sep=None,engine="python")\n                imp.columns=[str(c).strip().lower().replace("é","e").replace("è","e").replace("ê","e").replace("ë","e").replace("à","a").replace("â","a").replace("ä","a").replace("î","i").replace("ï","i").replace("ô","o").replace("ö","o").replace("ù","u").replace("û","u").replace("ü","u").replace("ç","c") for c in imp.columns]\n                aliases={"n° etudiant":"identifiant","n°etudiant":"identifiant","numero etudiant":"identifiant","numero_etudiant":"identifiant","formation":"composante","horaire":"jour_horaire","jour / horaire":"jour_horaire"}\n                imp=imp.rename(columns={c:aliases.get(c,c) for c in imp.columns})\n                required=["nom","prenom","email","identifiant","activite","creneau"]\n                missing=[c for c in required if c not in imp.columns]\n                if missing:\n                    st.error("Colonnes obligatoires manquantes : "+", ".join(missing))\n                else:\n                    st.dataframe(imp.head(25),use_container_width=True,hide_index=True)\n                    if st.button("Importer et répartir les étudiants",type="primary",key="do_import_users"):\n                        added=0; updated=0; enrolled=0; changed=0; errors=[]\n                        for idx,r in imp.iterrows():\n                            line=int(idx)+2\n                            def clean(name,default=""):\n                                v=str(r.get(name,default)).strip()\n                                return "" if v.lower()=="nan" else v\n                            nom=clean("nom"); prenom=clean("prenom"); email=clean("email").lower(); identifiant=clean("identifiant"); activite=clean("activite"); creneau=clean("creneau"); horaire=clean("jour_horaire")\n                            if not nom or not prenom or not email or not identifiant or not activite or not creneau:\n                                errors.append({"ligne":line,"email":email,"erreur":"Champ obligatoire vide"}); continue\n                            semestre=clean("semestre","Semestre 1 — 2026/2027")\n                            if semestre in ("S1","Semestre 1","1"): semestre="Semestre 1 — 2026/2027"\n                            elif semestre in ("S2","Semestre 2","2"): semestre="Semestre 2 — 2026/2027"\n                            if semestre not in ("Semestre 1 — 2026/2027","Semestre 2 — 2026/2027"):\n                                errors.append({"ligne":line,"email":email,"erreur":"Semestre inconnu"}); continue\n                            modalite=clean("modalite","")\n                            _flags=[]\n                            def _marked(name):\n                                return clean(name).lower() in ("x","1","oui","yes","true","vrai")\n                            if _marked("uet"): _flags.append("UET")\n                            if _marked("uecf"): _flags.append("UECF")\n                            if _marked("non note"): _flags.append("Non noté")\n                            if len(_flags)>1:\n                                errors.append({"ligne":line,"email":email,"erreur":"Une seule modalité doit être cochée : UET, UECF ou Non noté"}); continue\n                            if _flags: modalite=_flags[0]\n                            if not modalite: modalite="Non noté"\n                            norm_mod={"uet":"UET","uecf":"UECF","non note":"Non noté","non noté":"Non noté","non-note":"Non noté"}\n                            modalite=norm_mod.get(modalite.lower(),modalite)\n                            if modalite not in ("UET","UECF","Non noté"):\n                                errors.append({"ligne":line,"email":email,"erreur":"Modalité inconnue : "+modalite}); continue\n                            matches=rows("SELECT o.* FROM offres o JOIN offre_semestres os ON os.offre_id=o.id AND os.semestre=? WHERE lower(trim(o.activite))=lower(trim(?)) AND lower(trim(o.intitule))=lower(trim(?)) ORDER BY o.id",(semestre,activite,creneau))\n                            if horaire:\n                                matches=[o for o in matches if str(o.get("jour_horaire") or "").strip().lower()==horaire.lower()]\n                            if len(matches)==0:\n                                errors.append({"ligne":line,"email":email,"erreur":f"Créneau introuvable : {activite} / {creneau} / {semestre}"}); continue\n                            if len(matches)>1:\n                                errors.append({"ligne":line,"email":email,"erreur":"Plusieurs créneaux correspondent : renseigner jour_horaire"}); continue\n                            offre=matches[0]\n                            profil=clean("profil","Étudiant") or "Étudiant"; ident=clean("identifiant"); compo=clean("composante")\n                            exist=one("SELECT id FROM utilisateurs WHERE lower(email)=lower(?)",(email,))\n                            if exist:\n                                exe("UPDATE utilisateurs SET nom=?,prenom=?,identifiant=?,composante=?,profil=?,actif=1 WHERE id=?",(nom,prenom,ident,compo,profil,exist["id"])); uid=exist["id"]; updated+=1\n                            else:\n                                uid=exe("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,composante,actif) VALUES(?,?,?,?,?,?,1)",(profil,nom,prenom,email,ident,compo)); added+=1\n                            old_reg=one("SELECT id,modalite,statut FROM inscriptions WHERE utilisateur_id=? AND offre_id=?",(uid,offre["id"]))\n                            if old_reg:\n                                exe("UPDATE inscriptions SET modalite=?,statut='Inscrit' WHERE id=?",(modalite,old_reg["id"])); changed+=1\n                            else:\n                                exe("INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,statut,date_inscription) VALUES(?,?,?,'Inscrit',?)",(uid,offre["id"],modalite,str(date.today()))); enrolled+=1\n                        st.success(f"Import terminé : {added} étudiant(s) créé(s), {updated} mis à jour, {enrolled} nouvelle(s) inscription(s), {changed} inscription(s) mise(s) à jour.")\n                        if errors:\n                            st.warning(f"{len(errors)} ligne(s) non importée(s).")\n                            st.dataframe(pd.DataFrame(errors),use_container_width=True,hide_index=True)\n            except Exception as e:\n                st.error(f"Erreur d'import CSV / Excel : {e}")\n\n        st.markdown("### 📤 Exports CSV")\n        export_sem=st.radio("Semestre à exporter",["Semestre 1 — 2026/2027","Semestre 2 — 2026/2027"],horizontal=True,key="export_semester")\n        ins_rows=rows("SELECT u.nom AS 'Nom',u.prenom AS 'Prénom',u.email AS 'Email',u.identifiant AS 'N° étudiant',u.composante AS 'Composante',o.activite AS 'Activité',o.intitule AS 'Créneau',o.jour_horaire AS 'Jour / horaire',i.modalite AS 'Modalité',i.statut AS 'Statut',i.date_inscription AS 'Date inscription' FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id JOIN offres o ON o.id=i.offre_id JOIN offre_semestres os ON os.offre_id=o.id AND os.semestre=? ORDER BY o.activite,o.intitule,u.nom,u.prenom",(export_sem,))\n        pre_rows=rows("SELECT u.nom AS 'Nom',u.prenom AS 'Prénom',u.email AS 'Email',u.identifiant AS 'N° étudiant',o.activite AS 'Activité',o.intitule AS 'Créneau',o.jour_horaire AS 'Jour / horaire',s.date_seance AS 'Date séance',p.statut AS 'Présence',p.mode_validation AS 'Mode' FROM presences p JOIN utilisateurs u ON u.id=p.utilisateur_id JOIN seances s ON s.id=p.seance_id JOIN offres o ON o.id=s.offre_id JOIN offre_semestres os ON os.offre_id=o.id AND os.semestre=? ORDER BY s.date_seance,o.activite,u.nom,u.prenom",(export_sem,))\n        eva_rows=rows("SELECT u.nom AS 'Nom',u.prenom AS 'Prénom',u.email AS 'Email',u.identifiant AS 'N° étudiant',e.activite AS 'Activité',e.intitule AS 'Évaluation',e.note AS 'Note',e.bareme AS 'Barème',e.coefficient AS 'Coefficient',e.date_eval AS 'Date' FROM evaluations e JOIN utilisateurs u ON u.id=e.utilisateur_id WHERE EXISTS(SELECT 1 FROM offres o JOIN offre_semestres os ON os.offre_id=o.id WHERE os.semestre=? AND o.activite=e.activite) ORDER BY e.activite,u.nom,u.prenom",(export_sem,))\n        ins_cols=["Nom","Prénom","Email","N° étudiant","Composante","Activité","Créneau","Jour / horaire","Modalité","Statut","Date inscription"]\n        pre_cols=["Nom","Prénom","Email","N° étudiant","Activité","Créneau","Jour / horaire","Date séance","Présence","Mode"]\n        eva_cols=["Nom","Prénom","Email","N° étudiant","Activité","Évaluation","Note","Barème","Coefficient","Date"]\n        _export_xlsx=__import__("io").BytesIO()
        with pd.ExcelWriter(_export_xlsx,engine="openpyxl") as _ew:
            pd.DataFrame(ins_rows,columns=ins_cols).to_excel(_ew,index=False,sheet_name="Inscriptions")
            pd.DataFrame(pre_rows,columns=pre_cols).to_excel(_ew,index=False,sheet_name="Présences")
            pd.DataFrame(eva_rows,columns=eva_cols).to_excel(_ew,index=False,sheet_name="Évaluations")
            for _sheet in ("Inscriptions","Présences","Évaluations"):
                _wsx=_ew.book[_sheet]; _wsx.freeze_panes="A2"; _wsx.auto_filter.ref=_wsx.dimensions
        _export_xlsx.seek(0)
        st.download_button("📗 Export Excel complet",_export_xlsx.getvalue(),file_name=f"export_suaps_{export_sem.split('—')[0].strip().lower().replace(' ','_')}_2026_2027.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key="export_semester_xlsx",use_container_width=True)
        cex1,cex2,cex3=st.columns(3)
        cex1.download_button("Inscriptions CSV",pd.DataFrame(ins_rows,columns=ins_cols).to_csv(index=False).encode("utf-8-sig"),file_name=f"inscriptions_{export_sem.split('—')[0].strip().lower().replace(' ','_')}_2026_2027.csv",mime="text/csv",use_container_width=True)\n        cex2.download_button("Présences CSV",pd.DataFrame(pre_rows,columns=pre_cols).to_csv(index=False).encode("utf-8-sig"),file_name=f"presences_{export_sem.split('—')[0].strip().lower().replace(' ','_')}_2026_2027.csv",mime="text/csv",use_container_width=True)\n        cex3.download_button("Évaluations CSV",pd.DataFrame(eva_rows,columns=eva_cols).to_csv(index=False).encode("utf-8-sig"),file_name=f"evaluations_{export_sem.split('—')[0].strip().lower().replace(' ','_')}_2026_2027.csv",mime="text/csv",use_container_width=True)\n    if st.button("← Accueil"): go("Accueil")'''
        if tail in source and "### 📅 Semestres 2026/2027" not in source:
            source = source.replace(tail, semester_block, 1)

        # CRÉNEAUX RESPONSABLES V1
        # Une table séparée évite de modifier la structure historique de "offres".
        if "CREATE TABLE IF NOT EXISTS offre_responsables" not in source:
            _resp_anchor = "def rows(sql,p=()):"
            _resp_migration = '''try:
    _c_resp=db()
    _c_resp.execute("CREATE TABLE IF NOT EXISTS offre_responsables(id INTEGER PRIMARY KEY AUTOINCREMENT,offre_id INTEGER NOT NULL UNIQUE,responsable TEXT NOT NULL,coresponsable TEXT,cree_par TEXT,date_maj TEXT)")
    _c_resp.commit(); _c_resp.close()
except Exception:
    try: _c_resp.close()
    except Exception: pass

def rows(sql,p=()):'''
            if _resp_anchor in source:
                source = source.replace(_resp_anchor, _resp_migration, 1)

        _old_newslot = '''        with st.form("newslot"):
            a,b=st.columns(2); act=a.selectbox("Activité",ACTIVITES); title=b.text_input("Intitulé",value=f"{act} - créneau")
            c,d=st.columns(2); hor=c.text_input("Jour / horaire"); lieu=d.text_input("Lieu")
            e,f=st.columns(2); cap=e.number_input("Capacité",1,200,20); pub=f.selectbox("Public",["Tous","Étudiants","Personnel"])
            ok=st.form_submit_button("Créer le créneau",type="primary")
        if ok: exe("INSERT INTO offres(activite,intitule,jour_horaire,lieu,capacite,public) VALUES(?,?,?,?,?,?)",(act,title,hor,lieu,cap,pub)); st.success("Créneau créé."); st.rerun()'''
        _new_newslot = '''        _staff_names=["Hervé","Luhpo","Raphaël","Dudu","Geoffrey","Bernard","Mathieu","Michel","Stéphanie","Yan-Erick","Patrick","Sébastien"]
        _current_teacher=(st.session_state.get("teacher_name") or "").strip()
        with st.form("newslot"):
            a,b=st.columns(2); act=a.selectbox("Activité",ACTIVITES); title=b.text_input("Intitulé",value=f"{act} - créneau")
            c,d=st.columns(2); hor=c.text_input("Jour / horaire"); lieu=d.text_input("Lieu")
            e,f=st.columns(2); cap=e.number_input("Capacité",1,200,20); pub=f.selectbox("Public",["Tous","Étudiants","Personnel"])
            st.success(f"👤 Responsable automatique : {_current_teacher}" if _current_teacher else "👤 Responsable automatique : profil enseignant non identifié")
            _co_options=["Aucun"]+[n for n in _staff_names if n!=_current_teacher]
            co_resp=st.selectbox("Co-responsable (facultatif)",_co_options,key="newslot_co_responsable")
            ok=st.form_submit_button("Créer le créneau",type="primary")
        if ok:
            if not _current_teacher:
                st.error("Impossible d'identifier le responsable. Déconnecte-toi puis reconnecte-toi à l'espace enseignant.")
            else:
                _new_offer_id=exe("INSERT INTO offres(activite,intitule,jour_horaire,lieu,capacite,public) VALUES(?,?,?,?,?,?)",(act,title,hor,lieu,cap,pub))
                _co_value="" if co_resp=="Aucun" else co_resp
                exe("INSERT INTO offre_responsables(offre_id,responsable,coresponsable,cree_par,date_maj) VALUES(?,?,?,?,?)",(_new_offer_id,_current_teacher,_co_value,_current_teacher,str(date.today())))
                st.success(f"Créneau créé. Responsable : {_current_teacher}.")
                st.rerun()'''
        if _old_newslot in source and 'key="newslot_co_responsable"' not in source:
            source = source.replace(_old_newslot, _new_newslot, 1)

        _edit_pick = '            o=mp[st.selectbox("Modifier un créneau",list(mp))]\n            with st.form("editslot"):'
        _edit_pick_new = '''            o=mp[st.selectbox("Modifier un créneau",list(mp))]
            _resp_row=one("SELECT * FROM offre_responsables WHERE offre_id=?",(o["id"],))
            _resp_names=["Hervé","Luhpo","Raphaël","Dudu","Geoffrey","Bernard","Mathieu","Michel","Stéphanie","Yan-Erick","Patrick","Sébastien"]
            _current_resp=(_resp_row.get("responsable") or "") if _resp_row else ""
            _current_co=(_resp_row.get("coresponsable") or "") if _resp_row else ""
            if _current_resp and _current_resp not in _resp_names: _resp_names.append(_current_resp)
            if _current_co and _current_co not in _resp_names: _resp_names.append(_current_co)
            _resp_options=["— Non attribué —"]+_resp_names
            _co_edit_options=["Aucun"]+_resp_names
            with st.form("editslot"):'''
        if _edit_pick in source and '_resp_row=one("SELECT * FROM offre_responsables' not in source:
            source = source.replace(_edit_pick, _edit_pick_new, 1)

        _edit_capacity = '                e,f=st.columns(2); ec=e.number_input("Capacité",1,200,int(o["capacite"])); ep=f.selectbox("Public",["Tous","Étudiants","Personnel"],index=["Tous","Étudiants","Personnel"].index(o["public"]) if o["public"] in ["Tous","Étudiants","Personnel"] else 0)'
        _edit_capacity_new = _edit_capacity + '''
                _can_change_resp=st.session_state.get("teacher_role")=="Admin"
                r1,r2=st.columns(2)
                eresp=r1.selectbox("Responsable",_resp_options,index=_resp_options.index(_current_resp) if _current_resp in _resp_options else 0,disabled=not _can_change_resp,key=f"edit_resp_{o['id']}")
                ecoresp=r2.selectbox("Co-responsable",_co_edit_options,index=_co_edit_options.index(_current_co) if _current_co in _co_edit_options else 0,disabled=not _can_change_resp,key=f"edit_co_{o['id']}")
                if not _can_change_resp: st.caption("Le responsable peut être modifié uniquement par un administrateur.")'''
        if _edit_capacity in source and 'key=f"edit_resp_{o[\'id\']}"' not in source:
            source = source.replace(_edit_capacity, _edit_capacity_new, 1)

        _save_line = '            if save: exe("UPDATE offres SET activite=?,intitule=?,jour_horaire=?,lieu=?,capacite=?,public=?,ouverte=? WHERE id=?",(ea,et,eh,el,ec,ep,int(opened),o["id"])); st.success("Créneau mis à jour."); st.rerun()'
        _save_block = '''            if save:
                if eresp=="— Non attribué —" and ecoresp!="Aucun":
                    st.error("Choisis d'abord un responsable principal.")
                elif eresp!="— Non attribué —" and ecoresp!="Aucun" and eresp==ecoresp:
                    st.error("Le responsable et le co-responsable doivent être deux personnes différentes.")
                else:
                    exe("UPDATE offres SET activite=?,intitule=?,jour_horaire=?,lieu=?,capacite=?,public=?,ouverte=? WHERE id=?",(ea,et,eh,el,ec,ep,int(opened),o["id"]))
                    _resp_value="" if eresp=="— Non attribué —" else eresp
                    _co_value="" if ecoresp=="Aucun" else ecoresp
                    _existing_resp=one("SELECT id FROM offre_responsables WHERE offre_id=?",(o["id"],))
                    if _resp_value:
                        if _existing_resp:
                            exe("UPDATE offre_responsables SET responsable=?,coresponsable=?,date_maj=? WHERE offre_id=?",(_resp_value,_co_value,str(date.today()),o["id"]))
                        else:
                            exe("INSERT INTO offre_responsables(offre_id,responsable,coresponsable,cree_par,date_maj) VALUES(?,?,?,?,?)",(o["id"],_resp_value,_co_value,st.session_state.get("teacher_name") or _resp_value,str(date.today())))
                    elif _existing_resp:
                        exe("DELETE FROM offre_responsables WHERE offre_id=?",(o["id"],))
                    st.success("Créneau mis à jour.")
                    st.rerun()'''
        if _save_line in source and '_existing_resp=one("SELECT id FROM offre_responsables' not in source:
            source = source.replace(_save_line, _save_block, 1)

        _delete_offer = '                exe("DELETE FROM offres WHERE id=?",(o["id"],))'
        _delete_offer_new = '''                try: exe("DELETE FROM offre_responsables WHERE offre_id=?",(o["id"],))
                except Exception: pass
                exe("DELETE FROM offres WHERE id=?",(o["id"],))'''
        if _delete_offer in source and 'DELETE FROM offre_responsables WHERE offre_id' not in source:
            source = source.replace(_delete_offer, _delete_offer_new, 1)

        return source

    def _suaps_compile(source, filename, mode, *args, **kwargs):
        source = _patch_suaps_generated_app(source)
        return _original_compile(source, filename, mode, *args, **kwargs)

    builtins.compile = _suaps_compile
except Exception:
    pass

try:
    import streamlit as st
    _md = st.markdown
    _done = False
    _css = r'''<style>
    :root{--navy:#12365d;--blue:#1976d2;--cyan:#24b7c9;--ink:#17283a;--muted:#6f7f91;--line:#e5edf5}
    html,body,[class*="css"]{font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
    .stApp{background:linear-gradient(180deg,#f8faff 0%,#eef4f9 100%)!important;color:var(--ink)}
    .block-container{max-width:1080px!important;padding-top:.8rem!important;padding-bottom:5rem!important}
    header[data-testid="stHeader"]{background:rgba(248,250,255,.84)!important;backdrop-filter:blur(12px)}
    h1,h2,h3{letter-spacing:-.025em!important;color:var(--ink);font-weight:780!important}
    .hero{background:linear-gradient(135deg,#123b68 0%,#176faa 55%,#20b8c5 100%)!important;border-radius:28px!important;padding:29px 26px!important;box-shadow:0 18px 42px rgba(18,54,93,.22)!important;position:relative;overflow:hidden}
    .card{background:rgba(255,255,255,.97)!important;border:1px solid var(--line)!important;border-radius:22px!important;padding:19px!important;margin-bottom:14px!important;box-shadow:0 8px 24px rgba(31,64,98,.075)!important}
    .badge{border-radius:999px!important;padding:6px 11px!important;font-weight:750!important}
    div.stButton>button,div.stFormSubmitButton>button{width:100%;min-height:50px;border-radius:16px!important;font-weight:750!important;border:1px solid #dce7f1!important;box-shadow:0 5px 14px rgba(26,70,110,.08)!important}
    div[data-testid="stMetric"]{background:white!important;border:1px solid var(--line)!important;border-radius:18px!important;padding:13px 15px!important}
    div[data-baseweb="select"]>div,input,textarea{border-radius:14px!important;background:white!important}
    [data-testid="stAlert"],[data-testid="stDataFrame"]{border-radius:16px!important;overflow:hidden}
    @media(max-width:768px){.block-container{padding:.55rem .72rem 5.5rem!important}.hero{border-radius:23px!important;padding:23px 19px!important}.card{border-radius:19px!important;padding:17px!important}}
    </style>'''
    def _styled_markdown(body,*args,**kwargs):
        global _done
        if not _done:
            _done=True
            _md(_css,unsafe_allow_html=True)
        return _md(body,*args,**kwargs)
    st.markdown=_styled_markdown
except Exception:
    pass

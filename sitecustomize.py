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

        # Les transformations suivantes ne concernent que l'application SUAPS générée.
        if "def inscriptions():" not in source or "Enseignant / Admin" not in source:
            return source

        # Pandas sert aux imports/exports CSV.
        if "import pandas as pd" not in source:
            source = source.replace("import streamlit as st", "import streamlit as st\nimport pandas as pd", 1)

        # Table de rattachement des créneaux aux deux semestres 2026/2027.
        marker = "init_db()\n\ndef rows(sql,p=()):"
        migration = '''init_db()\n\n# Périodes universitaires 2026/2027. Un créneau peut être proposé sur un ou deux semestres.\ntry:\n    _c_sem=db()\n    _c_sem.execute("CREATE TABLE IF NOT EXISTS offre_semestres(offre_id INTEGER NOT NULL,semestre TEXT NOT NULL,PRIMARY KEY(offre_id,semestre))")\n    _c_sem.execute("INSERT OR IGNORE INTO offre_semestres(offre_id,semestre) SELECT id,'Semestre 1 — 2026/2027' FROM offres")\n    _c_sem.commit(); _c_sem.close()\nexcept Exception:\n    pass\n\ndef rows(sql,p=()):'''
        if marker in source and "CREATE TABLE IF NOT EXISTS offre_semestres" not in source:
            source = source.replace(marker, migration, 1)

        # Choix du semestre côté étudiant avant la liste des activités/créneaux.
        old_ins = '''    fam=st.selectbox("Famille d’activités",[x[1] for x in FAMILLES])\n    acts=FAMILY_MAP.get(fam,[])\n    data=rows("SELECT o.*,COUNT(CASE WHEN i.statut='Inscrit' THEN 1 END) n FROM offres o LEFT JOIN inscriptions i ON i.offre_id=o.id WHERE o.ouverte=1 GROUP BY o.id ORDER BY o.activite,o.intitule")'''
        new_ins = '''    semestre=st.radio("Année 2026/2027",["Semestre 1 — 2026/2027","Semestre 2 — 2026/2027"],horizontal=True,key="ins_semestre")\n    fam=st.selectbox("Famille d’activités",[x[1] for x in FAMILLES])\n    acts=FAMILY_MAP.get(fam,[])\n    data=rows("SELECT o.*,COUNT(CASE WHEN i.statut='Inscrit' THEN 1 END) n FROM offres o JOIN offre_semestres os ON os.offre_id=o.id AND os.semestre=? LEFT JOIN inscriptions i ON i.offre_id=o.id WHERE o.ouverte=1 GROUP BY o.id ORDER BY o.activite,o.intitule",(semestre,))'''
        if old_ins in source and "key=\"ins_semestre\"" not in source:
            source = source.replace(old_ins, new_ins, 1)

        # Nouvelle rubrique enseignant.
        old_radio = 'sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")'
        new_radio = 'sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités","Semestres & CSV"],horizontal=True,key="admin_section")'
        source = source.replace(old_radio, new_radio)

        # Rend la branche Actualités explicite pour réserver le dernier else à Semestres & CSV.
        source = source.replace(
            '    else:\n        st.markdown("### 📰 Gestion des Infos Live")',
            '    elif sec=="Actualités":\n        st.markdown("### 📰 Gestion des Infos Live")',
            1,
        )

        # Ajout du panneau Semestres & CSV juste avant le bouton de retour de l'administration.
        tail = '''            if supprimer: exe("DELETE FROM actualites WHERE id=?",(n["id"],)); st.success("Information supprimée."); st.rerun()\n    if st.button("← Accueil"): go("Accueil")'''
        semester_block = '''            if supprimer: exe("DELETE FROM actualites WHERE id=?",(n["id"],)); st.success("Information supprimée."); st.rerun()\n    else:\n        st.markdown("### 📅 Semestres 2026/2027")\n        st.caption("Affecte chaque créneau au Semestre 1, au Semestre 2 ou aux deux.")\n        offs_sem=rows("SELECT * FROM offres ORDER BY activite,intitule")\n        if offs_sem:\n            off_sem=st.selectbox("Créneau à paramétrer",offs_sem,format_func=lambda r:f"{r['activite']} — {r['intitule']}",key="semester_offer")\n            linked={r["semestre"] for r in rows("SELECT semestre FROM offre_semestres WHERE offre_id=?",(off_sem["id"],))}\n            s1=st.checkbox("Semestre 1 — 2026/2027","Semestre 1 — 2026/2027" in linked,key="semester_s1")\n            s2=st.checkbox("Semestre 2 — 2026/2027","Semestre 2 — 2026/2027" in linked,key="semester_s2")\n            if st.button("Enregistrer les semestres",type="primary",key="save_semesters"):\n                exe("DELETE FROM offre_semestres WHERE offre_id=?",(off_sem["id"],))\n                if s1: exe("INSERT OR IGNORE INTO offre_semestres(offre_id,semestre) VALUES(?,?)",(off_sem["id"],"Semestre 1 — 2026/2027"))\n                if s2: exe("INSERT OR IGNORE INTO offre_semestres(offre_id,semestre) VALUES(?,?)",(off_sem["id"],"Semestre 2 — 2026/2027"))\n                st.success("Semestres du créneau enregistrés."); st.rerun()\n\n        st.markdown("### 📥 Import CSV étudiants")\n        st.caption("Colonnes : nom, prenom, email. Facultatif : identifiant, composante, profil.")\n        csv_file=st.file_uploader("Choisir un fichier CSV",type=["csv"],key="import_users_csv")\n        if csv_file is not None:\n            try:\n                imp=pd.read_csv(csv_file)\n                imp.columns=[str(c).strip().lower() for c in imp.columns]\n                missing=[c for c in ["nom","prenom","email"] if c not in imp.columns]\n                if missing:\n                    st.error("Colonnes manquantes : "+", ".join(missing))\n                elif st.button("Importer les étudiants",type="primary",key="do_import_users"):\n                    added=0; updated=0\n                    for _,r in imp.iterrows():\n                        email=str(r.get("email","")).strip()\n                        if not email or email.lower()=="nan": continue\n                        profil=str(r.get("profil","Étudiant")).strip()\n                        if not profil or profil.lower()=="nan": profil="Étudiant"\n                        ident=str(r.get("identifiant","")).strip(); ident="" if ident.lower()=="nan" else ident\n                        compo=str(r.get("composante","")).strip(); compo="" if compo.lower()=="nan" else compo\n                        exist=one("SELECT id FROM utilisateurs WHERE email=?",(email,))\n                        if exist:\n                            exe("UPDATE utilisateurs SET nom=?,prenom=?,identifiant=?,composante=?,profil=?,actif=1 WHERE id=?",(str(r.get("nom","")).strip(),str(r.get("prenom","")).strip(),ident,compo,profil,exist["id"])); updated+=1\n                        else:\n                            exe("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,composante,actif) VALUES(?,?,?,?,?,?,1)",(profil,str(r.get("nom","")).strip(),str(r.get("prenom","")).strip(),email,ident,compo)); added+=1\n                    st.success(f"Import terminé : {added} ajouté(s), {updated} mis à jour.")\n            except Exception as e:\n                st.error(f"Erreur d'import CSV : {e}")\n\n        st.markdown("### 📤 Exports CSV")\n        export_sem=st.radio("Semestre à exporter",["Semestre 1 — 2026/2027","Semestre 2 — 2026/2027"],horizontal=True,key="export_semester")\n        ins_rows=rows("SELECT u.nom AS 'Nom',u.prenom AS 'Prénom',u.email AS 'Email',o.activite AS 'Activité',o.intitule AS 'Créneau',i.modalite AS 'Modalité',i.statut AS 'Statut',i.date_inscription AS 'Date inscription' FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id JOIN offres o ON o.id=i.offre_id JOIN offre_semestres os ON os.offre_id=o.id AND os.semestre=? ORDER BY o.activite,u.nom,u.prenom",(export_sem,))\n        pre_rows=rows("SELECT u.nom AS 'Nom',u.prenom AS 'Prénom',u.email AS 'Email',o.activite AS 'Activité',o.intitule AS 'Créneau',s.date_seance AS 'Date séance',p.statut AS 'Présence',p.mode_validation AS 'Mode' FROM presences p JOIN utilisateurs u ON u.id=p.utilisateur_id JOIN seances s ON s.id=p.seance_id JOIN offres o ON o.id=s.offre_id JOIN offre_semestres os ON os.offre_id=o.id AND os.semestre=? ORDER BY s.date_seance,o.activite,u.nom,u.prenom",(export_sem,))\n        eva_rows=rows("SELECT u.nom AS 'Nom',u.prenom AS 'Prénom',u.email AS 'Email',e.activite AS 'Activité',e.intitule AS 'Évaluation',e.note AS 'Note',e.bareme AS 'Barème',e.coefficient AS 'Coefficient',e.date_eval AS 'Date' FROM evaluations e JOIN utilisateurs u ON u.id=e.utilisateur_id WHERE EXISTS(SELECT 1 FROM offres o JOIN offre_semestres os ON os.offre_id=o.id WHERE os.semestre=? AND o.activite=e.activite) ORDER BY e.activite,u.nom,u.prenom",(export_sem,))\n        cex1,cex2,cex3=st.columns(3)\n        cex1.download_button("Inscriptions CSV",pd.DataFrame(ins_rows).to_csv(index=False).encode("utf-8-sig"),file_name=f"inscriptions_{export_sem.split('—')[0].strip().lower().replace(' ','_')}_2026_2027.csv",mime="text/csv",use_container_width=True)\n        cex2.download_button("Présences CSV",pd.DataFrame(pre_rows).to_csv(index=False).encode("utf-8-sig"),file_name=f"presences_{export_sem.split('—')[0].strip().lower().replace(' ','_')}_2026_2027.csv",mime="text/csv",use_container_width=True)\n        cex3.download_button("Évaluations CSV",pd.DataFrame(eva_rows).to_csv(index=False).encode("utf-8-sig"),file_name=f"evaluations_{export_sem.split('—')[0].strip().lower().replace(' ','_')}_2026_2027.csv",mime="text/csv",use_container_width=True)\n    if st.button("← Accueil"): go("Accueil")'''
        if tail in source and "### 📅 Semestres 2026/2027" not in source:
            source = source.replace(tail, semester_block, 1)

        return source

    def _suaps_compile(source, filename, mode, *args, **kwargs):
        source = _patch_suaps_generated_app(source)
        return _original_compile(source, filename, mode, *args, **kwargs)

    builtins.compile = _suaps_compile
except Exception:
    pass

# Identité visuelle SUAPS complémentaire.
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

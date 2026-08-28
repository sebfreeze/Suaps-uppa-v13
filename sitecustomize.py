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
        semester_block = '''            if supprimer: exe("DELETE FROM actualites WHERE id=?",(n["id"],)); st.success("Information supprimée."); st.rerun()\n    else:\n        st.markdown("### 📅 Semestres 2026/2027")\n        st.caption("Affecte chaque créneau au Semestre 1, au Semestre 2 ou aux deux.")\n        offs_sem=rows("SELECT * FROM offres ORDER BY activite,intitule,jour_horaire")\n        if offs_sem:\n            off_sem=st.selectbox("Créneau à paramétrer",offs_sem,format_func=lambda r:f"{r['activite']} — {r['intitule']} — {r['jour_horaire'] or 'horaire à définir'}",key="semester_offer")\n            linked={r["semestre"] for r in rows("SELECT semestre FROM offre_semestres WHERE offre_id=?",(off_sem["id"],))}\n            s1=st.checkbox("Semestre 1 — 2026/2027","Semestre 1 — 2026/2027" in linked,key="semester_s1")\n            s2=st.checkbox("Semestre 2 — 2026/2027","Semestre 2 — 2026/2027" in linked,key="semester_s2")\n            if st.button("Enregistrer les semestres",type="primary",key="save_semesters"):\n                exe("DELETE FROM offre_semestres WHERE offre_id=?",(off_sem["id"],))\n                if s1: exe("INSERT OR IGNORE INTO offre_semestres(offre_id,semestre) VALUES(?,?)",(off_sem["id"],"Semestre 1 — 2026/2027"))\n                if s2: exe("INSERT OR IGNORE INTO offre_semestres(offre_id,semestre) VALUES(?,?)",(off_sem["id"],"Semestre 2 — 2026/2027"))\n                st.success("Semestres du créneau enregistrés."); st.rerun()\n\n        st.markdown("### 📥 Import CSV étudiants et inscriptions")\n        st.caption("Import global possible : chaque étudiant est automatiquement réparti dans son activité et son créneau.")\n        st.info("Colonnes obligatoires : nom, prenom, email, activite, creneau. Recommandées : semestre, modalite, jour_horaire. Facultatives : identifiant, composante, profil.")\n        modele=pd.DataFrame([{\n            "nom":"DUPONT","prenom":"Paul","email":"paul.dupont@etu.univ-pau.fr","identifiant":"12345678","composante":"STAPS","profil":"Étudiant",\n            "semestre":"Semestre 1 — 2026/2027","modalite":"UET","activite":"Natation","creneau":"Natation tous niveaux","jour_horaire":"Lundi 18h00"\n        }])\n        st.download_button("⬇️ Télécharger un modèle CSV",modele.to_csv(index=False).encode("utf-8-sig"),file_name="modele_import_suaps_2026_2027.csv",mime="text/csv",key="download_import_template")\n        csv_file=st.file_uploader("Choisir le fichier CSV global",type=["csv"],key="import_users_csv")\n        if csv_file is not None:\n            try:\n                imp=pd.read_csv(csv_file,sep=None,engine="python")\n                imp.columns=[str(c).strip().lower().replace("é","e").replace("è","e").replace("ê","e") for c in imp.columns]\n                aliases={"activité":"activite","créneau":"creneau","modalité":"modalite","prénom":"prenom","n° étudiant":"identifiant","numero_etudiant":"identifiant","formation":"composante","horaire":"jour_horaire"}\n                imp=imp.rename(columns={c:aliases.get(c,c) for c in imp.columns})\n                required=["nom","prenom","email","activite","creneau"]\n                missing=[c for c in required if c not in imp.columns]\n                if missing:\n                    st.error("Colonnes obligatoires manquantes : "+", ".join(missing))\n                else:\n                    st.dataframe(imp.head(25),use_container_width=True,hide_index=True)\n                    if st.button("Importer et répartir les étudiants",type="primary",key="do_import_users"):\n                        added=0; updated=0; enrolled=0; changed=0; errors=[]\n                        for idx,r in imp.iterrows():\n                            line=int(idx)+2\n                            def clean(name,default=""):\n                                v=str(r.get(name,default)).strip()\n                                return "" if v.lower()=="nan" else v\n                            nom=clean("nom"); prenom=clean("prenom"); email=clean("email").lower(); activite=clean("activite"); creneau=clean("creneau"); horaire=clean("jour_horaire")\n                            if not nom or not prenom or not email or not activite or not creneau:\n                                errors.append({"ligne":line,"email":email,"erreur":"Champ obligatoire vide"}); continue\n                            semestre=clean("semestre","Semestre 1 — 2026/2027")\n                            if semestre in ("S1","Semestre 1","1"): semestre="Semestre 1 — 2026/2027"\n                            elif semestre in ("S2","Semestre 2","2"): semestre="Semestre 2 — 2026/2027"\n                            if semestre not in ("Semestre 1 — 2026/2027","Semestre 2 — 2026/2027"):\n                                errors.append({"ligne":line,"email":email,"erreur":"Semestre inconnu"}); continue\n                            modalite=clean("modalite","Non noté")\n                            norm_mod={"uet":"UET","uecf":"UECF","non note":"Non noté","non noté":"Non noté","non-note":"Non noté"}\n                            modalite=norm_mod.get(modalite.lower(),modalite)\n                            if modalite not in ("UET","UECF","Non noté"):\n                                errors.append({"ligne":line,"email":email,"erreur":"Modalité inconnue : "+modalite}); continue\n                            matches=rows("SELECT o.* FROM offres o JOIN offre_semestres os ON os.offre_id=o.id AND os.semestre=? WHERE lower(trim(o.activite))=lower(trim(?)) AND lower(trim(o.intitule))=lower(trim(?)) ORDER BY o.id",(semestre,activite,creneau))\n                            if horaire:\n                                matches=[o for o in matches if str(o.get("jour_horaire") or "").strip().lower()==horaire.lower()]\n                            if len(matches)==0:\n                                errors.append({"ligne":line,"email":email,"erreur":f"Créneau introuvable : {activite} / {creneau} / {semestre}"}); continue\n                            if len(matches)>1:\n                                errors.append({"ligne":line,"email":email,"erreur":"Plusieurs créneaux correspondent : renseigner jour_horaire"}); continue\n                            offre=matches[0]\n                            profil=clean("profil","Étudiant") or "Étudiant"; ident=clean("identifiant"); compo=clean("composante")\n                            exist=one("SELECT id FROM utilisateurs WHERE lower(email)=lower(?)",(email,))\n                            if exist:\n                                exe("UPDATE utilisateurs SET nom=?,prenom=?,identifiant=?,composante=?,profil=?,actif=1 WHERE id=?",(nom,prenom,ident,compo,profil,exist["id"])); uid=exist["id"]; updated+=1\n                            else:\n                                uid=exe("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,composante,actif) VALUES(?,?,?,?,?,?,1)",(profil,nom,prenom,email,ident,compo)); added+=1\n                            old_reg=one("SELECT id,modalite,statut FROM inscriptions WHERE utilisateur_id=? AND offre_id=?",(uid,offre["id"]))\n                            if old_reg:\n                                exe("UPDATE inscriptions SET modalite=?,statut='Inscrit' WHERE id=?",(modalite,old_reg["id"])); changed+=1\n                            else:\n                                exe("INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,statut,date_inscription) VALUES(?,?,?,'Inscrit',?)",(uid,offre["id"],modalite,str(date.today()))); enrolled+=1\n                        st.success(f"Import terminé : {added} étudiant(s) créé(s), {updated} mis à jour, {enrolled} nouvelle(s) inscription(s), {changed} inscription(s) mise(s) à jour.")\n                        if errors:\n                            st.warning(f"{len(errors)} ligne(s) non importée(s).")\n                            st.dataframe(pd.DataFrame(errors),use_container_width=True,hide_index=True)\n            except Exception as e:\n                st.error(f"Erreur d'import CSV : {e}")\n\n        st.markdown("### 📤 Exports CSV")\n        export_sem=st.radio("Semestre à exporter",["Semestre 1 — 2026/2027","Semestre 2 — 2026/2027"],horizontal=True,key="export_semester")\n        ins_rows=rows("SELECT u.nom AS 'Nom',u.prenom AS 'Prénom',u.email AS 'Email',u.identifiant AS 'N° étudiant',u.composante AS 'Composante',o.activite AS 'Activité',o.intitule AS 'Créneau',o.jour_horaire AS 'Jour / horaire',i.modalite AS 'Modalité',i.statut AS 'Statut',i.date_inscription AS 'Date inscription' FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id JOIN offres o ON o.id=i.offre_id JOIN offre_semestres os ON os.offre_id=o.id AND os.semestre=? ORDER BY o.activite,o.intitule,u.nom,u.prenom",(export_sem,))\n        pre_rows=rows("SELECT u.nom AS 'Nom',u.prenom AS 'Prénom',u.email AS 'Email',o.activite AS 'Activité',o.intitule AS 'Créneau',o.jour_horaire AS 'Jour / horaire',s.date_seance AS 'Date séance',p.statut AS 'Présence',p.mode_validation AS 'Mode' FROM presences p JOIN utilisateurs u ON u.id=p.utilisateur_id JOIN seances s ON s.id=p.seance_id JOIN offres o ON o.id=s.offre_id JOIN offre_semestres os ON os.offre_id=o.id AND os.semestre=? ORDER BY s.date_seance,o.activite,u.nom,u.prenom",(export_sem,))\n        eva_rows=rows("SELECT u.nom AS 'Nom',u.prenom AS 'Prénom',u.email AS 'Email',e.activite AS 'Activité',e.intitule AS 'Évaluation',e.note AS 'Note',e.bareme AS 'Barème',e.coefficient AS 'Coefficient',e.date_eval AS 'Date' FROM evaluations e JOIN utilisateurs u ON u.id=e.utilisateur_id WHERE EXISTS(SELECT 1 FROM offres o JOIN offre_semestres os ON os.offre_id=o.id WHERE os.semestre=? AND o.activite=e.activite) ORDER BY e.activite,u.nom,u.prenom",(export_sem,))\n        cex1,cex2,cex3=st.columns(3)\n        cex1.download_button("Inscriptions CSV",pd.DataFrame(ins_rows).to_csv(index=False).encode("utf-8-sig"),file_name=f"inscriptions_{export_sem.split('—')[0].strip().lower().replace(' ','_')}_2026_2027.csv",mime="text/csv",use_container_width=True)\n        cex2.download_button("Présences CSV",pd.DataFrame(pre_rows).to_csv(index=False).encode("utf-8-sig"),file_name=f"presences_{export_sem.split('—')[0].strip().lower().replace(' ','_')}_2026_2027.csv",mime="text/csv",use_container_width=True)\n        cex3.download_button("Évaluations CSV",pd.DataFrame(eva_rows).to_csv(index=False).encode("utf-8-sig"),file_name=f"evaluations_{export_sem.split('—')[0].strip().lower().replace(' ','_')}_2026_2027.csv",mime="text/csv",use_container_width=True)\n    if st.button("← Accueil"): go("Accueil")'''
        if tail in source and "### 📅 Semestres 2026/2027" not in source:
            source = source.replace(tail, semester_block, 1)

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

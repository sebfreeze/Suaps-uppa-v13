from pathlib import Path

# V17.1 : V15 + Infos Live + évaluation /20 + correctifs de fonctionnement.
base_path = Path(__file__).with_name("v15_base.py")
base = base_path.read_text(encoding="utf-8")

injection = r'''
# Compatibilité Streamlit : sqlite.Row -> dict sérialisable.
source = source.replace("def rows(sql,p=()):\n    c=db(); r=c.execute(sql,p).fetchall(); c.close(); return r", "def rows(sql,p=()):\n    c=db(); r=c.execute(sql,p).fetchall(); c.close(); return [dict(x) for x in r]")

# Navigation mobile réellement cliquable.
source = source.replace("""def nav():
    st.markdown('<div class=\"bottom-nav\"><span><b>⌂</b>Accueil</span><span><b>⚡</b>Activités</span><span><b>▣</b>Inscription</span><span><b>↗</b>Résultats</span><span><b>●</b>Profil</span></div>',unsafe_allow_html=True)""", """def nav():
    st.markdown('<div style=\"height:8px\"></div>',unsafe_allow_html=True)
    cols=st.columns(5)
    items=[("⌂ Accueil","Accueil"),("⚡ Activités","Famille"),("▣ Inscription","Inscriptions"),("↗ Résultats","Résultats"),("● Profil","Mon espace")]
    for col,(label,target) in zip(cols,items):
        with col:
            if st.button(label,key=f"bottom_{target}_{st.session_state.page}",use_container_width=True):
                if target=="Famille" and not st.session_state.family:
                    st.session_state.family=FAMILLES[0][1]
                if target in ("Inscriptions","Résultats","Mon espace") and not st.session_state.user_id:
                    if not st.session_state.profil: st.session_state.profil="Étudiant"
                    go("Connexion")
                else:
                    go(target)""")

# Tables V17.
source = source.replace("    CREATE TABLE IF NOT EXISTS baremes(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,nom TEXT NOT NULL,description TEXT,unite TEXT DEFAULT 'points',valeur_0 REAL DEFAULT 0,valeur_20 REAL DEFAULT 20,actif INTEGER DEFAULT 1);", "    CREATE TABLE IF NOT EXISTS baremes(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,nom TEXT NOT NULL,description TEXT,unite TEXT DEFAULT 'points',valeur_0 REAL DEFAULT 0,valeur_20 REAL DEFAULT 20,actif INTEGER DEFAULT 1);\n    CREATE TABLE IF NOT EXISTS actualites(id INTEGER PRIMARY KEY AUTOINCREMENT,categorie TEXT NOT NULL,titre TEXT NOT NULL,contenu TEXT NOT NULL,date_publication TEXT NOT NULL,lien TEXT,actif INTEGER DEFAULT 1);\n    CREATE TABLE IF NOT EXISTS evaluations_finales(id INTEGER PRIMARY KEY AUTOINCREMENT,utilisateur_id INTEGER NOT NULL,activite TEXT NOT NULL,performance REAL DEFAULT 0,competences REAL DEFAULT 0,presences REAL DEFAULT 0,projet REAL DEFAULT 0,total REAL DEFAULT 0,commentaire TEXT,date_evaluation TEXT,UNIQUE(utilisateur_id,activite));")

# Infos Live sur l'accueil + page dédiée.
source = source.replace("    nav()\n\ndef famille():", """    st.markdown('<div class=\"section-title\">🔥 Infos Live</div>',unsafe_allow_html=True)
    nb_live=one("SELECT COUNT(*) n FROM actualites WHERE actif=1")
    label_live=f"🔥 Infos Live • {nb_live['n']} info(s)" if nb_live and nb_live['n'] else "🔥 Infos Live"
    if st.button(label_live,key="home_infos_live",type="primary"): go("Infos Live")
    nav()

def infos_live():
    topbar(); hero("Infos Live","Toute l'actualité sportive et la vie du campus au même endroit.","SUAPS • EN DIRECT")
    filtre=st.radio("Rubrique",["Toutes","SUAPS Live","Association sportive","Vie de campus"],horizontal=True,key="infos_filter")
    news=rows("SELECT * FROM actualites WHERE actif=1 ORDER BY date_publication DESC,id DESC") if filtre=="Toutes" else rows("SELECT * FROM actualites WHERE actif=1 AND categorie=? ORDER BY date_publication DESC,id DESC",(filtre,))
    if not news: st.info("Aucune information publiée pour le moment.")
    for n in news:
        badge_cat={"SUAPS Live":"🔥 SUAPS Live","Association sportive":"🏆 Association sportive","Vie de campus":"🎓 Vie de campus"}.get(n["categorie"],n["categorie"])
        card(n["titre"],n["contenu"],[badge_cat,n["date_publication"]])
        if n["lien"]: st.link_button("En savoir plus",n["lien"],use_container_width=True)
    if st.button("← Accueil",key="infos_back"): go("Accueil")
    nav()

def famille():""")

# Accès aux pages privées : évite les erreurs si une page est appelée sans utilisateur connecté.
for _name in ("inscriptions","planning","presence","resultats"):
    source = source.replace(f"def {_name}():\n    u=user(); topbar()", f"def {_name}():\n    u=user()\n    if not u:\n        if not st.session_state.profil: st.session_state.profil='Étudiant'\n        go('Connexion')\n    topbar()")

# Présence QR : un étudiant ne peut valider que la séance d'un créneau auquel il est inscrit.
source = source.replace("SELECT s.id,o.activite FROM seances s JOIN offres o ON o.id=s.offre_id WHERE s.qr_token=? AND s.qr_ouvert=1 ORDER BY s.id DESC LIMIT 1", "SELECT s.id,s.offre_id,o.activite FROM seances s JOIN offres o ON o.id=s.offre_id WHERE s.qr_token=? AND s.qr_ouvert=1 ORDER BY s.id DESC LIMIT 1")
source = source.replace("""        if not s: st.error("Code invalide ou fermé.")
        else:
            try: exe("INSERT INTO presences(seance_id,utilisateur_id,statut,mode_validation) VALUES(?,?,?,?)",(s["id"],u["id"],"Présent","QR"))""", """        if not s: st.error("Code invalide ou fermé.")
        elif not one("SELECT id FROM inscriptions WHERE utilisateur_id=? AND offre_id=? AND statut='Inscrit'",(u["id"],s["offre_id"])):
            st.error("Tu n'es pas inscrit à ce créneau.")
        else:
            try: exe("INSERT INTO presences(seance_id,utilisateur_id,statut,mode_validation) VALUES(?,?,?,?)",(s["id"],u["id"],"Présent","QR"))""")

# Suppression d'un créneau avec nettoyage des données liées.
source = source.replace("opened=st.checkbox(\"Ouvert aux inscriptions\",bool(o[\"ouverte\"])); save=st.form_submit_button(\"Enregistrer\",type=\"primary\")", "opened=st.checkbox(\"Ouvert aux inscriptions\",bool(o[\"ouverte\"])); bsave,bdel=st.columns(2); save=bsave.form_submit_button(\"Enregistrer\",type=\"primary\"); delete_slot=bdel.form_submit_button(\"Supprimer le créneau\")")
source = source.replace("""            if save: exe("UPDATE offres SET activite=?,intitule=?,jour_horaire=?,lieu=?,capacite=?,public=?,ouverte=? WHERE id=?",(ea,et,eh,el,ec,ep,int(opened),o["id"])); st.success("Créneau mis à jour."); st.rerun()
    elif sec=="Présences":""", """            if save: exe("UPDATE offres SET activite=?,intitule=?,jour_horaire=?,lieu=?,capacite=?,public=?,ouverte=? WHERE id=?",(ea,et,eh,el,ec,ep,int(opened),o["id"])); st.success("Créneau mis à jour."); st.rerun()
            if delete_slot:
                exe("DELETE FROM presences WHERE seance_id IN (SELECT id FROM seances WHERE offre_id=?)",(o["id"],))
                exe("DELETE FROM seances WHERE offre_id=?",(o["id"],))
                exe("DELETE FROM inscriptions WHERE offre_id=?",(o["id"],))
                try: exe("DELETE FROM offre_semestres WHERE offre_id=?",(o["id"],))
                except Exception: pass
                exe("DELETE FROM offres WHERE id=?",(o["id"],))
                st.success("Créneau supprimé."); st.rerun()
    elif sec=="Présences":""")

# Évaluation /20 et Actualités dans l'espace enseignant.
source = source.replace('    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Compétences","Barèmes"],horizontal=True,key="admin_section")','    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")')
source = source.replace("""    elif sec=="Compétences":
        actc=st.selectbox""", """    elif sec=="Évaluation /20":
        st.markdown("### 🎯 Évaluation finale sur 20")
        st.caption("Performance 7 pts + Compétences 7 pts + Présences 3 pts + Projet / investissement 3 pts")
        us=rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' AND actif=1 ORDER BY nom,prenom")
        if not us: st.info("Aucun étudiant actif.")
        else:
            p=st.selectbox("Étudiant",us,format_func=lambda r:f"{r['nom']} {r['prenom']}",key="eval20_student")
            act=st.selectbox("Activité",ACTIVITES,key="eval20_act")
            old=one("SELECT * FROM evaluations_finales WHERE utilisateur_id=? AND activite=?",(p["id"],act))
            vp=float(old["performance"]) if old else 0.0; vc=float(old["competences"]) if old else 0.0; va=float(old["presences"]) if old else 0.0; vi=float(old["projet"]) if old else 0.0
            with st.form("eval20_form"):
                c1,c2=st.columns(2); perf=c1.number_input("🏃 Performance /7",0.0,7.0,vp,0.5); comp=c2.number_input("🎯 Compétences /7",0.0,7.0,vc,0.5)
                c3,c4=st.columns(2); pres=c3.number_input("📅 Présences /3",0.0,3.0,va,0.25); proj=c4.number_input("🤝 Projet / investissement /3",0.0,3.0,vi,0.25)
                commentaire=st.text_area("Commentaire",old["commentaire"] if old and old["commentaire"] else "")
                total=perf+comp+pres+proj; st.metric("Note finale calculée",f"{total:.2f} / 20"); save=st.form_submit_button("Enregistrer l'évaluation",type="primary")
            if save:
                exist=one("SELECT id FROM evaluations_finales WHERE utilisateur_id=? AND activite=?",(p["id"],act))
                if exist: exe("UPDATE evaluations_finales SET performance=?,competences=?,presences=?,projet=?,total=?,commentaire=?,date_evaluation=? WHERE id=?",(perf,comp,pres,proj,total,commentaire,str(date.today()),exist["id"]))
                else: exe("INSERT INTO evaluations_finales(utilisateur_id,activite,performance,competences,presences,projet,total,commentaire,date_evaluation) VALUES(?,?,?,?,?,?,?,?,?)",(p["id"],act,perf,comp,pres,proj,total,commentaire,str(date.today())))
                st.success(f"Évaluation enregistrée : {total:.2f}/20")
    elif sec=="Compétences":
        actc=st.selectbox""")
source = source.replace("""    else:
        actb=st.selectbox("Activité",ACTIVITES,key="bareme_admin_act")""", """    elif sec=="Barèmes":
        actb=st.selectbox("Activité",ACTIVITES,key="bareme_admin_act")""")
source = source.replace("""            st.caption("Les repères 0/20 et 20/20 sont entièrement modifiables par l'enseignant.")
    if st.button("← Accueil"): go("Accueil")""", """            st.caption("Les repères 0/20 et 20/20 sont entièrement modifiables par l'enseignant.")
    else:
        st.markdown("### 📰 Gestion des Infos Live")
        with st.expander("➕ Publier une information",expanded=True):
            with st.form("add_actualite"):
                cat=st.selectbox("Rubrique",["SUAPS Live","Association sportive","Vie de campus"]); titre=st.text_input("Titre"); contenu=st.text_area("Information"); dpub=st.date_input("Date de publication",date.today()); lien=st.text_input("Lien facultatif",placeholder="https://..."); publier=st.form_submit_button("Publier",type="primary")
            if publier:
                if not titre.strip() or not contenu.strip(): st.warning("Le titre et le texte sont obligatoires.")
                else: exe("INSERT INTO actualites(categorie,titre,contenu,date_publication,lien,actif) VALUES(?,?,?,?,?,1)",(cat,titre.strip(),contenu.strip(),str(dpub),lien.strip())); st.success("Information publiée."); st.rerun()
        news=rows("SELECT * FROM actualites ORDER BY date_publication DESC,id DESC")
        if news:
            n=st.selectbox("Information à modifier",news,format_func=lambda r:f"{r['date_publication']} • {r['categorie']} • {r['titre']}",key="news_edit_pick")
            with st.form("edit_actualite"):
                cats=["SUAPS Live","Association sportive","Vie de campus"]; ecat=st.selectbox("Rubrique",cats,index=cats.index(n["categorie"]) if n["categorie"] in cats else 0); etitre=st.text_input("Titre",n["titre"]); econtenu=st.text_area("Information",n["contenu"]); elien=st.text_input("Lien",n["lien"] or ""); eactif=st.checkbox("Visible",bool(n["actif"])); x1,x2=st.columns(2); sauver=x1.form_submit_button("Enregistrer",type="primary"); supprimer=x2.form_submit_button("Supprimer")
            if sauver: exe("UPDATE actualites SET categorie=?,titre=?,contenu=?,lien=?,actif=? WHERE id=?",(ecat,etitre.strip(),econtenu.strip(),elien.strip(),int(eactif),n["id"])); st.success("Information mise à jour."); st.rerun()
            if supprimer: exe("DELETE FROM actualites WHERE id=?",(n["id"],)); st.success("Information supprimée."); st.rerun()
    if st.button("← Accueil"): go("Accueil")""")

# La note finale /20 est maintenant visible côté étudiant dans Résultats > Notes.
source = source.replace("""        for r in data: card(f"{r['activite']} — {r['intitule']}",f"{r['note'] if r['note'] is not None else '-'} / {r['bareme']} • Coef. {r['coefficient']} • {r['date_eval']}")""", """        for r in data: card(f"{r['activite']} — {r['intitule']}",f"{r['note'] if r['note'] is not None else '-'} / {r['bareme']} • Coef. {r['coefficient']} • {r['date_eval']}")
        finales=rows("SELECT * FROM evaluations_finales WHERE utilisateur_id=? ORDER BY date_evaluation DESC,id DESC",(u["id"],))
        for r in finales: card(f"{r['activite']} — Évaluation finale",f"{r['total']:.2f} / 20 • Performance {r['performance']}/7 • Compétences {r['competences']}/7 • Présences {r['presences']}/3 • Projet {r['projet']}/3 • {r['date_evaluation']}",["Note finale"])
        if finales and not data: data=finales""")

# Confirmation correcte lors de la première validation d'une compétence.
source = source.replace("""                try: exe("INSERT INTO acquisitions(utilisateur_id,competence_id,niveau,date_validation) VALUES(?,?,?,?)",(p["id"],c["id"],niv,str(date.today())))
                except sqlite3.IntegrityError: exe("UPDATE acquisitions SET niveau=?,date_validation=? WHERE utilisateur_id=? AND competence_id=?",(niv,str(date.today()),p["id"],c["id"])); st.success("Compétence mise à jour.")""", """                try: exe("INSERT INTO acquisitions(utilisateur_id,competence_id,niveau,date_validation) VALUES(?,?,?,?)",(p["id"],c["id"],niv,str(date.today())))
                except sqlite3.IntegrityError: exe("UPDATE acquisitions SET niveau=?,date_validation=? WHERE utilisateur_id=? AND competence_id=?",(niv,str(date.today()),p["id"],c["id"]))
                st.success("Compétence mise à jour.")""")

source = source.replace('pages={"Accueil":accueil,"Famille":famille,"Connexion":connexion,"Mon espace":espace,"Inscriptions":inscriptions,"Planning":planning,"Présence":presence,"Résultats":resultats,"Administration":admin}','pages={"Accueil":accueil,"Infos Live":infos_live,"Famille":famille,"Connexion":connexion,"Mon espace":espace,"Inscriptions":inscriptions,"Planning":planning,"Présence":presence,"Résultats":resultats,"Administration":admin}')
'''

needle='exec(compile(source, str(source_path), "exec"), globals(), globals())'
if needle not in base:
    raise RuntimeError("Point d'injection V15 introuvable")
base=base.replace(needle,injection+"\n"+needle)
exec(compile(base,str(base_path),"exec"),globals(),globals())

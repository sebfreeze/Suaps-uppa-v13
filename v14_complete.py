from pathlib import Path

# V17 : conserve V15 + Infos Live et ajoute l'évaluation 7/7/3/3.
base_path = Path(__file__).with_name("v15_base.py")
base = base_path.read_text(encoding="utf-8")

injection = r"""
# Compatibilité Streamlit : lignes SQL sérialisables.
source = source.replace('''def rows(sql,p=()):
    c=db(); r=c.execute(sql,p).fetchall(); c.close(); return r''','''def rows(sql,p=()):
    c=db(); r=c.execute(sql,p).fetchall(); c.close(); return [dict(x) for x in r]''')

# Navigation basse : remplace l'ancien HTML décoratif par de vrais boutons.
source = source.replace('''def nav():
    st.markdown('<div class="bottom-nav"><span><b>⌂</b>Accueil</span><span><b>⚡</b>Activités</span><span><b>▣</b>Inscription</span><span><b>↗</b>Résultats</span><span><b>●</b>Profil</span></div>',unsafe_allow_html=True)''','''def nav():
    st.markdown('<div style="height:8px"></div>',unsafe_allow_html=True)
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
                    go(target)''')

# Tables Infos Live + évaluation finale /20.
source = source.replace("    CREATE TABLE IF NOT EXISTS baremes(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,nom TEXT NOT NULL,description TEXT,unite TEXT DEFAULT 'points',valeur_0 REAL DEFAULT 0,valeur_20 REAL DEFAULT 20,actif INTEGER DEFAULT 1);","    CREATE TABLE IF NOT EXISTS baremes(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,nom TEXT NOT NULL,description TEXT,unite TEXT DEFAULT 'points',valeur_0 REAL DEFAULT 0,valeur_20 REAL DEFAULT 20,actif INTEGER DEFAULT 1);\n    CREATE TABLE IF NOT EXISTS actualites(id INTEGER PRIMARY KEY AUTOINCREMENT,categorie TEXT NOT NULL,titre TEXT NOT NULL,contenu TEXT NOT NULL,date_publication TEXT NOT NULL,lien TEXT,actif INTEGER DEFAULT 1);\n    CREATE TABLE IF NOT EXISTS evaluations_finales(id INTEGER PRIMARY KEY AUTOINCREMENT,utilisateur_id INTEGER NOT NULL,activite TEXT NOT NULL,performance REAL DEFAULT 0,competences REAL DEFAULT 0,presences REAL DEFAULT 0,projet REAL DEFAULT 0,total REAL DEFAULT 0,commentaire TEXT,date_evaluation TEXT,UNIQUE(utilisateur_id,activite));")

# Infos Live sur l'accueil et page dédiée.
source = source.replace('''    nav()\n\ndef famille():''','''    st.markdown('<div class="section-title">🔥 Infos Live</div>',unsafe_allow_html=True)
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

def famille():''')

# Ajoute Evaluation /20 et Actualités aux rubriques enseignant.
source = source.replace('    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Compétences","Barèmes"],horizontal=True,key="admin_section")','    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")')

# Le bloc Compétences ne doit plus capter toutes les rubriques suivantes.
source = source.replace('''    elif sec=="Compétences":
        actc=st.selectbox''','''    elif sec=="Évaluation /20":
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
                c1,c2=st.columns(2)
                perf=c1.number_input("🏃 Performance /7",min_value=0.0,max_value=7.0,value=vp,step=0.5)
                comp=c2.number_input("🎯 Compétences /7",min_value=0.0,max_value=7.0,value=vc,step=0.5)
                c3,c4=st.columns(2)
                pres=c3.number_input("📅 Présences /3",min_value=0.0,max_value=3.0,value=va,step=0.25,help="Note d'assiduité, pouvant être ajustée par l'enseignant.")
                proj=c4.number_input("🤝 Projet / investissement /3",min_value=0.0,max_value=3.0,value=vi,step=0.25)
                commentaire=st.text_area("Commentaire",old["commentaire"] if old and old["commentaire"] else "")
                total=perf+comp+pres+proj
                st.metric("Note finale calculée",f"{total:.2f} / 20")
                save=st.form_submit_button("Enregistrer l'évaluation",type="primary")
            if save:
                exist=one("SELECT id FROM evaluations_finales WHERE utilisateur_id=? AND activite=?",(p["id"],act))
                if exist: exe("UPDATE evaluations_finales SET performance=?,competences=?,presences=?,projet=?,total=?,commentaire=?,date_evaluation=? WHERE id=?",(perf,comp,pres,proj,total,commentaire,str(date.today()),exist["id"]))
                else: exe("INSERT INTO evaluations_finales(utilisateur_id,activite,performance,competences,presences,projet,total,commentaire,date_evaluation) VALUES(?,?,?,?,?,?,?,?,?)",(p["id"],act,perf,comp,pres,proj,total,commentaire,str(date.today())))
                st.success(f"Évaluation enregistrée : {total:.2f}/20")
    elif sec=="Compétences":
        actc=st.selectbox''')

# Barèmes puis Actualités.
source = source.replace('''    else:
        actb=st.selectbox("Activité",ACTIVITES,key="bareme_admin_act")''','''    elif sec=="Barèmes":
        actb=st.selectbox("Activité",ACTIVITES,key="bareme_admin_act")''')
source = source.replace('''            st.caption("Les repères 0/20 et 20/20 sont entièrement modifiables par l'enseignant.")
    if st.button("← Accueil"): go("Accueil")''','''            st.caption("Les repères 0/20 et 20/20 sont entièrement modifiables par l'enseignant.")
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
    if st.button("← Accueil"): go("Accueil")''')

source = source.replace('pages={"Accueil":accueil,"Famille":famille,"Connexion":connexion,"Mon espace":espace,"Inscriptions":inscriptions,"Planning":planning,"Présence":presence,"Résultats":resultats,"Administration":admin}','pages={"Accueil":accueil,"Infos Live":infos_live,"Famille":famille,"Connexion":connexion,"Mon espace":espace,"Inscriptions":inscriptions,"Planning":planning,"Présence":presence,"Résultats":resultats,"Administration":admin}')
"""

needle='exec(compile(source, str(source_path), "exec"), globals(), globals())'
if needle not in base: raise RuntimeError("Point d'injection V15 introuvable")
base=base.replace(needle,injection+"\n"+needle)
exec(compile(base,str(base_path),"exec"),globals(),globals())

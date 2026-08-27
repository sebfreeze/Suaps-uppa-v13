from pathlib import Path

# V16 : conserve la V15 validée, puis ajoute le module Infos Live.
base_path = Path(__file__).with_name("v15_base.py")
base = base_path.read_text(encoding="utf-8")

injection = r"""

# --- V16 : Infos Live / Association sportive / Vie de campus ---
# Streamlit 1.62 tente de copier les options des selectbox. sqlite3.Row n'est pas sérialisable,
# on convertit donc toutes les lignes SQL en dictionnaires simples, compatibles partout.
source = source.replace(
'''def rows(sql,p=()):
    c=db(); r=c.execute(sql,p).fetchall(); c.close(); return r''',
'''def rows(sql,p=()):
    c=db(); r=c.execute(sql,p).fetchall(); c.close(); return [dict(x) for x in r]'''
)

source = source.replace(
'''    CREATE TABLE IF NOT EXISTS baremes(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,nom TEXT NOT NULL,description TEXT,unite TEXT DEFAULT 'points',valeur_0 REAL DEFAULT 0,valeur_20 REAL DEFAULT 20,actif INTEGER DEFAULT 1);''',
'''    CREATE TABLE IF NOT EXISTS baremes(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,nom TEXT NOT NULL,description TEXT,unite TEXT DEFAULT 'points',valeur_0 REAL DEFAULT 0,valeur_20 REAL DEFAULT 20,actif INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS actualites(id INTEGER PRIMARY KEY AUTOINCREMENT,categorie TEXT NOT NULL,titre TEXT NOT NULL,contenu TEXT NOT NULL,date_publication TEXT NOT NULL,lien TEXT,actif INTEGER DEFAULT 1);'''
)

source = source.replace(
'''    nav()\n\ndef famille():''',
'''    st.markdown('<div class="section-title">🔥 Infos Live</div>',unsafe_allow_html=True)
    nb_live=one("SELECT COUNT(*) n FROM actualites WHERE actif=1")
    label_live=f"🔥 Infos Live • {nb_live['n']} info(s)" if nb_live and nb_live['n'] else "🔥 Infos Live"
    if st.button(label_live,key="home_infos_live",type="primary"): go("Infos Live")
    nav()

def infos_live():
    topbar(); hero("Infos Live","Toute l'actualité sportive et la vie du campus au même endroit.","SUAPS • EN DIRECT")
    filtre=st.radio("Rubrique",["Toutes","SUAPS Live","Association sportive","Vie de campus"],horizontal=True,key="infos_filter")
    if filtre=="Toutes":
        news=rows("SELECT * FROM actualites WHERE actif=1 ORDER BY date_publication DESC,id DESC")
    else:
        news=rows("SELECT * FROM actualites WHERE actif=1 AND categorie=? ORDER BY date_publication DESC,id DESC",(filtre,))
    if not news:
        st.info("Aucune information publiée pour le moment.")
    for n in news:
        badge_cat={"SUAPS Live":"🔥 SUAPS Live","Association sportive":"🏆 Association sportive","Vie de campus":"🎓 Vie de campus"}.get(n["categorie"],n["categorie"])
        card(n["titre"],n["contenu"],[badge_cat,n["date_publication"]])
        if n["lien"]:
            st.link_button("En savoir plus",n["lien"],use_container_width=True)
    if st.button("← Accueil",key="infos_back"): go("Accueil")
    nav()

def famille():'''
)

source = source.replace(
'    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Compétences","Barèmes"],horizontal=True,key="admin_section")',
'    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")'
)
source = source.replace(
'''    else:\n        actb=st.selectbox("Activité",ACTIVITES,key="bareme_admin_act")''',
'''    elif sec=="Barèmes":
        actb=st.selectbox("Activité",ACTIVITES,key="bareme_admin_act")'''
)
source = source.replace(
'''            st.caption("Principe : les deux valeurs définissent les repères 0/20 et 20/20. L'enseignant peut les adapter à son test et à son public.")\n    if st.button("← Accueil"): go("Accueil")''',
'''            st.caption("Principe : les deux valeurs définissent les repères 0/20 et 20/20. L'enseignant peut les adapter à son test et à son public.")
    else:
        st.markdown("### 📰 Gestion des Infos Live")
        st.caption("Publiez ici les informations visibles immédiatement par les étudiants et personnels.")
        with st.expander("➕ Publier une information",expanded=True):
            with st.form("add_actualite"):
                cat=st.selectbox("Rubrique",["SUAPS Live","Association sportive","Vie de campus"])
                titre=st.text_input("Titre")
                contenu=st.text_area("Information")
                dpub=st.date_input("Date de publication",date.today())
                lien=st.text_input("Lien facultatif",placeholder="https://...")
                publier=st.form_submit_button("Publier",type="primary")
            if publier:
                if not titre.strip() or not contenu.strip(): st.warning("Le titre et le texte sont obligatoires.")
                else:
                    exe("INSERT INTO actualites(categorie,titre,contenu,date_publication,lien,actif) VALUES(?,?,?,?,?,1)",(cat,titre.strip(),contenu.strip(),str(dpub),lien.strip()))
                    st.success("Information publiée."); st.rerun()
        news=rows("SELECT * FROM actualites ORDER BY date_publication DESC,id DESC")
        if news:
            n=st.selectbox("Information à modifier",news,format_func=lambda r:f"{r['date_publication']} • {r['categorie']} • {r['titre']}",key="news_edit_pick")
            with st.form("edit_actualite"):
                cats=["SUAPS Live","Association sportive","Vie de campus"]
                ecat=st.selectbox("Rubrique",cats,index=cats.index(n["categorie"]) if n["categorie"] in cats else 0)
                etitre=st.text_input("Titre",n["titre"])
                econtenu=st.text_area("Information",n["contenu"])
                try: d0=date.fromisoformat(n["date_publication"])
                except Exception: d0=date.today()
                edate=st.date_input("Date",d0)
                elien=st.text_input("Lien",n["lien"] or "")
                eactif=st.checkbox("Visible dans Infos Live",bool(n["actif"]))
                x1,x2=st.columns(2); sauver=x1.form_submit_button("Enregistrer",type="primary"); supprimer=x2.form_submit_button("Supprimer")
            if sauver:
                exe("UPDATE actualites SET categorie=?,titre=?,contenu=?,date_publication=?,lien=?,actif=? WHERE id=?",(ecat,etitre.strip(),econtenu.strip(),str(edate),elien.strip(),int(eactif),n["id"]))
                st.success("Information mise à jour."); st.rerun()
            if supprimer:
                exe("DELETE FROM actualites WHERE id=?",(n["id"],)); st.success("Information supprimée."); st.rerun()
    if st.button("← Accueil"): go("Accueil")'''
)

source = source.replace(
'pages={"Accueil":accueil,"Famille":famille,"Connexion":connexion,"Mon espace":espace,"Inscriptions":inscriptions,"Planning":planning,"Présence":presence,"Résultats":resultats,"Administration":admin}',
'pages={"Accueil":accueil,"Infos Live":infos_live,"Famille":famille,"Connexion":connexion,"Mon espace":espace,"Inscriptions":inscriptions,"Planning":planning,"Présence":presence,"Résultats":resultats,"Administration":admin}'
)
"""

needle = 'exec(compile(source, str(source_path), "exec"), globals(), globals())'
if needle not in base:
    raise RuntimeError("Point d'injection V15 introuvable")
base = base.replace(needle, injection + "\n" + needle)
exec(compile(base, str(base_path), "exec"), globals(), globals())

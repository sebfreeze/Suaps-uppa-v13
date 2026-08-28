# Module Sports collectifs - équipes et feuilles de match
# Chargé par v14_complete.py après initialisation de la base.

SPORTS_CO = ["Rugby", "Basket-ball", "Handball", "Volley-ball", "Football", "Futsal"]


def init_sports_co_db(exe):
    exe("CREATE TABLE IF NOT EXISTS equipes(id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL, activite TEXT NOT NULL, couleur TEXT, capitaine_id INTEGER, date_creation TEXT)")
    exe("CREATE TABLE IF NOT EXISTS equipe_joueurs(id INTEGER PRIMARY KEY AUTOINCREMENT, equipe_id INTEGER NOT NULL, utilisateur_id INTEGER NOT NULL, numero TEXT, poste TEXT, titulaire INTEGER DEFAULT 1, UNIQUE(equipe_id,utilisateur_id))")
    exe("CREATE TABLE IF NOT EXISTS matchs(id INTEGER PRIMARY KEY AUTOINCREMENT, activite TEXT NOT NULL, equipe_a_id INTEGER NOT NULL, equipe_b_id INTEGER NOT NULL, date_match TEXT, heure TEXT, lieu TEXT, arbitre TEXT, score_a INTEGER, score_b INTEGER, statut TEXT DEFAULT 'Prévu', observations TEXT)")


def render_sports_co(st, rows, one, exe, date):
    st.markdown("### 🏆 Équipes & Matchs")
    sport = st.selectbox("Sport collectif", SPORTS_CO, key="sc_sport")
    onglet = st.radio("Gestion", ["Équipes", "Composer", "Matchs", "Feuille de match"], horizontal=True, key="sc_tab")

    if onglet == "Équipes":
        with st.form("sc_add_team"):
            nom = st.text_input("Nom de l'équipe")
            couleur = st.text_input("Couleur / chasuble", placeholder="Bleu, Rouge…")
            add = st.form_submit_button("Créer l'équipe", type="primary")
        if add and nom.strip():
            exe("INSERT INTO equipes(nom,activite,couleur,date_creation) VALUES(?,?,?,?)", (nom.strip(), sport, couleur.strip(), str(date.today())))
            st.success("Équipe créée."); st.rerun()
        teams = rows("SELECT * FROM equipes WHERE activite=? ORDER BY nom", (sport,))
        for t in teams:
            nb = one("SELECT COUNT(*) n FROM equipe_joueurs WHERE equipe_id=?", (t["id"],))
            st.markdown(f"**{t['nom']}** — {t['couleur'] or 'sans couleur'} • {nb['n'] if nb else 0} joueur(s)")

    elif onglet == "Composer":
        teams = rows("SELECT * FROM equipes WHERE activite=? ORDER BY nom", (sport,))
        if not teams:
            st.info("Crée d'abord au moins une équipe."); return
        team = st.selectbox("Équipe", teams, format_func=lambda r:r["nom"], key="sc_team_pick")
        students = rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' AND actif=1 ORDER BY nom,prenom")
        current = rows("SELECT ej.*,u.nom,u.prenom FROM equipe_joueurs ej JOIN utilisateurs u ON u.id=ej.utilisateur_id WHERE ej.equipe_id=? ORDER BY u.nom,u.prenom", (team["id"],))
        current_ids = {r["utilisateur_id"] for r in current}
        choices = [s for s in students if s["id"] not in current_ids]
        if choices:
            player = st.selectbox("Ajouter un joueur", choices, format_func=lambda r:f"{r['nom']} {r['prenom']}", key="sc_player")
            c1,c2 = st.columns(2); numero=c1.text_input("N°", key="sc_num"); poste=c2.text_input("Poste", key="sc_poste")
            titulaire=st.checkbox("Titulaire", True, key="sc_start")
            if st.button("➕ Ajouter à l'équipe", type="primary", key="sc_add_player"):
                exe("INSERT OR IGNORE INTO equipe_joueurs(equipe_id,utilisateur_id,numero,poste,titulaire) VALUES(?,?,?,?,?)", (team["id"],player["id"],numero.strip(),poste.strip(),int(titulaire)))
                st.rerun()
        st.markdown("#### Effectif")
        for p in current:
            c1,c2=st.columns([4,1])
            c1.write(f"{'⭐' if p['titulaire'] else '↪'} {p['numero'] or '-'} • {p['nom']} {p['prenom']} • {p['poste'] or 'poste libre'}")
            if c2.button("Retirer", key=f"sc_rm_{p['id']}"):
                exe("DELETE FROM equipe_joueurs WHERE id=?", (p["id"],)); st.rerun()

    elif onglet == "Matchs":
        teams = rows("SELECT * FROM equipes WHERE activite=? ORDER BY nom", (sport,))
        if len(teams) < 2:
            st.info("Il faut au moins deux équipes pour créer un match."); return
        with st.form("sc_add_match"):
            a=st.selectbox("Équipe A", teams, format_func=lambda r:r["nom"])
            b=st.selectbox("Équipe B", teams, format_func=lambda r:r["nom"], index=1)
            d=st.date_input("Date", date.today()); heure=st.text_input("Heure", placeholder="18:00"); lieu=st.text_input("Lieu"); arbitre=st.text_input("Arbitre")
            create=st.form_submit_button("Créer le match", type="primary")
        if create:
            if a["id"]==b["id"]: st.warning("Choisis deux équipes différentes.")
            else:
                exe("INSERT INTO matchs(activite,equipe_a_id,equipe_b_id,date_match,heure,lieu,arbitre) VALUES(?,?,?,?,?,?,?)", (sport,a["id"],b["id"],str(d),heure.strip(),lieu.strip(),arbitre.strip()))
                st.success("Match créé."); st.rerun()
        matches=rows("SELECT m.*,a.nom equipe_a,b.nom equipe_b FROM matchs m JOIN equipes a ON a.id=m.equipe_a_id JOIN equipes b ON b.id=m.equipe_b_id WHERE m.activite=? ORDER BY m.date_match DESC,m.id DESC", (sport,))
        for m in matches:
            score = "—" if m["score_a"] is None else f"{m['score_a']} - {m['score_b']}"
            st.write(f"**{m['equipe_a']} {score} {m['equipe_b']}** • {m['date_match']} {m['heure'] or ''} • {m['lieu'] or 'lieu à définir'}")

    else:
        matches=rows("SELECT m.*,a.nom equipe_a,b.nom equipe_b FROM matchs m JOIN equipes a ON a.id=m.equipe_a_id JOIN equipes b ON b.id=m.equipe_b_id WHERE m.activite=? ORDER BY m.date_match DESC,m.id DESC", (sport,))
        if not matches:
            st.info("Aucun match créé pour ce sport."); return
        m=st.selectbox("Match", matches, format_func=lambda r:f"{r['date_match']} • {r['equipe_a']} / {r['equipe_b']}", key="sc_match_sheet")
        st.markdown(f"## 📋 {m['equipe_a']} — {m['equipe_b']}")
        st.caption(f"{sport} • {m['date_match']} • {m['heure'] or 'heure à définir'} • {m['lieu'] or 'lieu à définir'} • Arbitre : {m['arbitre'] or 'à définir'}")
        ca,cb=st.columns(2)
        for col,team_id,name in [(ca,m["equipe_a_id"],m["equipe_a"]),(cb,m["equipe_b_id"],m["equipe_b"])]:
            with col:
                st.markdown(f"### {name}")
                ps=rows("SELECT ej.*,u.nom,u.prenom FROM equipe_joueurs ej JOIN utilisateurs u ON u.id=ej.utilisateur_id WHERE ej.equipe_id=? ORDER BY ej.titulaire DESC,u.nom", (team_id,))
                for p in ps: st.write(f"{'⭐' if p['titulaire'] else '↪'} {p['numero'] or '-'} • {p['nom']} {p['prenom']} • {p['poste'] or '-'}")
        with st.form("sc_score"):
            c1,c2=st.columns(2); sa=c1.number_input(f"Score {m['equipe_a']}", min_value=0, value=int(m['score_a'] or 0)); sb=c2.number_input(f"Score {m['equipe_b']}", min_value=0, value=int(m['score_b'] or 0))
            statut=st.selectbox("Statut", ["Prévu","En cours","Terminé","Reporté","Annulé"], index=["Prévu","En cours","Terminé","Reporté","Annulé"].index(m["statut"] if m["statut"] in ["Prévu","En cours","Terminé","Reporté","Annulé"] else "Prévu"))
            obs=st.text_area("Observations", m["observations"] or "")
            save=st.form_submit_button("Enregistrer la feuille de match", type="primary")
        if save:
            exe("UPDATE matchs SET score_a=?,score_b=?,statut=?,observations=? WHERE id=?", (sa,sb,statut,obs,m["id"]))
            st.success("Feuille de match enregistrée."); st.rerun()

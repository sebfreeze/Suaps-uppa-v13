# Module Sports collectifs - équipes, matchs, tournois et photos
SPORTS_CO = ["Rugby", "Basket-ball", "Handball", "Volley-ball", "Football", "Futsal", "Badminton", "Pelote Basque"]


def init_sports_co_db(exe):
    exe("CREATE TABLE IF NOT EXISTS equipes(id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL, activite TEXT NOT NULL, couleur TEXT, capitaine_id INTEGER, date_creation TEXT, photo BLOB)")
    exe("CREATE TABLE IF NOT EXISTS equipe_joueurs(id INTEGER PRIMARY KEY AUTOINCREMENT, equipe_id INTEGER NOT NULL, utilisateur_id INTEGER NOT NULL, numero TEXT, poste TEXT, titulaire INTEGER DEFAULT 1, photo BLOB, UNIQUE(equipe_id,utilisateur_id))")
    exe("CREATE TABLE IF NOT EXISTS tournois(id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL, activite TEXT NOT NULL, formule TEXT NOT NULL, date_tournoi TEXT, lieu TEXT, statut TEXT DEFAULT 'Préparation')")
    exe("CREATE TABLE IF NOT EXISTS tournoi_equipes(id INTEGER PRIMARY KEY AUTOINCREMENT, tournoi_id INTEGER NOT NULL, equipe_id INTEGER NOT NULL, poule TEXT DEFAULT 'A', UNIQUE(tournoi_id,equipe_id))")
    exe("CREATE TABLE IF NOT EXISTS matchs(id INTEGER PRIMARY KEY AUTOINCREMENT, activite TEXT NOT NULL, equipe_a_id INTEGER NOT NULL, equipe_b_id INTEGER NOT NULL, tournoi_id INTEGER, phase TEXT, date_match TEXT, heure TEXT, lieu TEXT, arbitre TEXT, score_a INTEGER, score_b INTEGER, statut TEXT DEFAULT 'Prévu', observations TEXT)")
    for table, col in [("equipes", "photo"), ("equipe_joueurs", "photo")]:
        try:
            exe(f"ALTER TABLE {table} ADD COLUMN {col} BLOB")
        except Exception:
            pass
    for col, typ in [("tournoi_id", "INTEGER"), ("phase", "TEXT")]:
        try:
            exe(f"ALTER TABLE matchs ADD COLUMN {col} {typ}")
        except Exception:
            pass


def _round_robin(team_ids):
    ids = list(team_ids)
    if len(ids) % 2:
        ids.append(None)
    games = []
    for rnd in range(len(ids) - 1):
        for i in range(len(ids) // 2):
            a, b = ids[i], ids[-1 - i]
            if a is not None and b is not None:
                games.append((a, b, f"Journée {rnd + 1}"))
        ids = [ids[0]] + [ids[-1]] + ids[1:-1]
    return games


def render_sports_co(st, rows, one, exe, date):
    st.markdown("### 🏆 Équipes • Matchs • Tournois")
    sport = st.selectbox("Sport / activité", SPORTS_CO, key="sc_sport")
    if sport == "Badminton":
        st.caption("Simple ou double : crée une équipe pour un joueur ou une paire. Les scores peuvent être saisis en sets/points dans les observations.")
    elif sport == "Pelote Basque":
        st.caption("Individuel ou paire : crée une équipe par joueur ou par paire selon la spécialité pratiquée.")
    tab = st.radio("Gestion", ["Équipes", "Composer", "Matchs", "Tournois", "Classement", "Feuille de match"], horizontal=True, key="sc_tab")

    if tab == "Équipes":
        with st.form("sc_team"):
            nom = st.text_input("Nom de l'équipe / joueur / paire")
            couleur = st.text_input("Couleur / chasuble")
            photo = st.file_uploader("Photo de l'équipe ou du joueur", type=["jpg", "jpeg", "png"], key="sc_team_photo")
            add = st.form_submit_button("Créer", type="primary")
        if add and nom.strip():
            exe("INSERT INTO equipes(nom,activite,couleur,date_creation,photo) VALUES(?,?,?,?,?)", (nom.strip(), sport, couleur.strip(), str(date.today()), photo.getvalue() if photo else None))
            st.success("Création enregistrée.")
            st.rerun()
        for t in rows("SELECT * FROM equipes WHERE activite=? ORDER BY nom", (sport,)):
            c1, c2 = st.columns([1, 3])
            if t.get("photo"):
                c1.image(t["photo"], width=100)
            nb = one("SELECT COUNT(*) n FROM equipe_joueurs WHERE equipe_id=?", (t["id"],))
            c2.markdown(f"**{t['nom']}** — {t['couleur'] or 'sans couleur'} • {nb['n'] if nb else 0} joueur(s)")

    elif tab == "Composer":
        teams = rows("SELECT * FROM equipes WHERE activite=? ORDER BY nom", (sport,))
        if not teams:
            st.info("Crée d'abord une équipe, un joueur ou une paire.")
            return
        team = st.selectbox("Équipe / joueur / paire", teams, format_func=lambda r: r["nom"], key="sc_team_pick")
        students = rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' AND actif=1 ORDER BY nom,prenom")
        current = rows("SELECT ej.*,u.nom,u.prenom FROM equipe_joueurs ej JOIN utilisateurs u ON u.id=ej.utilisateur_id WHERE ej.equipe_id=? ORDER BY ej.titulaire DESC,u.nom", (team["id"],))
        ids = {p["utilisateur_id"] for p in current}
        choices = [s for s in students if s["id"] not in ids]
        if choices:
            p = st.selectbox("Joueur", choices, format_func=lambda r: f"{r['nom']} {r['prenom']}")
            c1, c2 = st.columns(2)
            num = c1.text_input("Numéro")
            poste = c2.text_input("Poste / rôle")
            tit = st.checkbox("Titulaire", True)
            photo = st.file_uploader("Photo du joueur", type=["jpg", "jpeg", "png"], key="sc_player_photo")
            if st.button("Ajouter", type="primary"):
                exe("INSERT OR IGNORE INTO equipe_joueurs(equipe_id,utilisateur_id,numero,poste,titulaire,photo) VALUES(?,?,?,?,?,?)", (team["id"], p["id"], num, poste, int(tit), photo.getvalue() if photo else None))
                st.rerun()
        for p in current:
            c0, c1, c2 = st.columns([1, 4, 1])
            if p.get("photo"):
                c0.image(p["photo"], width=60)
            c1.write(f"{'⭐' if p['titulaire'] else '↪'} {p['numero'] or '-'} • {p['nom']} {p['prenom']} • {p['poste'] or '-'}")
            if c2.button("Retirer", key=f"rm{p['id']}"):
                exe("DELETE FROM equipe_joueurs WHERE id=?", (p["id"],))
                st.rerun()

    elif tab == "Tournois":
        with st.form("sc_tournament"):
            nom = st.text_input("Nom du tournoi")
            formule = st.selectbox("Formule", ["Championnat / toutes rondes", "Poules", "Élimination directe"])
            d = st.date_input("Date", date.today())
            lieu = st.text_input("Lieu")
            create = st.form_submit_button("Créer le tournoi", type="primary")
        if create and nom.strip():
            exe("INSERT INTO tournois(nom,activite,formule,date_tournoi,lieu) VALUES(?,?,?,?,?)", (nom.strip(), sport, formule, str(d), lieu))
            st.rerun()
        ts = rows("SELECT * FROM tournois WHERE activite=? ORDER BY id DESC", (sport,))
        if not ts:
            st.info("Aucun tournoi.")
            return
        t = st.selectbox("Tournoi", ts, format_func=lambda r: r["nom"])
        teams = rows("SELECT * FROM equipes WHERE activite=? ORDER BY nom", (sport,))
        selected = st.multiselect("Participants", teams, format_func=lambda r: r["nom"])
        if st.button("Enregistrer les participants"):
            exe("DELETE FROM tournoi_equipes WHERE tournoi_id=?", (t["id"],))
            for e in selected:
                exe("INSERT OR IGNORE INTO tournoi_equipes(tournoi_id,equipe_id) VALUES(?,?)", (t["id"], e["id"]))
            st.success("Participants enregistrés.")
            st.rerun()
        participants = rows("SELECT e.* FROM tournoi_equipes te JOIN equipes e ON e.id=te.equipe_id WHERE te.tournoi_id=? ORDER BY e.nom", (t["id"],))
        if len(participants) >= 2 and st.button("Générer les rencontres", type="primary"):
            exe("DELETE FROM matchs WHERE tournoi_id=?", (t["id"],))
            ids = [e["id"] for e in participants]
            games = _round_robin(ids) if t["formule"] != "Élimination directe" else [(ids[i], ids[i + 1], "1er tour") for i in range(0, len(ids) - 1, 2)]
            for a, b, phase in games:
                exe("INSERT INTO matchs(activite,equipe_a_id,equipe_b_id,tournoi_id,phase,date_match,lieu) VALUES(?,?,?,?,?,?,?)", (sport, a, b, t["id"], phase, t["date_tournoi"], t["lieu"]))
            st.success(f"{len(games)} rencontre(s) générée(s).")
            st.rerun()

    elif tab == "Classement":
        ts = rows("SELECT * FROM tournois WHERE activite=? ORDER BY id DESC", (sport,))
        if not ts:
            st.info("Aucun tournoi.")
            return
        t = st.selectbox("Tournoi", ts, format_func=lambda r: r["nom"], key="rank_t")
        teams = rows("SELECT e.* FROM tournoi_equipes te JOIN equipes e ON e.id=te.equipe_id WHERE te.tournoi_id=?", (t["id"],))
        stats = {e["id"]: {"Équipe": e["nom"], "J": 0, "G": 0, "N": 0, "P": 0, "Pour": 0, "Contre": 0, "Pts": 0} for e in teams}
        for m in rows("SELECT * FROM matchs WHERE tournoi_id=? AND statut='Terminé'", (t["id"],)):
            if m["score_a"] is None or m["score_b"] is None:
                continue
            a, b = stats.get(m["equipe_a_id"]), stats.get(m["equipe_b_id"])
            if not a or not b:
                continue
            a["J"] += 1
            b["J"] += 1
            a["Pour"] += m["score_a"]
            a["Contre"] += m["score_b"]
            b["Pour"] += m["score_b"]
            b["Contre"] += m["score_a"]
            if m["score_a"] > m["score_b"]:
                a["G"] += 1
                b["P"] += 1
                a["Pts"] += 3
            elif m["score_b"] > m["score_a"]:
                b["G"] += 1
                a["P"] += 1
                b["Pts"] += 3
            else:
                a["N"] += 1
                b["N"] += 1
                a["Pts"] += 1
                b["Pts"] += 1
        ranking = sorted(stats.values(), key=lambda x: (x["Pts"], x["Pour"] - x["Contre"], x["Pour"]), reverse=True)
        st.dataframe(ranking, use_container_width=True, hide_index=True)

    else:
        matches = rows("SELECT m.*,a.nom equipe_a,b.nom equipe_b FROM matchs m JOIN equipes a ON a.id=m.equipe_a_id JOIN equipes b ON b.id=m.equipe_b_id WHERE m.activite=? ORDER BY m.date_match DESC,m.id DESC", (sport,))
        if tab == "Matchs":
            teams = rows("SELECT * FROM equipes WHERE activite=? ORDER BY nom", (sport,))
            if len(teams) >= 2:
                with st.form("sc_match"):
                    a = st.selectbox("Participant A", teams, format_func=lambda r: r["nom"])
                    b = st.selectbox("Participant B", teams, format_func=lambda r: r["nom"], index=1)
                    d = st.date_input("Date", date.today())
                    h = st.text_input("Heure")
                    lieu = st.text_input("Lieu")
                    arb = st.text_input("Arbitre")
                    add = st.form_submit_button("Créer le match", type="primary")
                if add and a["id"] != b["id"]:
                    exe("INSERT INTO matchs(activite,equipe_a_id,equipe_b_id,date_match,heure,lieu,arbitre) VALUES(?,?,?,?,?,?,?)", (sport, a["id"], b["id"], str(d), h, lieu, arb))
                    st.rerun()
            for m in matches:
                st.write(f"**{m['equipe_a']} {'—' if m['score_a'] is None else str(m['score_a']) + ' - ' + str(m['score_b'])} {m['equipe_b']}** • {m['date_match']} • {m.get('phase') or ''}")
            return
        if not matches:
            st.info("Aucun match.")
            return
        m = st.selectbox("Match", matches, format_func=lambda r: f"{r['date_match']} • {r['equipe_a']} / {r['equipe_b']}")
        st.markdown(f"## 📋 {m['equipe_a']} — {m['equipe_b']}")
        st.caption(f"{sport} • {m['date_match']} • {m['heure'] or ''} • {m['lieu'] or ''} • Arbitre : {m['arbitre'] or 'à définir'}")
        ca, cb = st.columns(2)
        for col, tid, name in [(ca, m["equipe_a_id"], m["equipe_a"]), (cb, m["equipe_b_id"], m["equipe_b"])]:
            with col:
                st.markdown(f"### {name}")
                team = one("SELECT * FROM equipes WHERE id=?", (tid,))
                photo = team["photo"] if team and "photo" in team.keys() else None
                if photo:
                    st.image(photo, use_container_width=True)
                for p in rows("SELECT ej.*,u.nom,u.prenom FROM equipe_joueurs ej JOIN utilisateurs u ON u.id=ej.utilisateur_id WHERE ej.equipe_id=? ORDER BY ej.titulaire DESC,u.nom", (tid,)):
                    st.write(f"{'⭐' if p['titulaire'] else '↪'} {p['numero'] or '-'} • {p['nom']} {p['prenom']} • {p['poste'] or '-'}")
        statuses = ["Prévu", "En cours", "Terminé", "Reporté", "Annulé"]
        current_status = m.get("statut") or "Prévu"
        with st.form("sc_score"):
            c1, c2 = st.columns(2)
            sa = c1.number_input(f"Score {m['equipe_a']}", 0, value=int(m['score_a'] or 0))
            sb = c2.number_input(f"Score {m['equipe_b']}", 0, value=int(m['score_b'] or 0))
            statut = st.selectbox("Statut", statuses, index=statuses.index(current_status) if current_status in statuses else 0)
            obs = st.text_area("Observations / détail des sets", m["observations"] or "")
            save = st.form_submit_button("Enregistrer la feuille de match", type="primary")
        if save:
            exe("UPDATE matchs SET score_a=?,score_b=?,statut=?,observations=? WHERE id=?", (sa, sb, statut, obs, m["id"]))
            st.success("Feuille enregistrée.")
            st.rerun()

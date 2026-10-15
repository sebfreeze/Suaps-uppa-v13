"""Gestion déléguée d'un tournoi existant, liée aux inscriptions SUAPS."""
import hashlib
import secrets
import streamlit as st


def _hash(code):
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


def init_access(exe):
    exe("""CREATE TABLE IF NOT EXISTS tournoi_acces_etudiant (
        tournoi_id INTEGER PRIMARY KEY,
        offre_id INTEGER NOT NULL,
        code_hash TEXT NOT NULL
    )""")


def _tournaments(rows):
    return rows("SELECT id,nom,activite FROM tournois ORDER BY id DESC")


def _offers(rows, activity):
    return rows("SELECT id,activite,intitule,groupe,jour_horaire FROM offres_inscription WHERE LOWER(activite)=LOWER(?) ORDER BY id DESC", (activity,))


def _players(rows, offer_id):
    return rows("""SELECT DISTINCT e.id,e.nom,e.prenom,e.numero_etudiant
        FROM inscriptions i JOIN etudiants e ON e.id=i.etudiant_id
        WHERE i.offre_id=? AND i.statut='Inscrit' AND e.actif=1
        ORDER BY e.nom,e.prenom""", (offer_id,))


def teacher_setup(rows, one, exe):
    st.markdown("### 🔗 Déléguer la gestion d'un tournoi")
    tournaments = _tournaments(rows)
    if not tournaments:
        st.info("Créez d'abord un tournoi dans Compétition > Tournois.")
        return
    t = st.selectbox("Tournoi existant", tournaments, format_func=lambda x: x["nom"] + " — " + x["activite"], key="link_t")
    offers = _offers(rows, t["activite"])
    if not offers:
        st.warning("Aucune offre d'inscription de cette activité. Créez un créneau dans Inscriptions en ligne.")
        return
    existing = one("SELECT * FROM tournoi_acces_etudiant WHERE tournoi_id=?", (t["id"],))
    index = next((i for i,o in enumerate(offers) if existing and o["id"]==existing["offre_id"]), 0)
    offer = st.selectbox("Créneau dont les inscrits sont éligibles", offers, index=index,
        format_func=lambda o: f'{o["intitule"]} — {o["groupe"] or "Tous"} — {o["jour_horaire"] or ""}', key="link_o")
    st.caption(f'{len(_players(rows, offer["id"]))} étudiant(s) inscrit(s) au créneau.')
    if st.button("Enregistrer la liaison et générer un nouveau code", type="primary"):
        code = secrets.token_urlsafe(12).replace("-", "X").replace("_", "Y").upper()
        exe("DELETE FROM tournoi_acces_etudiant WHERE tournoi_id=?", (t["id"],))
        exe("INSERT INTO tournoi_acces_etudiant(tournoi_id,offre_id,code_hash) VALUES(?,?,?)",
            (t["id"], offer["id"], _hash(code)))
        st.session_state["new_tournament_code"] = (t["id"], code)
    saved = st.session_state.get("new_tournament_code")
    if saved and saved[0] == t["id"]:
        st.success("Code individuel de ce tournoi (à communiquer à l'étudiant organisateur) :")
        st.code(saved[1])
        st.caption("Le code n'est affiché qu'après sa génération. En générer un autre révoque le précédent.")
    elif existing:
        st.info("Accès déjà configuré pour ce tournoi. Générer un nouveau code pour le remplacer.")


def student_portal(rows, one, exe):
    st.subheader("🏆 Gestion du tournoi — étudiant organisateur")
    st.caption("Accès aux équipes et aux matchs d'un tournoi autorisé uniquement.")
    entered = st.text_input("Code du tournoi communiqué par l'enseignant", type="password", key="tournament_code")
    if st.button("Accéder au tournoi", type="primary"):
        record = one("SELECT tournoi_id FROM tournoi_acces_etudiant WHERE code_hash=?", (_hash(entered),)) if entered.strip() else None
        if record:
            st.session_state["tournament_authorized"] = (record["tournoi_id"], _hash(entered))
        else:
            st.session_state.pop("tournament_authorized", None)
            st.error("Code non reconnu.")
    access = st.session_state.get("tournament_authorized")
    if not access:
        return
    config = one("""SELECT a.*,t.nom,t.activite,t.statut
        FROM tournoi_acces_etudiant a JOIN tournois t ON t.id=a.tournoi_id
        WHERE a.tournoi_id=? AND a.code_hash=?""", access)
    if not config:
        st.session_state.pop("tournament_authorized", None)
        st.warning("Accès révoqué ou tournoi indisponible.")
        return
    tid = config["tournoi_id"]
    st.markdown(f'### {config["nom"]} — {config["activite"]}')
    eligible = _players(rows, config["offre_id"])
    eligible_ids = {p["id"] for p in eligible}
    st.caption(f"{len(eligible)} inscrit(s) éligible(s) depuis le créneau SUAPS associé.")
    teams = rows("""SELECT e.id,e.nom FROM tournoi_equipes te JOIN equipes e
        ON e.id=te.equipe_id WHERE te.tournoi_id=? ORDER BY e.nom""", (tid,))
    tab1,tab2 = st.tabs(["👥 Composer les équipes", "⚽ Saisir les scores"])
    with tab1:
        if not teams:
            st.warning("L'enseignant doit d'abord ajouter les équipes à ce tournoi.")
        else:
            team = st.selectbox("Équipe du tournoi", teams, format_func=lambda x:x["nom"])
            current = rows("""SELECT ej.id,ej.utilisateur_id,e.nom,e.prenom
                FROM equipe_joueurs ej JOIN etudiants e ON e.id=ej.utilisateur_id
                WHERE ej.equipe_id=? ORDER BY e.nom,e.prenom""", (team["id"],))
            for p in current:
                c1,c2=st.columns([5,1])
                c1.write(f'{p["nom"]} {p["prenom"]}')
                if c2.button("✕", key=f'tr_{tid}_{p["id"]}'):
                    exe("DELETE FROM equipe_joueurs WHERE id=? AND equipe_id=?", (p["id"],team["id"]))
                    st.rerun()
            already = {p["utilisateur_id"] for p in current}
            assigned = rows("""SELECT ej.utilisateur_id FROM equipe_joueurs ej JOIN tournoi_equipes te
                ON ej.equipe_id=te.equipe_id WHERE te.tournoi_id=?""",(tid,))
            assigned_ids = {p["utilisateur_id"] for p in assigned}
            available = [p for p in eligible if p["id"] not in already and p["id"] not in assigned_ids]
            if available:
                chosen=st.selectbox("Ajouter un inscrit",available,
                    format_func=lambda x:f'{x["nom"]} {x["prenom"]} — {x["numero_etudiant"] or ""}')
                if st.button("Ajouter à l'équipe",type="primary"):
                    if chosen["id"] in eligible_ids:
                        exe("""INSERT INTO equipe_joueurs(equipe_id,utilisateur_id,titulaire)
                            SELECT ?,?,1 WHERE NOT EXISTS (
                              SELECT 1 FROM equipe_joueurs ej JOIN tournoi_equipes te
                              ON ej.equipe_id=te.equipe_id
                              WHERE te.tournoi_id=? AND ej.utilisateur_id=?
                            )""",(team["id"],chosen["id"],tid,chosen["id"]))
                        st.rerun()
            else:
                st.info("Aucun autre inscrit disponible pour cette équipe.")
    with tab2:
        matches=rows("""SELECT m.id,m.score_a,m.score_b,m.statut,
            a.nom AS equipe_a,b.nom AS equipe_b FROM matchs m
            JOIN equipes a ON a.id=m.equipe_a_id
            JOIN equipes b ON b.id=m.equipe_b_id
            WHERE m.tournoi_id=? ORDER BY m.id""",(tid,))
        if not matches:
            st.info("Aucun match programmé par l'enseignant.")
        for m in matches:
            with st.form(f'score_{tid}_{m["id"]}'):
                st.write(f'**{m["equipe_a"]} – {m["equipe_b"]}**')
                a,b=st.columns(2)
                score_a=a.number_input(m["equipe_a"],min_value=0,step=1,value=int(m["score_a"] or 0))
                score_b=b.number_input(m["equipe_b"],min_value=0,step=1,value=int(m["score_b"] or 0))
                if st.form_submit_button("Valider le résultat"):
                    exe("UPDATE matchs SET score_a=?,score_b=?,statut='Terminé' WHERE id=? AND tournoi_id=?",
                        (score_a,score_b,m["id"],tid))
                    st.success("Score enregistré.")
                    st.rerun()

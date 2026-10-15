"""Gestion sécurisée des équipes de natation déjà créées.

Les modifications conservent les nageurs et les temps.
La suppression explicite nettoie les relations, même sans ON DELETE CASCADE.
"""
import math


def _positive_int(value, default=1):
    try:
        number = float(value)
        return int(number) if math.isfinite(number) and number >= 1 else default
    except (ValueError, TypeError, OverflowError):
        return default


def save_team_changes(rows, exe, competition_id, original, *, nom, universite,
                      categorie, niveau, manual, serie, ligne, reflow, max_lines=5):
    nom = str(nom or "").strip()
    universite = str(universite or "").strip()
    if not nom or not universite:
        return "Le nom de l'équipe et l'université / AS sont obligatoires."
    if categorie not in ("Masculin", "Féminin", "Mixte"):
        return "Catégorie invalide."
    if niveau not in (1, 2):
        return "Le niveau doit être 1 ou 2."
    duplicate = rows(
        """SELECT id FROM natation_equipes
           WHERE competition_id=? AND categorie=? AND LOWER(nom)=LOWER(?) AND id<>?""",
        (competition_id, categorie, nom, original["id"]),
    )
    if duplicate:
        return "Une autre équipe porte déjà ce nom dans cette catégorie."
    if manual:
        serie, ligne = _positive_int(serie), _positive_int(ligne)
        if not 1 <= ligne <= max_lines:
            return "Ligne d'eau invalide."
        occupied = rows(
            """SELECT nom FROM natation_equipes
               WHERE competition_id=? AND categorie=? AND serie=? AND ligne=? AND id<>?""",
            (competition_id, categorie, serie, ligne, original["id"]),
        )
        if occupied:
            return f"Série {serie}, ligne {ligne} déjà occupée par {occupied[0]['nom']}."
    else:
        serie, ligne = None, None

    exe(
        """UPDATE natation_equipes SET nom=?,universite=?,categorie=?,niveau=?,
           serie=?,ligne=?,placement_verrouille=?
           WHERE id=? AND competition_id=?""",
        (nom, universite, categorie, str(float(niveau)), serie, ligne,
         int(manual), original["id"], competition_id),
    )
    previous_category = original["categorie"]
    if previous_category != categorie:
        reflow(rows, exe, competition_id, previous_category, max_lines, unlock_all=False)
    if not manual:
        reflow(rows, exe, competition_id, categorie, max_lines, unlock_all=False)
    return None


def delete_swim_team(rows, exe, competition_id, team, reflow, max_lines=5):
    """Supprime uniquement cette équipe et ses dépendances natation."""
    team_id = team["id"]
    result_ids = rows(
        "SELECT id FROM natation_resultats WHERE competition_id=? AND equipe_id=?",
        (competition_id, team_id),
    )
    for result in result_ids:
        exe("DELETE FROM natation_splits WHERE resultat_id=?", (result["id"],))
    exe(
        "DELETE FROM natation_resultats WHERE competition_id=? AND equipe_id=?",
        (competition_id, team_id),
    )
    swimmers = rows("SELECT id FROM natation_nageurs WHERE equipe_id=?", (team_id,))
    for swimmer in swimmers:
        exe("DELETE FROM natation_engagements WHERE nageur_id=?", (swimmer["id"],))
    exe("DELETE FROM natation_nageurs WHERE equipe_id=?", (team_id,))
    exe(
        "DELETE FROM natation_equipes WHERE competition_id=? AND id=?",
        (competition_id, team_id),
    )
    reflow(rows, exe, competition_id, team["categorie"], max_lines, unlock_all=False)


def render_swim_team_management(st, rows, exe, comp, teams, reflow):
    """Édition et suppression réservées à l'onglet de gestion des équipes."""
    if not teams:
        return
    st.divider()
    st.markdown("#### ✏️ Modifier ou supprimer une équipe")
    by_id = {int(t["id"]): t for t in teams}
    team_id = st.selectbox(
        "Équipe à modifier",
        list(by_id),
        format_func=lambda tid: (
            f"{by_id[tid]['universite']} • {by_id[tid]['nom']} • "
            f"{by_id[tid]['categorie']} • Série {_positive_int(by_id[tid].get('serie'))}"
        ),
        key="swim_manage_existing_team",
    )
    team = by_id[team_id]
    universities = ["UPPA", "Toulouse", "Bordeaux", "Autre / saisie libre"]
    previous_university = str(team.get("universite") or "")
    selected_university = (
        previous_university if previous_university in universities[:3]
        else "Autre / saisie libre"
    )
    categories = ["Masculin", "Féminin", "Mixte"]
    manual_before = bool(_positive_int(team.get("placement_verrouille"), default=0))

    with st.form(f"swim_edit_team_{team_id}"):
        a, b = st.columns(2)
        name = a.text_input("Nom de l'équipe", value=str(team.get("nom") or ""))
        category = b.selectbox(
            "Catégorie", categories, index=categories.index(team["categorie"])
        )
        a, b = st.columns(2)
        university_choice = a.selectbox(
            "Université / AS", universities,
            index=universities.index(selected_university),
        )
        level = b.selectbox(
            "Niveau", [1, 2],
            index=1 if _positive_int(team.get("niveau")) == 2 else 0,
        )
        university_free = st.text_input(
            "Autre université / AS",
            value=previous_university if selected_university == "Autre / saisie libre" else "",
            disabled=university_choice != "Autre / saisie libre",
        )
        assignment = st.radio(
            "Placement", ["Automatique par niveau", "Manuel"],
            index=1 if manual_before else 0, horizontal=True,
        )
        a, b = st.columns(2)
        new_serie = a.number_input(
            "Série", min_value=1, value=_positive_int(team.get("serie")),
            step=1, disabled=assignment != "Manuel",
        )
        new_ligne = b.number_input(
            "Ligne d'eau", min_value=1,
            max_value=_positive_int(comp.get("nb_lignes"), 5),
            value=min(
                _positive_int(team.get("ligne"), 3),
                _positive_int(comp.get("nb_lignes"), 5),
            ),
            step=1, disabled=assignment != "Manuel",
        )
        save = st.form_submit_button(
            "💾 Enregistrer les modifications", type="primary",
            use_container_width=True,
        )
    if save:
        university = university_free if university_choice == "Autre / saisie libre" else university_choice
        error = save_team_changes(
            rows, exe, comp["id"], team,
            nom=name, universite=university, categorie=category,
            niveau=level, manual=assignment == "Manuel",
            serie=new_serie, ligne=new_ligne,
            reflow=reflow, max_lines=_positive_int(comp.get("nb_lignes"), 5),
        )
        if error:
            st.error(error)
        else:
            st.success("Équipe modifiée : nageurs, engagements et temps conservés.")
            st.rerun()

    with st.expander("🗑️ Supprimer cette équipe"):
        st.warning(
            "Cette suppression est définitive : les nageurs, engagements, "
            "temps des relayeurs et résultats de cette équipe seront également supprimés."
        )
        confirm = st.checkbox(
            f"Je confirme la suppression de « {team['nom']} »",
            key=f"swim_team_delete_confirm_{team_id}",
        )
        if st.button(
            "Supprimer définitivement l'équipe",
            key=f"swim_team_delete_{team_id}",
            disabled=not confirm, use_container_width=True,
        ):
            delete_swim_team(
                rows, exe, comp["id"], team, reflow,
                _positive_int(comp.get("nb_lignes"), 5),
            )
            st.success("Équipe et résultats associés supprimés.")
            st.rerun()

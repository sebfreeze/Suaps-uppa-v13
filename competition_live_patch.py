"""Injection ciblée du module Compétition dans le live V14/V17."""

SENTINEL = "# --- competition integration ---"

NAV_WITH_PRESENCE_NOTE = '    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Présence / Note évaluation","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")'
NAV_BASE = '    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")'
NAV_WITH_COMPETITION = '    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Présence / Note évaluation","Évaluations","Évaluation /20","Compétition","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")'
NAV_BASE_WITH_COMPETITION = '    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétition","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")'

COMPETENCE_MARKER = '    elif sec=="Compétences":\n'

COMPETITION_BLOCK = '''    # --- competition integration ---
    elif sec=="Compétition":
        st.markdown("## 🏆 Compétition")
        st.caption("Sports collectifs • Badminton • Pelote Basque")
        st.info("Équipes / joueurs • Composer • Matchs • Feuilles de match • Tournois • Classements")
        st.link_button(
            "🔗 My Sport U — compte, licence et compétitions",
            "https://sport-u.com/mysportu/",
            use_container_width=True,
        )
        from sports_co_module import init_sports_co_db, render_sports_co
        init_sports_co_db(exe)
        render_sports_co(st, rows, one, exe, date)
'''


def patch_app_source(source: str) -> str:
    """Ajoute uniquement Compétition au menu enseignant et son rendu."""
    if SENTINEL in source:
        return source

    if NAV_WITH_PRESENCE_NOTE in source:
        source = source.replace(NAV_WITH_PRESENCE_NOTE, NAV_WITH_COMPETITION, 1)
    elif NAV_BASE in source:
        source = source.replace(NAV_BASE, NAV_BASE_WITH_COMPETITION, 1)
    elif '"Compétition"' not in source:
        raise RuntimeError("Navigation enseignant live introuvable pour Compétition.")

    if 'elif sec=="Compétition":' not in source:
        if COMPETENCE_MARKER not in source:
            raise RuntimeError("Point d'insertion Compétences live introuvable pour Compétition.")
        source = source.replace(
            COMPETENCE_MARKER,
            COMPETITION_BLOCK + COMPETENCE_MARKER,
            1,
        )

    return source

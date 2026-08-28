"""Ajoute les modules Compétition et Pédagogie à l'application générée."""
import builtins

_previous_compile = builtins.compile


def _inject_modules(source):
    if not isinstance(source, str):
        return source
    if 'def admin()' not in source or 'key="admin_section"' not in source:
        return source

    # Compétition : sports collectifs + badminton + pelote basque.
    if '"Compétition"' not in source:
        if '"Sports collectifs"' in source:
            source = source.replace('"Sports collectifs"', '"Compétition"')
        elif '"Évaluation /20","Compétences"' in source:
            source = source.replace('"Évaluation /20","Compétences"', '"Évaluation /20","Compétition","Compétences"', 1)

    # Ajoute Pédagogie juste avant Compétences.
    if '"Pédagogie"' not in source:
        source = source.replace('"Compétition","Compétences"', '"Compétition","Pédagogie","Compétences"', 1)

    anchor = '    elif sec=="Compétences":\n'
    if anchor in source and 'elif sec=="Compétition":' not in source:
        competition = '''    elif sec=="Compétition":
        st.markdown("## 🏆 Compétition")
        st.caption("Sports collectifs • Badminton • Pelote basque")
        st.info("Équipes / joueurs • Composer • Matchs • Feuilles de match • Tournois • Classements")
        from sports_co_module import init_sports_co_db, render_sports_co
        init_sports_co_db(exe)
        render_sports_co(st, rows, one, exe, date)
    elif sec=="Compétences":
'''
        source = source.replace(anchor, competition, 1)

    anchor = '    elif sec=="Compétences":\n'
    if anchor in source and 'elif sec=="Pédagogie":' not in source:
        pedagogie = '''    elif sec=="Pédagogie":
        st.markdown("## 🎓 Pédagogie")
        st.caption("Un suivi simple de la séance à la progression de l'étudiant")
        ptab = st.radio("Suivi pédagogique", ["Séances", "Progression", "Bilans"], horizontal=True, key="pedagogie_tab")
        if ptab == "Séances":
            st.markdown("### 🎯 Objectifs de séance")
            st.info("Choisis 2 ou 3 objectifs prioritaires et relie-les aux compétences travaillées.")
            st.multiselect("Objectifs", ["Technique / maîtrise gestuelle", "Tactique / prise de décision", "Engagement / intensité", "Autonomie", "Coopération", "Sécurité", "Condition physique"], max_selections=3, key="pedago_objectifs")
            st.text_area("Observation rapide de la séance", placeholder="Points réussis, points à renforcer, consigne pour la prochaine séance…", key="pedago_obs")
        elif ptab == "Progression":
            st.markdown("### ⭐ Progression des compétences")
            st.info("Lecture simple : Non évalué → À renforcer → Acquis → Maîtrisé. Les validations détaillées restent dans la rubrique Compétences.")
            st.progress(0, text="Sélectionne ou évalue les compétences pour visualiser progressivement le parcours de l'étudiant.")
        else:
            st.markdown("### 👤 Bilan étudiant")
            st.info("Le bilan regroupe les éléments déjà présents dans l'application : présences, compétences, performances et note /20.")
            st.markdown("**Repères de bilan** : assiduité • progression • acquis • points à renforcer • investissement")
            st.text_area("Commentaire de bilan", placeholder="Bilan synthétique de fin de période ou de semestre…", key="pedago_bilan")
    elif sec=="Compétences":
'''
        source = source.replace(anchor, pedagogie, 1)
    return source


def _compile(source, filename, mode, flags=0, dont_inherit=False, optimize=-1, **kwargs):
    try:
        if str(filename).endswith("v14_core.py"):
            source = _inject_modules(source)
    except Exception:
        pass
    return _previous_compile(source, filename, mode, flags, dont_inherit, optimize, **kwargs)


builtins.compile = _compile

"""Ajoute le module Compétition à l'application générée, sans modifier le cœur historique."""
import builtins

_previous_compile = builtins.compile


def _inject_competition(source):
    if not isinstance(source, str):
        return source
    if 'def admin()' not in source or 'key="admin_section"' not in source:
        return source

    # Rubrique générale : sports collectifs + badminton + pelote basque.
    if '"Compétition"' not in source:
        if '"Sports collectifs"' in source:
            source = source.replace('"Sports collectifs"', '"Compétition"')
        elif '"Évaluation /20","Compétences"' in source:
            source = source.replace('"Évaluation /20","Compétences"', '"Évaluation /20","Compétition","Compétences"', 1)

    # Injection robuste juste avant la rubrique Compétences.
    anchor = '    elif sec=="Compétences":\n'
    if anchor in source and 'elif sec=="Compétition":' not in source:
        branch = '''    elif sec=="Compétition":
        st.markdown("## 🏆 Compétition")
        st.caption("Sports collectifs • Badminton • Pelote basque")
        st.info("Équipes / joueurs • Composer • Matchs • Feuilles de match • Tournois • Classements")
        from sports_co_module import init_sports_co_db, render_sports_co
        init_sports_co_db(exe)
        render_sports_co(st, rows, one, exe, date)
    elif sec=="Compétences":
'''
        source = source.replace(anchor, branch, 1)
    return source


def _compile(source, filename, mode, flags=0, dont_inherit=False, optimize=-1, **kwargs):
    try:
        if str(filename).endswith("v14_core.py"):
            source = _inject_competition(source)
    except Exception:
        pass
    return _previous_compile(source, filename, mode, flags, dont_inherit, optimize, **kwargs)


builtins.compile = _compile

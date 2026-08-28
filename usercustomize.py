"""Ajoute le module Sports collectifs à l'application générée, sans modifier le cœur historique."""
import builtins

_previous_compile = builtins.compile


def _inject_sports_collectifs(source):
    if not isinstance(source, str):
        return source
    if 'def admin()' not in source or 'key="admin_section"' not in source:
        return source

    # Ajoute l'entrée quel que soit l'état des correctifs appliqués avant nous.
    candidates = [
        '"Évaluation /20","Compétences"',
        '"Évaluation /20","Sports collectifs","Compétences"',
    ]
    if '"Sports collectifs"' not in source and candidates[0] in source:
        source = source.replace(candidates[0], '"Évaluation /20","Sports collectifs","Compétences"', 1)

    # Injection robuste juste avant la rubrique Compétences.
    anchor = '    elif sec=="Compétences":\n'
    if anchor in source and 'elif sec=="Sports collectifs":' not in source:
        branch = '''    elif sec=="Sports collectifs":
        st.markdown("## 🏆 Sports collectifs, badminton & pelote basque")
        st.info("Choisis ci-dessous : Équipes • Composer • Matchs • Tournois • Classement • Feuille de match")
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
            source = _inject_sports_collectifs(source)
    except Exception:
        pass
    return _previous_compile(source, filename, mode, flags, dont_inherit, optimize, **kwargs)


builtins.compile = _compile

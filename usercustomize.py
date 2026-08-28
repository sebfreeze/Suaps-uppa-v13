"""Ajoute le module Sports collectifs à l'application générée, sans modifier le cœur historique."""
import builtins

_previous_compile = builtins.compile


def _inject_sports_collectifs(source):
    if not isinstance(source, str):
        return source
    if 'def admin()' not in source or 'key="admin_section"' not in source:
        return source

    radios = [
        (
            'sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités","Semestres & CSV"],horizontal=True,key="admin_section")',
            'sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Sports collectifs","Compétences","Barèmes","Actualités","Semestres & CSV"],horizontal=True,key="admin_section")'
        ),
        (
            'sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")',
            'sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Sports collectifs","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")'
        ),
    ]
    for old, new in radios:
        if old in source:
            source = source.replace(old, new, 1)
            break

    anchor = '    elif sec=="Compétences":\n        actc=st.selectbox'
    if anchor in source and 'sec=="Sports collectifs"' not in source:
        branch = '''    elif sec=="Sports collectifs":
        from sports_co_module import init_sports_co_db, render_sports_co
        init_sports_co_db(exe)
        render_sports_co(st, rows, one, exe, date)
    elif sec=="Compétences":
        actc=st.selectbox'''
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

import ast
import importlib


def _sample_source():
    return '''import pandas as pd

class _St:
    def radio(self, *args, **kwargs):
        return "Semestres & CSV"

st = _St()

def admin():
    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")
    if sec=="Présences":
        pass
    elif sec=="Semestres & CSV":
        return len(pd.DataFrame([{"x": 1}]))
    elif sec=="Évaluations":
        pass
'''


def test_presence_patch_does_not_make_pandas_local_to_admin():
    mod = importlib.import_module("presence_note_live_patch")
    patched = mod.patch_app_source(_sample_source())

    tree = ast.parse(patched)
    admin_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "admin")
    local_pd_imports = []
    for node in ast.walk(admin_node):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pandas" and alias.asname == "pd":
                    local_pd_imports.append(node)
    assert not local_pd_imports, "pd ne doit jamais être importé localement dans admin()"

    namespace = {}
    exec(compile(patched, "<patched>", "exec"), namespace, namespace)
    assert namespace["admin"]() == 1

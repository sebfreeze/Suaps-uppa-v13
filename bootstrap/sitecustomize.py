"""Orchestrateur Render SUAPS.

Charge la couche sécurité/PostgreSQL et ses sauvegardes, puis rétablit le point
d'entrée Semestres & CSV au bon endroit dans la chaîne de compilation. Cela
conserve également Compétition, Pédagogie et les profils enseignants.
"""
from pathlib import Path
import builtins
import importlib.util
import re

_root = Path(__file__).resolve().parent.parent
_security_site = _root / "security_bootstrap" / "sitecustomize.py"

# 1) Sécurité, PostgreSQL et correctifs historiques.
_security_mod = None
try:
    if _security_site.exists():
        _spec = importlib.util.spec_from_file_location("suaps_security_sitecustomize", _security_site)
        _security_mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_security_mod)
except Exception:
    _security_mod = None

# 2) Sauvegardes + injections historiques Compétition / Pédagogie.
# Avec PYTHONPATH=bootstrap:security_bootstrap:., ce nom désigne bien
# security_bootstrap/usercustomize.py. Le chargement explicite évite tout
# problème d'ordre et Python ne le rechargera pas ensuite.
_user_mod = None
try:
    import usercustomize as _user_mod
except Exception:
    _user_mod = None

# 3) Le module Sauvegardes modifie d'abord le menu, puis appelle
# _previous_compile. On intercale ici Semestres & CSV juste après cette étape,
# avant Compétition/Pédagogie et la sécurité. Le correctif historique CSV placé
# plus bas dans la chaîne peut alors créer normalement toute la page import/export.
try:
    if _user_mod is not None and hasattr(_user_mod, "_previous_compile"):
        _next_compile = _user_mod._previous_compile

        def _csv_menu_bridge(source, filename, mode, *args, **kwargs):
            try:
                if isinstance(source, str) and 'key="admin_section"' in source and '"Semestres & CSV"' not in source:
                    pattern = r'sec=st\.radio\("Rubrique",\[(.*?)\],horizontal=True,key="admin_section"\)'

                    def _add_csv(match):
                        items = match.group(1)
                        if '"Semestres & CSV"' in items:
                            return match.group(0)
                        return 'sec=st.radio("Rubrique",[' + items + ',"Semestres & CSV"],horizontal=True,key="admin_section")'

                    source = re.sub(pattern, _add_csv, source, count=1)
            except Exception:
                pass
            return _next_compile(source, filename, mode, *args, **kwargs)

        _user_mod._previous_compile = _csv_menu_bridge
except Exception:
    pass

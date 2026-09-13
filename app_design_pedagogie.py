"""Point d'entrée V15 + Ressources pédagogiques.

Exécute la couche design historique inchangée et insère le module pédagogique
juste avant l'exécution de la source Streamlit transformée.
"""
from pathlib import Path

from pedagogie_integration import patch_app_source

_design_path = Path(__file__).with_name("app_design.py")
_design_source = _design_path.read_text(encoding="utf-8")
_exec_marker = 'exec(compile(source, str(source_path), "exec"), globals(), globals())'
if _exec_marker not in _design_source:
    raise RuntimeError("Point d'intégration app_design.py introuvable.")
_design_source = _design_source.replace(
    _exec_marker,
    'source = patch_app_source(source)\n' + _exec_marker,
    1,
)
exec(compile(_design_source, str(_design_path), "exec"), globals(), globals())

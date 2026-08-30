"""Bootstrap Render : charge d'abord Matchs/Pédagogie puis les correctifs historiques.

L'ordre est important : le correctif historique Semestres & CSV doit voir le menu
Enseignant d'origine avant que Compétition et Pédagogie ne soient ajoutés au code final.
En chargeant usercustomize en premier puis sitecustomize, le correctif CSV s'applique
d'abord lors de la compilation, puis Compétition/Pédagogie sont conservés.
"""
from pathlib import Path
import importlib.util

_root = Path(__file__).resolve().parent.parent
_legacy = _root / "sitecustomize.py"

# 1) Installer d'abord l'injection Compétition / Pédagogie.
try:
    import usercustomize
except Exception:
    pass

# 2) Installer ensuite les correctifs historiques (semestres, import/export CSV,
#    identité visuelle). Ce wrapper sera exécuté avant usercustomize à la compilation.
try:
    if _legacy.exists():
        _spec = importlib.util.spec_from_file_location("suaps_legacy_sitecustomize", _legacy)
        _module = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_module)
except Exception:
    pass

"""Bootstrap Render : conserve les correctifs historiques puis charge Matchs & Tournois."""
from pathlib import Path
import importlib.util

_root = Path(__file__).resolve().parent.parent
_legacy = _root / "sitecustomize.py"

try:
    if _legacy.exists():
        _spec = importlib.util.spec_from_file_location("suaps_legacy_sitecustomize", _legacy)
        _module = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_module)
except Exception:
    pass

try:
    import usercustomize  # force l'injection Sports collectifs / Matchs & Tournois
except Exception:
    pass

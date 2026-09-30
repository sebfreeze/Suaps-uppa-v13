"""Compatibilité Render : lance l'application SUAPS active.

Render historique démarre encore `v14_complete.py`. Ce fichier reste donc le
point d'entrée stable, mais délègue désormais à `app.py`, qui contient la V15
et conserve les écrans historiques via `app_legacy.py`.
"""

from pathlib import Path

_app_path = Path(__file__).with_name("app.py")
_app_code = _app_path.read_text(encoding="utf-8")
exec(compile(_app_code, str(_app_path), "exec"), globals(), globals())

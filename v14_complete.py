from pathlib import Path

# Active explicitement la couche d'indexation/montée en charge. Le chargement
# automatique du bootstrap peut échouer sur Render car ce module vit dans le
# sous-dossier security_bootstrap.
try:
    from security_bootstrap import scaling as _suaps_scaling
except Exception as _scaling_exc:
    print(f"[SUAPS_PERF] scaling_load_error={type(_scaling_exc).__name__}:{_scaling_exc}")

import pedagogie_integration
from competition_live_patch import patch_app_source as _patch_competition_source
from performance_live_patch import patch_app_source as _patch_performance_source
from presence_note_live_patch import patch_app_source as _patch_presence_note_source
from roster_admin_live_patch import patch_app_source as _patch_roster_admin_source


_original_pedagogy_patch = pedagogie_integration.patch_app_source


def _combined_live_patch(source: str) -> str:
    source = _patch_presence_note_source(source)
    source = _patch_competition_source(source)
    source = _patch_roster_admin_source(source)
    source = _original_pedagogy_patch(source)
    return _patch_performance_source(source)


pedagogie_integration.patch_app_source = _combined_live_patch
try:
    _legacy_path = Path(__file__).with_name("v14_complete_legacy.py")
    _legacy_code = _legacy_path.read_text(encoding="utf-8")
    exec(compile(_legacy_code, str(_legacy_path), "exec"), globals(), globals())
finally:
    pedagogie_integration.patch_app_source = _original_pedagogy_patch

from pathlib import Path

import pedagogie_integration
from competition_live_patch import patch_app_source as _patch_competition_source
from presence_note_live_patch import patch_app_source as _patch_presence_note_source


_original_pedagogy_patch = pedagogie_integration.patch_app_source


def _combined_live_patch(source: str) -> str:
    source = _patch_presence_note_source(source)
    source = _patch_competition_source(source)
    return _original_pedagogy_patch(source)


pedagogie_integration.patch_app_source = _combined_live_patch
try:
    _legacy_path = Path(__file__).with_name("v14_complete_legacy.py")
    _legacy_code = _legacy_path.read_text(encoding="utf-8")
    exec(compile(_legacy_code, str(_legacy_path), "exec"), globals(), globals())
finally:
    pedagogie_integration.patch_app_source = _original_pedagogy_patch

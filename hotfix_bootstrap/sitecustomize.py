"""Final compile-stage hotfix for the SUAPS generated Streamlit source.

Loads the normal security bootstrap, then repairs the legacy responsable/co-responsable
injection immediately before Python compiles the fully transformed source.
"""
from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path

from resp_options_hotfix import repair_source

_root = Path(__file__).resolve().parents[1]
_security_path = _root / "security_bootstrap" / "sitecustomize.py"

_spec = importlib.util.spec_from_file_location("suaps_security_bootstrap_hotfix_base", _security_path)
if not _spec or not _spec.loader:
    raise RuntimeError("SUAPS security bootstrap introuvable")

_security_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_security_mod)

_legacy_mod = getattr(_security_mod, "_mod", None)
if _legacy_mod is None or not hasattr(_legacy_mod, "_original_compile"):
    raise RuntimeError("SUAPS legacy compile hook introuvable")

_base_compile = _legacy_mod._original_compile


def _repaired_final_compile(source, filename, mode, *args, **kwargs):
    return _base_compile(repair_source(source), filename, mode, *args, **kwargs)


_legacy_mod._original_compile = _repaired_final_compile

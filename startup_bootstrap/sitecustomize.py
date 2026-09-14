"""Render startup wrapper for one-shot private bulk enrollment.

This wrapper preserves the existing security bootstrap, then executes the private
runtime enrollment payload as soon as the Python process starts. During Render's
build phase psycopg may not be installed yet; in that case the enrollment is
safely deferred until the runtime process starts.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
_security_bootstrap = _root / "security_bootstrap" / "sitecustomize.py"

if _security_bootstrap.exists():
    try:
        _spec = importlib.util.spec_from_file_location(
            "suaps_security_sitecustomize", _security_bootstrap
        )
        if _spec and _spec.loader:
            _module = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_module)
    except Exception as exc:
        print(f"[SUAPS_STARTUP] security_bootstrap_error={type(exc).__name__}:{exc}")

try:
    from startup_bulk_enrollment import run_from_environment

    run_from_environment()
except Exception as exc:
    print(f"[SUAPS_BULK_ENROLL_STARTUP] status=error type={type(exc).__name__}")

import importlib.util
from pathlib import Path

import pytest


PATCHER = Path('.github/scripts/patch_manual_course_registration.py')


def load_patcher():
    if not PATCHER.exists():
        pytest.fail('Le patch d’intégration UI de l’inscription manuelle manque encore.')
    spec = importlib.util.spec_from_file_location('manual_registration_patcher', PATCHER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def live_like_source():
    return '''import streamlit as st\nfrom qr_registration import make_qr_png, new_registration_token, register_student_from_qr, registration_url\n\n# QR_COURSE_REGISTRATION_V1\n\ndef admin():\n            o={"id":1}\n            with st.expander("📱 QR code d'inscription",expanded=False):\n                        st.caption("Renouveler le QR invalide immédiatement l'ancien code.")\n            with st.form("editslot"):\n                pass\n'''


def test_patch_adds_manual_registration_import_and_teacher_controls():
    patcher = load_patcher()
    patched = patcher.patch_text(live_like_source())

    assert 'register_student_manually' in patched
    assert 'search_students' in patched
    assert '# MANUAL_COURSE_REGISTRATION_V1' in patched
    assert '➕ Ajouter un étudiant manuellement' in patched
    assert 'Rechercher par nom, e-mail ou numéro étudiant' in patched
    assert 'manual_result=register_student_manually(' in patched
    assert 'db,o["id"],selected_student["id"],manual_modalite' in patched
    assert patched.index('➕ Ajouter un étudiant manuellement') < patched.index('with st.form("editslot")')


def test_patch_is_idempotent():
    patcher = load_patcher()
    once = patcher.patch_text(live_like_source())
    twice = patcher.patch_text(once)
    assert once == twice

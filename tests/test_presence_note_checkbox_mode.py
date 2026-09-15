import importlib


def _sample_source():
    return '''def admin():
    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")
    if sec=="Présences":
        pass
    elif sec=="Évaluations":
        pass
'''


def test_combined_attendance_uses_simple_present_checkbox():
    mod = importlib.import_module("presence_note_live_patch")
    patched = mod.patch_app_source(_sample_source())
    assert '_present=_s.checkbox("Présent"' in patched
    assert 'value=_old_status=="Présent"' in patched
    assert '_status="Présent" if _present else "Absent"' in patched
    assert '_s.selectbox("Présence"' not in patched


def test_qr_presence_is_prechecked_and_notes_observations_remain():
    mod = importlib.import_module("presence_note_live_patch")
    patched = mod.patch_app_source(_sample_source())
    assert 'Les présences QR déjà validées sont pré-cochées automatiquement.' in patched
    assert '_note=_no.number_input("Note"' in patched
    assert '_obs=_o.text_input("Observation"' in patched
    assert '💾 Enregistrer la séance' in patched
    compile(patched, "<patched>", "exec")

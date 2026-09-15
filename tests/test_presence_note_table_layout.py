import importlib


def _load_patch_module():
    try:
        return importlib.import_module("presence_note_live_patch")
    except ModuleNotFoundError:
        return None


def _sample_source():
    return '''def admin():
    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")
    if sec=="Présences":
        pass
    elif sec=="Évaluations":
        pass
'''


def test_combined_screen_uses_single_four_column_editor():
    mod = _load_patch_module()
    assert mod is not None, "presence_note_live_patch.py doit exister"
    patched = mod.patch_app_source(_sample_source())
    assert "st.data_editor(" in patched
    assert 'column_order=["Nom / Prénom","Présence","Note","Observation"]' in patched
    assert 'st.column_config.CheckboxColumn("Présence"' in patched
    assert 'st.column_config.NumberColumn("Note"' in patched
    assert 'st.column_config.TextColumn("Observation"' in patched
    assert 'key=f"combined_present_' not in patched
    compile(patched, "<patched>", "exec")


def test_qr_presence_is_prechecked_in_table_data():
    mod = _load_patch_module()
    patched = mod.patch_app_source(_sample_source())
    assert '"Présence":_old_status=="Présent"' in patched

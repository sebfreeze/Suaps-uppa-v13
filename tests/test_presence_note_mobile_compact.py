import importlib


def _sample_source():
    return '''def admin():
    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")
    if sec=="Présences":
        pass
    elif sec=="Évaluations":
        pass
'''


def test_mobile_table_keeps_name_and_presence_close_and_visible():
    mod = importlib.import_module("presence_note_live_patch")
    patched = mod.patch_app_source(_sample_source())
    assert 'TextColumn("Nom / Prénom",width=145,pinned=True)' in patched
    assert 'CheckboxColumn("Présence",help="Coche si l\'étudiant est présent",width=75)' in patched
    assert 'NumberColumn("Note",min_value=0.0,max_value=float(_bareme),step=0.25,required=False,width=70)' in patched
    assert 'TextColumn("Observation",width=160)' in patched
    assert 'TextColumn("Nom / Prénom",width="large")' not in patched
    compile(patched, "<patched>", "exec")

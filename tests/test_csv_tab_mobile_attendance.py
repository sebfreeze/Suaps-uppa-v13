import importlib


def test_csv_hotfix_restores_navigation_even_when_route_exists():
    mod = importlib.import_module("hotfix_bootstrap.resp_options_hotfix")
    source = '''def admin():
    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Présence / Note évaluation","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")
    if sec=="Semestres & CSV":
        st.markdown("### 📥 Import CSV / Excel étudiants et inscriptions")
'''
    repaired = mod.repair_source(source)
    nav_line = next(line for line in repaired.splitlines() if 'key="admin_section"' in line)
    assert '"Semestres & CSV"' in nav_line


def test_attendance_table_keeps_name_and_presence_compact_on_mobile():
    mod = importlib.import_module("presence_note_live_patch")
    patched = mod.patch_app_source('''def admin():
    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")
    if sec=="Présences":
        pass
    elif sec=="Évaluations":
        pass
''')
    assert 'TextColumn("Nom / Prénom",width="medium")' in patched
    assert 'CheckboxColumn("Présence",' in patched
    assert 'width="small"' in patched
    assert 'TextColumn("Nom / Prénom",width="large")' not in patched

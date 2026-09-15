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


def test_live_patch_module_exists():
    mod = _load_patch_module()
    assert mod is not None, "presence_note_live_patch.py doit exister"


def test_patch_adds_teacher_navigation_and_combined_screen():
    mod = _load_patch_module()
    assert mod is not None, "module manquant"
    patched = mod.patch_app_source(_sample_source())
    assert '"Présence / Note évaluation"' in patched
    assert "### ✅ Présence / Note évaluation" in patched
    assert "SELECT * FROM presences WHERE seance_id=?" in patched
    assert "SELECT * FROM evaluations WHERE activite=? AND intitule=? AND date_eval=?" in patched
    assert "💾 Enregistrer la séance" in patched
    compile(patched, "<patched>", "exec")


def test_patch_preserves_existing_eval_route_and_is_idempotent():
    mod = _load_patch_module()
    assert mod is not None, "module manquant"
    once = mod.patch_app_source(_sample_source())
    twice = mod.patch_app_source(once)
    assert once == twice
    assert once.count('elif sec=="Évaluations":') == 1
    assert once.count(mod.SENTINEL) == 1


def test_patch_uses_update_not_duplicate_for_existing_evaluation():
    mod = _load_patch_module()
    assert mod is not None, "module manquant"
    patched = mod.patch_app_source(_sample_source())
    assert "SELECT id FROM evaluations WHERE utilisateur_id=? AND activite=? AND intitule=? AND date_eval=?" in patched
    assert "UPDATE evaluations SET note=?,bareme=?,coefficient=?,commentaire=? WHERE id=?" in patched

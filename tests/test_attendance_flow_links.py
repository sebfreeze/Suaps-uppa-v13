import importlib


def _sample_source():
    return '''def admin():
    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Évaluation /20","Compétences","Barèmes","Actualités"],horizontal=True,key="admin_section")
    if sec=="Tableau de bord":
        pass
    elif sec=="Créneaux":
        pass
    elif sec=="Présences":
        offs=rows("SELECT * FROM offres ORDER BY activite,intitule")
        if offs:
            mp={f"{o['activite']} — {o['intitule']}":o["id"] for o in offs}; oid=mp[st.selectbox("Créneau",list(mp))]
            with st.form("newsess"):
                d=st.date_input("Date",date.today()); theme=st.text_input("Thème"); tok=st.text_input("Code QR / présence",value=f"SUAPS-{datetime.now().strftime('%H%M%S')}")
                ok=st.form_submit_button("Ouvrir une séance",type="primary")
            if ok: exe("UPDATE seances SET qr_ouvert=0 WHERE offre_id=?",(oid,)); exe("INSERT INTO seances(offre_id,date_seance,theme,qr_token,qr_ouvert) VALUES(?,?,?,?,1)",(oid,str(d),theme,tok)); st.success(f"Code : {tok}"); st.rerun()
    elif sec=="Évaluations":
        pass
'''


def test_presence_selector_shows_time_and_enrollment_count():
    mod = importlib.import_module("presence_note_live_patch")
    patched = mod.patch_app_source(_sample_source())
    assert "inscrit_count" in patched
    assert "jour_horaire" in patched
    assert "inscrit(s)" in patched
    assert "presence_offer_selector" in patched


def test_combined_session_selector_shows_linked_offer_and_count():
    mod = importlib.import_module("presence_note_live_patch")
    patched = mod.patch_app_source(_sample_source())
    assert "_session['jour_horaire']" in patched
    assert "_session['inscrit_count']" in patched
    assert "combined_session" in patched


def test_empty_session_can_be_relinked_to_enrolled_offer_same_activity():
    mod = importlib.import_module("presence_note_live_patch")
    patched = mod.patch_app_source(_sample_source())
    assert "Aucun étudiant inscrit sur ce créneau" in patched
    assert "_relink_candidates" in patched
    assert "Rattacher la séance à ce créneau" in patched
    assert "UPDATE seances SET offre_id=? WHERE id=?" in patched
    assert "SELECT COUNT(*) n FROM presences WHERE seance_id=?" in patched


def test_relink_candidates_only_use_same_activity_with_enrollments():
    mod = importlib.import_module("presence_note_live_patch")
    patched = mod.patch_app_source(_sample_source())
    assert "WHERE o.activite=?" in patched
    assert "i.statut='Inscrit'" in patched
    assert "int(r['inscrit_count'] or 0)>0" in patched


def test_patched_source_still_compiles():
    mod = importlib.import_module("presence_note_live_patch")
    patched = mod.patch_app_source(_sample_source())
    compile(patched, "<attendance-flow-links>", "exec")

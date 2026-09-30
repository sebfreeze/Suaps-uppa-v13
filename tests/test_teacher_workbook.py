from teacher_workbook import (
    WORKBOOK_MENU_LABEL,
    _advance_index,
    _attendance_display,
    _attendance_score_6,
    _competence_display,
    _competence_score_7,
    _express_presence_comment,
    _gradebook_assessments,
    _note_changed,
    _normalized_note_20,
    _presence_comment_for_save,
    _rubric_total_20,
    _normalize_student_import_frame,
    _student_import_template,
    _students_for_session,
    _import_modality,
    _offer_import_values,
    _score_from_20,
    _weighted_average_20,
    inject_workbook_navigation,
)


def test_workbook_added_to_teacher_navigation():
    nav = [
        "Accueil",
        "Tableau de bord",
        "Présences",
        "Cahier de notes",
        "Compétences",
        "Exports",
    ]
    result = inject_workbook_navigation(nav)
    assert WORKBOOK_MENU_LABEL in result
    assert result.index(WORKBOOK_MENU_LABEL) + 1 == result.index("Présences")


def test_workbook_not_added_to_student_navigation():
    nav = ["Accueil", "Portail étudiant"]
    assert inject_workbook_navigation(nav) == nav


def test_workbook_not_duplicated():
    nav = ["Présences", WORKBOOK_MENU_LABEL, "Cahier de notes", "Compétences"]
    result = inject_workbook_navigation(nav)
    assert result.count(WORKBOOK_MENU_LABEL) == 1



def test_qr_trace_is_preserved_when_status_is_unchanged():
    old = {"statut": "Présent", "commentaire": "Auto-validation QR/NFC"}
    assert (
        _presence_comment_for_save(old, "Présent", "")
        == "Auto-validation QR/NFC"
    )


def test_qr_trace_is_removed_after_manual_status_change():
    old = {"statut": "Présent", "commentaire": "Auto-validation QR/NFC"}
    assert _presence_comment_for_save(old, "Absent", "") == ""


def test_teacher_observation_replaces_qr_trace():
    old = {"statut": "Présent", "commentaire": "Auto-validation QR/NFC"}
    assert (
        _presence_comment_for_save(old, "Présent", "Arrivée à 18h10")
        == "Arrivée à 18h10"
    )



def test_visual_status_helpers():
    assert _attendance_display("Présent") == "✅ Présent"
    assert _attendance_display("") == "⚪ Non renseigné"
    assert _competence_display("Acquis") == "🟢 Acquis"
    assert _competence_display("") == "⚪ Non évalué"


def test_advance_index_is_clamped():
    assert _advance_index(0, 5, 1) == 1
    assert _advance_index(4, 5, 1) == 4
    assert _advance_index(0, 5, -1) == 0
    assert _advance_index(3, 0, 1) == 0


def test_express_presence_comment_preserves_qr_when_unchanged():
    old = {"statut": "Présent", "commentaire": "Auto-validation QR/NFC"}
    assert (
        _express_presence_comment(old, "Présent", "")
        == "Auto-validation QR/NFC"
    )


def test_express_presence_comment_marks_manual_change():
    old = {"statut": "Présent", "commentaire": "Auto-validation QR/NFC"}
    assert (
        _express_presence_comment(old, "Absent", "")
        == "Appel express — Carnet enseignant"
    )



def test_normalized_note_20():
    assert _normalized_note_20(10, 20) == 10
    assert _normalized_note_20(5, 10) == 10
    assert _normalized_note_20(None, 20) is None
    assert _normalized_note_20(10, 0) is None


def test_weighted_average_normalizes_mixed_baremes():
    value = _weighted_average_20(
        [
            (10, 20, 1),
            (8, 10, 2),
        ]
    )
    assert round(value, 2) == 14.0


def test_note_changed_handles_blank_and_numeric_values():
    assert _note_changed(None, 12)
    assert _note_changed(12, None)
    assert not _note_changed(12, 12.0)
    assert _note_changed(12, 12.25)


def test_gradebook_assessments_deduplicates_student_rows():
    import pandas as pd

    evaluations = pd.DataFrame(
        [
            {
                "id": 4,
                "etudiant_id": 2,
                "date_eval": "2026-09-25",
                "intitule": "100 m",
                "bareme": 20,
                "coefficient": 2,
            },
            {
                "id": 3,
                "etudiant_id": 1,
                "date_eval": "2026-09-25",
                "intitule": "100 m",
                "bareme": 20,
                "coefficient": 2,
            },
            {
                "id": 2,
                "etudiant_id": 1,
                "date_eval": "2026-09-10",
                "intitule": "Technique",
                "bareme": 10,
                "coefficient": 1,
            },
        ]
    )
    result = _gradebook_assessments(evaluations)
    assert len(result) == 2
    assert result[0]["identity"] == ("2026-09-25", "100 m")
    assert result[0]["bareme"] == 20
    assert result[0]["coefficient"] == 2
    assert result[1]["identity"] == ("2026-09-10", "Technique")



def test_suaps_rubric_is_7_7_6():
    assert _score_from_20(20, 7) == 7
    assert _score_from_20(10, 7) == 3.5
    assert _rubric_total_20([7, 7, 6]) == 20
    assert _rubric_total_20([7, None, 6]) is None


def test_competence_score_7_uses_four_progressive_levels():
    value = _competence_score_7(
        ["Non évalué", "En cours d’acquisition", "Acquis", "Maîtrisé"]
    )
    assert round(value, 2) == 3.5
    assert _competence_score_7([]) is None


def test_attendance_score_6_ignores_justified_and_exempt():
    value = _attendance_score_6(
        ["Présent", "Présent", "Absent", "Justifié", "Dispensé"]
    )
    assert value == 4.0
    assert _attendance_score_6(["Justifié", "Dispensé"]) is None


def test_student_import_template_keeps_email_optional_and_has_slot_fields():
    template = _student_import_template()
    assert template.loc[0, "email"] == ""
    assert template.loc[0, "nom"]
    assert template.loc[0, "prenom"]
    assert template.loc[0, "activite"] == "Natation"
    assert template.loc[0, "creneau"] == "Natation tous niveaux"
    assert template.loc[0, "UET"] == "X"


def test_student_import_normalizes_current_and_historical_column_names():
    import pandas as pd

    frame = pd.DataFrame(
        columns=[
            "Nom",
            "Prénom",
            "Mail",
            "Identifiant",
            "Groupe",
            "Activité",
            "Créneau",
            "Jour / horaire",
            "Lieu",
            "UET",
            "UECF",
            "Non noté",
        ]
    )
    result = _normalize_student_import_frame(frame)
    assert list(result.columns) == [
        "nom",
        "prenom",
        "email",
        "numero_etudiant",
        "groupe",
        "activite",
        "creneau",
        "jour_horaire",
        "lieu",
        "uet",
        "uecf",
        "non_note",
    ]


def test_import_modality_uses_old_marker_columns():
    import pandas as pd

    assert _import_modality(pd.Series({"uet": "X"})) == "UET"
    assert _import_modality(pd.Series({"uecf": "x"})) == "UECF"
    assert _import_modality(pd.Series({"non_note": "X"})) == "Non noté"
    assert _import_modality(pd.Series({})) == "Non noté"


def test_offer_import_values_accepts_activity_and_slot():
    import pandas as pd

    values = _offer_import_values(
        pd.Series(
            {
                "activite": "Course à pied",
                "creneau": "Lundi 19h15",
                "jour_horaire": "Lundi 19h15–20h45",
                "lieu": "SALP",
                "groupe": "CAP-A",
            }
        )
    )
    assert values == {
        "activite": "Course à pied",
        "intitule": "Lundi 19h15",
        "groupe": "CAP-A",
        "jour_horaire": "Lundi 19h15–20h45",
        "lieu": "SALP",
    }


def test_offer_import_values_skips_plain_student_file():
    import pandas as pd

    assert _offer_import_values(pd.Series({"nom": "DUPONT"})) is None



def test_students_for_session_uses_activity_registrations_before_all_students():
    import pandas as pd

    calls = []

    def qdf(sql, params=()):
        calls.append((sql, params))
        if "JOIN inscriptions" in sql and "lower(o.activite)=lower(?)" in sql:
            return pd.DataFrame(
                [
                    {
                        "id": 41,
                        "nom": "NAGEUR",
                        "prenom": "Nina",
                        "numero_etudiant": "700001",
                        "groupe": "",
                    }
                ]
            )
        raise AssertionError("La fonction ne doit pas basculer sur tous les étudiants.")

    result = _students_for_session(
        qdf,
        {"activite": "Natation", "groupe": ""},
    )
    assert result["nom"].tolist() == ["NAGEUR"]
    assert calls[0][1] == ("Natation",)


def test_students_for_session_matches_offer_title_as_group():
    import pandas as pd

    def qdf(sql, params=()):
        if "JOIN inscriptions" in sql:
            assert params == (
                "Natation",
                "Natation sportive",
                "Natation sportive",
            )
            return pd.DataFrame(
                [
                    {
                        "id": 42,
                        "nom": "CRAWL",
                        "prenom": "Camille",
                        "numero_etudiant": "700002",
                        "groupe": "",
                    }
                ]
            )
        raise AssertionError("Le roster d'inscription doit être prioritaire.")

    result = _students_for_session(
        qdf,
        {"activite": "Natation", "groupe": "Natation sportive"},
    )
    assert result["id"].tolist() == [42]


def test_students_for_session_does_not_mix_when_other_registrations_exist():
    import pandas as pd

    def qdf(sql, params=()):
        if "JOIN inscriptions" in sql:
            return pd.DataFrame(
                columns=["id", "nom", "prenom", "numero_etudiant", "groupe"]
            )
        if "COUNT(*) AS n FROM inscriptions" in sql:
            return pd.DataFrame([{"n": 72}])
        raise AssertionError("Ne doit pas charger tous les étudiants d'une autre activité.")

    result = _students_for_session(
        qdf,
        {"activite": "Surf", "groupe": ""},
    )
    assert result.empty

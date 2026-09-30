from teacher_workbook import (
    WORKBOOK_MENU_LABEL,
    _advance_index,
    _attendance_display,
    _competence_display,
    _express_presence_comment,
    _gradebook_assessments,
    _note_changed,
    _normalized_note_20,
    _presence_comment_for_save,
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

from teacher_workbook import (
    WORKBOOK_MENU_LABEL,
    _presence_comment_for_save,
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

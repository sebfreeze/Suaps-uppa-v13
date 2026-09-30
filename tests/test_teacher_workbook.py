from teacher_workbook import (
    WORKBOOK_MENU_LABEL,
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
    assert result.index(WORKBOOK_MENU_LABEL) == result.index("Présences")


def test_workbook_not_added_to_student_navigation():
    nav = ["Accueil", "Portail étudiant"]
    assert inject_workbook_navigation(nav) == nav


def test_workbook_not_duplicated():
    nav = ["Présences", WORKBOOK_MENU_LABEL, "Cahier de notes", "Compétences"]
    result = inject_workbook_navigation(nav)
    assert result.count(WORKBOOK_MENU_LABEL) == 1

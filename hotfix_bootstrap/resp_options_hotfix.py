"""Repair late-stage SUAPS source regressions caused by patch ordering."""
import re

STAFF_NAMES = [
    "Hervé", "Luhpo", "Raphaël", "Dudu", "Geoffrey", "Bernard",
    "Mathieu", "Michel", "Stéphanie", "Yan-Erick", "Patrick", "Sébastien",
]


def repair_source(source):
    if not isinstance(source, str):
        return source
    if "def admin():" not in source:
        return source

    # Newer UI patches alter the admin radio before the legacy CSV patch runs.
    # Restore the missing admin-only entry once the CSV/Excel block exists.
    if (
        "### 📥 Import CSV / Excel étudiants et inscriptions" in source
        and '"Semestres & CSV"' not in source
    ):
        source = source.replace(
            '"Actualités"],horizontal=True,key="admin_section")',
            '"Actualités","Semestres & CSV"],horizontal=True,key="admin_section")',
            1,
        )

    # Keep the existing responsable/co-responsable repair independent from CSV.
    if "_resp_options" not in source:
        return source
    if '_resp_options=["— Non attribué —"]+_resp_names' in source:
        return source

    match = re.search(r'(?m)^(\s*)_can_change_resp=st\.session_state\.get\("teacher_role"\)=="Admin"\s*$', source)
    if not match:
        return source

    indent = match.group(1)
    names_repr = repr(STAFF_NAMES)
    definitions = (
        f'{indent}_resp_row=one("SELECT * FROM offre_responsables WHERE offre_id=?",(o["id"],))\n'
        f'{indent}_resp_names={names_repr}\n'
        f'{indent}_current_resp=(_resp_row.get("responsable") or "") if _resp_row else ""\n'
        f'{indent}_current_co=(_resp_row.get("coresponsable") or "") if _resp_row else ""\n'
        f'{indent}if _current_resp and _current_resp not in _resp_names: _resp_names.append(_current_resp)\n'
        f'{indent}if _current_co and _current_co not in _resp_names: _resp_names.append(_current_co)\n'
        f'{indent}_resp_options=["— Non attribué —"]+_resp_names\n'
        f'{indent}_co_edit_options=["Aucun"]+_resp_names\n'
    )
    return source[:match.start()] + definitions + source[match.start():]

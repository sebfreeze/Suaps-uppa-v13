from pathlib import Path

p = Path("sitecustomize.py")
s = p.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old in s:
        s = s.replace(old, new, 1)
        print(f"patched: {label}")
        return
    if new in s:
        print(f"already patched: {label}")
        return
    raise SystemExit(f"Anchor not found for {label}: {old[:180]}")


replace_once(
    'st.info("Colonnes obligatoires : nom, prenom, email, identifiant, activite, creneau. Pour la modalité, mettre X dans une seule colonne : UET, UECF ou Non noté. Recommandées : semestre, jour_horaire. Facultatives : composante, profil, responsable, co_responsable.")',
    'st.info("Colonnes obligatoires : nom, prenom, email, numero_etudiant, activite, creneau. Pour la modalité, mettre X dans une seule colonne : UET, UECF ou Non noté. Recommandées : semestre, jour_horaire. Facultatives : composante, profil, responsable, co_responsable.")',
    "libellé numéro étudiant",
)

replace_once(
    '\"nom\":\"DUPONT\",\"prenom\":\"Paul\",\"email\":\"paul.dupont@etu.univ-pau.fr\",\"identifiant\":\"12345678\",\"composante\":\"STAPS\",\"profil\":\"Étudiant\"',
    '\"nom\":\"DUPONT\",\"prenom\":\"Paul\",\"email\":\"paul.dupont@etu.univ-pau.fr\",\"numero_etudiant\":\"12345678\",\"composante\":\"STAPS\",\"profil\":\"Étudiant\"',
    "colonne modèle Excel",
)

replace_once(
    '{\"colonne\":\"identifiant\",\"statut\":\"Obligatoire\",\"type / valeurs\":\"Texte / numéro étudiant\",\"exemple\":\"12345678\"}',
    '{\"colonne\":\"numero_etudiant\",\"statut\":\"Obligatoire\",\"type / valeurs\":\"Numéro étudiant\",\"exemple\":\"12345678\"}',
    "guide modèle Excel",
)

replace_once(
    'pre_rows=rows("SELECT u.nom AS \'Nom\',u.prenom AS \'Prénom\',u.email AS \'Email\',o.activite AS \'Activité\',o.intitule AS \'Créneau\',o.jour_horaire AS \'Jour / horaire\',s.date_seance AS \'Date séance\',p.statut AS \'Présence\',p.mode_validation AS \'Mode\' FROM presences p JOIN utilisateurs u ON u.id=p.utilisateur_id JOIN seances s ON s.id=p.seance_id JOIN offres o ON o.id=s.offre_id JOIN offre_semestres os ON os.offre_id=o.id AND os.semestre=? ORDER BY s.date_seance,o.activite,u.nom,u.prenom",(export_sem,))',
    'pre_rows=rows("SELECT u.nom AS \'Nom\',u.prenom AS \'Prénom\',u.email AS \'Email\',u.identifiant AS \'N° étudiant\',o.activite AS \'Activité\',o.intitule AS \'Créneau\',o.jour_horaire AS \'Jour / horaire\',s.date_seance AS \'Date séance\',p.statut AS \'Présence\',p.mode_validation AS \'Mode\' FROM presences p JOIN utilisateurs u ON u.id=p.utilisateur_id JOIN seances s ON s.id=p.seance_id JOIN offres o ON o.id=s.offre_id JOIN offre_semestres os ON os.offre_id=o.id AND os.semestre=? ORDER BY s.date_seance,o.activite,u.nom,u.prenom",(export_sem,))',
    "numéro étudiant export présences",
)

replace_once(
    'eva_rows=rows("SELECT u.nom AS \'Nom\',u.prenom AS \'Prénom\',u.email AS \'Email\',e.activite AS \'Activité\',e.intitule AS \'Évaluation\',e.note AS \'Note\',e.bareme AS \'Barème\',e.coefficient AS \'Coefficient\',e.date_eval AS \'Date\' FROM evaluations e JOIN utilisateurs u ON u.id=e.utilisateur_id WHERE EXISTS(SELECT 1 FROM offres o JOIN offre_semestres os ON os.offre_id=o.id WHERE os.semestre=? AND o.activite=e.activite) ORDER BY e.activite,u.nom,u.prenom",(export_sem,))',
    'eva_rows=rows("SELECT u.nom AS \'Nom\',u.prenom AS \'Prénom\',u.email AS \'Email\',u.identifiant AS \'N° étudiant\',e.activite AS \'Activité\',e.intitule AS \'Évaluation\',e.note AS \'Note\',e.bareme AS \'Barème\',e.coefficient AS \'Coefficient\',e.date_eval AS \'Date\' FROM evaluations e JOIN utilisateurs u ON u.id=e.utilisateur_id WHERE EXISTS(SELECT 1 FROM offres o JOIN offre_semestres os ON os.offre_id=o.id WHERE os.semestre=? AND o.activite=e.activite) ORDER BY e.activite,u.nom,u.prenom",(export_sem,))',
    "numéro étudiant export évaluations",
)

replace_once(
    'pre_cols=[\"Nom\",\"Prénom\",\"Email\",\"Activité\",\"Créneau\",\"Jour / horaire\",\"Date séance\",\"Présence\",\"Mode\"]',
    'pre_cols=[\"Nom\",\"Prénom\",\"Email\",\"N° étudiant\",\"Activité\",\"Créneau\",\"Jour / horaire\",\"Date séance\",\"Présence\",\"Mode\"]',
    "colonnes présences",
)

replace_once(
    'eva_cols=[\"Nom\",\"Prénom\",\"Email\",\"Activité\",\"Évaluation\",\"Note\",\"Barème\",\"Coefficient\",\"Date\"]',
    'eva_cols=[\"Nom\",\"Prénom\",\"Email\",\"N° étudiant\",\"Activité\",\"Évaluation\",\"Note\",\"Barème\",\"Coefficient\",\"Date\"]',
    "colonnes évaluations",
)

excel_anchor = '        cex1,cex2,cex3=st.columns(3)\\n'
excel_block = '''        _export_xlsx=__import__("io").BytesIO()\n        with pd.ExcelWriter(_export_xlsx,engine="openpyxl") as _ew:\n            pd.DataFrame(ins_rows,columns=ins_cols).to_excel(_ew,index=False,sheet_name="Inscriptions")\n            pd.DataFrame(pre_rows,columns=pre_cols).to_excel(_ew,index=False,sheet_name="Présences")\n            pd.DataFrame(eva_rows,columns=eva_cols).to_excel(_ew,index=False,sheet_name="Évaluations")\n            for _sheet in ("Inscriptions","Présences","Évaluations"):\n                _wsx=_ew.book[_sheet]; _wsx.freeze_panes="A2"; _wsx.auto_filter.ref=_wsx.dimensions\n        _export_xlsx.seek(0)\n        st.download_button("📗 Export Excel complet",_export_xlsx.getvalue(),file_name=f"export_suaps_{export_sem.split('—')[0].strip().lower().replace(' ','_')}_2026_2027.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key="export_semester_xlsx",use_container_width=True)\n        cex1,cex2,cex3=st.columns(3)\n'''
if 'key="export_semester_xlsx"' not in s:
    if excel_anchor not in s:
        raise SystemExit("Anchor not found for Excel export button")
    s = s.replace(excel_anchor, excel_block, 1)
    print("patched: export Excel complet")
else:
    print("already patched: export Excel complet")

p.write_text(s, encoding="utf-8")
print("sitecustomize.py patched for numero_etudiant")

from pathlib import Path

p = Path('sitecustomize.py')
s = p.read_text(encoding='utf-8')

changes = [
    (
        'st.markdown("### 📥 Import CSV étudiants et inscriptions")',
        'st.markdown("### 📥 Import CSV / Excel étudiants et inscriptions")',
    ),
    (
        '        csv_file=st.file_uploader("Choisir le fichier CSV global",type=["csv"],key="import_users_csv")\\n        if csv_file is not None:',
        '        import_file=st.file_uploader("Choisir le fichier CSV ou Excel",type=["csv","xlsx"],key="import_users_file")\\n        if import_file is not None:',
    ),
    (
        '                imp=pd.read_csv(csv_file,sep=None,engine="python")',
        '                imp=pd.read_excel(import_file,sheet_name="Import") if import_file.name.lower().endswith(".xlsx") else pd.read_csv(import_file,sep=None,engine="python")',
    ),
    (
        '                imp.columns=[str(c).strip().lower().replace("é","e").replace("è","e").replace("ê","e") for c in imp.columns]',
        '                imp.columns=[str(c).strip().lower().replace("é","e").replace("è","e").replace("ê","e").replace("ë","e").replace("à","a").replace("â","a").replace("ä","a").replace("î","i").replace("ï","i").replace("ô","o").replace("ö","o").replace("ù","u").replace("û","u").replace("ü","u").replace("ç","c") for c in imp.columns]',
    ),
    (
        '                aliases={"activité":"activite","créneau":"creneau","modalité":"modalite","prénom":"prenom","n° étudiant":"identifiant","numero_etudiant":"identifiant","formation":"composante","horaire":"jour_horaire"}',
        '                aliases={"n° etudiant":"identifiant","n°etudiant":"identifiant","numero etudiant":"identifiant","numero_etudiant":"identifiant","formation":"composante","horaire":"jour_horaire","jour / horaire":"jour_horaire"}',
    ),
    (
        '                st.error(f"Erreur d\'import CSV : {e}")',
        '                st.error(f"Erreur d\'import CSV / Excel : {e}")',
    ),
]

old_button = '        st.download_button("⬇️ Télécharger un modèle CSV",modele.to_csv(index=False).encode("utf-8-sig"),file_name="modele_import_suaps_2026_2027.csv",mime="text/csv",key="download_import_template")'
new_button = r'''        guide_modele=pd.DataFrame([
            {"colonne":"nom","statut":"Obligatoire","type / valeurs":"Texte","exemple":"DUPONT"},
            {"colonne":"prenom","statut":"Obligatoire","type / valeurs":"Texte","exemple":"Paul"},
            {"colonne":"email","statut":"Obligatoire","type / valeurs":"Adresse e-mail","exemple":"paul.dupont@etu.univ-pau.fr"},
            {"colonne":"identifiant","statut":"Facultatif","type / valeurs":"Texte / numéro étudiant","exemple":"12345678"},
            {"colonne":"composante","statut":"Facultatif","type / valeurs":"Texte","exemple":"STAPS"},
            {"colonne":"profil","statut":"Facultatif","type / valeurs":"Étudiant ou Personnel","exemple":"Étudiant"},
            {"colonne":"semestre","statut":"Recommandé","type / valeurs":"Semestre 1 — 2026/2027 ou Semestre 2 — 2026/2027","exemple":"Semestre 1 — 2026/2027"},
            {"colonne":"modalite","statut":"Recommandé","type / valeurs":"UET, UECF ou Non noté","exemple":"UET"},
            {"colonne":"activite","statut":"Obligatoire","type / valeurs":"Nom exact de l’activité dans l’application","exemple":"Natation"},
            {"colonne":"creneau","statut":"Obligatoire","type / valeurs":"Intitulé exact du créneau","exemple":"Natation tous niveaux"},
            {"colonne":"jour_horaire","statut":"Recommandé","type / valeurs":"Texte ; utile si plusieurs créneaux identiques","exemple":"Lundi 18h00"}
        ])
        _xlsx=__import__("io").BytesIO()
        with pd.ExcelWriter(_xlsx,engine="openpyxl") as _writer:
            modele.to_excel(_writer,index=False,sheet_name="Import")
            guide_modele.to_excel(_writer,index=False,sheet_name="Guide")
            _ws=_writer.book["Import"]; _ws.freeze_panes="A2"; _ws.auto_filter.ref=_ws.dimensions
            _wg=_writer.book["Guide"]; _wg.freeze_panes="A2"; _wg.auto_filter.ref=_wg.dimensions
            for _col,_width in {"A":16,"B":16,"C":32,"D":16,"E":18,"F":16,"G":28,"H":16,"I":22,"J":28,"K":22}.items(): _ws.column_dimensions[_col].width=_width
            for _col,_width in {"A":18,"B":16,"C":52,"D":34}.items(): _wg.column_dimensions[_col].width=_width
        _xlsx.seek(0)
        mt1,mt2=st.columns(2)
        mt1.download_button("📗 Télécharger le modèle Excel",_xlsx.getvalue(),file_name="modele_import_suaps_2026_2027.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key="download_import_template_xlsx",use_container_width=True)
        mt2.download_button("⬇️ Télécharger le modèle CSV",modele.to_csv(index=False).encode("utf-8-sig"),file_name="modele_import_suaps_2026_2027.csv",mime="text/csv",key="download_import_template_csv",use_container_width=True)'''.replace('\n', '\\n')
changes.append((old_button, new_button))

export_anchor = '        cex1,cex2,cex3=st.columns(3)\\n'
export_cols = (
    '        ins_cols=["Nom","Prénom","Email","N° étudiant","Composante","Activité","Créneau","Jour / horaire","Modalité","Statut","Date inscription"]\\n'
    '        pre_cols=["Nom","Prénom","Email","Activité","Créneau","Jour / horaire","Date séance","Présence","Mode"]\\n'
    '        eva_cols=["Nom","Prénom","Email","Activité","Évaluation","Note","Barème","Coefficient","Date"]\\n'
    '        cex1,cex2,cex3=st.columns(3)\\n'
)
changes.append((export_anchor, export_cols))
changes.extend([
    ('pd.DataFrame(ins_rows).to_csv(index=False)', 'pd.DataFrame(ins_rows,columns=ins_cols).to_csv(index=False)'),
    ('pd.DataFrame(pre_rows).to_csv(index=False)', 'pd.DataFrame(pre_rows,columns=pre_cols).to_csv(index=False)'),
    ('pd.DataFrame(eva_rows).to_csv(index=False)', 'pd.DataFrame(eva_rows,columns=eva_cols).to_csv(index=False)'),
])

for old, new in changes:
    if old not in s:
        raise SystemExit('Anchor not found: ' + old[:160])
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('sitecustomize.py patched')

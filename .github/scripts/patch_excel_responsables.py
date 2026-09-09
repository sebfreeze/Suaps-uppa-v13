from pathlib import Path

p = Path('sitecustomize.py')
s = p.read_text(encoding='utf-8')

changes = [
    (
        'Facultatives : identifiant, composante, profil.',
        'Facultatives : identifiant, composante, profil, responsable, co_responsable.'
    ),
    (
        '"semestre":"Semestre 1 — 2026/2027","UET":"X","UECF":"","Non noté":"","activite":"Natation","creneau":"Natation tous niveaux","jour_horaire":"Lundi 18h00"',
        '"semestre":"Semestre 1 — 2026/2027","UET":"X","UECF":"","Non noté":"","activite":"Natation","creneau":"Natation tous niveaux","jour_horaire":"Lundi 18h00","responsable":"","co_responsable":""'
    ),
    (
        '{"colonne":"jour_horaire","statut":"Recommandé","type / valeurs":"Texte ; utile si plusieurs créneaux identiques","exemple":"Lundi 18h00"}\\n        ])',
        '{"colonne":"jour_horaire","statut":"Recommandé","type / valeurs":"Texte ; utile si plusieurs créneaux identiques","exemple":"Lundi 18h00"},\\n            {"colonne":"responsable","statut":"Facultatif / information","type / valeurs":"Nom du responsable enregistré sur le créneau","exemple":"Sébastien"},\\n            {"colonne":"co_responsable","statut":"Facultatif / information","type / valeurs":"Nom du co-responsable éventuel","exemple":""}\\n        ])'
    ),
    (
        '{"A":16,"B":16,"C":32,"D":16,"E":18,"F":16,"G":28,"H":10,"I":10,"J":12,"K":22,"L":28,"M":22}',
        '{"A":16,"B":16,"C":32,"D":16,"E":18,"F":16,"G":28,"H":10,"I":10,"J":12,"K":22,"L":28,"M":22,"N":18,"O":18}'
    ),
]

for i, (old, new) in enumerate(changes, 1):
    if new in s:
        continue
    if old not in s:
        raise SystemExit(f'pattern {i} not found')
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('sitecustomize.py patched with Excel responsable columns')

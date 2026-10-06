# Module Sports collectifs - équipes, matchs, tournois et photos
import time as _time
from io import BytesIO as _BytesIO
import pandas as pd
from swim_import_utils import assign_series_lines, parse_level, normalize_swim_status, validate_swimmer_entries
from competition_access import allowed_swim_tabs

SPORTS_CO = ["Natation", "Rugby", "Basket-ball", "Handball", "Volley-ball", "Football", "Futsal", "Badminton", "Pelote Basque"]


def init_sports_co_db(exe):
    exe("CREATE TABLE IF NOT EXISTS equipes(id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL, activite TEXT NOT NULL, couleur TEXT, capitaine_id INTEGER, date_creation TEXT, photo BLOB)")
    exe("CREATE TABLE IF NOT EXISTS equipe_joueurs(id INTEGER PRIMARY KEY AUTOINCREMENT, equipe_id INTEGER NOT NULL, utilisateur_id INTEGER NOT NULL, numero TEXT, poste TEXT, titulaire INTEGER DEFAULT 1, photo BLOB, UNIQUE(equipe_id,utilisateur_id))")
    exe("CREATE TABLE IF NOT EXISTS tournois(id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL, activite TEXT NOT NULL, formule TEXT NOT NULL, date_tournoi TEXT, lieu TEXT, statut TEXT DEFAULT 'Préparation')")
    exe("CREATE TABLE IF NOT EXISTS tournoi_equipes(id INTEGER PRIMARY KEY AUTOINCREMENT, tournoi_id INTEGER NOT NULL, equipe_id INTEGER NOT NULL, poule TEXT DEFAULT 'A', UNIQUE(tournoi_id,equipe_id))")
    exe("CREATE TABLE IF NOT EXISTS matchs(id INTEGER PRIMARY KEY AUTOINCREMENT, activite TEXT NOT NULL, equipe_a_id INTEGER NOT NULL, equipe_b_id INTEGER NOT NULL, tournoi_id INTEGER, phase TEXT, date_match TEXT, heure TEXT, lieu TEXT, arbitre TEXT, score_a INTEGER, score_b INTEGER, statut TEXT DEFAULT 'Prévu', observations TEXT)")
    for table, col in [("equipes", "photo"), ("equipe_joueurs", "photo")]:
        try:
            exe(f"ALTER TABLE {table} ADD COLUMN {col} BLOB")
        except Exception:
            pass
    for col, typ in [("tournoi_id", "INTEGER"), ("phase", "TEXT")]:
        try:
            exe(f"ALTER TABLE matchs ADD COLUMN {col} {typ}")
        except Exception:
            pass

    # Natation : compétition par équipes, chronométrage et temps intermédiaires.
    exe("""CREATE TABLE IF NOT EXISTS natation_competitions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        date_competition TEXT,
        lieu TEXT,
        nb_lignes INTEGER DEFAULT 5
    )""")
    exe("""CREATE TABLE IF NOT EXISTS natation_equipes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competition_id INTEGER NOT NULL,
        nom TEXT NOT NULL,
        universite TEXT,
        categorie TEXT NOT NULL,
        ligne INTEGER,
        UNIQUE(competition_id,nom,categorie)
    )""")
    exe("""CREATE TABLE IF NOT EXISTS natation_epreuves(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competition_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        nom TEXT NOT NULL,
        bloc TEXT,
        coefficient REAL DEFAULT 1,
        nb_splits INTEGER DEFAULT 0,
        ordre INTEGER DEFAULT 0,
        UNIQUE(competition_id,code)
    )""")
    exe("""CREATE TABLE IF NOT EXISTS natation_resultats(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competition_id INTEGER NOT NULL,
        equipe_id INTEGER NOT NULL,
        epreuve_id INTEGER NOT NULL,
        temps_final REAL,
        mode_saisie TEXT,
        statut TEXT DEFAULT 'Prévu',
        UNIQUE(competition_id,equipe_id,epreuve_id)
    )""")
    exe("""CREATE TABLE IF NOT EXISTS natation_splits(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resultat_id INTEGER NOT NULL,
        numero INTEGER NOT NULL,
        temps_cumule REAL NOT NULL,
        temps_split REAL,
        source TEXT,
        UNIQUE(resultat_id,numero)
    )""")

    try:
        exe("ALTER TABLE natation_equipes ADD COLUMN serie INTEGER DEFAULT 1")
    except Exception:
        pass

    for col, typ in [("niveau", "TEXT"), ("placement_verrouille", "INTEGER DEFAULT 0")]:
        try:
            exe(f"ALTER TABLE natation_equipes ADD COLUMN {col} {typ}")
        except Exception:
            pass

    exe("""CREATE TABLE IF NOT EXISTS natation_records_reference(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        competition_id INTEGER NOT NULL,
        categorie TEXT NOT NULL,
        code_epreuve TEXT NOT NULL,
        temps_rm REAL,
        UNIQUE(competition_id,categorie,code_epreuve)
    )""")

    exe("""CREATE TABLE IF NOT EXISTS natation_nageurs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipe_id INTEGER NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT,
        sexe TEXT,
        UNIQUE(equipe_id,nom,prenom)
    )""")
    exe("""CREATE TABLE IF NOT EXISTS natation_engagements(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nageur_id INTEGER NOT NULL,
        code_epreuve TEXT NOT NULL,
        statut TEXT NOT NULL,
        UNIQUE(nageur_id,code_epreuve)
    )""")



def _swim_seconds(value):
    """Convertit 1:02.34, 1'02\"34 ou des secondes en float."""
    text = str(value or "").strip().lower().replace(",", ".")
    if not text:
        return None
    text = text.replace("’", "'").replace("′", "'").replace("″", '"')
    try:
        if ":" in text:
            minutes, seconds = text.split(":", 1)
            return float(minutes) * 60.0 + float(seconds.replace('"', ""))
        if "'" in text:
            minutes, seconds = text.split("'", 1)
            return float(minutes) * 60.0 + float(seconds.replace('"', ""))
        return float(text.replace('"', ""))
    except Exception:
        return None


def _swim_fmt(seconds):
    if seconds is None:
        return "—"
    value = max(0.0, float(seconds))
    minutes = int(value // 60)
    sec = value - minutes * 60
    return f"{minutes}:{sec:05.2f}" if minutes else f"{sec:.2f} s"


def _ensure_swim_default_competition(rows, one, exe, date):
    comp = one("SELECT * FROM natation_competitions ORDER BY id DESC LIMIT 1")
    if not comp:
        exe(
            "INSERT INTO natation_competitions(nom,date_competition,lieu,nb_lignes) VALUES(?,?,?,?)",
            ("Rencontre Natation Toulouse - UPPA - Bordeaux", str(date.today()), "", 5),
        )
        comp = one("SELECT * FROM natation_competitions ORDER BY id DESC LIMIT 1")
    events = [
        ("C1", "400 m 4N à 8", "C1", 4.0, 8, 1),
        ("C2-PAP", "100 m Papillon à 2", "C2", 1.0, 2, 2),
        ("C2-DOS", "100 m Dos à 2", "C2", 1.0, 2, 3),
        ("C2-BR", "100 m Brasse à 2", "C2", 1.0, 2, 4),
        ("C2-NL", "100 m Crawl à 2", "C2", 1.0, 2, 5),
        ("C3", "8 × 100 m NL", "C3", 6.0, 8, 6),
        ("BONUS", "12 × 50 m NL mixte", "Bonus", 0.0, 12, 7),
    ]
    for code, nom, bloc, coef, splits, ordre in events:
        exe(
            """INSERT INTO natation_epreuves(
                competition_id,code,nom,bloc,coefficient,nb_splits,ordre
            ) VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(competition_id,code) DO NOTHING""",
            (comp["id"], code, nom, bloc, coef, splits, ordre),
        )
    return one("SELECT * FROM natation_competitions WHERE id=?", (comp["id"],))



def _swim_next_slot(rows, competition_id, categorie, nb_lignes=5):
    """Première ligne libre, en ouvrant automatiquement une nouvelle série si besoin."""
    teams = rows(
        """SELECT serie,ligne FROM natation_equipes
           WHERE competition_id=? AND categorie=?
           ORDER BY serie,ligne,id""",
        (competition_id, categorie),
    )
    occupied = {
        (int(t["serie"] or 1), int(t["ligne"] or 0))
        for t in teams
        if t["ligne"]
    }
    serie = 1
    while True:
        for ligne in range(1, int(nb_lignes) + 1):
            if (serie, ligne) not in occupied:
                return serie, ligne
        serie += 1


def _swim_series_summary(rows, competition_id, categorie, nb_lignes=5):
    teams = rows(
        """SELECT serie,COUNT(*) n FROM natation_equipes
           WHERE competition_id=? AND categorie=?
           GROUP BY serie ORDER BY serie""",
        (competition_id, categorie),
    )
    return {
        int(t["serie"] or 1): int(t["n"] or 0)
        for t in teams
    }



def _swim_category_label(value):
    text = str(value or "").strip().lower()
    if text.startswith("mix") or text == "x":
        return "Mixte"
    if text.startswith("m"):
        return "Masculin"
    if text.startswith("f"):
        return "Féminin"
    return None


def _swim_reflow_category(rows, exe, competition_id, categorie, max_lines=5, unlock_all=False):
    teams = rows(
        """SELECT * FROM natation_equipes
           WHERE competition_id=? AND categorie=?
           ORDER BY id""",
        (competition_id, categorie),
    )
    payload = []
    for t in teams:
        locked = int(t.get("placement_verrouille") or 0)
        universite_norm = str(t.get("universite") or "").strip().lower()
        preferred_line = (
            3 if "uppa" in universite_norm
            else 2 if "toulouse" in universite_norm
            else 4 if "bordeaux" in universite_norm
            else None
        )
        payload.append(
            {
                "team": str(t["id"]),
                "level": t.get("niveau"),
                "preferred_line": preferred_line,
                "series": None if (unlock_all or not locked) else t.get("serie"),
                "line": None if (unlock_all or not locked) else t.get("ligne"),
            }
        )
    assigned = assign_series_lines(payload, max_lines=max_lines)
    by_id = {int(a["team"]): a for a in assigned}
    for t in teams:
        pos = by_id[int(t["id"])]
        exe(
            """UPDATE natation_equipes
               SET serie=?,ligne=?,placement_verrouille=?
               WHERE id=?""",
            (
                int(pos["series"]),
                int(pos["line"]),
                0 if unlock_all else int(t.get("placement_verrouille") or 0),
                int(t["id"]),
            ),
        )


def _swim_import_dataframe(uploaded):
    name = (uploaded.name or "").lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded, sep=None, engine="python")
    return pd.read_excel(uploaded)


def _swim_import_model_bytes():
    model = pd.DataFrame(
        [
            {
                "Université / AS": "UPPA",
                "Nom équipe": "UPPA Mixte 1",
                "Catégorie": "Mixte",
                "Niveau": 2,
                "Série": "",
                "Ligne": "",
                "Nom nageur": "Dupont",
                "Prénom nageur": "Léa",
                "C1": "Titulaire",
                "C2 Pap": "Titulaire",
                "C2 Dos": "",
                "C2 Brasse": "",
                "C2 Crawl": "",
                "C3": "Titulaire",
                "BONUS": "Engagé",
            },
            {
                "Université / AS": "Toulouse",
                "Nom équipe": "Toulouse Mixte 1",
                "Catégorie": "Mixte",
                "Niveau": 1,
                "Série": 2,
                "Ligne": 3,
                "Nom nageur": "",
                "Prénom nageur": "",
                "C1": "",
                "C2 Pap": "",
                "C2 Dos": "",
                "C2 Brasse": "",
                "C2 Crawl": "",
                "C3": "",
                "BONUS": "",
            },
        ]
    )
    csv_bytes = model.to_csv(index=False).encode("utf-8-sig")
    xlsx_buffer = _BytesIO()
    with pd.ExcelWriter(xlsx_buffer, engine="openpyxl") as writer:
        model.to_excel(writer, index=False, sheet_name="Équipes")
    return csv_bytes, xlsx_buffer.getvalue()


def _swim_prepare_import(df):
    aliases = {
        "université / as": "universite",
        "universite / as": "universite",
        "université": "universite",
        "universite": "universite",
        "as": "universite",
        "nom équipe": "nom",
        "nom equipe": "nom",
        "équipe": "nom",
        "equipe": "nom",
        "catégorie": "categorie",
        "categorie": "categorie",
        "niveau": "niveau",
        "série": "serie",
        "serie": "serie",
        "ligne": "ligne",
        "ligne d'eau": "ligne",
        "ligne d’eau": "ligne",
        "nom nageur": "nageur_nom",
        "nageur nom": "nageur_nom",
        "prénom nageur": "nageur_prenom",
        "prenom nageur": "nageur_prenom",
        "nageur prénom": "nageur_prenom",
        "nageur prenom": "nageur_prenom",
        "c1": "eng_c1",
        "c2 pap": "eng_c2_pap",
        "c2-pap": "eng_c2_pap",
        "c2 papillon": "eng_c2_pap",
        "c2 dos": "eng_c2_dos",
        "c2-dos": "eng_c2_dos",
        "c2 brasse": "eng_c2_br",
        "c2-br": "eng_c2_br",
        "c2 crawl": "eng_c2_nl",
        "c2-cr": "eng_c2_nl",
        "c2 nl": "eng_c2_nl",
        "c2-nl": "eng_c2_nl",
        "c3": "eng_c3",
        "bonus": "eng_bonus",
    }
    renamed = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in aliases:
            renamed[col] = aliases[key]
    work = df.rename(columns=renamed).copy()
    required = ["universite", "nom", "categorie", "niveau"]
    missing = [x for x in required if x not in work.columns]
    if missing:
        return None, "Colonnes obligatoires manquantes : " + ", ".join(missing)
    if "serie" not in work.columns:
        work["serie"] = None
    if "ligne" not in work.columns:
        work["ligne"] = None
    for col in ["nageur_nom", "nageur_prenom", "eng_c1", "eng_c2_pap", "eng_c2_dos", "eng_c2_br", "eng_c2_nl", "eng_c3", "eng_bonus"]:
        if col not in work.columns:
            work[col] = None

    prepared = []
    errors = []
    for idx, r in work.iterrows():
        universite = str(r.get("universite") or "").strip()
        nom = str(r.get("nom") or "").strip()
        categorie = _swim_category_label(r.get("categorie"))
        niveau = parse_level(r.get("niveau"))
        if not universite or not nom or not categorie:
            errors.append(f"Ligne {idx + 2}")
            continue
        if niveau not in (1.0, 2.0):
            errors.append(f"Ligne {idx + 2} : niveau obligatoire 1 ou 2")
            continue

        def _opt_int(v):
            try:
                if pd.isna(v) or str(v).strip() == "":
                    return None
                n = int(float(v))
                return n if n > 0 else None
            except Exception:
                return None

        serie = _opt_int(r.get("serie"))
        ligne = _opt_int(r.get("ligne"))
        if ligne is not None and not 1 <= ligne <= 5:
            errors.append(f"Ligne {idx + 2} : ligne d'eau hors 1-5")
            continue
        locked = int(serie is not None and ligne is not None)
        nageur_nom = "" if pd.isna(r.get("nageur_nom")) else str(r.get("nageur_nom") or "").strip()
        nageur_prenom = "" if pd.isna(r.get("nageur_prenom")) else str(r.get("nageur_prenom") or "").strip()
        swimmer = None
        engagements = []
        if nageur_nom or nageur_prenom:
            swimmer = {"nom": nageur_nom, "prenom": nageur_prenom}
            swimmer_key = f"{nageur_nom}|{nageur_prenom}".strip("|")
            for code, col, bonus in [
                ("C1", "eng_c1", False),
                ("C2-PAP", "eng_c2_pap", False),
                ("C2-DOS", "eng_c2_dos", False),
                ("C2-BR", "eng_c2_br", False),
                ("C2-NL", "eng_c2_nl", False),
                ("C3", "eng_c3", False),
                ("BONUS", "eng_bonus", True),
            ]:
                raw = r.get(col)
                status = normalize_swim_status(raw, bonus=bonus)
                raw_text = "" if pd.isna(raw) else str(raw or "").strip()
                if raw_text and not status:
                    errors.append(f"Ligne {idx + 2} : statut {code} non reconnu")
                if status:
                    engagements.append({"swimmer": swimmer_key, "code": code, "status": status})

        prepared.append(
            {
                "universite": universite,
                "nom": nom,
                "categorie": categorie,
                "niveau": niveau,
                "serie": serie if locked else None,
                "ligne": ligne if locked else None,
                "locked": locked,
                "swimmer": swimmer,
                "engagements": engagements,
            }
        )
    if not errors:
        grouped = {}
        for item in prepared:
            key = (item["universite"], item["nom"], item["categorie"])
            grouped.setdefault(key, []).extend(item.get("engagements") or [])
        for key, entries in grouped.items():
            for msg in validate_swimmer_entries(entries):
                errors.append(f"{key[1]} : {msg}")
    if errors:
        return None, "Import à corriger : " + " ; ".join(errors[:8])
    return prepared, None


def _swim_result(rows, one, exe, comp_id, team_id, event_id):
    result = one(
        """SELECT * FROM natation_resultats
           WHERE competition_id=? AND equipe_id=? AND epreuve_id=?""",
        (comp_id, team_id, event_id),
    )
    if result:
        return result
    exe(
        """INSERT INTO natation_resultats(
            competition_id,equipe_id,epreuve_id,statut
        ) VALUES(?,?,?,'Prévu')
        ON CONFLICT(competition_id,equipe_id,epreuve_id) DO NOTHING""",
        (comp_id, team_id, event_id),
    )
    return one(
        """SELECT * FROM natation_resultats
           WHERE competition_id=? AND equipe_id=? AND epreuve_id=?""",
        (comp_id, team_id, event_id),
    )


def _save_swim_split(rows, exe, result_id, cumulative, source):
    existing = rows(
        "SELECT * FROM natation_splits WHERE resultat_id=? ORDER BY numero",
        (result_id,),
    )
    numero = len(existing) + 1
    previous = float(existing[-1]["temps_cumule"]) if existing else 0.0
    split = max(0.0, float(cumulative) - previous)
    exe(
        """INSERT INTO natation_splits(
            resultat_id,numero,temps_cumule,temps_split,source
        ) VALUES(?,?,?,?,?)
        ON CONFLICT(resultat_id,numero)
        DO UPDATE SET temps_cumule=excluded.temps_cumule,
                      temps_split=excluded.temps_split,
                      source=excluded.source""",
        (result_id, numero, float(cumulative), split, source),
    )



def _swim_reference_code(event_code):
    if event_code == "C1":
        return "C1"
    if event_code in {"C2-PAP", "C2-DOS", "C2-BR", "C2-NL"}:
        return event_code
    if event_code == "C3":
        return "C3"
    return None


def _swim_points(rm_seconds, performance_seconds):
    if rm_seconds is None or performance_seconds is None:
        return None
    try:
        rm = float(rm_seconds)
        perf = float(performance_seconds)
    except Exception:
        return None
    if rm <= 0 or perf <= 0:
        return None
    return rm / perf * 100.0


def _swim_rankings(rows, comp_id, category):
    """Calcule classements C1, C2, C3 et général pour une catégorie."""
    teams = rows(
        """SELECT * FROM natation_equipes
           WHERE competition_id=? AND categorie=?
           ORDER BY serie,ligne,nom""",
        (comp_id, category),
    )
    refs = rows(
        """SELECT code_epreuve,temps_rm
           FROM natation_records_reference
           WHERE competition_id=? AND categorie=?""",
        (comp_id, category),
    )
    ref_map = {r["code_epreuve"]: r["temps_rm"] for r in refs}

    results = rows(
        """SELECT nr.*,ne.code,ne.bloc,ne.nom epreuve
           FROM natation_resultats nr
           JOIN natation_epreuves ne ON ne.id=nr.epreuve_id
           WHERE nr.competition_id=? AND nr.temps_final IS NOT NULL""",
        (comp_id,),
    )
    by_team = {}
    for team in teams:
        by_team[int(team["id"])] = {
            "Équipe": team["nom"],
            "Université / AS": team["universite"],
            "Catégorie": category,
            "Série": int(team["serie"] or 1),
            "Ligne": int(team["ligne"] or 0),
            "C1": None,
            "C2-PAP": None,
            "C2-DOS": None,
            "C2-BR": None,
            "C2-NL": None,
            "C2": None,
            "C3": None,
            "Général": None,
        }

    for r in results:
        tid = int(r["equipe_id"])
        if tid not in by_team:
            continue
        code = r["code"]
        ref_code = _swim_reference_code(code)
        if not ref_code or ref_code not in ref_map:
            continue
        pts = _swim_points(ref_map[ref_code], r["temps_final"])
        if pts is not None:
            by_team[tid][code] = pts

    out = list(by_team.values())
    for item in out:
        c2_parts = [
            item.get("C2-PAP"),
            item.get("C2-DOS"),
            item.get("C2-BR"),
            item.get("C2-NL"),
        ]
        if all(v is not None for v in c2_parts):
            item["C2"] = sum(c2_parts) / 4.0
        if item.get("C1") is not None and item.get("C2") is not None and item.get("C3") is not None:
            item["Général"] = (
                item["C1"] * 4.0
                + item["C2"] * 4.0
                + item["C3"] * 6.0
            ) / 14.0
    return out


def _swim_sorted_table(rankings, format_name):
    metric_map = {
        "C1": "C1",
        "C2": "C2",
        "C3": "C3",
        "Général": "Général",
    }
    metric = metric_map[format_name]
    filtered = [r.copy() for r in rankings if r.get(metric) is not None]
    filtered.sort(key=lambda r: float(r[metric]), reverse=True)
    table = []
    for idx, r in enumerate(filtered, start=1):
        row = {
            "Rang": idx,
            "Équipe": r["Équipe"],
            "Université / AS": r["Université / AS"],
            "Catégorie": r["Catégorie"],
            "Série": r["Série"],
            "Ligne": r["Ligne"],
        }
        if format_name == "C1":
            row["Points C1"] = round(r["C1"], 3)
        elif format_name == "C2":
            row["Pap"] = round(r["C2-PAP"], 3)
            row["Dos"] = round(r["C2-DOS"], 3)
            row["Brasse"] = round(r["C2-BR"], 3)
            row["NL"] = round(r["C2-NL"], 3)
            row["Points C2"] = round(r["C2"], 3)
        elif format_name == "C3":
            row["Points C3"] = round(r["C3"], 3)
        else:
            row["C1"] = round(r["C1"], 3)
            row["C2"] = round(r["C2"], 3)
            row["C3"] = round(r["C3"], 3)
            row["Points général"] = round(r["Général"], 3)
        table.append(row)
    return table


def _swim_export_excel(all_tables):
    output = _BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, data in all_tables.items():
            frame = pd.DataFrame(data)
            frame.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            ws = writer.book[sheet_name[:31]]
            ws.freeze_panes = "A2"
            for cell in ws[1]:
                cell.font = cell.font.copy(bold=True)
            for column_cells in ws.columns:
                width = min(
                    32,
                    max(
                        10,
                        max(len(str(cell.value or "")) for cell in column_cells) + 2,
                    ),
                )
                ws.column_dimensions[column_cells[0].column_letter].width = width
    return output.getvalue()


def _render_swim_timer_display(st, start_epoch, running):
    if not running or not start_epoch:
        return
    elapsed = max(0.0, _time.time() - float(start_epoch))
    # Affichage serveur simple ; les actions enregistrent toujours le temps exact au clic.
    st.markdown(
        f"<div style='font-size:2.2rem;font-weight:800;text-align:center;padding:.35rem 0'>"
        f"⏱️ {_swim_fmt(elapsed)}</div>",
        unsafe_allow_html=True,
    )


def render_natation_competition(st, rows, one, exe, date, role="Enseignant"):
    comp = _ensure_swim_default_competition(rows, one, exe, date)
    st.markdown("### 🏊 Natation • Compétition par équipes")
    st.caption(
        "5 lignes d'eau • Masculin / Féminin / Mixte • chronomètre + temps intermédiaires + saisie manuelle"
    )

    swim_tabs = allowed_swim_tabs(role)
    if not swim_tabs:
        st.error("Accès compétition non autorisé.")
        return
    tab = st.radio(
        "Natation",
        swim_tabs,
        horizontal=True,
        key="swim_tab",
    )

    if tab == "👥 Équipes":
        st.caption(
            "5 équipes maximum par série. La dernière série est la plus forte. "
            "Ordre des lignes dans chaque série : 3 → 2 → 4 → 1 → 5."
        )

        st.markdown("#### 📥 Importer les équipes")
        model_csv, model_xlsx = _swim_import_model_bytes()
        mc1, mc2 = st.columns(2)
        mc1.download_button(
            "⬇️ Modèle CSV",
            data=model_csv,
            file_name="modele_equipes_natation.csv",
            mime="text/csv",
            use_container_width=True,
        )
        mc2.download_button(
            "⬇️ Modèle Excel",
            data=model_xlsx,
            file_name="modele_equipes_natation.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        upload = st.file_uploader(
            "Importer un fichier Excel ou CSV",
            type=["xlsx", "csv"],
            key="swim_team_import",
        )
        if upload is not None:
            try:
                imported_df = _swim_import_dataframe(upload)
                prepared, import_error = _swim_prepare_import(imported_df)
            except Exception as exc:
                prepared, import_error = None, f"Lecture impossible : {exc}"
            if import_error:
                st.error(import_error)
            elif prepared is not None:
                st.success(f"{len({(x['nom'], x['categorie']) for x in prepared})} équipe(s) prête(s) à importer.")
                st.caption(
                    "Les nageurs et leurs engagements sont facultatifs. Si Série et Ligne sont vides, l'APK répartit par niveau : "
                    "dernière série = plus forte, avec lignes 3-2-4-1-5."
                )
                if st.button(
                    "Importer et répartir par niveau",
                    type="primary",
                    use_container_width=True,
                    key="swim_import_confirm",
                ):
                    touched_categories = set()
                    for item in prepared:
                        exe(
                            """INSERT INTO natation_equipes(
                                competition_id,nom,universite,categorie,niveau,
                                serie,ligne,placement_verrouille
                            ) VALUES(?,?,?,?,?,?,?,?)
                            ON CONFLICT(competition_id,nom,categorie)
                            DO UPDATE SET universite=excluded.universite,
                                          niveau=excluded.niveau,
                                          serie=excluded.serie,
                                          ligne=excluded.ligne,
                                          placement_verrouille=excluded.placement_verrouille""",
                            (
                                comp["id"],
                                item["nom"],
                                item["universite"],
                                item["categorie"],
                                str(item["niveau"]),
                                item["serie"],
                                item["ligne"],
                                item["locked"],
                            ),
                        )
                        team_row = one(
                            """SELECT id FROM natation_equipes
                               WHERE competition_id=? AND nom=? AND categorie=?""",
                            (comp["id"], item["nom"], item["categorie"]),
                        )
                        if team_row and item.get("swimmer"):
                            sw = item["swimmer"]
                            exe(
                                """INSERT INTO natation_nageurs(equipe_id,nom,prenom)
                                   VALUES(?,?,?)
                                   ON CONFLICT(equipe_id,nom,prenom) DO NOTHING""",
                                (team_row["id"], sw["nom"], sw["prenom"]),
                            )
                            swimmer_row = one(
                                """SELECT id FROM natation_nageurs
                                   WHERE equipe_id=? AND nom=? AND prenom=?""",
                                (team_row["id"], sw["nom"], sw["prenom"]),
                            )
                            if swimmer_row:
                                for eng in item.get("engagements") or []:
                                    exe(
                                        """INSERT INTO natation_engagements(nageur_id,code_epreuve,statut)
                                           VALUES(?,?,?)
                                           ON CONFLICT(nageur_id,code_epreuve)
                                           DO UPDATE SET statut=excluded.statut""",
                                        (swimmer_row["id"], eng["code"], eng["status"]),
                                    )
                        touched_categories.add(item["categorie"])
                    for cat in touched_categories:
                        _swim_reflow_category(
                            rows,
                            exe,
                            comp["id"],
                            cat,
                            int(comp["nb_lignes"] or 5),
                            unlock_all=False,
                        )
                    st.success("Import terminé et séries recalculées par niveau.")
                    st.rerun()

        if st.button(
            "🔄 Refaire toutes les séries automatiquement par niveau",
            use_container_width=True,
            key="swim_reflow_all",
        ):
            for cat in ["Masculin", "Féminin", "Mixte"]:
                _swim_reflow_category(
                    rows,
                    exe,
                    comp["id"],
                    cat,
                    int(comp["nb_lignes"] or 5),
                    unlock_all=True,
                )
            st.success("Séries recalculées : niveau 2 dans les séries les plus fortes, avec priorités de lignes UPPA 3 / Toulouse 2 / Bordeaux 4.")
            st.rerun()

        st.divider()
        st.markdown("#### ➕ Ajouter une équipe manuellement")
        with st.form("swim_team_create"):
            c1, c2 = st.columns(2)
            university_choice = c1.selectbox(
                "Université / AS",
                ["UPPA", "Toulouse", "Bordeaux", "Autre / saisie libre"],
            )
            categorie = c2.selectbox("Catégorie", ["Masculin", "Féminin", "Mixte"])
            university_free = st.text_input(
                "Nom de l'université / AS (si autre)",
                placeholder="Ex. Limoges, La Rochelle, ENSMA…",
            )
            c3, c4 = st.columns(2)
            nom = c3.text_input("Nom de l'équipe", placeholder="Ex. Limoges Mixte 1")
            niveau = c4.selectbox(
                "Niveau",
                [1, 2],
                index=0,
                help="Niveau 2 = plus fort que niveau 1.",
            )
            assignment = st.radio(
                "Placement",
                ["Automatique par niveau", "Manuel"],
                horizontal=True,
            )
            c5, c6 = st.columns(2)
            serie_manual = c5.number_input(
                "Série",
                min_value=1,
                value=1,
                step=1,
                disabled=assignment == "Automatique par niveau",
            )
            ligne_manual = c6.number_input(
                "Ligne d'eau",
                min_value=1,
                max_value=5,
                value=3,
                step=1,
                disabled=assignment == "Automatique par niveau",
            )
            add = st.form_submit_button(
                "Créer l'équipe",
                type="primary",
                use_container_width=True,
            )

        if add and nom.strip():
            universite = (
                university_free.strip()
                if university_choice == "Autre / saisie libre"
                else university_choice
            )
            if not universite:
                st.error("Renseigne le nom de l'université / AS.")
            elif assignment == "Manuel":
                serie, ligne = int(serie_manual), int(ligne_manual)
                occupied = rows(
                    """SELECT id,nom FROM natation_equipes
                       WHERE competition_id=? AND categorie=?
                         AND serie=? AND ligne=?""",
                    (comp["id"], categorie, serie, ligne),
                )
                if occupied:
                    st.error(
                        f"Série {serie}, ligne {ligne} est déjà occupée par "
                        f"{occupied[0]['nom']}."
                    )
                else:
                    exe(
                        """INSERT INTO natation_equipes(
                            competition_id,nom,universite,categorie,niveau,
                            serie,ligne,placement_verrouille
                        ) VALUES(?,?,?,?,?,?,?,1)
                        ON CONFLICT(competition_id,nom,categorie)
                        DO UPDATE SET universite=excluded.universite,
                                      niveau=excluded.niveau,
                                      serie=excluded.serie,
                                      ligne=excluded.ligne,
                                      placement_verrouille=1""",
                        (
                            comp["id"], nom.strip(), universite, categorie,
                            str(float(niveau)), serie, ligne
                        ),
                    )
                    st.success(f"Équipe enregistrée • Série {serie} • Ligne {ligne}.")
                    st.rerun()
            else:
                exe(
                    """INSERT INTO natation_equipes(
                        competition_id,nom,universite,categorie,niveau,
                        serie,ligne,placement_verrouille
                    ) VALUES(?,?,?,?,?,NULL,NULL,0)
                    ON CONFLICT(competition_id,nom,categorie)
                    DO UPDATE SET universite=excluded.universite,
                                  niveau=excluded.niveau,
                                  serie=NULL,
                                  ligne=NULL,
                                  placement_verrouille=0""",
                    (
                        comp["id"], nom.strip(), universite, categorie,
                        str(float(niveau))
                    ),
                )
                _swim_reflow_category(
                    rows,
                    exe,
                    comp["id"],
                    categorie,
                    int(comp["nb_lignes"] or 5),
                    unlock_all=False,
                )
                st.success("Équipe enregistrée et séries recalculées.")
                st.rerun()

        for cat in ["Masculin", "Féminin", "Mixte"]:
            summary = _swim_series_summary(
                rows, comp["id"], cat, int(comp["nb_lignes"] or 5)
            )
            if summary:
                summary_text = " • ".join(
                    f"Série {serie}: {count}/5"
                    for serie, count in summary.items()
                )
                st.caption(f"**{cat}** — {summary_text}")

        teams = rows(
            """SELECT * FROM natation_equipes
               WHERE competition_id=?
               ORDER BY categorie,serie,ligne,universite,nom""",
            (comp["id"],),
        )
        if teams:
            st.dataframe(
                [
                    {
                        "Catégorie": t["categorie"],
                        "Série": int(t["serie"] or 1),
                        "Ligne": t["ligne"],
                        "Niveau": t.get("niveau") or "",
                        "Université / AS": t["universite"],
                        "Équipe": t["nom"],
                        "Placement": "Manuel" if int(t.get("placement_verrouille") or 0) else "Auto",
                    }
                    for t in teams
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Crée ou importe les équipes avant le chronométrage.")

        if teams:
            st.divider()
            st.markdown("#### 🏊‍♀️ Nageurs de l'équipe")
            managed_team = st.selectbox(
                "Équipe à gérer",
                teams,
                format_func=lambda t: f"{t['universite']} • {t['nom']} • {t['categorie']}",
                key="swim_roster_team",
            )
            swimmers = rows(
                """SELECT * FROM natation_nageurs
                   WHERE equipe_id=? ORDER BY nom,prenom,id""",
                (managed_team["id"],),
            )
            roster_rows = []
            for sw in swimmers:
                engs = rows(
                    """SELECT code_epreuve,statut FROM natation_engagements
                       WHERE nageur_id=? ORDER BY code_epreuve""",
                    (sw["id"],),
                )
                eng_map = {e["code_epreuve"]: e["statut"] for e in engs}
                roster_rows.append(
                    {
                        "Nom": sw["nom"],
                        "Prénom": sw["prenom"] or "",
                        "C1": eng_map.get("C1", ""),
                        "C2 Pap": eng_map.get("C2-PAP", ""),
                        "C2 Dos": eng_map.get("C2-DOS", ""),
                        "C2 Brasse": eng_map.get("C2-BR", ""),
                        "C2 Crawl": eng_map.get("C2-NL", ""),
                        "C3": eng_map.get("C3", ""),
                        "BONUS": eng_map.get("BONUS", ""),
                    }
                )
            if roster_rows:
                st.dataframe(roster_rows, use_container_width=True, hide_index=True)
            else:
                st.caption("Aucun nageur renseigné pour cette équipe. L'équipe reste engagée.")

            with st.form(f"swim_add_swimmer_{managed_team['id']}"):
                a1, a2 = st.columns(2)
                swimmer_nom = a1.text_input("Nom du nageur")
                swimmer_prenom = a2.text_input("Prénom du nageur")
                status_options = ["Non engagé", "Titulaire", "Remplaçant"]
                s1, s2, s3 = st.columns(3)
                c1_status = s1.selectbox("C1", status_options)
                c3_status = s2.selectbox("C3", status_options)
                bonus_status = s3.checkbox("BONUS 12 × 50 m NL")
                st.caption("C2 : 2 nageurs maximum par nage")
                c21, c22 = st.columns(2)
                c2_pap_status = c21.selectbox("C2 Papillon", status_options)
                c2_dos_status = c22.selectbox("C2 Dos", status_options)
                c23, c24 = st.columns(2)
                c2_br_status = c23.selectbox("C2 Brasse", status_options)
                c2_nl_status = c24.selectbox("C2 Crawl", status_options)
                save_swimmer = st.form_submit_button(
                    "➕ Ajouter / mettre à jour le nageur",
                    type="primary",
                    use_container_width=True,
                )

            if save_swimmer:
                if not swimmer_nom.strip() and not swimmer_prenom.strip():
                    st.error("Renseigne au moins le nom ou le prénom du nageur.")
                else:
                    current_entries = []
                    current = rows(
                        """SELECT n.id,n.nom,n.prenom,e.code_epreuve,e.statut
                           FROM natation_nageurs n
                           LEFT JOIN natation_engagements e ON e.nageur_id=n.id
                           WHERE n.equipe_id=?""",
                        (managed_team["id"],),
                    )
                    target_key = f"{swimmer_nom.strip()}|{swimmer_prenom.strip()}".strip("|")
                    for e in current:
                        if not e.get("code_epreuve"):
                            continue
                        existing_key = f"{e['nom']}|{e.get('prenom') or ''}".strip("|")
                        if existing_key == target_key:
                            continue
                        current_entries.append(
                            {"swimmer": existing_key, "code": e["code_epreuve"], "status": e["statut"]}
                        )
                    chosen = []
                    for code, status in [
                        ("C1", c1_status),
                        ("C2-PAP", c2_pap_status),
                        ("C2-DOS", c2_dos_status),
                        ("C2-BR", c2_br_status),
                        ("C2-NL", c2_nl_status),
                        ("C3", c3_status),
                    ]:
                        if status != "Non engagé":
                            chosen.append({"swimmer": target_key, "code": code, "status": status})
                    if bonus_status:
                        chosen.append({"swimmer": target_key, "code": "BONUS", "status": "Engagé"})
                    limit_errors = validate_swimmer_entries(current_entries + chosen)
                    if limit_errors:
                        st.error(" • ".join(limit_errors))
                    else:
                        exe(
                            """INSERT INTO natation_nageurs(equipe_id,nom,prenom)
                               VALUES(?,?,?)
                               ON CONFLICT(equipe_id,nom,prenom) DO NOTHING""",
                            (managed_team["id"], swimmer_nom.strip(), swimmer_prenom.strip()),
                        )
                        saved = one(
                            """SELECT id FROM natation_nageurs
                               WHERE equipe_id=? AND nom=? AND prenom=?""",
                            (managed_team["id"], swimmer_nom.strip(), swimmer_prenom.strip()),
                        )
                        if saved:
                            exe("DELETE FROM natation_engagements WHERE nageur_id=?", (saved["id"],))
                            for eng in chosen:
                                exe(
                                    """INSERT INTO natation_engagements(nageur_id,code_epreuve,statut)
                                       VALUES(?,?,?)""",
                                    (saved["id"], eng["code"], eng["status"]),
                                )
                        st.success("Nageur enregistré.")
                        st.rerun()

            if swimmers:
                st.markdown("##### 🗑️ Supprimer un nageur")
                swimmer_to_delete = st.selectbox(
                    "Nageur",
                    swimmers,
                    format_func=lambda s: f"{s['nom']} {s['prenom'] or ''}".strip(),
                    key=f"swim_delete_swimmer_{managed_team['id']}",
                )
                if st.button(
                    "Supprimer ce nageur",
                    key=f"swim_delete_swimmer_btn_{managed_team['id']}",
                    use_container_width=True,
                ):
                    exe("DELETE FROM natation_engagements WHERE nageur_id=?", (swimmer_to_delete["id"],))
                    exe("DELETE FROM natation_nageurs WHERE id=?", (swimmer_to_delete["id"],))
                    st.success("Nageur supprimé. L'équipe reste engagée.")
                    st.rerun()
        return

    events = rows(
        """SELECT * FROM natation_epreuves
           WHERE competition_id=? ORDER BY ordre,id""",
        (comp["id"],),
    )
    teams = rows(
        """SELECT * FROM natation_equipes
           WHERE competition_id=? ORDER BY categorie,serie,ligne,nom""",
        (comp["id"],),
    )

    if tab == "🏅 Classements":
        st.markdown("#### 🏅 Classements par points")
        st.caption(
            "Formule : points = RM / performance × 100. "
            "C2 = moyenne des 4 relais 100 m. Général = (C1×4 + C2×4 + C3×6) / 14."
        )

        category = st.selectbox(
            "Catégorie du classement",
            ["Masculin", "Féminin", "Mixte"],
            key="swim_rank_category",
        )
        st.markdown("##### Références record du monde")
        st.caption(
            "Renseigne les références officielles en secondes. "
            "Elles restent modifiables si la FFSU publie une actualisation."
        )
        ref_labels = [
            ("C1", "400 4N"),
            ("C2-PAP", "100 Pap"),
            ("C2-DOS", "100 Dos"),
            ("C2-BR", "100 Brasse"),
            ("C2-NL", "100 NL"),
            ("C3", "800 NL"),
        ]
        existing_refs = rows(
            """SELECT code_epreuve,temps_rm
               FROM natation_records_reference
               WHERE competition_id=? AND categorie=?""",
            (comp["id"], category),
        )
        ref_map = {r["code_epreuve"]: r["temps_rm"] for r in existing_refs}
        with st.form(f"swim_refs_{category}"):
            ref_values = {}
            cols = st.columns(3)
            for i, (code, label) in enumerate(ref_labels):
                current = ref_map.get(code)
                ref_values[code] = cols[i % 3].text_input(
                    label,
                    value=_swim_fmt(current).replace(" s", "") if current else "",
                    key=f"rm_{category}_{code}",
                )
            save_refs = st.form_submit_button(
                "Enregistrer les références",
                use_container_width=True,
            )
        if save_refs:
            invalid = []
            parsed = {}
            for code, value in ref_values.items():
                sec = _swim_seconds(value)
                if sec is None or sec <= 0:
                    invalid.append(code)
                else:
                    parsed[code] = sec
            if invalid:
                st.error("Références invalides : " + ", ".join(invalid))
            else:
                for code, sec in parsed.items():
                    exe(
                        """INSERT INTO natation_records_reference(
                            competition_id,categorie,code_epreuve,temps_rm
                        ) VALUES(?,?,?,?)
                        ON CONFLICT(competition_id,categorie,code_epreuve)
                        DO UPDATE SET temps_rm=excluded.temps_rm""",
                        (comp["id"], category, code, float(sec)),
                    )
                st.success("Références enregistrées.")
                st.rerun()

        rankings = _swim_rankings(rows, comp["id"], category)
        format_name = st.radio(
            "Format",
            ["C1", "C2", "C3", "Général"],
            horizontal=True,
            key="swim_rank_format",
        )
        table = _swim_sorted_table(rankings, format_name)
        if table:
            st.dataframe(table, use_container_width=True, hide_index=True)
            csv_data = pd.DataFrame(table).to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Export CSV du classement affiché",
                data=csv_data,
                file_name=f"classement_natation_{category}_{format_name}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info(
                "Classement incomplet : renseigne les records de référence et les temps des épreuves."
            )

        st.markdown("##### Export Excel complet")
        all_tables = {}
        for cat in ["Masculin", "Féminin", "Mixte"]:
            cat_rankings = _swim_rankings(rows, comp["id"], cat)
            for fmt in ["C1", "C2", "C3", "Général"]:
                all_tables[f"{cat[:3]}-{fmt}"] = _swim_sorted_table(cat_rankings, fmt)
        xlsx = _swim_export_excel(all_tables)
        st.download_button(
            "⬇️ Export Excel complet",
            data=xlsx,
            file_name="classements_natation_SUAPS.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        return

    if tab == "📊 Résultats":
        data = []
        for r in rows(
            """SELECT nr.*,ne.code,ne.nom epreuve,ne.bloc,ne.coefficient,
                      e.nom equipe,e.universite,e.categorie,e.ligne,e.serie
               FROM natation_resultats nr
               JOIN natation_epreuves ne ON ne.id=nr.epreuve_id
               JOIN natation_equipes e ON e.id=nr.equipe_id
               WHERE nr.competition_id=?
               ORDER BY e.categorie,ne.ordre,e.serie,e.ligne,e.nom""",
            (comp["id"],),
        ):
            splits = rows(
                "SELECT * FROM natation_splits WHERE resultat_id=? ORDER BY numero",
                (r["id"],),
            )
            data.append(
                {
                    "Catégorie": r["categorie"],
                    "Épreuve": r["epreuve"],
                    "Série": int(r["serie"] or 1),
                    "Ligne": r["ligne"],
                    "Équipe": r["equipe"],
                    "Temps final": _swim_fmt(r["temps_final"]),
                    "Intermédiaires": " | ".join(_swim_fmt(s["temps_split"]) for s in splits),
                    "Mode": r["mode_saisie"] or "",
                }
            )
        if data:
            st.dataframe(data, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun temps enregistré.")
        return

    if not teams:
        st.warning("Crée d'abord les équipes dans l'onglet « Équipes ».")
        return

    c1, c2 = st.columns(2)
    event = c1.selectbox(
        "Épreuve",
        events,
        format_func=lambda r: f"{r['code']} • {r['nom']}",
        key="swim_event",
    )
    category = c2.selectbox(
        "Catégorie",
        ["Masculin", "Féminin", "Mixte"],
        key="swim_category",
    )
    eligible = [t for t in teams if t["categorie"] == category]
    if not eligible:
        st.info(f"Aucune équipe {category}.")
        return
    team = st.selectbox(
        "Équipe / ligne",
        eligible,
        format_func=lambda r: f"Série {int(r['serie'] or 1)} • Ligne {r['ligne']} • {r['universite']} • {r['nom']}",
        key="swim_team",
    )
    result = _swim_result(rows, one, exe, comp["id"], team["id"], event["id"])
    result_id = int(result["id"])
    key_base = f"swim_timer_{result_id}"
    start_key = key_base + "_start"
    running_key = key_base + "_running"

    relay_count = int(event["nb_splits"] or 0)
    current_splits = rows(
        "SELECT * FROM natation_splits WHERE resultat_id=? ORDER BY numero",
        (result_id,),
    )
    next_relay = len(current_splits) + 1
    st.markdown(
        f"#### Série {int(team['serie'] or 1)} • Ligne {team['ligne']} • {team['nom']}  \n"
        f"**{event['nom']}** • {relay_count} relayeur(s)"
    )

    _render_swim_timer_display(
        st,
        st.session_state.get(start_key),
        st.session_state.get(running_key, False),
    )

    b1, b2 = st.columns([1, 2])
    if b1.button("▶️ DÉMARRER", type="primary", use_container_width=True, key=key_base+"_go"):
        st.session_state[start_key] = _time.time()
        st.session_state[running_key] = True
        exe("DELETE FROM natation_splits WHERE resultat_id=?", (result_id,))
        exe(
            "UPDATE natation_resultats SET temps_final=NULL,mode_saisie='Chrono',statut='En cours' WHERE id=?",
            (result_id,),
        )
        st.rerun()

    relay_label = (
        f"🏁 RELAYEUR {next_relay} — TEMPS FINAL"
        if relay_count and next_relay == relay_count
        else f"⏱️ RELAYEUR {next_relay}"
    )
    relay_disabled = not st.session_state.get(running_key, False) or next_relay > relay_count
    if b2.button(
        relay_label,
        use_container_width=True,
        type="primary" if relay_count and next_relay == relay_count else "secondary",
        key=key_base+"_relay",
        disabled=relay_disabled,
    ):
        start = st.session_state.get(start_key)
        if not start:
            st.warning("Démarre le chrono avant d'enregistrer un relayeur.")
        else:
            elapsed = _time.time() - float(start)
            _save_swim_split(rows, exe, result_id, elapsed, "Chrono")
            if next_relay == relay_count:
                exe(
                    """UPDATE natation_resultats
                       SET temps_final=?,mode_saisie='Chrono',statut='Terminé'
                       WHERE id=?""",
                    (float(elapsed), result_id),
                )
                st.session_state[running_key] = False
            st.rerun()

    splits = rows(
        "SELECT * FROM natation_splits WHERE resultat_id=? ORDER BY numero",
        (result_id,),
    )
    if splits:
        st.markdown("**Temps des relayeurs enregistrés**")
        st.dataframe(
            [
                {
                    "Relayeur": f"Relayeur {s['numero']}",
                    "Temps du relayeur": _swim_fmt(s["temps_split"]),
                    "Cumul": _swim_fmt(s["temps_cumule"]),
                    "Source": s["source"],
                }
                for s in splits
            ],
            use_container_width=True,
            hide_index=True,
        )

    saved = one("SELECT * FROM natation_resultats WHERE id=?", (result_id,))
    if saved and saved["temps_final"] is not None:
        st.success(f"Temps final : {_swim_fmt(saved['temps_final'])}")

    st.divider()
    st.markdown("#### ✍️ Saisie manuelle")
    st.caption("Formats acceptés : 62.35 • 1:02.35 • 1'02.35")
    with st.form(f"swim_manual_{result_id}"):
        manual = st.text_input("Temps")
        m1, m2 = st.columns(2)
        add_split = m1.form_submit_button("Ajouter comme intermédiaire", use_container_width=True)
        save_final = m2.form_submit_button("Enregistrer comme temps final", type="primary", use_container_width=True)
    if add_split or save_final:
        seconds = _swim_seconds(manual)
        if seconds is None or seconds <= 0:
            st.error("Temps invalide.")
        elif add_split:
            current_splits = rows(
                "SELECT * FROM natation_splits WHERE resultat_id=? ORDER BY numero",
                (result_id,),
            )
            if len(current_splits) >= int(event["nb_splits"] or 0):
                st.error("Le nombre d'intermédiaires prévu est déjà atteint.")
            else:
                _save_swim_split(rows, exe, result_id, seconds, "Manuel")
                st.success("Temps intermédiaire ajouté.")
                st.rerun()
        else:
            exe(
                """UPDATE natation_resultats
                   SET temps_final=?,mode_saisie='Manuel',statut='Terminé'
                   WHERE id=?""",
                (float(seconds), result_id),
            )
            st.success("Temps final enregistré.")
            st.rerun()

    if st.button("🗑️ Réinitialiser ce chrono", use_container_width=True, key=key_base+"_reset"):
        exe("DELETE FROM natation_splits WHERE resultat_id=?", (result_id,))
        exe(
            """UPDATE natation_resultats
               SET temps_final=NULL,mode_saisie=NULL,statut='Prévu'
               WHERE id=?""",
            (result_id,),
        )
        st.session_state.pop(start_key, None)
        st.session_state.pop(running_key, None)
        st.rerun()


def _round_robin(team_ids):
    ids = list(team_ids)
    if len(ids) % 2:
        ids.append(None)
    games = []
    for rnd in range(len(ids) - 1):
        for i in range(len(ids) // 2):
            a, b = ids[i], ids[-1 - i]
            if a is not None and b is not None:
                games.append((a, b, f"Journée {rnd + 1}"))
        ids = [ids[0]] + [ids[-1]] + ids[1:-1]
    return games


def render_sports_co(st, rows, one, exe, date, role="Enseignant"):
    st.markdown("### 🏆 Équipes • Matchs • Tournois")
    st.caption("Natation • Rugby • Basket-ball • Handball • Volley-ball • Football • Futsal • Badminton • Pelote Basque")
    if role in {"Chronométreur étudiant", "Gestion compétition"}:
        sport = "Natation"
        st.info("🏊 Accès limité à la compétition natation.")
    else:
        sport = st.selectbox("Sport / activité", SPORTS_CO, key="sc_sport")
    if sport == "Natation":
        render_natation_competition(st, rows, one, exe, date, role=role)
        return
    individuel = sport in ("Badminton", "Pelote Basque")
    participant_label = "joueur / paire" if individuel else "équipe"
    if sport == "Badminton":
        st.info("🏸 Badminton : matchs et tournois en simple ou en double. Un participant peut être un joueur ou une paire.")
    elif sport == "Pelote Basque":
        st.info("🥎 Pelote Basque : matchs et tournois en individuel ou par paire selon la spécialité.")
    tab = st.radio("Gestion", ["Équipes", "Composer", "Matchs", "Tournois", "Classement", "Feuille de match"], horizontal=True, key="sc_tab")

    if tab == "Équipes":
        with st.form("sc_team"):
            nom = st.text_input("Nom de l'équipe / joueur / paire")
            couleur = st.text_input("Couleur / chasuble")
            photo = st.file_uploader("Photo de l'équipe ou du joueur", type=["jpg", "jpeg", "png"], key="sc_team_photo")
            add = st.form_submit_button("Créer", type="primary")
        if add and nom.strip():
            exe("INSERT INTO equipes(nom,activite,couleur,date_creation,photo) VALUES(?,?,?,?,?)", (nom.strip(), sport, couleur.strip(), str(date.today()), photo.getvalue() if photo else None))
            st.success("Création enregistrée.")
            st.rerun()
        for t in rows("SELECT * FROM equipes WHERE activite=? ORDER BY nom", (sport,)):
            c1, c2 = st.columns([1, 3])
            if t.get("photo"):
                c1.image(t["photo"], width=100)
            nb = one("SELECT COUNT(*) n FROM equipe_joueurs WHERE equipe_id=?", (t["id"],))
            c2.markdown(f"**{t['nom']}** — {t['couleur'] or 'sans couleur'} • {nb['n'] if nb else 0} joueur(s)")

    elif tab == "Composer":
        teams = rows("SELECT * FROM equipes WHERE activite=? ORDER BY nom", (sport,))
        if not teams:
            st.info("Crée d'abord une équipe, un joueur ou une paire.")
            return
        team = st.selectbox("Équipe / joueur / paire", teams, format_func=lambda r: r["nom"], key="sc_team_pick")
        students = rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' AND actif=1 ORDER BY nom,prenom")
        current = rows("SELECT ej.*,u.nom,u.prenom FROM equipe_joueurs ej JOIN utilisateurs u ON u.id=ej.utilisateur_id WHERE ej.equipe_id=? ORDER BY ej.titulaire DESC,u.nom", (team["id"],))
        ids = {p["utilisateur_id"] for p in current}
        choices = [s for s in students if s["id"] not in ids]
        if choices:
            p = st.selectbox("Joueur", choices, format_func=lambda r: f"{r['nom']} {r['prenom']}")
            c1, c2 = st.columns(2)
            num = c1.text_input("Numéro")
            poste = c2.text_input("Poste / rôle")
            tit = st.checkbox("Titulaire", True)
            photo = st.file_uploader("Photo du joueur", type=["jpg", "jpeg", "png"], key="sc_player_photo")
            if st.button("Ajouter", type="primary"):
                exe("INSERT OR IGNORE INTO equipe_joueurs(equipe_id,utilisateur_id,numero,poste,titulaire,photo) VALUES(?,?,?,?,?,?)", (team["id"], p["id"], num, poste, int(tit), photo.getvalue() if photo else None))
                st.rerun()
        for p in current:
            c0, c1, c2 = st.columns([1, 4, 1])
            if p.get("photo"):
                c0.image(p["photo"], width=60)
            c1.write(f"{'⭐' if p['titulaire'] else '↪'} {p['numero'] or '-'} • {p['nom']} {p['prenom']} • {p['poste'] or '-'}")
            if c2.button("Retirer", key=f"rm{p['id']}"):
                exe("DELETE FROM equipe_joueurs WHERE id=?", (p["id"],))
                st.rerun()

    elif tab == "Tournois":
        if individuel:
            st.markdown(f"#### ➕ Ajouter rapidement un {participant_label}")
            with st.form(f"sc_quick_tournament_participant_{sport}"):
                qnom = st.text_input("Nom du joueur ou de la paire", key=f"sc_qt_name_{sport}")
                qadd = st.form_submit_button("Ajouter le participant")
            if qadd and qnom.strip():
                exe("INSERT INTO equipes(nom,activite,date_creation) VALUES(?,?,?)", (qnom.strip(), sport, str(date.today())))
                st.success(f"{qnom.strip()} ajouté à {sport}.")
                st.rerun()

        with st.form("sc_tournament"):
            nom = st.text_input("Nom du tournoi")
            formule = st.selectbox("Formule", ["Championnat / toutes rondes", "Poules", "Élimination directe"])
            d = st.date_input("Date", date.today())
            lieu = st.text_input("Lieu")
            create = st.form_submit_button("Créer le tournoi", type="primary")
        if create and nom.strip():
            exe("INSERT INTO tournois(nom,activite,formule,date_tournoi,lieu) VALUES(?,?,?,?,?)", (nom.strip(), sport, formule, str(d), lieu))
            st.success(f"Tournoi {sport} créé.")
            st.rerun()
        ts = rows("SELECT * FROM tournois WHERE activite=? ORDER BY id DESC", (sport,))
        if not ts:
            st.info(f"Aucun tournoi {sport} pour le moment.")
            return
        t = st.selectbox("Tournoi", ts, format_func=lambda r: r["nom"])
        teams = rows("SELECT * FROM equipes WHERE activite=? ORDER BY nom", (sport,))
        if len(teams) < 2:
            st.warning(f"Ajoute au moins 2 {participant_label}s pour générer des rencontres.")
        selected = st.multiselect("Participants", teams, format_func=lambda r: r["nom"])
        if st.button("Enregistrer les participants"):
            exe("DELETE FROM tournoi_equipes WHERE tournoi_id=?", (t["id"],))
            for e in selected:
                exe("INSERT OR IGNORE INTO tournoi_equipes(tournoi_id,equipe_id) VALUES(?,?)", (t["id"], e["id"]))
            st.success("Participants enregistrés.")
            st.rerun()
        participants = rows("SELECT e.* FROM tournoi_equipes te JOIN equipes e ON e.id=te.equipe_id WHERE te.tournoi_id=? ORDER BY e.nom", (t["id"],))
        if len(participants) >= 2 and st.button("Générer les rencontres", type="primary"):
            exe("DELETE FROM matchs WHERE tournoi_id=?", (t["id"],))
            ids = [e["id"] for e in participants]
            games = _round_robin(ids) if t["formule"] != "Élimination directe" else [(ids[i], ids[i + 1], "1er tour") for i in range(0, len(ids) - 1, 2)]
            for a, b, phase in games:
                exe("INSERT INTO matchs(activite,equipe_a_id,equipe_b_id,tournoi_id,phase,date_match,lieu) VALUES(?,?,?,?,?,?,?)", (sport, a, b, t["id"], phase, t["date_tournoi"], t["lieu"]))
            st.success(f"{len(games)} rencontre(s) {sport} générée(s).")
            st.rerun()

    elif tab == "Classement":
        ts = rows("SELECT * FROM tournois WHERE activite=? ORDER BY id DESC", (sport,))
        if not ts:
            st.info("Aucun tournoi.")
            return
        t = st.selectbox("Tournoi", ts, format_func=lambda r: r["nom"], key="rank_t")
        teams = rows("SELECT e.* FROM tournoi_equipes te JOIN equipes e ON e.id=te.equipe_id WHERE te.tournoi_id=?", (t["id"],))
        stats = {e["id"]: {"Équipe": e["nom"], "J": 0, "G": 0, "N": 0, "P": 0, "Pour": 0, "Contre": 0, "Pts": 0} for e in teams}
        for m in rows("SELECT * FROM matchs WHERE tournoi_id=? AND statut='Terminé'", (t["id"],)):
            if m["score_a"] is None or m["score_b"] is None:
                continue
            a, b = stats.get(m["equipe_a_id"]), stats.get(m["equipe_b_id"])
            if not a or not b:
                continue
            a["J"] += 1
            b["J"] += 1
            a["Pour"] += m["score_a"]
            a["Contre"] += m["score_b"]
            b["Pour"] += m["score_b"]
            b["Contre"] += m["score_a"]
            if m["score_a"] > m["score_b"]:
                a["G"] += 1
                b["P"] += 1
                a["Pts"] += 3
            elif m["score_b"] > m["score_a"]:
                b["G"] += 1
                a["P"] += 1
                b["Pts"] += 3
            else:
                a["N"] += 1
                b["N"] += 1
                a["Pts"] += 1
                b["Pts"] += 1
        ranking = sorted(stats.values(), key=lambda x: (x["Pts"], x["Pour"] - x["Contre"], x["Pour"]), reverse=True)
        st.dataframe(ranking, use_container_width=True, hide_index=True)

    else:
        matches = rows("SELECT m.*,a.nom equipe_a,b.nom equipe_b FROM matchs m JOIN equipes a ON a.id=m.equipe_a_id JOIN equipes b ON b.id=m.equipe_b_id WHERE m.activite=? ORDER BY m.date_match DESC,m.id DESC", (sport,))
        if tab == "Matchs":
            teams = rows("SELECT * FROM equipes WHERE activite=? ORDER BY nom", (sport,))
            if individuel:
                st.markdown(f"#### ➕ Ajouter rapidement un {participant_label}")
                with st.form(f"sc_quick_match_participant_{sport}"):
                    qnom = st.text_input("Nom du joueur ou de la paire", key=f"sc_qm_name_{sport}")
                    qadd = st.form_submit_button("Ajouter le participant")
                if qadd and qnom.strip():
                    exe("INSERT INTO equipes(nom,activite,date_creation) VALUES(?,?,?)", (qnom.strip(), sport, str(date.today())))
                    st.success(f"{qnom.strip()} ajouté à {sport}.")
                    st.rerun()
            if len(teams) >= 2:
                with st.form("sc_match"):
                    a = st.selectbox("Participant A", teams, format_func=lambda r: r["nom"])
                    b = st.selectbox("Participant B", teams, format_func=lambda r: r["nom"], index=1)
                    d = st.date_input("Date", date.today())
                    h = st.text_input("Heure")
                    lieu = st.text_input("Lieu")
                    arb = st.text_input("Arbitre")
                    add = st.form_submit_button(f"Créer le match {sport}", type="primary")
                if add and a["id"] != b["id"]:
                    exe("INSERT INTO matchs(activite,equipe_a_id,equipe_b_id,date_match,heure,lieu,arbitre) VALUES(?,?,?,?,?,?,?)", (sport, a["id"], b["id"], str(d), h, lieu, arb))
                    st.success(f"Match {sport} créé.")
                    st.rerun()
            else:
                st.warning(f"Il faut au moins 2 {participant_label}s pour créer un match {sport}.")
            for m in matches:
                st.write(f"**{m['equipe_a']} {'—' if m['score_a'] is None else str(m['score_a']) + ' - ' + str(m['score_b'])} {m['equipe_b']}** • {m['date_match']} • {m.get('phase') or ''}")
            return
        if not matches:
            st.info("Aucun match.")
            return
        m = st.selectbox("Match", matches, format_func=lambda r: f"{r['date_match']} • {r['equipe_a']} / {r['equipe_b']}")
        st.markdown(f"## 📋 {m['equipe_a']} — {m['equipe_b']}")
        st.caption(f"{sport} • {m['date_match']} • {m['heure'] or ''} • {m['lieu'] or ''} • Arbitre : {m['arbitre'] or 'à définir'}")
        ca, cb = st.columns(2)
        for col, tid, name in [(ca, m["equipe_a_id"], m["equipe_a"]), (cb, m["equipe_b_id"], m["equipe_b"])]:
            with col:
                st.markdown(f"### {name}")
                team = one("SELECT * FROM equipes WHERE id=?", (tid,))
                photo = team["photo"] if team and "photo" in team.keys() else None
                if photo:
                    st.image(photo, use_container_width=True)
                for p in rows("SELECT ej.*,u.nom,u.prenom FROM equipe_joueurs ej JOIN utilisateurs u ON u.id=ej.utilisateur_id WHERE ej.equipe_id=? ORDER BY ej.titulaire DESC,u.nom", (tid,)):
                    st.write(f"{'⭐' if p['titulaire'] else '↪'} {p['numero'] or '-'} • {p['nom']} {p['prenom']} • {p['poste'] or '-'}")
        statuses = ["Prévu", "En cours", "Terminé", "Reporté", "Annulé"]
        current_status = m.get("statut") or "Prévu"
        with st.form("sc_score"):
            c1, c2 = st.columns(2)
            sa = c1.number_input(f"Score {m['equipe_a']}", 0, value=int(m['score_a'] or 0))
            sb = c2.number_input(f"Score {m['equipe_b']}", 0, value=int(m['score_b'] or 0))
            statut = st.selectbox("Statut", statuses, index=statuses.index(current_status) if current_status in statuses else 0)
            obs = st.text_area("Observations / détail des sets", m["observations"] or "")
            save = st.form_submit_button("Enregistrer la feuille de match", type="primary")
        if save:
            exe("UPDATE matchs SET score_a=?,score_b=?,statut=?,observations=? WHERE id=?", (sa, sb, statut, obs, m["id"]))
            st.success("Feuille enregistrée.")
            st.rerun()

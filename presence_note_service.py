COMBINED_MENU_LABEL = "✅ Présence / Note évaluation"


def evaluation_title(theme, date_eval):
    cleaned = (theme or "").strip()
    return cleaned or f"Évaluation du {date_eval}"


def inject_combined_navigation(options):
    items = list(options)
    if (
        "Présences" in items
        and "Cahier de notes" in items
        and COMBINED_MENU_LABEL not in items
    ):
        items.insert(items.index("Présences"), COMBINED_MENU_LABEL)
    return items


def save_rows(
    conn,
    *,
    session_id,
    activity,
    date_eval,
    title,
    bareme,
    coefficient,
    rows,
):
    title = evaluation_title(title, date_eval)
    for row in rows:
        student_id = int(row["student_id"])
        status = row["status"]
        observation = (row.get("observation") or "").strip()
        note = row.get("note")

        conn.execute(
            """
            INSERT INTO presences(seance_id, etudiant_id, statut, commentaire)
            VALUES(?,?,?,?)
            ON CONFLICT(seance_id, etudiant_id)
            DO UPDATE SET statut=excluded.statut, commentaire=excluded.commentaire
            """,
            (int(session_id), student_id, status, observation),
        )

        if note is None:
            continue

        existing = conn.execute(
            """
            SELECT id
            FROM evaluations
            WHERE etudiant_id=? AND activite=? AND intitule=? AND date_eval=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (student_id, activity, title, date_eval),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE evaluations
                SET note=?, bareme=?, coefficient=?, commentaire=?
                WHERE id=?
                """,
                (
                    float(note),
                    float(bareme),
                    float(coefficient),
                    observation,
                    int(existing[0]),
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO evaluations(
                    etudiant_id, activite, intitule, date_eval,
                    note, bareme, coefficient, commentaire
                )
                VALUES(?,?,?,?,?,?,?,?)
                """,
                (
                    student_id,
                    activity,
                    title,
                    date_eval,
                    float(note),
                    float(bareme),
                    float(coefficient),
                    observation,
                ),
            )

    conn.commit()

"""Safe, transactional bulk enrollment helpers.

The helper is intentionally data-agnostic: personal student identifiers must be
supplied at runtime and are never committed to the repository.
"""
from __future__ import annotations

from datetime import datetime
import unicodedata

VALID_MODALITIES = {"UET", "UECF", "Non noté"}


def _norm(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in text if not unicodedata.combining(ch)).lower().strip()


def _as_dict(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        return row


def apply_bulk_enrollment(db_factory, payload, *, use_postgres=False):
    """Enroll a complete batch only when target offer and all students are valid.

    The operation is all-or-nothing. It never creates student accounts; every
    student must already have one active Étudiant profile identified by the exact
    student number supplied in ``payload['students']``.
    """
    payload = payload or {}
    activity = str(payload.get("activity") or "").strip()
    semester = str(payload.get("semester") or "").strip()
    schedule_terms = [_norm(x) for x in (payload.get("schedule_terms") or []) if str(x or "").strip()]
    students = list(payload.get("students") or [])

    if not activity or not semester or not schedule_terms or not students:
        return {"status": "invalid_payload"}

    seen = set()
    requested = []
    for item in students:
        ident = str((item or {}).get("identifiant") or "").strip()
        modality = str((item or {}).get("modalite") or "").strip()
        if not ident or modality not in VALID_MODALITIES or ident in seen:
            return {"status": "invalid_payload"}
        seen.add(ident)
        requested.append((ident, modality))

    conn = db_factory()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT o.id,o.intitule,o.jour_horaire,o.capacite "
            "FROM offres o JOIN offre_semestres os ON os.offre_id=o.id "
            "WHERE lower(o.activite)=lower(?) AND os.semestre=?",
            (activity, semester),
        )
        candidates = [_as_dict(r) for r in cur.fetchall()]
        matches = []
        for offer in candidates:
            haystack = _norm(f"{offer['intitule'] or ''} {offer['jour_horaire'] or ''}")
            if all(term in haystack for term in schedule_terms):
                matches.append(offer)
        if not matches:
            conn.rollback()
            return {"status": "offer_not_found", "candidate_count": len(candidates)}
        if len(matches) != 1:
            conn.rollback()
            return {"status": "ambiguous_offer", "match_count": len(matches)}

        offer = matches[0]
        offer_id = offer["id"]
        if use_postgres:
            cur.execute("SELECT id,capacite FROM offres WHERE id=? FOR UPDATE", (offer_id,))
        else:
            try:
                conn.execute("BEGIN IMMEDIATE")
            except Exception:
                pass
            cur.execute("SELECT id,capacite FROM offres WHERE id=?", (offer_id,))
        locked_offer = _as_dict(cur.fetchone())
        if not locked_offer:
            conn.rollback()
            return {"status": "offer_not_found", "candidate_count": len(candidates)}

        resolved = []
        missing = []
        ambiguous = []
        for ident, modality in requested:
            cur.execute(
                "SELECT id,identifiant FROM utilisateurs "
                "WHERE identifiant=? AND profil='Étudiant' AND actif=1",
                (ident,),
            )
            found = [_as_dict(r) for r in cur.fetchall()]
            if not found:
                missing.append(ident)
            elif len(found) != 1:
                ambiguous.append(ident)
            else:
                resolved.append((found[0]["id"], ident, modality))

        if missing:
            conn.rollback()
            return {"status": "missing_students", "missing": missing}
        if ambiguous:
            conn.rollback()
            return {"status": "ambiguous_students", "ambiguous": ambiguous}

        cur.execute(
            "SELECT COUNT(*) AS n FROM inscriptions WHERE offre_id=? AND statut='Inscrit'",
            (offer_id,),
        )
        count_row = _as_dict(cur.fetchone())
        registered = int((count_row or {}).get("n") or 0)

        existing_by_student = {}
        new_needed = 0
        for student_id, ident, modality in resolved:
            cur.execute(
                "SELECT id,statut FROM inscriptions WHERE utilisateur_id=? AND offre_id=?",
                (student_id, offer_id),
            )
            existing = _as_dict(cur.fetchone())
            existing_by_student[student_id] = existing
            if not existing or existing.get("statut") != "Inscrit":
                new_needed += 1

        capacity = max(0, int(locked_offer.get("capacite") or 0))
        if capacity and registered + new_needed > capacity:
            conn.rollback()
            return {
                "status": "full",
                "capacity": capacity,
                "registered": registered,
                "requested_new": new_needed,
            }

        now = datetime.now().isoformat(timespec="seconds")
        created = 0
        updated = 0
        for student_id, ident, modality in resolved:
            existing = existing_by_student.get(student_id)
            if existing:
                cur.execute(
                    "UPDATE inscriptions SET modalite=?,statut='Inscrit',date_inscription=? WHERE id=?",
                    (modality, now, existing["id"]),
                )
                updated += 1
            else:
                cur.execute(
                    "INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,statut,date_inscription) "
                    "VALUES(?,?,?,'Inscrit',?)",
                    (student_id, offer_id, modality, now),
                )
                created += 1

        conn.commit()
        return {
            "status": "ok",
            "offer_id": offer_id,
            "enrolled": len(resolved),
            "created": created,
            "updated": updated,
        }
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

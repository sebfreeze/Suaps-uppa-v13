"""Secure helpers for SUAPS course registration from a QR code."""
from __future__ import annotations

from datetime import datetime
import secrets
from urllib.parse import quote
from io import BytesIO

import qrcode

VALID_MODALITIES = ("UET", "UECF", "Non noté")


def new_registration_token():
    return secrets.token_urlsafe(24)


def registration_url(base_url, token):
    return f"{str(base_url or '').rstrip('/')}/?inscription={quote(str(token or ''), safe='')}"


def make_qr_png(data):
    buffer = BytesIO()
    qrcode.make(str(data)).save(buffer, format="PNG")
    return buffer.getvalue()


def register_student_from_qr(db_factory, token, email, identifiant, modalite, *, use_postgres=False):
    """Register one student in the offer identified by the QR token."""
    conn = db_factory()
    try:
        cur = conn.cursor()
        if use_postgres:
            cur.execute(
                "SELECT id, capacite, ouverte, public FROM offres WHERE inscription_token=? FOR UPDATE",
                (str(token or "").strip(),),
            )
        else:
            try:
                conn.execute("BEGIN IMMEDIATE")
            except Exception:
                pass
            cur.execute(
                "SELECT id, capacite, ouverte, public FROM offres WHERE inscription_token=?",
                (str(token or "").strip(),),
            )
        offer = cur.fetchone()
        cur.execute(
            "SELECT id, identifiant FROM utilisateurs WHERE lower(email)=lower(?) "
            "AND profil='Étudiant' AND actif=1",
            (str(email or "").strip(),),
        )
        student = cur.fetchone()
        if not offer:
            conn.rollback()
            return "invalid"
        if not int(offer["ouverte"] or 0):
            conn.rollback()
            return "closed"
        if str(offer["public"] or "Tous") == "Personnel":
            conn.rollback()
            return "forbidden"
        if not student:
            conn.rollback()
            return "unknown_student"
        stored_ident = str(student["identifiant"] or "").strip()
        if not stored_ident or not secrets.compare_digest(str(identifiant or "").strip(), stored_ident):
            conn.rollback()
            return "bad_credentials"
        cur.execute(
            "SELECT id, statut FROM inscriptions WHERE utilisateur_id=? AND offre_id=?",
            (student["id"], offer["id"]),
        )
        existing = cur.fetchone()
        if existing and existing["statut"] == "Inscrit":
            conn.rollback()
            return "duplicate"
        cur.execute(
            "SELECT COUNT(*) AS n FROM inscriptions WHERE offre_id=? AND statut='Inscrit'",
            (offer["id"],),
        )
        registered = int(cur.fetchone()["n"] or 0)
        capacity = max(0, int(offer["capacite"] or 0))
        if capacity and registered >= capacity:
            conn.rollback()
            return "full"
        cur.execute(
            "INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,statut,date_inscription) "
            "VALUES(?,?,?,'Inscrit',?)",
            (student["id"], offer["id"], modalite, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return "ok"
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()

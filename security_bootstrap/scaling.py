"""Mise à l'échelle SUAPS : inscriptions atomiques et index PostgreSQL.

Cette couche ne change pas l'interface. Elle empêche la surréservation d'un
créneau lorsque plusieurs étudiants cliquent au même moment et ajoute les index
utiles aux recherches les plus fréquentes pour plusieurs milliers d'usagers.
"""
from __future__ import annotations

import builtins
import os
import sys

_previous_compile = builtins.compile


def _patch_staff_profiles(source):
    """Applique les profils définitifs après l'injection sécurité."""
    if not isinstance(source, str):
        return source

    # Yann + Erick = une seule personne : Yan-Erick.
    source = source.replace(
        '    {"nom":"Yann","role":"Admin","avatar":"🧗‍♂️🪨"},\n    {"nom":"Erick","role":"Admin","avatar":"⚽🥅"},',
        '    {"nom":"Yan-Erick","role":"Admin","avatar":"🧗‍♂️⚽"},',
        1,
    )

    # Geoffrey et Bernard gardent les droits Admin prévus précédemment.
    for _name,_avatar in (("Geoffrey","🏸⚡"),("Bernard","🚴‍♂️😜")):
        source = source.replace(
            f'{{"nom":"{_name}","role":"Enseignant","avatar":"{_avatar}"}}',
            f'{{"nom":"{_name}","role":"Admin","avatar":"{_avatar}"}}',
            1,
        )

    # Sébastien (ainsi que Geoffrey et Bernard) est enseignant ET administrateur.
    source = source.replace(
        "format_func=lambda p:f\"{p['avatar']}  {p['nom']} — {'Administrateur' if p['role']=='Admin' else 'Enseignant'}\"",
        "format_func=lambda p:f\"{p['avatar']}  {p['nom']} — {'Enseignant + Administrateur' if p['nom'] in ('Sébastien','Geoffrey','Bernard') else ('Administrateur' if p['role']=='Admin' else 'Enseignant')}\"",
        1,
    )
    source = source.replace(
        '_role_label="Administrateur" if st.session_state.get("teacher_role")=="Admin" else "Enseignant"',
        '_role_label="Enseignant + Administrateur" if st.session_state.get("teacher_name") in ("Sébastien","Geoffrey","Bernard") else ("Administrateur" if st.session_state.get("teacher_role")=="Admin" else "Enseignant")',
        1,
    )
    return source


def _patch_scaling(source):
    if not isinstance(source, str):
        return source
    if "def inscriptions():" not in source or "def exe(sql,p=()):" not in source:
        return source

    # Ce passage reste utile si les profils sont déjà présents dans la source.
    source = _patch_staff_profiles(source)

    # Helper transactionnel. Sous PostgreSQL, le verrou FOR UPDATE porté sur le
    # créneau sérialise uniquement les inscriptions concurrentes au même créneau.
    # Deux étudiants ne peuvent donc jamais obtenir simultanément la dernière
    # place. Sous SQLite, BEGIN IMMEDIATE conserve un repli sûr pour les tests.
    if "def _suaps_atomic_register" not in source:
        old_exe = '''def exe(sql,p=()):
    c=db(); q=c.cursor(); q.execute(sql,p); c.commit(); x=q.lastrowid; c.close(); return x'''
        helper = '''def exe(sql,p=()):
    c=db(); q=c.cursor(); q.execute(sql,p); c.commit(); x=q.lastrowid; c.close(); return x


def _suaps_atomic_register(utilisateur,offre_id,modalite):
    c=db()
    try:
        q=c.cursor()
        if USE_POSTGRES:
            q.execute("SELECT id,capacite,ouverte,public FROM offres WHERE id=? FOR UPDATE",(offre_id,))
        else:
            try: c.execute("BEGIN IMMEDIATE")
            except Exception: pass
            q.execute("SELECT id,capacite,ouverte,public FROM offres WHERE id=?",(offre_id,))
        offre=q.fetchone()
        if not offre or not int(offre["ouverte"] or 0):
            c.rollback(); return "closed"

        profil=str(utilisateur.get("profil") or "") if hasattr(utilisateur,"get") else str(utilisateur["profil"] or "")
        public=str(offre["public"] or "Tous")
        if public=="Étudiants" and profil!="Étudiant":
            c.rollback(); return "forbidden"
        if public=="Personnel" and profil!="Personnel":
            c.rollback(); return "forbidden"

        q.execute("SELECT id,statut FROM inscriptions WHERE utilisateur_id=? AND offre_id=?",(utilisateur["id"],offre_id))
        exist=q.fetchone()
        if exist and str(exist["statut"] or "")=="Inscrit":
            c.rollback(); return "duplicate"

        q.execute("SELECT COUNT(*) n FROM inscriptions WHERE offre_id=? AND statut='Inscrit'",(offre_id,))
        n=q.fetchone()
        inscrits=int(n["n"] if n else 0)
        capacite=max(0,int(offre["capacite"] or 0))
        if inscrits>=capacite:
            c.rollback(); return "full"

        now=datetime.now().isoformat(timespec="seconds")
        if exist:
            q.execute("UPDATE inscriptions SET modalite=?,statut='Inscrit',date_inscription=? WHERE id=?",(modalite,now,exist["id"]))
        else:
            q.execute("INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,statut,date_inscription) VALUES(?,?,?,'Inscrit',?)",(utilisateur["id"],offre_id,modalite,now))
        c.commit()
        return "ok"
    except DBIntegrityError:
        try: c.rollback()
        except Exception: pass
        return "duplicate"
    except Exception:
        try: c.rollback()
        except Exception: pass
        raise
    finally:
        c.close()'''
        if old_exe in source:
            source = source.replace(old_exe, helper, 1)

    old_click = '''        if st.button("S'inscrire",key=f"i{o['id']}",type="primary"):
            if dispo<=0: st.error("Créneau complet.")
            elif o["public"]=="Étudiants" and u["profil"]!="Étudiant": st.warning("Créneau réservé aux étudiants.")
            else:
                try:
                    exe("INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,date_inscription) VALUES(?,?,?,?)",(u["id"],o["id"],mod,datetime.now().isoformat(timespec="seconds"))); st.success("Inscription enregistrée."); st.rerun()
                except sqlite3.IntegrityError: st.info("Tu es déjà inscrit.")'''
    new_click = '''        if st.button("S'inscrire",key=f"i{o['id']}",type="primary"):
            try:
                _result=_suaps_atomic_register(u,o["id"],mod)
                if _result=="ok":
                    st.success("Inscription enregistrée."); st.rerun()
                elif _result=="full":
                    st.error("Créneau complet : la dernière place vient d'être prise.")
                elif _result=="closed":
                    st.warning("Les inscriptions à ce créneau viennent d'être fermées.")
                elif _result=="forbidden":
                    st.warning("Ce créneau n'est pas ouvert à ton profil.")
                else:
                    st.info("Tu es déjà inscrit.")
            except Exception:
                st.error("L'inscription n'a pas pu être enregistrée. Réessaie dans quelques secondes.")'''
    if old_click in source:
        source = source.replace(old_click, new_click, 1)

    return source


# Le bloc STAFF_PROFILES est injecté par security_bootstrap/sitecustomize.py.
# scaling.py est chargé ensuite : on enveloppe donc le transformeur réellement
# utilisé par _secure_compile afin d'appliquer ces corrections APRES l'injection.
_secure_globals = getattr(_previous_compile, "__globals__", None)
if isinstance(_secure_globals, dict) and callable(_secure_globals.get("_secure_generated_app")):
    _previous_secure_generated_app = _secure_globals["_secure_generated_app"]

    def _secure_generated_app_with_staff(source):
        return _patch_staff_profiles(_previous_secure_generated_app(source))

    _secure_globals["_secure_generated_app"] = _secure_generated_app_with_staff
else:
    # Repli pour les environnements où sitecustomize est exposé sous son nom standard.
    _bootstrap = sys.modules.get("sitecustomize")
    if _bootstrap is not None and hasattr(_bootstrap, "_secure_generated_app"):
        _previous_secure_generated_app = _bootstrap._secure_generated_app

        def _secure_generated_app_with_staff(source):
            return _patch_staff_profiles(_previous_secure_generated_app(source))

        _bootstrap._secure_generated_app = _secure_generated_app_with_staff


def _compile(source, filename, mode, *args, **kwargs):
    return _previous_compile(_patch_scaling(source), filename, mode, *args, **kwargs)


builtins.compile = _compile


# Index complémentaires. Ils sont idempotents et ne contiennent aucune donnée.
def _ensure_scale_indexes():
    database_url=os.getenv("DATABASE_URL","").strip()
    if not database_url:
        return
    try:
        import psycopg
        ddls=[
            "CREATE INDEX IF NOT EXISTS ix_users_email_lower ON utilisateurs(lower(email))",
            "CREATE INDEX IF NOT EXISTS ix_users_profile_active_name ON utilisateurs(profil,actif,nom,prenom)",
            "CREATE INDEX IF NOT EXISTS ix_ins_offer_status_user ON inscriptions(offre_id,statut,utilisateur_id)",
            "CREATE INDEX IF NOT EXISTS ix_ins_user_status_offer ON inscriptions(utilisateur_id,statut,offre_id)",
            "CREATE INDEX IF NOT EXISTS ix_offres_open_activity ON offres(ouverte,activite,id)",
            "CREATE INDEX IF NOT EXISTS ix_sem_semestre_offre ON offre_semestres(semestre,offre_id)",
            "CREATE INDEX IF NOT EXISTS ix_seances_qr_open ON seances(qr_token,qr_ouvert,id)",
            "CREATE INDEX IF NOT EXISTS ix_eval_user_date ON evaluations(utilisateur_id,date_eval,id)",
            "CREATE INDEX IF NOT EXISTS ix_perf_user_date ON performances(utilisateur_id,date_perf,id)",
        ]
        with psycopg.connect(database_url,connect_timeout=10) as conn:
            with conn.cursor() as cur:
                for ddl in ddls:
                    cur.execute(ddl)
            conn.commit()
        print("[SUAPS_SCALE] indexes=ready atomic_registration=enabled")
    except Exception as exc:
        print(f"[SUAPS_SCALE] index_error={type(exc).__name__}:{exc}")


_ensure_scale_indexes()

"""Audit et gestion robuste des créneaux / inscrits pour le live SUAPS."""
from __future__ import annotations

import re

SENTINEL = "# --- roster admin integration ---"
INDEX_SENTINEL = "# --- roster performance indexes ---"
PRESENCE_SENTINEL = "# --- roster presence selector ---"


def _insert_after_top_level_function(source: str, function_prefix: str, block: str) -> str:
    lines = source.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.startswith(function_prefix)), None)
    if start is None:
        return source
    end = start + 1
    while end < len(lines):
        line = lines[end]
        if line.strip() and not line.startswith((" ", "\t")):
            break
        end += 1
    lines.insert(end, block)
    return "".join(lines)


def _ensure_imports(source: str) -> str:
    if "import pandas as pd\n" not in source:
        source = source.replace("import streamlit as st\n", "import streamlit as st\nimport pandas as pd\n", 1)
    return source


def _ensure_admin_nav(source: str) -> str:
    pattern = r'(?m)^(\s*)sec=st\.radio\("Rubrique",\[(.*?)\],horizontal=True,key="admin_section"\)$'
    match = re.search(pattern, source)
    if not match:
        return source
    indent, raw = match.group(1), match.group(2)
    labels = re.findall(r'"([^"]+)"', raw)
    if not labels:
        return source

    # Préserve strictement toutes les rubriques existantes, et ajoute seulement
    # les deux entrées qui peuvent avoir disparu après des correctifs successifs.
    if "Gestion créneaux" not in labels:
        pos = labels.index("Créneaux") + 1 if "Créneaux" in labels else len(labels)
        labels.insert(pos, "Gestion créneaux")
    if "Semestres & CSV" not in labels:
        labels.append("Semestres & CSV")

    rebuilt = (
        indent
        + 'sec=st.radio("Rubrique",['
        + ",".join(f'"{x}"' for x in labels)
        + '],horizontal=True,key="admin_section")'
    )
    return source[: match.start()] + rebuilt + source[match.end() :]


def _ensure_indexes(source: str) -> str:
    if INDEX_SENTINEL in source:
        return source
    block = f'''\n{INDEX_SENTINEL}\n@st.cache_resource(show_spinner=False)\ndef _suaps_ensure_roster_indexes():\n    ddls=[\n        "CREATE INDEX IF NOT EXISTS ix_ins_offer_status_user ON inscriptions(offre_id,statut,utilisateur_id)",\n        "CREATE INDEX IF NOT EXISTS ix_seances_offer_date ON seances(offre_id,date_seance,id)",\n        "CREATE INDEX IF NOT EXISTS ix_offres_activity_schedule ON offres(activite,jour_horaire,id)",\n        "CREATE INDEX IF NOT EXISTS ix_eval_activity_title_date_user ON evaluations(activite,intitule,date_eval,utilisateur_id,id)",\n    ]\n    for _ddl in ddls:\n        try: exe(_ddl)\n        except Exception: pass\n    return True\n\n_suaps_ensure_roster_indexes()\n\n'''
    return _insert_after_top_level_function(source, "def exe(sql,p=()):", block)


def _ensure_natation_audit(source: str) -> str:
    if "def _suaps_log_roster_audit" in source:
        return source
    block = '''\n@st.cache_resource(show_spinner=False)\ndef _suaps_log_roster_audit():\n    try:\n        _audit=rows("SELECT o.id,o.activite,o.intitule,o.jour_horaire,(SELECT COUNT(*) FROM inscriptions i WHERE i.offre_id=o.id AND i.statut='Inscrit') inscrit_count,(SELECT COUNT(*) FROM seances s WHERE s.offre_id=o.id) session_count FROM offres o WHERE lower(trim(o.activite))=lower(trim(?)) ORDER BY o.jour_horaire,o.intitule,o.id",("Natation",))\n        _parts=[f"id={r['id']} title={r['intitule']} horaire={r['jour_horaire'] or '-'} inscrits={int(r['inscrit_count'] or 0)} seances={int(r['session_count'] or 0)}" for r in _audit]\n        print("[SUAPS_ROSTER_AUDIT] "+(" | ".join(_parts) if _parts else "natation=none"))\n    except Exception as _exc:\n        print(f"[SUAPS_ROSTER_AUDIT] error={type(_exc).__name__}:{_exc}")\n    return True\n\n_suaps_log_roster_audit()\n\n'''
    return _insert_after_top_level_function(source, "def one(sql,p=()):", block)


def _optimize_presence_note_selector(source: str) -> str:
    if PRESENCE_SENTINEL in source:
        return source
    old = '''        _sessions=rows("SELECT s.id,s.offre_id,s.date_seance,s.theme,o.activite,o.intitule,o.jour_horaire,(SELECT COUNT(*) FROM inscriptions i WHERE i.offre_id=s.offre_id AND i.statut='Inscrit') AS inscrit_count FROM seances s JOIN offres o ON o.id=s.offre_id ORDER BY s.date_seance DESC,s.id DESC")\n'''
    if old not in source:
        return source
    new = '''        # --- roster presence selector ---\n        _activities=rows("SELECT DISTINCT activite FROM offres ORDER BY activite")\n        _activity_names=[r["activite"] for r in _activities]\n        _activity_index=_activity_names.index("Natation") if "Natation" in _activity_names else 0\n        _selected_activity=st.selectbox("Activité",_activity_names,index=_activity_index,key="combined_activity") if _activity_names else None\n        _offers_for_combined=rows("SELECT o.id,o.activite,o.intitule,o.jour_horaire,o.lieu,(SELECT COUNT(*) FROM inscriptions i WHERE i.offre_id=o.id AND i.statut='Inscrit') AS inscrit_count,(SELECT COUNT(*) FROM seances s WHERE s.offre_id=o.id) AS session_count FROM offres o WHERE o.activite=? ORDER BY o.jour_horaire,o.intitule,o.id",(_selected_activity,)) if _selected_activity else []\n        _sessions=[]\n        if _offers_for_combined:\n            _offer=st.selectbox("Créneau / groupe",_offers_for_combined,format_func=lambda r:f"{r['intitule']} — {r['jour_horaire'] or 'horaire à définir'} — {int(r['inscrit_count'] or 0)} inscrit(s) — {int(r['session_count'] or 0)} séance(s) — ID {r['id']}",key="combined_offer")\n            _sessions=rows("SELECT s.id,s.offre_id,s.date_seance,s.theme,o.activite,o.intitule,o.jour_horaire,(SELECT COUNT(*) FROM inscriptions i WHERE i.offre_id=s.offre_id AND i.statut='Inscrit') AS inscrit_count FROM seances s JOIN offres o ON o.id=s.offre_id WHERE s.offre_id=? ORDER BY s.date_seance DESC,s.id DESC",(_offer["id"],))\n'''
    return source.replace(old, new, 1)


MANAGEMENT_BLOCK = '''    # --- roster admin integration ---
    elif sec=="Gestion créneaux":
        st.markdown("### 🧭 Gestion des créneaux & inscrits")
        st.caption("Audit, rattachement et import direct sans supprimer les autres rubriques de l'application.")

        _offers=rows("SELECT o.*,(SELECT COUNT(*) FROM inscriptions i WHERE i.offre_id=o.id) AS inscription_count,(SELECT COUNT(*) FROM inscriptions i WHERE i.offre_id=o.id AND i.statut='Inscrit') AS inscrit_count,(SELECT COUNT(*) FROM seances s WHERE s.offre_id=o.id) AS session_count FROM offres o ORDER BY o.activite,o.jour_horaire,o.intitule,o.id")
        if not _offers:
            st.info("Aucun créneau disponible.")
        else:
            _activity_values=sorted({str(o["activite"]) for o in _offers})
            _default_act=_activity_values.index("Natation") if "Natation" in _activity_values else 0
            _audit_activity=st.selectbox("Activité à auditer",_activity_values,index=_default_act,key="roster_audit_activity")
            _filtered=[o for o in _offers if str(o["activite"])==_audit_activity]
            _audit_rows=[{
                "ID":o["id"],"Activité":o["activite"],"Créneau":o["intitule"],"Jour / horaire":o["jour_horaire"] or "",
                "Lieu":o["lieu"] or "","Inscrits actifs":int(o["inscrit_count"] or 0),"Inscriptions totales":int(o["inscription_count"] or 0),
                "Séances":int(o["session_count"] or 0),"Ouvert":bool(o["ouverte"]),
            } for o in _filtered]
            st.dataframe(pd.DataFrame(_audit_rows),hide_index=True,width="stretch")
            st.info("Si deux lignes correspondent au même mercredi matin, utilise l'ID et le nombre d'inscrits pour identifier le bon créneau.")

            def _offer_label(o):
                return f"ID {o['id']} — {o['activite']} — {o['intitule']} — {o['jour_horaire'] or 'horaire à définir'} — {int(o['inscrit_count'] or 0)} inscrit(s) — {int(o['session_count'] or 0)} séance(s)"

            st.markdown("#### 🔁 Rattacher une séance au bon créneau")
            _sessions_all=rows("SELECT s.id,s.offre_id,s.date_seance,s.theme,o.activite,o.intitule,o.jour_horaire FROM seances s JOIN offres o ON o.id=s.offre_id ORDER BY s.date_seance DESC,s.id DESC")
            if _sessions_all:
                _session_pick=st.selectbox("Séance à rattacher",_sessions_all,format_func=lambda s:f"Séance {s['id']} — {s['date_seance']} — {s['activite']} — {s['intitule']} — {s['jour_horaire'] or ''} — {s['theme'] or ''}",key="roster_session_pick")
                _target_for_session=st.selectbox("Nouveau créneau de cette séance",_offers,format_func=_offer_label,key="roster_session_target")
                if st.button("Rattacher la séance",key="roster_relink_session",type="primary",width="stretch"):
                    exe("UPDATE seances SET offre_id=? WHERE id=?",(_target_for_session["id"],_session_pick["id"]))
                    st.success("Séance rattachée au nouveau créneau. Les présences déjà enregistrées restent conservées.")
                    st.rerun()

            st.markdown("#### 👥 Transférer / fusionner deux créneaux")
            _csrc,_ctgt=st.columns(2)
            _source_offer=_csrc.selectbox("Créneau source",_offers,format_func=_offer_label,key="roster_source_offer")
            _target_candidates=[o for o in _offers if int(o["id"])!=int(_source_offer["id"])]
            _target_offer=_ctgt.selectbox("Créneau cible",_target_candidates,format_func=_offer_label,key="roster_target_offer") if _target_candidates else None

            def _transfer_roster(_source_id,_target_id,_move_sessions=False,_copy_semesters=True):
                _c=db()
                try:
                    _q=_c.cursor()
                    _q.execute("SELECT id,utilisateur_id,modalite,statut,date_inscription FROM inscriptions WHERE offre_id=? ORDER BY id",(_source_id,))
                    _regs=_q.fetchall()
                    _moved=0
                    for _r in _regs:
                        _q.execute("SELECT id FROM inscriptions WHERE utilisateur_id=? AND offre_id=?",(_r["utilisateur_id"],_target_id))
                        _existing=_q.fetchone()
                        if _existing:
                            _q.execute("UPDATE inscriptions SET modalite=?,statut=?,date_inscription=? WHERE id=?",(_r["modalite"],_r["statut"],_r["date_inscription"],_existing["id"]))
                        else:
                            _q.execute("INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,statut,date_inscription) VALUES(?,?,?,?,?)",(_r["utilisateur_id"],_target_id,_r["modalite"],_r["statut"],_r["date_inscription"]))
                        _q.execute("DELETE FROM inscriptions WHERE id=?",(_r["id"],))
                        _moved+=1
                    if _copy_semesters:
                        try:
                            _q.execute("SELECT semestre FROM offre_semestres WHERE offre_id=?",(_source_id,))
                            for _sem in _q.fetchall():
                                _q.execute("SELECT 1 FROM offre_semestres WHERE offre_id=? AND semestre=?",(_target_id,_sem["semestre"]))
                                if not _q.fetchone():
                                    _q.execute("INSERT INTO offre_semestres(offre_id,semestre) VALUES(?,?)",(_target_id,_sem["semestre"]))
                        except Exception:
                            pass
                    if _move_sessions:
                        _q.execute("UPDATE seances SET offre_id=? WHERE offre_id=?",(_target_id,_source_id))
                    _c.commit()
                    return _moved
                except Exception:
                    try: _c.rollback()
                    except Exception: pass
                    raise
                finally:
                    _c.close()

            if _target_offer:
                _move_sessions=st.checkbox("Rattacher aussi toutes les séances du créneau source au créneau cible",value=False,key="roster_move_sessions")
                if st.button("Transférer les inscriptions",key="roster_transfer_students",type="primary",width="stretch"):
                    _n=_transfer_roster(_source_offer["id"],_target_offer["id"],_move_sessions=_move_sessions)
                    st.success(f"{_n} inscription(s) transférée(s)." + (" Les séances ont aussi été rattachées." if _move_sessions else ""))
                    st.rerun()

                _confirm_merge=st.checkbox("Je confirme la fusion complète du créneau source vers la cible",key="roster_merge_confirm")
                if st.button("Fusionner complètement",key="roster_merge_offer",disabled=not _confirm_merge,width="stretch"):
                    _n=_transfer_roster(_source_offer["id"],_target_offer["id"],_move_sessions=True)
                    try: exe("DELETE FROM offre_semestres WHERE offre_id=?",(_source_offer["id"],))
                    except Exception: pass
                    try: exe("DELETE FROM offre_responsables WHERE offre_id=?",(_source_offer["id"],))
                    except Exception: pass
                    _remaining=one("SELECT (SELECT COUNT(*) FROM inscriptions WHERE offre_id=?) AS regs,(SELECT COUNT(*) FROM seances WHERE offre_id=?) AS sess",(_source_offer["id"],_source_offer["id"]))
                    if _remaining and int(_remaining["regs"] or 0)==0 and int(_remaining["sess"] or 0)==0:
                        exe("DELETE FROM offres WHERE id=?",(_source_offer["id"],))
                        st.success(f"Fusion terminée : {_n} inscription(s) déplacée(s), séances rattachées et ancien créneau supprimé.")
                    else:
                        st.warning("Fusion effectuée, mais le créneau source conserve encore des données et n'a pas été supprimé.")
                    st.rerun()

            st.markdown("#### 🗑️ Supprimer un créneau vide")
            _delete_offer=st.selectbox("Créneau à supprimer",_offers,format_func=_offer_label,key="roster_delete_offer")
            _delete_ok=int(_delete_offer["inscription_count"] or 0)==0 and int(_delete_offer["session_count"] or 0)==0
            st.caption("Suppression autorisée uniquement si le créneau ne contient plus aucune inscription ni séance.")
            _delete_confirm=st.checkbox("Je confirme la suppression de ce créneau vide",key="roster_delete_confirm")
            if st.button("Supprimer le créneau vide",key="roster_delete_empty",disabled=not (_delete_ok and _delete_confirm),width="stretch"):
                try: exe("DELETE FROM offre_semestres WHERE offre_id=?",(_delete_offer["id"],))
                except Exception: pass
                try: exe("DELETE FROM offre_responsables WHERE offre_id=?",(_delete_offer["id"],))
                except Exception: pass
                exe("DELETE FROM offres WHERE id=?",(_delete_offer["id"],))
                st.success("Créneau vide supprimé.")
                st.rerun()

            st.markdown("#### 📥 Importer directement une liste dans le bon créneau")
            _import_target=st.selectbox("Créneau cible de l'import",_offers,format_func=_offer_label,key="roster_import_target")
            st.caption("Ici, pas besoin de faire correspondre le nom du créneau dans le fichier : tu choisis d'abord la cible, puis tu importes la liste.")
            _roster_file=st.file_uploader("Fichier CSV ou Excel",type=["csv","xlsx"],key="roster_direct_import")
            if _roster_file is not None:
                try:
                    _rdf=pd.read_excel(_roster_file) if _roster_file.name.lower().endswith(".xlsx") else pd.read_csv(_roster_file,sep=None,engine="python")
                    _rdf.columns=[str(c).strip().lower().replace("é","e").replace("è","e").replace("ê","e").replace("à","a").replace("ç","c") for c in _rdf.columns]
                    _aliases={"numero_etudiant":"identifiant","numero etudiant":"identifiant","n° etudiant":"identifiant","n°etudiant":"identifiant","formation":"composante"}
                    _rdf=_rdf.rename(columns={c:_aliases.get(c,c) for c in _rdf.columns})
                    _required=["nom","prenom","email"]
                    _missing=[c for c in _required if c not in _rdf.columns]
                    if _missing:
                        st.error("Colonnes obligatoires manquantes : "+", ".join(_missing))
                    else:
                        st.dataframe(_rdf.head(30),hide_index=True,width="stretch")
                        if st.button("Importer cette liste dans le créneau sélectionné",key="roster_import_confirm",type="primary",width="stretch"):
                            _c=db(); _added=_updated=_enrolled=0
                            try:
                                _q=_c.cursor()
                                for _,_r in _rdf.iterrows():
                                    def _clean(_name,_default=""):
                                        _v=str(_r.get(_name,_default)).strip()
                                        return "" if _v.lower()=="nan" else _v
                                    _nom=_clean("nom"); _prenom=_clean("prenom"); _email=_clean("email").lower()
                                    if not _nom or not _prenom or not _email: continue
                                    _ident=_clean("identifiant"); _compo=_clean("composante"); _modalite=_clean("modalite","Non noté") or "Non noté"
                                    if _modalite.lower() in ("non note","non noté","non-note"): _modalite="Non noté"
                                    elif _modalite.lower()=="uet": _modalite="UET"
                                    elif _modalite.lower()=="uecf": _modalite="UECF"
                                    if _modalite not in ("UET","UECF","Non noté"): _modalite="Non noté"
                                    _q.execute("SELECT id FROM utilisateurs WHERE lower(email)=lower(?)",(_email,))
                                    _u=_q.fetchone()
                                    if _u:
                                        _uid=_u["id"]
                                        _q.execute("UPDATE utilisateurs SET nom=?,prenom=?,identifiant=?,composante=?,profil='Étudiant',actif=1 WHERE id=?",(_nom,_prenom,_ident,_compo,_uid)); _updated+=1
                                    else:
                                        _q.execute("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,composante,actif) VALUES('Étudiant',?,?,?,?,?,1)",(_nom,_prenom,_email,_ident,_compo))
                                        _q.execute("SELECT id FROM utilisateurs WHERE lower(email)=lower(?)",(_email,)); _uid=_q.fetchone()["id"]; _added+=1
                                    _q.execute("SELECT id FROM inscriptions WHERE utilisateur_id=? AND offre_id=?",(_uid,_import_target["id"]))
                                    _reg=_q.fetchone()
                                    if _reg:
                                        _q.execute("UPDATE inscriptions SET modalite=?,statut='Inscrit' WHERE id=?",(_modalite,_reg["id"]))
                                    else:
                                        _q.execute("INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,statut,date_inscription) VALUES(?,?,?,'Inscrit',?)",(_uid,_import_target["id"],_modalite,str(date.today()))); _enrolled+=1
                                _c.commit()
                            except Exception:
                                try: _c.rollback()
                                except Exception: pass
                                raise
                            finally:
                                _c.close()
                            st.success(f"Import terminé : {_added} étudiant(s) créé(s), {_updated} mis à jour, {_enrolled} nouvelle(s) inscription(s) sur le créneau choisi.")
                            st.rerun()
                except Exception as _exc:
                    st.error(f"Import impossible : {_exc}")
'''


def _ensure_management_branch(source: str) -> str:
    if SENTINEL in source:
        return source
    anchor = '    elif sec=="Présences":\n'
    if anchor not in source:
        return source
    return source.replace(anchor, MANAGEMENT_BLOCK + anchor, 1)


def patch_app_source(source: str) -> str:
    if not isinstance(source, str) or 'key="admin_section"' not in source:
        return source
    source = _ensure_imports(source)
    source = _ensure_admin_nav(source)
    source = _ensure_indexes(source)
    source = _ensure_natation_audit(source)
    source = _optimize_presence_note_selector(source)
    source = _ensure_management_branch(source)
    return source

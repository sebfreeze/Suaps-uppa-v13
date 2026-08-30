'''Orchestrateur Render SUAPS.

Point de convergence des correctifs live : sécurité/PostgreSQL, sauvegardes,
Compétition, Pédagogie, Semestres & CSV et profils enseignants. Les garde-fous
ci-dessous sont idempotents pour éviter qu'une évolution d'une couche fasse
disparaître une rubrique déjà validée.
'''
from pathlib import Path
import importlib.util
import re

_root = Path(__file__).resolve().parent.parent
_security_site = _root / "security_bootstrap" / "sitecustomize.py"

_menu_audit_done = False
_staff_audit_done = False


def _fix_staff_profiles(source):
    '''Applique les profils validés après l'injection de sécurité.'''
    global _staff_audit_done
    if not isinstance(source, str):
        return source

    source = source.replace(
        '    {"nom":"Yann","role":"Admin","avatar":"🧗‍♂️🪨"},\n'
        '    {"nom":"Erick","role":"Admin","avatar":"⚽🥅"},',
        '    {"nom":"Yan-Erick","role":"Admin","avatar":"🧗‍♂️⚽"},',
        1,
    )

    for _name, _avatar in (("Geoffrey", "🏸⚡"), ("Bernard", "🚴‍♂️😜")):
        source = source.replace(
            f'{{"nom":"{_name}","role":"Enseignant","avatar":"{_avatar}"}}',
            f'{{"nom":"{_name}","role":"Admin","avatar":"{_avatar}"}}',
            1,
        )

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

    if not _staff_audit_done and "STAFF_PROFILES=[" in source:
        _staff_audit_done = True
        print(
            "[SUAPS_UI_AUDIT] "
            f"yan_erick={'Yan-Erick' in source} "
            f"sebastien_dual={'Enseignant + Administrateur' in source}"
        )
    return source


def _ensure_admin_modules(source):
    '''Rétablit toutes les rubriques validées et leurs blocs Compétition/Pédagogie.'''
    global _menu_audit_done
    if not isinstance(source, str) or 'key="admin_section"' not in source:
        return source

    pattern = r'sec=st\.radio\("Rubrique",\[(.*?)\],horizontal=True,key="admin_section"\)'
    match = re.search(pattern, source)
    if match:
        existing = re.findall(r'"([^"]+)"', match.group(1))
        existing = ["Compétition" if x == "Sports collectifs" else x for x in existing]
        wanted = [
            "Tableau de bord",
            "Créneaux",
            "Présences",
            "Évaluations",
            "Évaluation /20",
            "Compétition",
            "Pédagogie",
            "Compétences",
            "Barèmes",
            "Sauvegardes",
            "Actualités",
            "Semestres & CSV",
        ]
        final = []
        for item in wanted + existing:
            if item not in final:
                final.append(item)
        rebuilt = 'sec=st.radio("Rubrique",[' + ",".join(f'"{x}"' for x in final) + '],horizontal=True,key="admin_section")'
        source = source[:match.start()] + rebuilt + source[match.end():]

    anchor = '    elif sec=="Compétences":\n'

    if anchor in source and 'elif sec=="Compétition":' not in source:
        competition = '''    elif sec=="Compétition":
        st.markdown("## 🏆 Compétition")
        st.caption("Sports collectifs • Badminton • Pelote basque")
        st.info("Équipes / joueurs • Composer • Matchs • Feuilles de match • Tournois • Classements")
        from sports_co_module import init_sports_co_db, render_sports_co
        init_sports_co_db(exe)
        render_sports_co(st, rows, one, exe, date)
    elif sec=="Compétences":
'''
        source = source.replace(anchor, competition, 1)

    anchor = '    elif sec=="Compétences":\n'
    if anchor in source and 'elif sec=="Pédagogie":' not in source:
        pedagogie = '''    elif sec=="Pédagogie":
        st.markdown("## 🎓 Pédagogie")
        st.caption("Un suivi simple de la séance à la progression de l'étudiant")
        ptab = st.radio("Suivi pédagogique", ["Séances", "Progression", "Bilans"], horizontal=True, key="pedagogie_tab")
        if ptab == "Séances":
            st.markdown("### 🎯 Objectifs de séance")
            st.info("Choisis 2 ou 3 objectifs prioritaires et relie-les aux compétences travaillées.")
            st.multiselect("Objectifs", ["Technique / maîtrise gestuelle", "Tactique / prise de décision", "Engagement / intensité", "Autonomie", "Coopération", "Sécurité", "Condition physique"], max_selections=3, key="pedago_objectifs")
            st.text_area("Observation rapide de la séance", placeholder="Points réussis, points à renforcer, consigne pour la prochaine séance…", key="pedago_obs")
        elif ptab == "Progression":
            st.markdown("### ⭐ Progression des compétences")
            st.info("Lecture simple : Non évalué → À renforcer → Acquis → Maîtrisé. Les validations détaillées restent dans la rubrique Compétences.")
            st.progress(0, text="Sélectionne ou évalue les compétences pour visualiser progressivement le parcours de l'étudiant.")
        else:
            st.markdown("### 👤 Bilan étudiant")
            st.info("Le bilan regroupe les éléments déjà présents dans l'application : présences, compétences, performances et note /20.")
            st.markdown("**Repères de bilan** : assiduité • progression • acquis • points à renforcer • investissement")
            st.text_area("Commentaire de bilan", placeholder="Bilan synthétique de fin de période ou de semestre…", key="pedago_bilan")
    elif sec=="Compétences":
'''
        source = source.replace(anchor, pedagogie, 1)

    if not _menu_audit_done and 'key="admin_section"' in source:
        _menu_audit_done = True
        print(
            "[SUAPS_UI_AUDIT] "
            f"competition={(chr(34)+'Compétition'+chr(34) in source and 'elif sec==\"Compétition\":' in source)} "
            f"pedagogie={(chr(34)+'Pédagogie'+chr(34) in source and 'elif sec==\"Pédagogie\":' in source)} "
            f"sauvegardes={(chr(34)+'Sauvegardes'+chr(34) in source)} "
            f"csv={(chr(34)+'Semestres & CSV'+chr(34) in source)}"
        )
    return source


_security_mod = None
try:
    if _security_site.exists():
        _spec = importlib.util.spec_from_file_location("suaps_security_sitecustomize", _security_site)
        _security_mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_security_mod)
except Exception as exc:
    print(f"[SUAPS_ORCHESTRATOR] security_load_error={type(exc).__name__}")
    _security_mod = None

try:
    if _security_mod is not None and hasattr(_security_mod, "_secure_generated_app"):
        _previous_secure_generated_app = _security_mod._secure_generated_app

        def _secure_generated_app_final(source):
            return _fix_staff_profiles(_previous_secure_generated_app(source))

        _security_mod._secure_generated_app = _secure_generated_app_final
except Exception as exc:
    print(f"[SUAPS_ORCHESTRATOR] staff_hook_error={type(exc).__name__}")

_user_mod = None
try:
    import usercustomize as _user_mod
except Exception as exc:
    print(f"[SUAPS_ORCHESTRATOR] usercustomize_load_error={type(exc).__name__}")
    _user_mod = None

try:
    if _user_mod is not None and hasattr(_user_mod, "_previous_compile"):
        _next_compile = _user_mod._previous_compile

        def _admin_features_bridge(source, filename, mode, *args, **kwargs):
            try:
                source = _ensure_admin_modules(source)
            except Exception as exc:
                print(f"[SUAPS_ORCHESTRATOR] admin_bridge_error={type(exc).__name__}")
            return _next_compile(source, filename, mode, *args, **kwargs)

        _user_mod._previous_compile = _admin_features_bridge
except Exception as exc:
    print(f"[SUAPS_ORCHESTRATOR] bridge_install_error={type(exc).__name__}")

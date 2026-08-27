"""SUAPS UPPA — couche design mobile V15.
Conserve toutes les fonctions de app.py et applique l'identité visuelle ainsi que le catalogue d'activités enrichi.
"""
from pathlib import Path
import streamlit as st

_original_markdown = st.markdown
_design_loaded = False

DESIGN_CSS = r"""
<style>
:root{
  --navy:#12365d; --blue:#1976d2; --cyan:#24b7c9; --ink:#17283a;
  --muted:#6f7f91; --surface:#ffffff; --line:#e8eef5; --bg:#f4f7fb;
}
html,body,[class*="css"]{font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.stApp{background:linear-gradient(180deg,#f7f9fc 0%,#eef4f9 100%)!important;color:var(--ink)}
.block-container{max-width:1080px!important;padding-top:.8rem!important;padding-bottom:5rem!important}
header[data-testid="stHeader"]{background:rgba(247,249,252,.82);backdrop-filter:blur(12px)}
#MainMenu,footer{visibility:hidden}
h1,h2,h3{letter-spacing:-.025em;color:var(--ink)}
h1{font-weight:850!important} h2,h3{font-weight:780!important}
p{line-height:1.5}
.student-hero{background:linear-gradient(135deg,#143b68 0%,#176eaa 55%,#20b7c4 100%)!important;border:0!important;border-radius:28px!important;padding:28px 26px!important;color:white!important;box-shadow:0 18px 42px rgba(18,54,93,.22)!important;margin:8px 0 20px!important;position:relative;overflow:hidden}
.student-hero:before{content:"";position:absolute;width:190px;height:190px;border-radius:50%;right:-70px;top:-90px;background:rgba(255,255,255,.11)}
.student-hero:after{content:"";position:absolute;width:110px;height:110px;border-radius:50%;right:75px;bottom:-80px;background:rgba(255,255,255,.08)}
.student-hero h1,.student-hero h2,.student-hero h3{color:white!important;margin:0 0 7px!important}
.student-hero p{color:rgba(255,255,255,.93)!important;margin:0!important;font-weight:520}
.student-card{background:rgba(255,255,255,.96)!important;border:1px solid var(--line)!important;border-radius:22px!important;padding:18px!important;margin:9px 0 15px!important;box-shadow:0 8px 25px rgba(31,64,98,.075)!important;transition:transform .16s ease,box-shadow .16s ease!important}
.student-card:hover{transform:translateY(-2px);box-shadow:0 13px 30px rgba(31,64,98,.13)!important}
.student-card h3{margin:0 0 8px!important;font-size:1.06rem!important}.student-card p{color:var(--muted);margin:.25rem 0!important}
.student-pill{display:inline-block!important;background:#eef7ff!important;color:#1767a6!important;border:1px solid #dcecf8!important;border-radius:999px!important;padding:5px 10px!important;margin:3px 4px 3px 0!important;font-size:.79rem!important;font-weight:650!important}
.student-section-title{font-size:1.15rem!important;margin:24px 0 10px!important;color:var(--navy)!important}
div.stButton>button,div.stFormSubmitButton>button{width:100%;min-height:50px;border-radius:16px!important;font-weight:750!important;border:1px solid #dce7f1!important;box-shadow:0 5px 14px rgba(26,70,110,.08);transition:transform .14s ease,box-shadow .14s ease}
div.stButton>button:hover,div.stFormSubmitButton>button:hover{transform:translateY(-1px);box-shadow:0 9px 18px rgba(26,70,110,.13);border-color:#a8cce8!important}
button[kind="primary"],div.stButton>button[kind="primary"]{background:linear-gradient(135deg,#1769aa,#22aebd)!important;color:white!important;border:0!important}
div[data-testid="stMetric"]{background:white;border:1px solid var(--line);border-radius:18px;padding:13px 15px;box-shadow:0 5px 16px rgba(31,64,98,.055)}
div[data-testid="stMetricValue"]{color:var(--navy);font-weight:800}
div[data-baseweb="select"]>div,input,textarea{border-radius:14px!important;background:white!important}
div[data-baseweb="tab-list"]{gap:7px;background:#eaf0f6;padding:5px;border-radius:15px}button[data-baseweb="tab"]{border-radius:11px!important}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:16px;overflow:hidden}[data-testid="stAlert"]{border-radius:16px}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#12365d,#174f78)!important}[data-testid="stSidebar"] *{color:white!important}[data-testid="stSidebar"] div[role="radiogroup"] label{padding:5px 3px;border-radius:10px}
@media(max-width:768px){.block-container{padding:.55rem .72rem 5.5rem!important}.student-hero{border-radius:23px!important;padding:23px 19px!important;margin-top:4px!important}.student-hero h1{font-size:1.65rem!important;line-height:1.12!important}.student-card{border-radius:19px!important;padding:16px!important;margin-bottom:11px!important}.student-card h3{font-size:1rem!important}div.stButton>button,div.stFormSubmitButton>button{min-height:54px!important;font-size:.96rem!important}div[data-testid="stHorizontalBlock"]{gap:.55rem!important;flex-wrap:wrap!important}div[data-testid="column"]{min-width:calc(50% - .55rem)!important;flex:1 1 calc(50% - .55rem)!important}h1{font-size:1.65rem!important}h2{font-size:1.35rem!important}h3{font-size:1.08rem!important}}
@media(max-width:430px){div[data-testid="column"]{min-width:100%!important;flex:1 1 100%!important}.student-hero{padding:21px 17px!important}}
</style>
"""

def _markdown_with_design(body, *args, **kwargs):
    global _design_loaded
    if not _design_loaded:
        _design_loaded = True
        _original_markdown(DESIGN_CSS, unsafe_allow_html=True)
    return _original_markdown(body, *args, **kwargs)

st.markdown = _markdown_with_design

source_path = Path(__file__).with_name("app.py")
source = source_path.read_text(encoding="utf-8")

# 1) Catalogue complet d'activités
old_activities = 'ACTIVITES = ["Natation", "Sauvetage", "Surf", "Rugby", "Course à pied", "Pelote Basque"]'
new_activities = '''ACTIVITES = [
    "Natation", "Sauvetage", "Sauvetage côtier", "Surf", "Canoë-kayak",
    "Rugby", "Basket-ball", "Handball", "Volley-ball", "Football", "Futsal",
    "Badminton", "Pelote Basque", "Escalade", "Ski / Snowboard",
    "Danse contemporaine", "Salsa", "Danse africaine",
    "Musculation", "CrossFit", "Remise en forme", "Préparation physique généralisée",
    "Course à pied"
]'''
source = source.replace(old_activities, new_activities)

# 2) Compétences proposées par activité. Elles restent modifiables par l'enseignant.
marker_defaults = '    defaults = {\n        "Natation": ['
extra_defaults = '''    defaults = {
        "Basket-ball": [
            ("BAS1", "Maîtriser dribble, passe et réception en mouvement"),
            ("BAS2", "Choisir et réaliser un tir adapté à la situation"),
            ("BAS3", "Se démarquer et occuper efficacement les espaces"),
            ("BAS4", "Participer à l'organisation collective offensive et défensive"),
        ],
        "Handball": [
            ("HAN1", "Maîtriser passes, réceptions et conduite de balle"),
            ("HAN2", "Tirer avec précision dans des situations variées"),
            ("HAN3", "Créer et exploiter des espaces en attaque"),
            ("HAN4", "Coopérer en défense et respecter les règles de contact"),
        ],
        "Volley-ball": [
            ("VOL1", "Maîtriser manchette, passe haute et service"),
            ("VOL2", "Construire une attaque en plusieurs touches"),
            ("VOL3", "Se placer et se replacer selon la trajectoire du ballon"),
            ("VOL4", "Coopérer et communiquer efficacement avec son équipe"),
        ],
        "Football": [
            ("FOO1", "Maîtriser conduite de balle, passe et contrôle"),
            ("FOO2", "Tirer et finir une action avec efficacité"),
            ("FOO3", "Se démarquer et utiliser les espaces disponibles"),
            ("FOO4", "Participer au projet collectif offensif et défensif"),
        ],
        "Futsal": [
            ("FUT1", "Maîtriser contrôle orienté, passe et conduite en espace réduit"),
            ("FUT2", "Enchaîner rapidement prise d'information et décision"),
            ("FUT3", "Créer des solutions de passe et se démarquer"),
            ("FUT4", "Défendre collectivement et respecter les rotations"),
        ],
        "Badminton": [
            ("BAD1", "Maîtriser les frappes fondamentales et le service"),
            ("BAD2", "Se déplacer et se replacer efficacement"),
            ("BAD3", "Varier trajectoires, longueurs et zones pour construire le point"),
            ("BAD4", "Analyser le rapport de force et adapter sa stratégie"),
        ],
        "Musculation": [
            ("MUS1", "Réaliser les mouvements avec une technique sûre et maîtrisée"),
            ("MUS2", "Choisir une charge et un volume adaptés à l'objectif"),
            ("MUS3", "Organiser une séance cohérente et progressive"),
            ("MUS4", "Respecter échauffement, récupération et règles de sécurité"),
        ],
        "Escalade": [
            ("ESC1", "S'équiper, s'encorder et assurer en sécurité"),
            ("ESC2", "Utiliser efficacement appuis, placements et équilibres"),
            ("ESC3", "Lire une voie et adapter son itinéraire"),
            ("ESC4", "Gérer son effort et sa prise de risque"),
        ],
        "Danse contemporaine": [
            ("DCO1", "Mobiliser espace, temps, énergie et qualités de mouvement"),
            ("DCO2", "Mémoriser et interpréter une phrase chorégraphique"),
            ("DCO3", "Composer et faire des choix chorégraphiques"),
            ("DCO4", "S'engager dans une présence expressive et collective"),
        ],
        "Salsa": [
            ("SAL1", "Maîtriser le pas de base et les changements de direction"),
            ("SAL2", "Danser en rythme et respecter la structure musicale"),
            ("SAL3", "Guider ou suivre avec précision dans la danse à deux"),
            ("SAL4", "Enchaîner des figures avec fluidité et aisance"),
        ],
        "Danse africaine": [
            ("DAF1", "Maîtriser les appuis, coordinations et isolations corporelles"),
            ("DAF2", "Respecter pulsation, rythme et accents musicaux"),
            ("DAF3", "Mémoriser et enchaîner une séquence chorégraphique"),
            ("DAF4", "S'engager corporellement avec énergie et expressivité"),
        ],
        "Ski / Snowboard": [
            ("SKI1", "Contrôler vitesse et trajectoire sur terrain adapté"),
            ("SKI2", "Enchaîner des virages avec équilibre et maîtrise"),
            ("SKI3", "Adapter sa technique au relief et à la neige"),
            ("SKI4", "Respecter les règles de sécurité et de priorité"),
        ],
        "Sauvetage côtier": [
            ("SCO1", "Analyser le milieu côtier, les courants et les dangers"),
            ("SCO2", "Réaliser une entrée à l'eau et une progression adaptées"),
            ("SCO3", "Approcher, sécuriser et remorquer une victime"),
            ("SCO4", "Organiser une intervention en respectant les règles de sécurité"),
        ],
        "CrossFit": [
            ("CRF1", "Réaliser les mouvements fonctionnels avec une technique sûre"),
            ("CRF2", "Adapter charge, intensité et rythme à ses capacités"),
            ("CRF3", "Maintenir la qualité d'exécution sous fatigue"),
            ("CRF4", "Gérer échauffement, récupération et prévention des blessures"),
        ],
        "Canoë-kayak": [
            ("CK1", "Embarquer, débarquer et s'équiper en sécurité"),
            ("CK2", "Propulser et diriger efficacement l'embarcation"),
            ("CK3", "Manœuvrer et s'adapter au milieu et aux trajectoires"),
            ("CK4", "Naviguer en respectant les consignes de sécurité"),
        ],
        "Remise en forme": [
            ("REF1", "Réaliser les exercices avec une posture et une technique adaptées"),
            ("REF2", "Gérer intensité, respiration et récupération"),
            ("REF3", "Construire une séance équilibrée selon son objectif"),
            ("REF4", "Mesurer ses progrès et ajuster sa pratique"),
        ],
        "Préparation physique généralisée": [
            ("PPG1", "Développer force, endurance, vitesse et coordination"),
            ("PPG2", "Réaliser les exercices avec une technique efficace"),
            ("PPG3", "Gérer charge de travail, intensité et récupération"),
            ("PPG4", "Construire une progression adaptée à un objectif sportif"),
        ],
        "Natation": ['''
source = source.replace(marker_defaults, extra_defaults)

# 3) Barèmes initiaux : une évaluation sur 20 par activité, entièrement modifiable ensuite.
marker_seed = '''    conn.commit()\n    conn.close()\n\ndef qdf(sql, params=()):'''
seed_code = '''    conn.commit()

    default_baremes = {
        "Natation": "Évaluation technique et performance natation",
        "Sauvetage": "Parcours de sauvetage",
        "Sauvetage côtier": "Parcours de sauvetage côtier",
        "Surf": "Maîtrise technique surf",
        "Canoë-kayak": "Parcours de maniabilité",
        "Rugby": "Évaluation technique et tactique rugby",
        "Basket-ball": "Parcours dribble, passe et tir",
        "Handball": "Parcours passe, déplacement et tir",
        "Volley-ball": "Service, réception et construction",
        "Football": "Conduite, passe et tir",
        "Futsal": "Technique et prise de décision futsal",
        "Badminton": "Technique et construction du point",
        "Pelote Basque": "Technique, placement et construction du point",
        "Escalade": "Maîtrise d'une voie et sécurité",
        "Ski / Snowboard": "Maîtrise d'un parcours",
        "Danse contemporaine": "Composition et interprétation chorégraphique",
        "Salsa": "Enchaînement technique et musicalité",
        "Danse africaine": "Enchaînement, rythme et expressivité",
        "Musculation": "Technique, programmation et sécurité",
        "CrossFit": "Circuit fonctionnel et qualité d'exécution",
        "Remise en forme": "Circuit forme et maîtrise technique",
        "Préparation physique généralisée": "Circuit PPG",
        "Course à pied": "Gestion de l'allure et performance",
    }
    for act, nom_b in default_baremes.items():
        cur.execute(
            """INSERT INTO baremes(activite,niveau_groupe,nom,unite,sens,valeur_0,valeur_20,actif)
               SELECT ?,?,?,?,?,?,?,1
               WHERE NOT EXISTS (
                   SELECT 1 FROM baremes
                   WHERE activite=? AND nom=? AND COALESCE(niveau_groupe,'')=''
               )""",
            (act, "", nom_b, "points", "Plus élevé = meilleur", 0.0, 20.0, act, nom_b)
        )
    conn.commit()
    conn.close()

def qdf(sql, params=()):'''
source = source.replace(marker_seed, seed_code, 1)

# 4) Affichage des familles d'activités sur l'accueil étudiant.
family_replacements = {
'''  <span class="student-pill">Natation</span>\n  <span class="student-pill">Sauvetage</span>\n  <span class="student-pill">Aquagym</span>''': '''  <span class="student-pill">Natation</span>\n  <span class="student-pill">Sauvetage</span>\n  <span class="student-pill">Sauvetage côtier</span>''',
'''  <span class="student-pill">Sports collectifs</span>\n  <span class="student-pill">Raquettes</span>\n  <span class="student-pill">Combat</span>''': '''  <span class="student-pill">Rugby</span>\n  <span class="student-pill">Basket-ball</span>\n  <span class="student-pill">Handball</span>\n  <span class="student-pill">Volley-ball</span>\n  <span class="student-pill">Football</span>\n  <span class="student-pill">Futsal</span>\n  <span class="student-pill">Badminton</span>\n  <span class="student-pill">Pelote Basque</span>''',
'''  <span class="student-pill">Nature</span>\n  <span class="student-pill">Glisse</span>\n  <span class="student-pill">Aventure</span>''': '''  <span class="student-pill">Surf</span>\n  <span class="student-pill">Escalade</span>\n  <span class="student-pill">Ski / Snowboard</span>\n  <span class="student-pill">Canoë-kayak</span>''',
'''  <span class="student-pill">Danse</span>\n  <span class="student-pill">Expression</span>\n  <span class="student-pill">Créativité</span>''': '''  <span class="student-pill">Danse contemporaine</span>\n  <span class="student-pill">Salsa</span>\n  <span class="student-pill">Danse africaine</span>''',
'''  <span class="student-pill">Bien-être</span>\n  <span class="student-pill">Renforcement</span>\n  <span class="student-pill">Forme</span>''': '''  <span class="student-pill">Musculation</span>\n  <span class="student-pill">CrossFit</span>\n  <span class="student-pill">Remise en forme</span>\n  <span class="student-pill">Préparation physique généralisée</span>''',
'''  <span class="student-pill">Course</span>\n  <span class="student-pill">Endurance</span>\n  <span class="student-pill">Performance</span>''': '''  <span class="student-pill">Course à pied</span>\n  <span class="student-pill">Endurance</span>\n  <span class="student-pill">Performance</span>'''
}
for old, new in family_replacements.items():
    source = source.replace(old, new)

# 5) Édition complète des barèmes existants par l'enseignant.
bar_marker = '''        st.dataframe(bdf, use_container_width=True, hide_index=True)\n\n        if not bdf.empty:\n            bid = st.selectbox(\n                "Barème à activer/désactiver",'''
bar_edit = '''        st.dataframe(bdf, use_container_width=True, hide_index=True)

        if not bdf.empty:
            with st.expander("✏️ Modifier un barème existant"):
                edit_bid = st.selectbox(
                    "Barème à modifier",
                    bdf["id"].tolist(),
                    format_func=lambda x: f'{bdf[bdf.id==x].iloc[0]["activite"]} — {bdf[bdf.id==x].iloc[0]["nom"]}',
                    key="edit_bareme_id"
                )
                edit_row = bdf[bdf.id == edit_bid].iloc[0]
                with st.form("edit_bareme_form"):
                    eb_act = st.selectbox("Activité", ACTIVITES, index=ACTIVITES.index(edit_row["activite"]) if edit_row["activite"] in ACTIVITES else 0)
                    eb_niv = st.text_input("Niveau / groupe", value=edit_row["niveau_groupe"] or "")
                    eb_nom = st.text_input("Nom du barème", value=edit_row["nom"] or "")
                    ec1, ec2 = st.columns(2)
                    unit_options = ["s", "min", "m", "km", "répétitions", "points", "autre"]
                    eb_unit = ec1.selectbox("Unité", unit_options, index=unit_options.index(edit_row["unite"]) if edit_row["unite"] in unit_options else 5)
                    sens_options = ["Plus élevé = meilleur", "Plus faible = meilleur"]
                    eb_sens = ec2.selectbox("Sens", sens_options, index=sens_options.index(edit_row["sens"]) if edit_row["sens"] in sens_options else 0)
                    ec3, ec4 = st.columns(2)
                    eb_v0 = ec3.number_input("Valeur correspondant à 0/20", value=float(edit_row["valeur_0"] or 0.0), step=0.1)
                    eb_v20 = ec4.number_input("Valeur correspondant à 20/20", value=float(edit_row["valeur_20"] or 20.0), step=0.1)
                    save_edit_b = st.form_submit_button("Enregistrer les modifications", type="primary", use_container_width=True)
                    if save_edit_b:
                        exec_sql("UPDATE baremes SET activite=?, niveau_groupe=?, nom=?, unite=?, sens=?, valeur_0=?, valeur_20=? WHERE id=?",
                                 (eb_act, eb_niv.strip(), eb_nom.strip(), eb_unit, eb_sens, eb_v0, eb_v20, int(edit_bid)))
                        st.success("Barème modifié.")
                        st.rerun()

            bid = st.selectbox(
                "Barème à activer/désactiver",'''
source = source.replace(bar_marker, bar_edit, 1)

# 6) Modification / suppression des compétences proposées.
comp_marker = '''        if etuds.empty:\n            st.info("Ajoute d’abord des étudiants.")'''
comp_edit = '''        if not comps.empty:
            with c2.expander("✏️ Modifier / supprimer une compétence"):
                edit_cid = st.selectbox(
                    "Compétence",
                    comps["id"].tolist(),
                    format_func=lambda x: f'{comps[comps.id==x].iloc[0]["code"]} — {comps[comps.id==x].iloc[0]["libelle"]}',
                    key=f"edit_comp_{activite}"
                )
                edit_comp_row = comps[comps.id == edit_cid].iloc[0]
                with st.form("edit_comp_form"):
                    new_code = st.text_input("Code", value=edit_comp_row["code"])
                    new_lib = st.text_input("Libellé", value=edit_comp_row["libelle"])
                    cc1, cc2 = st.columns(2)
                    save_comp = cc1.form_submit_button("Enregistrer", type="primary", use_container_width=True)
                    delete_comp = cc2.form_submit_button("Supprimer", use_container_width=True)
                    if save_comp:
                        try:
                            exec_sql("UPDATE competences SET code=?, libelle=? WHERE id=?", (new_code.strip(), new_lib.strip(), int(edit_cid)))
                            st.success("Compétence modifiée.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                    if delete_comp:
                        exec_sql("DELETE FROM competences WHERE id=?", (int(edit_cid),))
                        st.success("Compétence supprimée.")
                        st.rerun()

        if etuds.empty:
            st.info("Ajoute d’abord des étudiants.")'''
source = source.replace(comp_marker, comp_edit, 1)

exec(compile(source, str(source_path), "exec"), globals(), globals())

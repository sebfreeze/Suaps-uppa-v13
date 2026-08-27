from pathlib import Path

# V15 : on conserve le moteur V14 actuel et on applique les enrichissements demandés
# avant son exécution, afin de ne pas casser l'interface déjà déployée.
source_path = Path(__file__).with_name("v14_core.py")
source = source_path.read_text(encoding="utf-8")

# --- Activités et familles ---
source = source.replace(
    'ACTIVITES=["Natation","Sauvetage","Surf","Rugby","Course à pied","Pelote Basque"]',
    'ACTIVITES=["Natation","Sauvetage","Sauvetage côtier","Surf","Canoë-kayak","Rugby","Basket-ball","Handball","Volley-ball","Football","Futsal","Badminton","Pelote Basque","Escalade","Ski / Snowboard","Danse contemporaine","Salsa","Danse africaine","Musculation","CrossFit","Remise en forme","Préparation physique généralisée","Course à pied"]'
)
source = source.replace(
'''FAMILY_MAP={
    "Activités aquatiques":["Natation","Sauvetage"],
    "Activités collectives et duelles":["Rugby","Pelote Basque"],
    "Activités physiques de pleine nature":["Surf"],
    "Activités dansées et artistiques":[],
    "Activités douces et remise en forme":[],
    "Activités athlétiques":["Course à pied"],
}''',
'''FAMILY_MAP={
    "Activités aquatiques":["Natation","Sauvetage","Sauvetage côtier"],
    "Activités collectives et duelles":["Rugby","Basket-ball","Handball","Volley-ball","Football","Futsal","Badminton","Pelote Basque"],
    "Activités physiques de pleine nature":["Surf","Escalade","Ski / Snowboard","Canoë-kayak"],
    "Activités dansées et artistiques":["Danse contemporaine","Salsa","Danse africaine"],
    "Activités douces et remise en forme":["Musculation","CrossFit","Remise en forme","Préparation physique généralisée"],
    "Activités athlétiques":["Course à pied"],
}'''
)

# Affiche tout le catalogue d'une famille, même sans créneau ouvert.
source = source.replace(
'''    if not acts: st.info("Les activités de cette famille seront ajoutées prochainement.")
    else:
        offs=rows("SELECT * FROM offres WHERE ouverte=1 ORDER BY activite,intitule")
        found=[o for o in offs if o["activite"] in acts]
        for o in found: card(f"{o['activite']} — {o['intitule']}",f"🕒 {o['jour_horaire'] or 'À définir'}  •  📍 {o['lieu'] or 'À définir'}",[o["public"]])''',
'''    if not acts: st.info("Les activités de cette famille seront ajoutées prochainement.")
    else:
        offs=rows("SELECT * FROM offres WHERE ouverte=1 ORDER BY activite,intitule")
        for act in acts:
            found=[o for o in offs if o["activite"]==act]
            if found:
                for o in found:
                    card(f"{o['activite']} — {o['intitule']}",f"🕒 {o['jour_horaire'] or 'À définir'}  •  📍 {o['lieu'] or 'À définir'}",[o["public"]])
            else:
                card(act,"Créneau à venir",["Activité proposée"] )'''
)

# --- Table des barèmes ---
source = source.replace(
'    CREATE TABLE IF NOT EXISTS acquisitions(id INTEGER PRIMARY KEY AUTOINCREMENT,utilisateur_id INTEGER NOT NULL,competence_id INTEGER NOT NULL,niveau TEXT DEFAULT \'Non évalué\',commentaire TEXT,date_validation TEXT,UNIQUE(utilisateur_id,competence_id));',
'''    CREATE TABLE IF NOT EXISTS acquisitions(id INTEGER PRIMARY KEY AUTOINCREMENT,utilisateur_id INTEGER NOT NULL,competence_id INTEGER NOT NULL,niveau TEXT DEFAULT 'Non évalué',commentaire TEXT,date_validation TEXT,UNIQUE(utilisateur_id,competence_id));
    CREATE TABLE IF NOT EXISTS baremes(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,nom TEXT NOT NULL,description TEXT,unite TEXT DEFAULT 'points',valeur_0 REAL DEFAULT 0,valeur_20 REAL DEFAULT 20,actif INTEGER DEFAULT 1);'''
)

# --- Compétences initiales pour toutes les nouvelles activités ---
old_defs = '''    defs={"Natation":["Respiration et aisance","Propulsion","Endurance","Virages"],"Sauvetage":["Sécurité","Approche victime","Remorquage","Conduite de secours"],"Surf":["Lecture du milieu","Rame","Take-off","Sécurité et priorités"],"Rugby":["Passe","Placement","Défense","Organisation collective"],"Course à pied":["Gestion d'allure","Endurance","Technique","Échauffement-récupération"],"Pelote Basque":["Frappe","Placement","Choix tactiques","Règles et sécurité"]}'''
new_defs = '''    defs={
        "Natation":["Respiration et aisance","Propulsion","Endurance","Virages"],
        "Sauvetage":["Sécurité","Approche victime","Remorquage","Conduite de secours"],
        "Sauvetage côtier":["Lecture du milieu côtier","Entrée à l'eau et progression","Approche et remorquage","Organisation d'une intervention sûre"],
        "Surf":["Lecture du milieu","Rame","Take-off","Sécurité et priorités"],
        "Canoë-kayak":["Embarquer et s'équiper en sécurité","Propulsion et direction","Manœuvres et trajectoires","Navigation et sécurité"],
        "Rugby":["Passe","Placement","Défense","Organisation collective"],
        "Basket-ball":["Dribble, passe et réception","Tir adapté","Démarquage et occupation de l'espace","Organisation collective offensive et défensive"],
        "Handball":["Passe, réception et conduite","Tir précis","Création et exploitation des espaces","Organisation défensive et sécurité"],
        "Volley-ball":["Manchette, passe et service","Construction de l'attaque","Placement et replacement","Communication collective"],
        "Football":["Conduite, passe et contrôle","Tir et finition","Démarquage et utilisation des espaces","Organisation collective"],
        "Futsal":["Contrôle orienté, passe et conduite","Prise d'information et décision","Démarquage en espace réduit","Défense collective et rotations"],
        "Badminton":["Frappes fondamentales et service","Déplacements et replacement","Variation des trajectoires","Choix tactiques et adaptation"],
        "Pelote Basque":["Frappe","Placement","Choix tactiques","Règles et sécurité"],
        "Escalade":["Équipement, encordement et assurage","Appuis, placements et équilibres","Lecture de voie","Gestion de l'effort et du risque"],
        "Ski / Snowboard":["Contrôle de la vitesse","Virages et équilibre","Adaptation au terrain et à la neige","Sécurité et priorités"],
        "Danse contemporaine":["Espace, temps et énergie","Mémorisation et interprétation","Composition chorégraphique","Présence expressive et collective"],
        "Salsa":["Pas de base et changements de direction","Rythme et musicalité","Guidage et suivi","Enchaînement fluide des figures"],
        "Danse africaine":["Appuis et coordinations","Rythme et accents musicaux","Mémorisation de séquences","Énergie et expressivité"],
        "Musculation":["Technique et sécurité des mouvements","Choix des charges et du volume","Organisation d'une séance","Échauffement et récupération"],
        "CrossFit":["Technique des mouvements fonctionnels","Adaptation de la charge et de l'intensité","Qualité d'exécution sous fatigue","Échauffement et récupération"],
        "Remise en forme":["Posture et technique","Gestion de l'intensité et de la respiration","Construction d'une séance équilibrée","Suivi des progrès"],
        "Préparation physique généralisée":["Développement des qualités physiques","Technique d'exécution","Gestion de la charge et de la récupération","Construction d'une progression"],
        "Course à pied":["Gestion d'allure","Endurance","Technique","Échauffement-récupération"]
    }'''
source = source.replace(old_defs, new_defs)

# Codes de compétences plus lisibles que les trois premières lettres quand nécessaire.
source = source.replace(
'''    for a,items in defs.items():
        for i,x in enumerate(items,1): q.execute("INSERT OR IGNORE INTO competences(activite,code,libelle) VALUES(?,?,?)",(a,f"{a[:3].upper()}{i}",x))
    c.commit(); c.close()''',
'''    prefixes={"Basket-ball":"BAS","Handball":"HAN","Volley-ball":"VOL","Football":"FOO","Futsal":"FUT","Badminton":"BAD","Musculation":"MUS","Escalade":"ESC","Danse contemporaine":"DCO","Salsa":"SAL","Danse africaine":"DAF","Ski / Snowboard":"SKI","Sauvetage côtier":"SCO","CrossFit":"CRF","Canoë-kayak":"CK","Remise en forme":"REF","Préparation physique généralisée":"PPG"}
    for a,items in defs.items():
        pref=prefixes.get(a,a[:3].upper())
        for i,x in enumerate(items,1): q.execute("INSERT OR IGNORE INTO competences(activite,code,libelle) VALUES(?,?,?)",(a,f"{pref}{i}",x))
    default_baremes={
        "Natation":"Technique et performance natation","Sauvetage":"Parcours de sauvetage","Sauvetage côtier":"Parcours de sauvetage côtier",
        "Surf":"Maîtrise technique surf","Canoë-kayak":"Parcours de maniabilité","Rugby":"Technique et tactique rugby",
        "Basket-ball":"Parcours dribble, passe et tir","Handball":"Parcours passe, déplacement et tir","Volley-ball":"Service, réception et construction",
        "Football":"Conduite, passe et tir","Futsal":"Technique et prise de décision futsal","Badminton":"Technique et construction du point",
        "Pelote Basque":"Technique, placement et construction du point","Escalade":"Maîtrise d'une voie et sécurité","Ski / Snowboard":"Maîtrise d'un parcours",
        "Danse contemporaine":"Composition et interprétation chorégraphique","Salsa":"Enchaînement technique et musicalité","Danse africaine":"Enchaînement, rythme et expressivité",
        "Musculation":"Technique, programmation et sécurité","CrossFit":"Circuit fonctionnel et qualité d'exécution","Remise en forme":"Circuit forme et maîtrise technique",
        "Préparation physique généralisée":"Circuit PPG","Course à pied":"Gestion de l'allure et performance"
    }
    for a,n in default_baremes.items():
        q.execute("INSERT INTO baremes(activite,nom,description,unite,valeur_0,valeur_20,actif) SELECT ?,?,?,?,?,?,1 WHERE NOT EXISTS(SELECT 1 FROM baremes WHERE activite=? AND nom=?)",(a,n,"Barème initial proposé par le SUAPS, modifiable par l'enseignant.","points",0.0,20.0,a,n))
    c.commit(); c.close()'''
)

# --- Nouvelle rubrique Barèmes ---
source = source.replace(
'    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Compétences"],horizontal=True,key="admin_section")',
'    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Compétences","Barèmes"],horizontal=True,key="admin_section")'
)

# Remplace l'ancien bloc final Compétences par deux rubriques dédiées : Compétences et Barèmes.
old_block = '''    else:
        us=rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' AND actif=1 ORDER BY nom,prenom")
        if us:
            p=st.selectbox("Étudiant",us,format_func=lambda r:f"{r['nom']} {r['prenom']}")
            comps=rows("SELECT * FROM competences ORDER BY activite,code")
            if comps:
                c=st.selectbox("Compétence",comps,format_func=lambda r:f"{r['activite']} • {r['code']} — {r['libelle']}")
                niv=st.selectbox("Niveau",["Non évalué","En cours","Acquis","Maîtrisé"])
                if st.button("Valider la compétence",type="primary"):
                    try: exe("INSERT INTO acquisitions(utilisateur_id,competence_id,niveau,date_validation) VALUES(?,?,?,?)",(p["id"],c["id"],niv,str(date.today())))
                    except sqlite3.IntegrityError: exe("UPDATE acquisitions SET niveau=?,date_validation=? WHERE utilisateur_id=? AND competence_id=?",(niv,str(date.today()),p["id"],c["id"]))
                    st.success("Compétence mise à jour.")'''
new_block = '''    elif sec=="Compétences":
        actc=st.selectbox("Activité",ACTIVITES,key="comp_admin_act")
        comps=rows("SELECT * FROM competences WHERE activite=? ORDER BY code",(actc,))
        with st.expander("➕ Ajouter une compétence"):
            with st.form("add_comp_v15"):
                c1,c2=st.columns(2); newcode=c1.text_input("Code"); newlib=c2.text_input("Compétence")
                addc=st.form_submit_button("Ajouter",type="primary")
            if addc and newcode.strip() and newlib.strip():
                try: exe("INSERT INTO competences(activite,code,libelle) VALUES(?,?,?)",(actc,newcode.strip(),newlib.strip())); st.success("Compétence ajoutée."); st.rerun()
                except sqlite3.IntegrityError: st.error("Ce code existe déjà pour cette activité.")
        if comps:
            ce=st.selectbox("Compétence à modifier",comps,format_func=lambda r:f"{r['code']} — {r['libelle']}",key="comp_edit_pick")
            with st.form("edit_comp_v15"):
                e1,e2=st.columns(2); ecode=e1.text_input("Code",ce["code"]); elib=e2.text_input("Libellé",ce["libelle"])
                b1,b2=st.columns(2); savec=b1.form_submit_button("Enregistrer",type="primary"); delc=b2.form_submit_button("Supprimer")
            if savec:
                try: exe("UPDATE competences SET code=?,libelle=? WHERE id=?",(ecode.strip(),elib.strip(),ce["id"])); st.success("Compétence modifiée."); st.rerun()
                except sqlite3.IntegrityError: st.error("Ce code existe déjà.")
            if delc:
                exe("DELETE FROM acquisitions WHERE competence_id=?",(ce["id"],)); exe("DELETE FROM competences WHERE id=?",(ce["id"],)); st.success("Compétence supprimée."); st.rerun()
        us=rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' AND actif=1 ORDER BY nom,prenom")
        comps=rows("SELECT * FROM competences WHERE activite=? ORDER BY code",(actc,))
        if us and comps:
            st.markdown("#### Valider pour un étudiant")
            p=st.selectbox("Étudiant",us,format_func=lambda r:f"{r['nom']} {r['prenom']}")
            c=st.selectbox("Compétence",comps,format_func=lambda r:f"{r['code']} — {r['libelle']}",key="comp_validate_pick")
            niv=st.selectbox("Niveau",["Non évalué","En cours","Acquis","Maîtrisé"])
            if st.button("Valider la compétence",type="primary"):
                try: exe("INSERT INTO acquisitions(utilisateur_id,competence_id,niveau,date_validation) VALUES(?,?,?,?)",(p["id"],c["id"],niv,str(date.today())))
                except sqlite3.IntegrityError: exe("UPDATE acquisitions SET niveau=?,date_validation=? WHERE utilisateur_id=? AND competence_id=?",(niv,str(date.today()),p["id"],c["id"]))
                st.success("Compétence mise à jour.")
    else:
        actb=st.selectbox("Activité",ACTIVITES,key="bareme_admin_act")
        bs=rows("SELECT * FROM baremes WHERE activite=? ORDER BY nom",(actb,))
        with st.expander("➕ Ajouter un barème"):
            with st.form("add_bareme_v15"):
                bn=st.text_input("Nom du barème"); bd=st.text_input("Description"); bu=st.text_input("Unité",value="points")
                x1,x2=st.columns(2); bv0=x1.number_input("Valeur = 0/20",value=0.0); bv20=x2.number_input("Valeur = 20/20",value=20.0)
                addb=st.form_submit_button("Ajouter",type="primary")
            if addb and bn.strip(): exe("INSERT INTO baremes(activite,nom,description,unite,valeur_0,valeur_20,actif) VALUES(?,?,?,?,?,?,1)",(actb,bn.strip(),bd.strip(),bu.strip(),bv0,bv20)); st.success("Barème ajouté."); st.rerun()
        if bs:
            b=st.selectbox("Barème à modifier",bs,format_func=lambda r:r["nom"])
            with st.form("edit_bareme_v15"):
                en=st.text_input("Nom",b["nom"]); ed=st.text_input("Description",b["description"] or ""); eu=st.text_input("Unité",b["unite"] or "points")
                z1,z2=st.columns(2); ev0=z1.number_input("Valeur = 0/20",value=float(b["valeur_0"])); ev20=z2.number_input("Valeur = 20/20",value=float(b["valeur_20"]))
                active=st.checkbox("Actif",bool(b["actif"])); q1,q2=st.columns(2); saveb=q1.form_submit_button("Enregistrer",type="primary"); delb=q2.form_submit_button("Supprimer")
            if saveb: exe("UPDATE baremes SET nom=?,description=?,unite=?,valeur_0=?,valeur_20=?,actif=? WHERE id=?",(en.strip(),ed.strip(),eu.strip(),ev0,ev20,int(active),b["id"])); st.success("Barème modifié."); st.rerun()
            if delb: exe("DELETE FROM baremes WHERE id=?",(b["id"],)); st.success("Barème supprimé."); st.rerun()
            st.caption("Principe : les deux valeurs définissent les repères 0/20 et 20/20. L'enseignant peut les adapter à son test et à son public.")'''
source = source.replace(old_block, new_block)

exec(compile(source, str(source_path), "exec"), globals(), globals())

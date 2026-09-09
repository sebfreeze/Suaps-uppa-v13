import os
import sqlite3
from datetime import date
from pathlib import Path

import streamlit as st

try:
    import psycopg
except Exception:
    psycopg = None

st.set_page_config(page_title="Pédagogie SUAPS", page_icon="📚", layout="wide")

if st.session_state.get("role") != "Enseignant":
    st.warning("🔒 La partie Pédagogie est réservée au mode Enseignant. Passe d'abord l'application en mode Enseignant.")
    st.stop()


def secret_value(name, default=""):
    env = os.getenv(name, "")
    if env:
        return env
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default


DATABASE_URL = secret_value("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)
DB = str(Path(__file__).resolve().parents[1] / "suaps_presence.db")


def sql_compat(sql):
    if not USE_POSTGRES:
        return sql
    q = sql.replace("?", "%s")
    q = q.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    return q


def connect_db():
    if USE_POSTGRES:
        if psycopg is None:
            raise RuntimeError("Le paquet psycopg n'est pas installé.")
        return psycopg.connect(DATABASE_URL, autocommit=False)
    return sqlite3.connect(DB, check_same_thread=False)


def execute(sql, params=()):
    conn = connect_db()
    try:
        cur = conn.cursor()
        cur.execute(sql_compat(sql), params)
        conn.commit()
    finally:
        conn.close()


def query_rows(sql, params=()):
    conn = connect_db()
    try:
        cur = conn.cursor()
        cur.execute(sql_compat(sql), params)
        cols = [d[0] for d in cur.description] if cur.description else []
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


# Chaque séance : titre, objectif, contenu, situation, critères, durée, matériel, compétences par défaut.
DEFAULT_CYCLES = {
    "Natation": [
        ("Diagnostic et aisance aquatique", "Évaluer le niveau initial et installer confiance, respiration et équilibre.", "Entrées dans l'eau, immersions, coulées, 25 m au choix et parcours diagnostic.", "Parcours : immersion, étoile ventrale/dorsale, coulée puis 25 m continu.", "Respiration maîtrisée, relâchement, déplacement continu et sécurité.", 60, "Planches, pull-buoys, plots", ["NAT1", "NAT2"]),
        ("Respiration et équilibre", "Coordonner expiration aquatique, inspiration et position horizontale.", "Bulles, glissées, battements, respiration latérale.", "6 × 25 m : 12,5 m battements + 12,5 m nage complète.", "Expiration continue, tête stable, bassin haut et rythme régulier.", 60, "Planches, frites", ["NAT1", "NAT2"]),
        ("Propulsion crawl", "Améliorer les appuis et la continuité du crawl.", "Rattrapé, un bras, poings fermés, amplitude et nage complète.", "8 × 25 m avec une contrainte technique différente à chaque répétition.", "Appuis vers l'arrière, trajet moteur continu, respiration sans rupture.", 60, "Pull-buoys, plaquettes selon niveau", ["NAT1", "NAT2"]),
        ("Dos crawlé", "Construire une nage dorsale équilibrée et propulsive.", "Battements dos, rotation des épaules, bras alternés et repères.", "4 × 50 m dos avec régularité du nombre de coups de bras.", "Bassin haut, battements continus, trajectoire rectiligne.", 60, "Planches", ["NAT2", "NAT3"]),
        ("Brasse : coordination", "Coordonner traction, respiration, jambes et glisse.", "Jambes, bras seuls, éducatifs puis nage complète.", "6 × 25 m en identifiant une vraie phase de glisse.", "Symétrie, poussée efficace et respiration coordonnée.", 60, "Planches, pull-buoys", ["NAT1", "NAT2"]),
        ("Virages et reprises", "Réduire les ruptures de vitesse au mur.", "Approche, demi-tour ou culbute selon niveau, poussée et coulée.", "10 passages : 5 m avant + virage + 5 m après.", "Approche sans hésitation, poussée tonique, reprise rapide.", 60, "Repères au bord", ["NAT4"]),
        ("Endurance et gestion d'allure", "Nager plus longtemps à une allure adaptée.", "Séries de 50 à 200 m et repères d'allure.", "3 × 200 m réguliers avec faible écart entre les temps.", "Allure stable, technique conservée et récupération maîtrisée.", 60, "Chronomètres", ["NAT3"]),
        ("Vitesse et fréquence", "Accélérer sans dégrader fortement la technique.", "Départs, 15 m rapides, 25 m sprint, récupération complète.", "6 × 25 m vite avec comparaison temps/qualité technique.", "Accélération nette, alignement et fréquence adaptée.", 60, "Chronomètres, plots", ["NAT2", "NAT3"]),
        ("Parcours combiné", "Mobiliser plusieurs nages et compétences dans un parcours continu.", "Crawl, dos, brasse, virages, coulées et changements d'allure.", "Parcours de 300 à 500 m adapté au niveau.", "Enchaînement sans arrêt, consignes respectées, autonomie.", 60, "Matériel de nage varié", ["NAT1", "NAT2", "NAT3", "NAT4"]),
        ("Évaluation et bilan", "Mesurer les progrès techniques et énergétiques.", "Distance continue, épreuve courte chronométrée et observation technique.", "Évaluation : distance + 50/100 m + grille technique.", "Progression mesurable, efficience, sécurité et analyse de sa prestation.", 60, "Chronomètres, grille d'évaluation", ["NAT1", "NAT2", "NAT3", "NAT4"]),
    ],
    "Rugby": [
        ("Diagnostic, sécurité et principes du jeu", "Évaluer le niveau et installer les règles essentielles de sécurité et de continuité.", "Échauffement ballon, passes en mouvement et jeu réduit sans contact.", "4 contre 4, essai, deux passes minimum avant de marquer.", "Ballon vivant, soutien proche, passes vers l'arrière, communication.", 90, "Ballons, plots, chasubles", ["RUG1", "RUG3"]),
        ("Passe et prise d'information", "Passer efficacement en mouvement en regardant défense et partenaires.", "2 contre 1, 3 contre 2, passes avant contact et variations de largeur.", "Vagues offensives successives en surnombre.", "Course droite, fixation et passe au bon moment.", 90, "Ballons, plots", ["RUG1", "RUG2"]),
        ("Soutien et continuité", "Se replacer rapidement pour assurer la continuité.", "Soutien axial/latéral, jeu après toucher, relais offensifs.", "Jeu au toucher : libération du ballon en moins de 3 secondes.", "Soutien disponible, profondeur adaptée, conservation de l'avancée.", 90, "Ballons, chasubles", ["RUG1", "RUG2"]),
        ("Défense individuelle et collective", "Construire une défense organisée, alignée et communicante.", "Placement, montée, cadrage et fermeture des espaces.", "4 attaquants contre 4 défenseurs avec lancement imposé.", "Ligne cohérente, montée ensemble, communication et sécurité.", 90, "Ballons, plots, chasubles", ["RUG3", "RUG4"]),
        ("Plaquage sécurisé / toucher", "Apprendre les principes d'un contact sécurisé lorsque le cadre le permet.", "Posture, placement de tête, ceinturage, chute contrôlée ; variante toucher.", "Ateliers progressifs puis 1 contre 1 encadré.", "Posture stable, tête en sécurité, contrôle et respect des consignes.", 90, "Boucliers, tapis, ballons", ["RUG3"]),
        ("Ruck, libération et replacement", "Comprendre la conservation après contact et le replacement offensif.", "Libération au sol, arrivée du soutien et sortie rapide.", "3 contre 2 + soutien avec zone de libération matérialisée.", "Ballon libéré vite, soutien dans l'axe, continuité.", 90, "Ballons, plots", ["RUG1", "RUG3", "RUG4"]),
        ("Occupation de l'espace", "Écarter, fixer et jouer dans les intervalles.", "Largeur, profondeur, courses de leurre et changements de sens.", "5 contre 5 avec couloirs bonus.", "Espaces occupés, solutions autour du porteur et choix pertinent.", 90, "Ballons, plots, chasubles", ["RUG2", "RUG4"]),
        ("Jeu au pied et transition", "Utiliser le jeu au pied à bon escient et réagir collectivement.", "Jeu au pied rasant ou de déplacement, poursuite et replacement.", "Bonus si le jeu au pied crée gain territorial ou récupération.", "Choix pertinent, poursuite organisée, couverture défensive.", 90, "Ballons, plots", ["RUG2", "RUG4"]),
        ("Projet collectif", "Mettre en place une organisation simple offensive et défensive.", "Lancements, annonces, rôles et adaptation à l'adversaire.", "Matchs courts avec temps mort tactique.", "Projet identifiable, communication et adaptation.", 90, "Ballons, chasubles", ["RUG1", "RUG2", "RUG4"]),
        ("Évaluation en match", "Évaluer la contribution individuelle au projet collectif.", "Matchs aménagés et observation technique, tactique et sécuritaire.", "Tournoi final avec grille : avancer, soutenir, défendre, respecter.", "Décisions pertinentes, engagement maîtrisé et efficacité collective.", 90, "Ballons, chasubles, grille", ["RUG1", "RUG2", "RUG3", "RUG4"]),
    ],
    "Sauvetage": [
        ("Diagnostic aquatique et sécurité", "Évaluer les capacités aquatiques et installer les règles du cycle SSA.", "Nage, immersion, apnée courte, récupération d'objet et remorquage léger.", "Parcours combinant nage, immersion et retour en zone sécurisée.", "Aisance, lucidité, sécurité et capacité à interrompre l'action.", 90, "Mannequin léger, objets immergés", ["SAU1", "SAU2"]),
        ("Surveillance et détection", "Observer une zone et repérer rapidement une difficulté.", "Balayage visuel, zones, indices de difficulté et communication.", "Scénarios d'observation avec comportements différenciés.", "Détection rapide, information pertinente, surveillance globale.", 90, "Fiches scénario, sifflet", ["SAU1"]),
        ("Entrées dans l'eau et approche", "Choisir une entrée et une nage d'approche adaptées.", "Entrées contrôlées, nage tête haute et approche avec matériel.", "Départs variés vers une victime simulée à différentes distances.", "Entrée sûre, contact visuel maintenu, approche maîtrisée.", 90, "Bouée tube selon matériel", ["SAU2"]),
        ("Immersion et recherche", "Réaliser une recherche subaquatique courte et sécurisée.", "Canard, immersion, récupération de mannequin/objet, remontée.", "Recherche dans une zone et profondeur adaptées au groupe.", "Immersion efficace, trajet court et remontée contrôlée.", 90, "Mannequin, objets lestés", ["SAU2", "SAU3"]),
        ("Prises et remorquages", "Transporter une victime simulée en position de sécurité.", "Rétropédalage, prises de remorquage et adaptation à la distance.", "4 × 25 m de remorquage avec variantes de prise.", "Voies aériennes dégagées, prise stable et propulsion continue.", 90, "Mannequin, bouée tube", ["SAU3"]),
        ("Sortie d'eau et transmission", "Organiser la fin d'intervention et transmettre les informations utiles.", "Approche du bord, aide à la sortie, alerte et bilan.", "Scénario complet de la détection à la zone sécurisée.", "Enchaînement ordonné, sécurité, message clair et coopération.", 90, "Mannequin, fiches scénario", ["SAU3", "SAU4"]),
        ("Matériel de sauvetage", "Utiliser le matériel disponible de manière adaptée.", "Bouée tube, perche, corde ou matériel local.", "Ateliers tournants : atteindre, sécuriser et ramener.", "Choix adapté, matériel maîtrisé et communication.", 90, "Bouée tube, perche, corde", ["SAU1", "SAU3"]),
        ("Scénarios d'intervention", "Prendre des décisions rapides dans des situations variées.", "Victime simulée consciente/inconsciente, coordination à deux.", "Scénarios surprise avec observateur et débriefing immédiat.", "Priorités cohérentes, efficacité, sécurité et communication.", 90, "Matériel de sauvetage, fiches", ["SAU1", "SAU2", "SAU3", "SAU4"]),
        ("Parcours SSA complet", "Enchaîner nage, recherche, prise, remorquage et sortie.", "Parcours combiné adapté au niveau et au référentiel retenu.", "Parcours chronométré ou critérié avec pénalités techniques.", "Continuité, maîtrise technique, sécurité et gestion de l'effort.", 90, "Mannequin, obstacles, chronomètre", ["SAU2", "SAU3", "SAU4"]),
        ("Évaluation et mise en situation", "Valider les acquis dans une situation globale de surveillance et sauvetage.", "Observation, déclenchement, intervention, transmission et débriefing.", "Mise en situation finale avec grille individualisée.", "Détection, choix d'intervention, maîtrise aquatique, sécurité, communication.", 90, "Matériel SSA, grille d'évaluation", ["SAU1", "SAU2", "SAU3", "SAU4"]),
    ],
    "Pelote Basque": [
        ("Diagnostic et prise en main", "Découvrir l'activité, la sécurité et les habiletés initiales.", "Manipulations, jonglages, frappes simples et règles de base.", "Défis de 10 frappes consécutives à distance adaptée.", "Contact régulier, trajectoire contrôlée et sécurité.", 75, "Pelotes, protections selon spécialité", ["PEL1", "PEL4"]),
        ("Frappe coup droit", "Construire une frappe régulière et orientée.", "Placement, armé, transfert, accompagnement et cible.", "5 séries de 8 frappes vers trois zones-cibles.", "Appuis stables, frappe devant soi, précision.", 75, "Pelotes, cibles", ["PEL1"]),
        ("Revers et placement", "Élargir les possibilités de frappe et ajuster les déplacements.", "Déplacement latéral, orientation du corps et retour en position.", "Alternance coup droit/revers dans deux couloirs.", "Placement précoce, équilibre et trajectoire maîtrisée.", 75, "Pelotes, plots", ["PEL1", "PEL2"]),
        ("Lecture de trajectoire", "Anticiper rebond, vitesse et profondeur.", "Balles courtes/longues, variations de hauteur et déplacements.", "Annoncer la zone de frappe avant le rebond puis jouer.", "Anticipation, ajustement des appuis et distance optimale.", 75, "Pelotes, zones matérialisées", ["PEL2"]),
        ("Continuité de l'échange", "Maintenir un échange en privilégiant régularité et replacement.", "Échanges coopératifs et augmentation progressive de la distance.", "Contrat collectif : atteindre 20 échanges sans faute.", "Régularité, replacement, communication et sécurité.", 75, "Pelotes", ["PEL1", "PEL2", "PEL4"]),
        ("Précision et zones de jeu", "Orienter volontairement la balle pour déplacer l'adversaire.", "Zones droite/gauche et court/long.", "Points bonus quand une zone annoncée est atteinte.", "Intention identifiable et précision croissante.", 75, "Pelotes, cibles", ["PEL1", "PEL3"]),
        ("Construction du point", "Passer d'un jeu de renvoi à une logique tactique.", "Fixer, déplacer, changer de rythme et jouer l'espace libre.", "Point doublé si l'adversaire est déplacé avant le coup gagnant.", "Enchaînement tactique cohérent et exploitation de l'espace.", 75, "Pelotes, feuille de score", ["PEL2", "PEL3"]),
        ("Service / engagement", "Maîtriser la mise en jeu et préparer le coup suivant.", "Régularité, zones et replacement après engagement.", "10 services ciblés puis mini-matchs avec intention annoncée.", "Service valide, précision et replacement immédiat.", 75, "Pelotes, cibles", ["PEL1", "PEL3"]),
        ("Matchs à thème et stratégie", "Adapter son projet de jeu au profil de l'adversaire.", "Observation, choix de zones, gestion du risque et score aménagé.", "Matchs courts avec fiche d'observation par binôme.", "Projet visible, adaptation, régularité et respect des règles.", 75, "Pelotes, fiches", ["PEL3", "PEL4"]),
        ("Évaluation et tournoi", "Évaluer technique, tactique, engagement et respect du cadre.", "Tournoi, observation croisée et bilan individuel.", "Poules puis classement avec grille technique/tactique/comportementale.", "Frappe maîtrisée, déplacement efficace, autonomie et fair-play.", 75, "Pelotes, grille d'évaluation", ["PEL1", "PEL2", "PEL3", "PEL4"]),
    ],
    "Course à pied": [
        ("Diagnostic et repères d'allure", "Situer son niveau initial et apprendre à relier vitesse, sensations et respiration.", "Échauffement, éducatifs, test progressif ou course de 6 minutes selon le groupe.", "Courir 6 minutes à allure régulière puis comparer distance, fréquence cardiaque si disponible et ressenti.", "Allure maîtrisée, engagement régulier et repères personnels identifiés.", 75, "Plots, chronomètres, piste ou parcours mesuré", ["CAP1", "CAP2", "CAP4"]),
        ("Technique de course", "Améliorer posture, fréquence, pose de pied et relâchement.", "Gammes : montées de genoux, talons-fesses, foulées bondissantes, lignes droites.", "6 × 80 m en alternant consigne technique et course relâchée.", "Buste stable, appuis dynamiques, bras actifs et relâchement.", 75, "Plots, lattes facultatives", ["CAP3", "CAP4"]),
        ("Endurance fondamentale", "Courir longtemps à intensité modérée et stable.", "Échauffement puis blocs continus de 8 à 15 minutes.", "2 × 12 min à allure conversationnelle avec 3 min de récupération.", "Allure stable, respiration contrôlée et technique conservée.", 75, "Chronomètres, parcours balisé", ["CAP1", "CAP2"]),
        ("VMA courte", "Développer la capacité à répéter des efforts rapides et contrôlés.", "30/30 ou 45/30 à intensité individualisée.", "2 séries de 8 × 30 s vite / 30 s lent, récupération 3 min entre séries.", "Régularité des distances, engagement et récupération active.", 75, "Plots, chronomètre, repères de distance", ["CAP1", "CAP2"]),
        ("Allure soutenue / seuil", "Tenir une allure exigeante sans départ excessif.", "Blocs de 4 à 8 minutes à allure soutenue avec récupération courte.", "3 × 6 min à allure régulière, récupération 2 min.", "Faible dérive d'allure, contrôle respiratoire et lucidité.", 75, "Chronomètres, parcours mesuré", ["CAP1", "CAP2"]),
        ("Côtes et puissance", "Développer force spécifique, posture et qualité d'appui.", "Échauffement complet, répétitions en côte, retour en récupération.", "8 à 10 × 20 à 30 s en côte avec récupération en descente.", "Posture haute, poussée active, fréquence maintenue et sécurité.", 75, "Côte sécurisée, plots", ["CAP3", "CAP4"]),
        ("Intervalles longs", "Améliorer la capacité à soutenir une vitesse élevée sur des fractions longues.", "Répétitions de 400 à 800 m selon niveau.", "4 × 600 m réguliers, récupération 2 à 3 min.", "Temps proches, allure maîtrisée et technique stable.", 75, "Piste/parcours mesuré, chronomètres", ["CAP1", "CAP2", "CAP3"]),
        ("Allure cible et stratégie", "Construire une stratégie d'allure pour une distance donnée.", "Travail au kilomètre ou par blocs de temps à l'allure cible.", "3 × 1000 m ou équivalent temps avec objectif de régularité.", "Allure prévue respectée, capacité à accélérer sans s'effondrer.", 75, "Chronomètres, repères kilométriques", ["CAP1", "CAP2"]),
        ("Séance spécifique et autonomie", "Savoir préparer et réaliser une séance adaptée à son objectif.", "Par petits groupes, choix d'un objectif, échauffement, corps de séance et récupération.", "Chaque groupe conduit une séance courte validée par l'enseignant.", "Cohérence de la séance, autonomie, sécurité et gestion de l'effort.", 75, "Matériel selon séance", ["CAP1", "CAP2", "CAP3", "CAP4"]),
        ("Évaluation et bilan", "Mesurer les progrès et analyser sa gestion de course.", "Reprise du test initial ou épreuve de référence choisie.", "Test final + comparaison des temps/distances et bilan personnel.", "Progression, régularité, stratégie d'allure et analyse pertinente.", 75, "Chronomètres, grille de bilan", ["CAP1", "CAP2", "CAP3", "CAP4"]),
    ],
    "Surf": [
        ("Sécurité, milieu et diagnostic", "Lire les conditions, connaître les règles de sécurité et évaluer l'aisance initiale.", "Observation du spot, courants, zones, météo, priorités, échauffement et aisance dans les mousses.", "Sur la plage, identifier dangers et zone de pratique puis réaliser un parcours d'aisance encadré.", "Dangers repérés, consignes comprises, comportement adapté au milieu.", 120, "Planches adaptées, leashs, combinaisons, repères plage", ["SUR1", "SUR4"]),
        ("Rame, position et franchissement", "Se déplacer efficacement sur la planche et franchir les mousses adaptées au niveau.", "Position sur la planche, rame alternée, demi-tour, passage de mousse et retour au bord.", "Séries de départs depuis zone peu profonde, rame vers un repère puis retour contrôlé.", "Planche équilibrée, rame efficace, trajectoire maîtrisée et sécurité.", 120, "Planches adaptées, leashs, combinaisons", ["SUR1", "SUR2"]),
        ("Take-off et prise de vague", "Réaliser un redressement rapide et stable sur mousse ou vague adaptée.", "Take-off à sec, placement des mains/pieds, regard, choix du moment de départ.", "5 à 10 prises de mousse/vague avec objectif de se lever avant la perte de vitesse.", "Redressement fluide, pieds placés, regard vers l'avant, stabilité.", 120, "Planches adaptées, leashs", ["SUR2", "SUR3"]),
        ("Trajectoires, priorités et choix de vague", "Commencer à orienter la planche et évoluer en respectant les autres pratiquants.", "Regard, appuis, trajectoire droite puis légère prise de direction, règles de priorité.", "Sur vagues adaptées, annoncer son choix de direction et conserver une trajectoire contrôlée.", "Choix de vague pertinent, trajectoire maîtrisée, priorité respectée.", 120, "Planches adaptées, leashs, chasubles si besoin", ["SUR1", "SUR3", "SUR4"]),
        ("Autonomie encadrée et évaluation", "Mobiliser lecture du milieu, rame, take-off, trajectoire et sécurité dans une pratique plus autonome.", "Échauffement autonome, choix de zone, séries de vagues observées et bilan.", "Séquence de pratique encadrée avec grille : sécurité, choix, rame, take-off, trajectoire, priorités.", "Décisions adaptées au milieu, take-off maîtrisé, respect des règles et capacité d'auto-évaluation.", 120, "Planches adaptées, leashs, combinaisons, grille d'évaluation", ["SUR1", "SUR2", "SUR3", "SUR4"]),
    ],
}

DISPLAY = {
    "Natation": "🏊 Natation",
    "Rugby": "🏉 Rugby",
    "Sauvetage": "🛟 SSA / Sauvetage",
    "Pelote Basque": "🥎 Pelote basque",
    "Course à pied": "🏃 Course à pied",
    "Surf": "🏄 Surf",
}


@st.cache_resource
def init_pedagogy():
    execute("""
        CREATE TABLE IF NOT EXISTS pedagogie_seances(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activite TEXT NOT NULL,
            numero INTEGER NOT NULL,
            titre TEXT NOT NULL,
            objectif TEXT,
            contenu TEXT,
            situation TEXT,
            criteres TEXT,
            duree INTEGER DEFAULT 60,
            materiel TEXT,
            UNIQUE(activite, numero)
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS pedagogie_liens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activite TEXT NOT NULL,
            numero INTEGER NOT NULL,
            competence_id INTEGER NOT NULL,
            UNIQUE(activite, numero, competence_id)
        )
    """)

    execute("""
        CREATE TABLE IF NOT EXISTS pedagogie_suppressions(
            activite TEXT NOT NULL,
            numero INTEGER NOT NULL,
            PRIMARY KEY(activite, numero)
        )
    """)
    suppressions = {
        (r["activite"], r["numero"])
        for r in query_rows("SELECT activite, numero FROM pedagogie_suppressions")
    }
    for activite, seances in DEFAULT_CYCLES.items():
        for numero, data in enumerate(seances, start=1):
            if (activite, numero) in suppressions:
                continue
            titre, objectif, contenu, situation, criteres, duree, materiel, codes = data
            execute("""
                INSERT INTO pedagogie_seances(activite,numero,titre,objectif,contenu,situation,criteres,duree,materiel)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(activite,numero) DO NOTHING
            """, (activite, numero, titre, objectif, contenu, situation, criteres, duree, materiel))
            if codes:
                placeholders = ",".join(["?"] * len(codes))
                comps = query_rows(
                    f"SELECT id, code FROM competences WHERE activite=? AND code IN ({placeholders})",
                    (activite, *codes)
                )
                for comp in comps:
                    execute("""
                        INSERT INTO pedagogie_liens(activite,numero,competence_id)
                        VALUES(?,?,?)
                        ON CONFLICT(activite,numero,competence_id) DO NOTHING
                    """, (activite, numero, comp["id"]))
    return True


init_pedagogy()

st.title("📚 Pédagogie SUAPS")
st.caption("Progressions prêtes à l'emploi, modifiables par l'enseignant et reliées aux compétences et aux évaluations.")
st.info("🛟 SSA et 🏄 Surf : les contenus sont des trames pédagogiques à adapter au référentiel en vigueur, aux conditions du milieu, au matériel et au protocole de sécurité de l'établissement.")

activite = st.selectbox("Choisir l'activité", list(DEFAULT_CYCLES.keys()), format_func=lambda x: DISPLAY[x])

deleted_rows = query_rows(
    "SELECT numero FROM pedagogie_suppressions WHERE activite=? ORDER BY numero",
    (activite,)
)
deleted_numbers = [int(r["numero"]) for r in deleted_rows]

if deleted_numbers:
    with st.expander(f"🗑️ Séances supprimées ({len(deleted_numbers)})"):
        restore_num = st.selectbox(
            "Séance à restaurer",
            deleted_numbers,
            format_func=lambda n: f"Séance {n}",
            key=f"restore_deleted_{activite}"
        )
        if st.button(
            "↩️ Restaurer cette séance",
            use_container_width=True,
            key=f"restore_deleted_btn_{activite}"
        ):
            execute(
                "DELETE FROM pedagogie_suppressions WHERE activite=? AND numero=?",
                (activite, restore_num)
            )
            st.success(f"Séance {restore_num} restaurée.")
            st.rerun()

all_sessions = query_rows(
    "SELECT numero, titre FROM pedagogie_seances WHERE activite=? ORDER BY numero",
    (activite,)
)
available_sessions = [r for r in all_sessions if int(r["numero"]) not in deleted_numbers]
nb_seances = len(available_sessions)

if not available_sessions:
    st.warning("Toutes les séances de cette activité ont été supprimées. Tu peux en restaurer une dans la rubrique ci-dessus.")
    st.stop()

session_numbers = [int(r["numero"]) for r in available_sessions]
session_titles = {int(r["numero"]): r["titre"] for r in available_sessions}
numero = st.selectbox(
    "Séance",
    session_numbers,
    format_func=lambda n: f"Séance {n} — {session_titles[n]}"
)
session_position = session_numbers.index(numero) + 1

rows = query_rows("SELECT * FROM pedagogie_seances WHERE activite=? AND numero=?", (activite, numero))
if not rows:
    st.error("Séance introuvable.")
    st.stop()
s = rows[0]

competences = query_rows("SELECT id, code, libelle FROM competences WHERE activite=? ORDER BY code", (activite,))
liens = query_rows("SELECT competence_id FROM pedagogie_liens WHERE activite=? AND numero=?", (activite, numero))
linked_ids = {r["competence_id"] for r in liens}
linked = [c for c in competences if c["id"] in linked_ids]

c1, c2, c3 = st.columns(3)
c1.metric("Progression", f"{session_position}/{nb_seances}")
c2.metric("Durée indicative", f"{s['duree']} min")
c3.metric("Compétences liées", len(linked))

fiche_tab, edit_tab, eval_tab = st.tabs(["📋 Fiche séance", "✏️ Modifier", "✅ Évaluer le groupe"])

with fiche_tab:
    st.subheader(f"Séance {numero} — {s['titre']}")
    left, right = st.columns(2)
    with left:
        st.markdown("### 🎯 Objectif")
        st.write(s["objectif"] or "—")
        st.markdown("### 🧩 Contenus")
        st.write(s["contenu"] or "—")
        st.markdown("### 🎒 Matériel")
        st.write(s["materiel"] or "—")
    with right:
        st.markdown("### 🏃 Situation principale")
        st.write(s["situation"] or "—")
        st.markdown("### ✅ Critères de réussite")
        st.write(s["criteres"] or "—")
        st.markdown("### 🧠 Compétences associées")
        if linked:
            for comp in linked:
                st.write(f"**{comp['code']}** — {comp['libelle']}")
        else:
            st.caption("Aucune compétence liée pour le moment.")

    st.divider()
    st.markdown("### Vue d'ensemble du cycle")
    cycle_rows = [item for item in query_rows("SELECT * FROM pedagogie_seances WHERE activite=? ORDER BY numero", (activite,)) if int(item["numero"]) not in deleted_numbers]
    for item in cycle_rows:
        with st.expander(f"Séance {item['numero']} — {item['titre']}", expanded=(item["numero"] == numero)):
            st.markdown(f"**Objectif :** {item['objectif']}")
            st.markdown(f"**Situation :** {item['situation']}")
            st.markdown(f"**Durée :** {item['duree']} min")
            st.markdown(f"**Matériel :** {item['materiel'] or '—'}")

with edit_tab:
    st.caption("Les changements sont enregistrés dans la même base de données que le reste de l'application.")
    comp_options = {c["id"]: f"{c['code']} — {c['libelle']}" for c in competences}
    with st.form(f"edit_session_{activite}_{numero}"):
        titre = st.text_input("Titre", value=s["titre"] or "")
        objectif = st.text_area("Objectif", value=s["objectif"] or "")
        contenu = st.text_area("Contenus", value=s["contenu"] or "")
        situation = st.text_area("Situation principale", value=s["situation"] or "")
        criteres = st.text_area("Critères de réussite", value=s["criteres"] or "")
        cc1, cc2 = st.columns(2)
        duree = cc1.number_input("Durée indicative (min)", min_value=15, max_value=240, step=5, value=int(s["duree"] or 60))
        materiel = cc2.text_area("Matériel", value=s["materiel"] or "")
        selected_comps = st.multiselect(
            "Compétences liées",
            options=list(comp_options.keys()),
            default=[x for x in comp_options if x in linked_ids],
            format_func=lambda x: comp_options[x]
        )
        save = st.form_submit_button("💾 Enregistrer les modifications", type="primary", use_container_width=True)
        if save:
            execute("""
                UPDATE pedagogie_seances
                SET titre=?, objectif=?, contenu=?, situation=?, criteres=?, duree=?, materiel=?
                WHERE activite=? AND numero=?
            """, (titre.strip(), objectif.strip(), contenu.strip(), situation.strip(), criteres.strip(), int(duree), materiel.strip(), activite, numero))
            execute("DELETE FROM pedagogie_liens WHERE activite=? AND numero=?", (activite, numero))
            for cid in selected_comps:
                execute("""
                    INSERT INTO pedagogie_liens(activite,numero,competence_id)
                    VALUES(?,?,?)
                    ON CONFLICT(activite,numero,competence_id) DO NOTHING
                """, (activite, numero, cid))
            st.success("Séance mise à jour.")
            st.rerun()

    st.divider()
    delete_state_key = f"confirm_delete_ped_{activite}_{numero}"
    if st.button(
        "🗑️ Supprimer cette séance",
        use_container_width=True,
        key=f"delete_ped_{activite}_{numero}"
    ):
        st.session_state[delete_state_key] = True

    if st.session_state.get(delete_state_key):
        st.warning(
            f"Confirmer la suppression de la séance {numero} — {s['titre']} ? "
            "Les notes et évaluations déjà enregistrées seront conservées."
        )
        dc1, dc2 = st.columns(2)
        if dc1.button(
            "Oui, supprimer",
            type="primary",
            use_container_width=True,
            key=f"confirm_delete_yes_{activite}_{numero}"
        ):
            execute(
                "INSERT INTO pedagogie_suppressions(activite,numero) VALUES(?,?) "
                "ON CONFLICT(activite,numero) DO NOTHING",
                (activite, numero)
            )
            st.session_state.pop(delete_state_key, None)
            st.success("Séance supprimée.")
            st.rerun()
        if dc2.button(
            "Annuler",
            use_container_width=True,
            key=f"confirm_delete_no_{activite}_{numero}"
        ):
            st.session_state.pop(delete_state_key, None)
            st.rerun()

    if st.button("↩️ Restaurer cette séance à la version proposée", use_container_width=True):
        d = DEFAULT_CYCLES[activite][numero - 1]
        titre0, objectif0, contenu0, situation0, criteres0, duree0, materiel0, codes0 = d
        execute("""
            UPDATE pedagogie_seances
            SET titre=?, objectif=?, contenu=?, situation=?, criteres=?, duree=?, materiel=?
            WHERE activite=? AND numero=?
        """, (titre0, objectif0, contenu0, situation0, criteres0, duree0, materiel0, activite, numero))
        execute("DELETE FROM pedagogie_liens WHERE activite=? AND numero=?", (activite, numero))
        if codes0:
            placeholders = ",".join(["?"] * len(codes0))
            comps0 = query_rows(f"SELECT id FROM competences WHERE activite=? AND code IN ({placeholders})", (activite, *codes0))
            for comp in comps0:
                execute("INSERT INTO pedagogie_liens(activite,numero,competence_id) VALUES(?,?,?) ON CONFLICT(activite,numero,competence_id) DO NOTHING", (activite, numero, comp["id"]))
        st.success("Version proposée restaurée.")
        st.rerun()

with eval_tab:
    groupes = query_rows("SELECT DISTINCT groupe FROM etudiants WHERE actif=1 AND groupe IS NOT NULL AND groupe<>'' ORDER BY groupe")
    if not groupes:
        st.info("Aucun groupe étudiant n'est encore défini.")
    else:
        groupe = st.selectbox("Groupe", [g["groupe"] for g in groupes], key=f"ped_group_{activite}_{numero}")
        etudiants = query_rows("SELECT id, nom, prenom FROM etudiants WHERE actif=1 AND groupe=? ORDER BY nom, prenom", (groupe,))
        if not etudiants:
            st.info("Aucun étudiant dans ce groupe.")
        else:
            linked_options = {c["id"]: f"{c['code']} — {c['libelle']}" for c in linked}
            with st.form(f"group_eval_{activite}_{numero}_{groupe}"):
                ec1, ec2, ec3 = st.columns(3)
                intitule = ec1.text_input("Intitulé", value=f"Séance {numero} — {s['titre']}")
                bareme = ec2.number_input("Barème", min_value=1.0, value=20.0, step=1.0)
                coefficient = ec3.number_input("Coefficient", min_value=0.1, value=1.0, step=0.1)
                date_eval = st.date_input("Date", value=date.today())
                comps_to_validate = st.multiselect(
                    "Compétence(s) à valider avec cette évaluation",
                    options=list(linked_options.keys()),
                    format_func=lambda x: linked_options[x]
                ) if linked_options else []

                st.markdown("#### Saisie rapide")
                saisies = []
                for e in etudiants:
                    st.markdown(f"**{e['nom']} {e['prenom']}**")
                    a, b, c, d = st.columns([1, 1.2, 2, 3])
                    actif = a.checkbox("Évaluer", value=True, key=f"do_{activite}_{numero}_{e['id']}")
                    note = b.number_input("Note", min_value=0.0, max_value=float(bareme), value=0.0, step=0.25, key=f"note_{activite}_{numero}_{e['id']}")
                    niveau = c.selectbox("Niveau", ["Non évalué", "En cours d’acquisition", "Acquis", "Maîtrisé"], key=f"niv_{activite}_{numero}_{e['id']}")
                    commentaire = d.text_input("Commentaire", key=f"com_{activite}_{numero}_{e['id']}")
                    saisies.append((e["id"], actif, note, niveau, commentaire))

                save_eval = st.form_submit_button("✅ Enregistrer l'évaluation du groupe", type="primary", use_container_width=True)
                if save_eval:
                    count = 0
                    for eid, actif_e, note_e, niveau_e, commentaire_e in saisies:
                        if not actif_e:
                            continue
                        execute("""
                            INSERT INTO evaluations(etudiant_id,activite,intitule,date_eval,note,bareme,coefficient,commentaire)
                            VALUES(?,?,?,?,?,?,?,?)
                        """, (eid, activite, intitule.strip(), str(date_eval), note_e, bareme, coefficient, commentaire_e.strip()))
                        for cid in comps_to_validate:
                            dval = str(date_eval) if niveau_e in ["Acquis", "Maîtrisé"] else None
                            execute("""
                                INSERT INTO acquisitions(etudiant_id,competence_id,niveau,date_validation,commentaire)
                                VALUES(?,?,?,?,?)
                                ON CONFLICT(etudiant_id,competence_id)
                                DO UPDATE SET niveau=excluded.niveau, date_validation=excluded.date_validation, commentaire=excluded.commentaire
                            """, (eid, cid, niveau_e, dval, f"Pédagogie — {intitule.strip()}"))
                        count += 1
                    st.success(f"Évaluation enregistrée pour {count} étudiant(s). Elle apparaît aussi dans le cahier de notes.")

st.caption("Pédagogie V2 — Natation 10 • Rugby 10 • SSA/Sauvetage 10 • Pelote basque 10 • Course à pied 10 • Surf 5.")
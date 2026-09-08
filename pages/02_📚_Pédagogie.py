import streamlit as st

st.set_page_config(page_title="Pédagogie SUAPS", page_icon="📚", layout="wide")

# Cette page est destinée à l'espace enseignant de l'application.
if st.session_state.get("role") != "Enseignant":
    st.warning("🔒 La partie Pédagogie est réservée au mode Enseignant. Ouvre d'abord l'application principale puis passe en mode Enseignant.")
    st.stop()

st.title("📚 Pédagogie")
st.caption("Cycles prêts à l'emploi sur 10 séances — objectifs, contenus, situations et critères de réussite.")

CYCLES = {
    "🏊 Natation": [
        {
            "titre": "Diagnostic et aisance aquatique",
            "objectif": "Évaluer le niveau initial et installer confiance, respiration et équilibre.",
            "contenu": "Échauffement libre ; entrées dans l'eau ; immersions ; coulées ; 25 m nage au choix ; petit parcours diagnostic.",
            "situation": "Parcours 4 ateliers : immersion complète, étoile ventrale/dorsale, coulée, 25 m continu.",
            "criteres": "Respiration maîtrisée ; corps relâché ; déplacement continu ; règles de sécurité respectées."
        },
        {
            "titre": "Respiration et équilibre",
            "objectif": "Coordonner expiration aquatique, inspiration et position horizontale.",
            "contenu": "Bulles, glissées ventrales/dorsales, battements avec matériel, alternance respiration latérale.",
            "situation": "6 × 25 m : 12,5 m battements + 12,5 m nage complète, récupération courte.",
            "criteres": "Expiration continue ; tête stable ; bassin proche de la surface ; rythme régulier."
        },
        {
            "titre": "Propulsion crawl",
            "objectif": "Améliorer l'efficacité des appuis et la continuité du crawl.",
            "contenu": "Rattrapé, un bras, poings fermés, nage complète ; travail d'amplitude.",
            "situation": "8 × 25 m crawl avec contrainte technique différente à chaque répétition.",
            "criteres": "Appui orienté vers l'arrière ; trajet moteur continu ; respiration sans rupture de nage."
        },
        {
            "titre": "Dos crawlé et repères dorsaux",
            "objectif": "Construire une nage dorsale équilibrée et propulsive.",
            "contenu": "Battements dos, rotation des épaules, bras alternés, repérage de la ligne d'eau.",
            "situation": "4 × 50 m dos avec objectif de régularité et nombre de coups de bras stabilisé.",
            "criteres": "Bassin haut ; battements continus ; entrée de main alignée ; trajectoire rectiligne."
        },
        {
            "titre": "Brasse : coordination",
            "objectif": "Coordonner traction, respiration, jambes et glisse.",
            "contenu": "Jambes de brasse, bras seuls, 2 jambes/1 bras puis nage complète.",
            "situation": "6 × 25 m en cherchant une phase de glisse identifiable après chaque cycle.",
            "criteres": "Symétrie ; talons ramenés ; poussée efficace ; respiration coordonnée."
        },
        {
            "titre": "Virages et reprises de nage",
            "objectif": "Réduire les ruptures de vitesse au mur.",
            "contenu": "Approche du mur, demi-tour simple, culbute selon niveau, poussée et coulée.",
            "situation": "10 passages chronométrés sur 5 m avant + virage + 5 m après.",
            "criteres": "Approche sans hésitation ; poussée tonique ; reprise de nage rapide et équilibrée."
        },
        {
            "titre": "Endurance et gestion d'allure",
            "objectif": "Nager plus longtemps à une allure adaptée.",
            "contenu": "Séries de 50 à 100 m ; repères respiratoires ; comparaison temps/perception d'effort.",
            "situation": "3 × 200 m à allure régulière avec objectif de faible écart entre les temps.",
            "criteres": "Allure stable ; technique conservée ; récupération maîtrisée ; effort perçu cohérent."
        },
        {
            "titre": "Vitesse et fréquence gestuelle",
            "objectif": "Produire une accélération efficace sans dégrader fortement la technique.",
            "contenu": "Départs, 15 m rapides, 25 m sprint, récupération complète.",
            "situation": "6 × 25 m vite avec comparaison temps, fréquence et qualité technique.",
            "criteres": "Accélération nette ; maintien de l'alignement ; respiration adaptée à l'intensité."
        },
        {
            "titre": "Parcours combiné et autonomie",
            "objectif": "Mobiliser plusieurs nages et compétences dans un parcours continu.",
            "contenu": "Crawl, dos, brasse, virages, coulées et changements d'allure.",
            "situation": "Parcours 300 à 500 m adapté au niveau avec consignes techniques successives.",
            "criteres": "Enchaînement sans arrêt ; consignes respectées ; gestion de l'effort ; autonomie."
        },
        {
            "titre": "Évaluation et bilan de cycle",
            "objectif": "Mesurer les progrès techniques et énergétiques du cycle.",
            "contenu": "Test continu, épreuve chronométrée courte et observation technique.",
            "situation": "Évaluation choisie par l'enseignant : distance continue + 50/100 m + grille technique.",
            "criteres": "Progression mesurable ; nage efficiente ; sécurité ; capacité à analyser sa prestation."
        },
    ],

    "🏉 Rugby": [
        {
            "titre": "Diagnostic, sécurité et principes du jeu",
            "objectif": "Évaluer le niveau et installer les règles essentielles de sécurité et de continuité.",
            "contenu": "Échauffement ballon ; passes en mouvement ; jeu réduit sans contact ; repères avant/arrière.",
            "situation": "4 contre 4, terrain étroit, marque par essai, obligation de deux passes minimum.",
            "criteres": "Ballon vivant ; soutien proche ; passes vers l'arrière ; communication."
        },
        {
            "titre": "Passe et prise d'information",
            "objectif": "Passer efficacement en mouvement en regardant défense et partenaires.",
            "contenu": "2 contre 1, 3 contre 2, passes avant contact, variations de largeur.",
            "situation": "Vagues offensives successives avec surnombre.",
            "criteres": "Course droite ; fixation du défenseur ; passe au bon moment ; réception en avançant."
        },
        {
            "titre": "Soutien et continuité",
            "objectif": "Se replacer rapidement pour assurer la continuité après la passe ou le contact simulé.",
            "contenu": "Soutien axial/latéral, jeu après toucher, relais offensifs.",
            "situation": "Jeu au toucher : 3 secondes maximum pour libérer le ballon après le toucher.",
            "criteres": "Soutien disponible ; profondeur adaptée ; conservation de l'avancée."
        },
        {
            "titre": "Défense individuelle et montée collective",
            "objectif": "Construire une défense organisée, alignée et communicante.",
            "contenu": "Placement, montée, cadrage, fermeture des espaces ; contact adapté au niveau.",
            "situation": "4 attaquants contre 4 défenseurs avec lancement imposé.",
            "criteres": "Ligne défensive cohérente ; montée ensemble ; communication ; sécurité."
        },
        {
            "titre": "Plaquage sécurisé / alternative au toucher",
            "objectif": "Apprendre les principes d'un contact sécurisé lorsque le niveau et le cadre le permettent.",
            "contenu": "Postures, placement de la tête, ceinturage, chute contrôlée, progression très graduée.",
            "situation": "Ateliers à vitesse réduite puis situations 1 contre 1 encadrées ; variante toucher si nécessaire.",
            "criteres": "Posture stable ; tête placée en sécurité ; contrôle de l'adversaire ; arrêt immédiat au signal."
        },
        {
            "titre": "Ruck, libération et replacement",
            "objectif": "Comprendre la logique de conservation après contact et le replacement offensif.",
            "contenu": "Libération au sol, arrivée du soutien, sortie rapide du ballon, replacement.",
            "situation": "3 contre 2 + soutien avec zone de libération matérialisée.",
            "criteres": "Ballon libéré vite ; soutien dans l'axe ; joueur au sol protégé ; continuité."
        },
        {
            "titre": "Occupation de l'espace",
            "objectif": "Écarter, fixer et jouer dans les intervalles.",
            "contenu": "Largeur, profondeur, courses de leurre, changements de sens.",
            "situation": "5 contre 5 avec couloirs bonus pour valoriser l'utilisation de toute la largeur.",
            "criteres": "Espaces occupés ; porteur entouré de solutions ; défense déplacée avant attaque de l'intervalle."
        },
        {
            "titre": "Jeu au pied et transition",
            "objectif": "Découvrir l'utilisation tactique du jeu au pied et la réaction collective.",
            "contenu": "Coup de pied rasant, haut ou de déplacement selon niveau ; poursuite et replacement.",
            "situation": "Jeu réduit avec bonus si le jeu au pied crée un gain territorial ou une récupération.",
            "criteres": "Choix pertinent ; poursuite organisée ; couverture défensive ; sécurité."
        },
        {
            "titre": "Projet collectif",
            "objectif": "Mettre en place une organisation simple offensive et défensive.",
            "contenu": "Lancements de jeu, annonces, rôles, adaptation à l'adversaire.",
            "situation": "Matchs courts avec temps mort tactique et objectif collectif choisi par l'équipe.",
            "criteres": "Projet identifiable ; communication ; adaptation ; continuité du jeu."
        },
        {
            "titre": "Évaluation en match",
            "objectif": "Évaluer la contribution individuelle au projet collectif.",
            "contenu": "Matchs aménagés ; observation des compétences techniques, tactiques et sécuritaires.",
            "situation": "Tournoi final avec grille : avancer, faire avancer, soutenir, défendre, respecter les règles.",
            "criteres": "Décisions pertinentes ; engagement maîtrisé ; efficacité collective ; respect et sécurité."
        },
    ],

    "🛟 SSA / Sauvetage": [
        {
            "titre": "Diagnostic aquatique et sécurité",
            "objectif": "Évaluer les capacités aquatiques et installer les règles de sécurité du cycle SSA.",
            "contenu": "Nage continue, immersion, apnée courte, récupération d'objet, remorquage léger.",
            "situation": "Parcours diagnostic combinant nage, immersion et retour vers une zone sécurisée.",
            "criteres": "Aisance ; lucidité ; respect des consignes ; capacité à interrompre l'action si nécessaire."
        },
        {
            "titre": "Surveillance et détection",
            "objectif": "Observer une zone de baignade et repérer rapidement un comportement inhabituel.",
            "contenu": "Balayage visuel, zones de surveillance, indices de difficulté, communication entre surveillants.",
            "situation": "Scénarios d'observation avec nageurs aux comportements différenciés.",
            "criteres": "Détection rapide ; information pertinente ; maintien d'une surveillance globale."
        },
        {
            "titre": "Entrées dans l'eau et approche",
            "objectif": "Choisir une entrée et une nage d'approche adaptées à la situation.",
            "contenu": "Entrées contrôlées, nage tête haute, approche avec matériel selon équipement disponible.",
            "situation": "Départs variés vers une victime simulée placée à différentes distances.",
            "criteres": "Entrée sûre ; contact visuel maintenu ; approche rapide et maîtrisée."
        },
        {
            "titre": "Immersion et recherche",
            "objectif": "Améliorer l'efficacité d'une recherche subaquatique courte et sécurisée.",
            "contenu": "Canard, immersion, récupération de mannequin/objet, remontée contrôlée.",
            "situation": "Recherche d'un objet immergé avec zone et profondeur adaptées au groupe.",
            "criteres": "Immersion efficace ; trajet court ; récupération contrôlée ; remontée sans précipitation."
        },
        {
            "titre": "Prises et remorquages",
            "objectif": "Transporter une victime simulée en maintenant une position de sécurité.",
            "contenu": "Rétropédalage, prises de remorquage, adaptation à la distance et au matériel.",
            "situation": "4 × 25 m de remorquage avec variantes de prise.",
            "criteres": "Voies aériennes dégagées ; propulsion continue ; prise stable ; économie d'effort."
        },
        {
            "titre": "Sortie d'eau et transmission",
            "objectif": "Organiser la fin de l'intervention et la transmission d'informations.",
            "contenu": "Approche du bord, aide à la sortie selon contexte, alerte et bilan transmis à l'équipe.",
            "situation": "Scénario complet depuis la détection jusqu'à la prise en charge sur la zone sécurisée.",
            "criteres": "Enchaînement ordonné ; sécurité du sauveteur ; message clair ; coopération."
        },
        {
            "titre": "Matériel de sauvetage",
            "objectif": "Utiliser à bon escient le matériel disponible dans l'établissement.",
            "contenu": "Bouée tube, perche, corde ou autre matériel local ; choix selon distance et victime.",
            "situation": "Ateliers tournants : atteindre, sécuriser, ramener une victime simulée avec différents matériels.",
            "criteres": "Choix adapté ; matériel maîtrisé ; distance de sécurité pertinente ; communication."
        },
        {
            "titre": "Scénarios d'intervention",
            "objectif": "Prendre des décisions rapides dans des situations variées.",
            "contenu": "Victime consciente/inconsciente simulée, plusieurs zones, coordination à deux sauveteurs.",
            "situation": "Scénarios surprise avec observateur et débriefing immédiat.",
            "criteres": "Priorités cohérentes ; sécurité ; efficacité ; communication ; retour d'expérience."
        },
        {
            "titre": "Parcours SSA complet",
            "objectif": "Enchaîner nage, recherche, prise, remorquage et sortie dans un effort continu.",
            "contenu": "Parcours combiné adapté au niveau et au référentiel retenu par l'enseignant.",
            "situation": "Parcours chronométré ou critérié avec pénalités techniques plutôt qu'une logique de vitesse seule.",
            "criteres": "Continuité ; maîtrise technique ; sécurité ; gestion de l'effort ; décisions pertinentes."
        },
        {
            "titre": "Évaluation et mise en situation finale",
            "objectif": "Valider les acquis du cycle dans une situation globale de surveillance et sauvetage.",
            "contenu": "Observation, déclenchement de l'action, intervention aquatique, transmission et débriefing.",
            "situation": "Mise en situation finale avec grille d'évaluation individualisée.",
            "criteres": "Détection ; choix d'intervention ; maîtrise aquatique ; sécurité ; communication ; analyse réflexive."
        },
    ],

    "🥎 Pelote basque": [
        {
            "titre": "Diagnostic et prise en main",
            "objectif": "Découvrir l'activité, les règles de sécurité et évaluer les habiletés initiales.",
            "contenu": "Manipulations, jonglages, frappes simples, échanges près du mur, règles de base.",
            "situation": "Défis de 10 frappes consécutives à distance adaptée.",
            "criteres": "Contact régulier ; trajectoire contrôlée ; placement sécurisé ; respect des zones."
        },
        {
            "titre": "Frappe coup droit",
            "objectif": "Construire une frappe régulière et orientée.",
            "contenu": "Placement, armé, transfert, accompagnement ; cible au fronton.",
            "situation": "5 séries de 8 frappes vers trois zones-cibles.",
            "criteres": "Appuis stables ; frappe devant soi ; cible atteinte régulièrement."
        },
        {
            "titre": "Revers et adaptation de placement",
            "objectif": "Élargir les possibilités de frappe et ajuster les déplacements.",
            "contenu": "Déplacement latéral, orientation du corps, frappe revers, retour en position.",
            "situation": "Alternance coup droit/revers sur balles envoyées dans deux couloirs.",
            "criteres": "Placement précoce ; équilibre ; trajectoire maîtrisée ; retour disponible."
        },
        {
            "titre": "Lecture de trajectoire",
            "objectif": "Anticiper rebond, vitesse et profondeur.",
            "contenu": "Balles courtes/longues, variations de hauteur, déplacement avant/arrière.",
            "situation": "Partenaire lanceur : annoncer zone de frappe avant le rebond puis jouer la balle.",
            "criteres": "Anticipation ; ajustement des appuis ; frappe à distance optimale."
        },
        {
            "titre": "Continuité de l'échange",
            "objectif": "Maintenir un échange en privilégiant régularité et replacement.",
            "contenu": "Échanges coopératifs, cible large, augmentation progressive de la distance.",
            "situation": "Contrat collectif : atteindre 20 échanges sans faute.",
            "criteres": "Régularité ; replacement ; communication ; choix de frappe sécurisé."
        },
        {
            "titre": "Précision et zones de jeu",
            "objectif": "Orienter volontairement la balle pour déplacer l'adversaire.",
            "contenu": "Zones droite/gauche, court/long, objectifs de précision.",
            "situation": "Points bonus quand la balle atteint une zone annoncée avant la frappe.",
            "criteres": "Intention identifiable ; trajectoire choisie ; précision croissante."
        },
        {
            "titre": "Construction du point",
            "objectif": "Passer d'un jeu de renvoi à une logique tactique.",
            "contenu": "Fixer, déplacer, changer de rythme, jouer dans l'espace libre.",
            "situation": "Match à thème : point doublé si l'adversaire est déplacé avant le coup gagnant.",
            "criteres": "Enchaînement tactique cohérent ; patience ; exploitation de l'espace."
        },
        {
            "titre": "Service / engagement et première intention",
            "objectif": "Maîtriser la mise en jeu et préparer le coup suivant.",
            "contenu": "Régularité de l'engagement, zones, enchaînement service + replacement.",
            "situation": "10 services dans zones cibles puis mini-matchs où le serveur annonce son intention.",
            "criteres": "Service valide ; précision ; replacement immédiat ; projet simple."
        },
        {
            "titre": "Matchs à thème et stratégie",
            "objectif": "Adapter son projet de jeu au profil de l'adversaire.",
            "contenu": "Observation, choix de zones, gestion du risque, score aménagé.",
            "situation": "Matchs courts avec fiche d'observation par binôme.",
            "criteres": "Projet de jeu visible ; adaptation ; régularité ; respect des règles."
        },
        {
            "titre": "Évaluation et tournoi final",
            "objectif": "Évaluer technique, tactique, engagement et respect du cadre de pratique.",
            "contenu": "Tournoi, observation croisée, bilan individuel et objectifs de poursuite.",
            "situation": "Poules puis classement adapté ; grille technique/tactique/comportementale.",
            "criteres": "Frappe maîtrisée ; déplacement efficace ; construction du point ; autonomie et fair-play."
        },
    ],
}

# Avertissement utile pour le sauvetage : la page constitue une trame pédagogique,
# et non un remplacement des référentiels officiels, protocoles de sécurité ou formations certifiantes.
st.info("🛟 Pour le SSA/Sauvetage, la progression est une trame pédagogique à adapter au référentiel en vigueur, au matériel disponible et au protocole de sécurité de l'établissement.")

activite = st.selectbox("Choisir l'activité", list(CYCLES.keys()))
seances = CYCLES[activite]

c1, c2 = st.columns([1, 2])
with c1:
    numero = st.selectbox("Séance", range(1, 11), format_func=lambda n: f"Séance {n}")
with c2:
    st.metric("Progression", f"{numero}/10")

s = seances[numero - 1]
st.subheader(f"Séance {numero} — {s['titre']}")

col1, col2 = st.columns(2)
with col1:
    st.markdown("### 🎯 Objectif")
    st.write(s["objectif"])
    st.markdown("### 🧩 Contenus")
    st.write(s["contenu"])
with col2:
    st.markdown("### 🏃 Situation principale")
    st.write(s["situation"])
    st.markdown("### ✅ Critères de réussite")
    st.write(s["criteres"])

st.divider()
st.markdown("### Vue d'ensemble du cycle")
for i, item in enumerate(seances, start=1):
    with st.expander(f"Séance {i} — {item['titre']}", expanded=(i == numero)):
        st.markdown(f"**Objectif :** {item['objectif']}")
        st.markdown(f"**Contenus :** {item['contenu']}")
        st.markdown(f"**Situation :** {item['situation']}")
        st.markdown(f"**Critères :** {item['criteres']}")

st.caption("Version 1 — les contenus peuvent ensuite être rendus modifiables par chaque enseignant et reliés aux compétences/évaluations de l'application.")

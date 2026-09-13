"""Fonds officiel de 55 séances pédagogiques SUAPS UPPA."""
from __future__ import annotations

from pedagogie_resources import create_resource


def _session(slug, activity, number, title, objective, competences, material,
             warmup, situations, variables, criteria, safety, bilan):
    return {
        "seed_key": f"suaps:{slug}:{number:02d}",
        "activite": activity,
        "numero": number,
        "titre": title,
        "objectif": objective,
        "competences": list(competences),
        "materiel": list(material),
        "echauffement": warmup,
        "situations": list(situations),
        "variables": list(variables),
        "criteres_reussite": list(criteria),
        "securite": list(safety),
        "retour_bilan": bilan,
    }


S = []

NAT_MAT = ["Planches", "Frites", "Pull-buoys", "Plots de bord"]
NAT_SAFE = ["Respecter le sens de circulation et les départs espacés", "Ne jamais plonger sans zone libre et profondeur autorisée"]
S += [
_session("natation", "Natation", 1, "Diagnostic et aisance aquatique", "Situer le niveau initial et installer les règles de sécurité.",
         ["Entrer dans l’eau en sécurité", "S’immerger et se déplacer sans appréhension"], NAT_MAT,
         "200 m libres progressifs, puis 4 immersions complètes et 4 coulées courtes.",
         ["Parcours 25 m avec entrée, immersion, déplacement ventral et dorsal", "Nager 6 minutes à allure confortable pour observer continuité et respiration", "Test de coulée : pousser, s’aligner et repérer la distance parcourue"],
         ["Utiliser une frite pour les nageurs peu à l’aise", "Allonger le parcours à 50 m pour les plus autonomes"],
         ["Réaliser le parcours sans arrêt paniqué", "Identifier une priorité personnelle de progrès en fin de séance"], NAT_SAFE,
         "Chaque nageur formule un point fort et un axe de travail; l’enseignant constitue les groupes de besoin."),
_session("natation", "Natation", 2, "Respiration et équilibre", "Expirer dans l’eau et stabiliser un corps aligné.",
         ["Expirer de façon continue sous l’eau", "Maintenir un alignement tête-tronc-jambes"], NAT_MAT,
         "8 x 25 m souples en alternant nage ventrale et dorsale, récupération 15 s.",
         ["Bulles longues : inspiration hors eau, expiration complète visage immergé", "Flèche ventrale puis dorsale avec recherche d’alignement", "6 x 25 m crawl avec respiration tous les 3 temps sans accélérer"],
         ["Passer d’une respiration 2 temps à 3 temps", "Ajouter 6 battements en flèche avant la reprise de nage"],
         ["Expiration continue visible sous l’eau", "Conserver bassin proche de la surface sur la majorité de la longueur"], NAT_SAFE,
         "Comparer la sensation de glisse avant/après correction de la position de tête."),
_session("natation", "Natation", 3, "Propulsion et coulée", "Produire une propulsion efficace et conserver la glisse.",
         ["Orienter les surfaces propulsives vers l’arrière", "Conserver la vitesse gagnée après poussée"], NAT_MAT,
         "4 x 50 m faciles en comptant les coups de bras sur le deuxième 25 m.",
         ["Coulées murales avec repères à 5 m puis 7 m", "Traction crawl un bras avec planche dans la main opposée", "8 x 25 m en cherchant moins de coups de bras à vitesse identique"],
         ["Avec ou sans pull-buoy", "Imposer un nombre maximal de coups de bras par 25 m"],
         ["Dépasser le repère de 5 m en coulée sans mouvement parasite", "Réduire d’au moins 2 coups de bras sans ralentissement marqué"], NAT_SAFE,
         "Noter le nombre de coups de bras le plus efficace et expliquer ce qui a amélioré la propulsion."),
_session("natation", "Natation", 4, "Crawl : coordination complète", "Coordonner respiration, bras et battements.",
         ["Synchroniser rotation du corps et respiration", "Maintenir une propulsion continue des bras"], NAT_MAT,
         "300 m progressifs dont 4 x 25 m crawl rattrapé.",
         ["6 x 25 m crawl un bras en respirant du côté du bras actif", "4 x 50 m crawl complet : 25 m technique + 25 m nage normale", "Relais technique où la qualité de coordination prime sur la vitesse"],
         ["Respiration 2, 3 ou 4 temps selon niveau", "Utiliser des palmes courtes pour libérer l’attention sur les bras"],
         ["Tourner la tête sans la relever", "Conserver un rythme de bras régulier malgré la respiration"], NAT_SAFE,
         "Filmer ou observer un binôme sur 15 m et donner un seul conseil technique prioritaire."),
_session("natation", "Natation", 5, "Dos crawlé", "Se déplacer efficacement sur le dos avec repères stables.",
         ["Maintenir bassin haut et tête fixe", "Coordonner rotation d’épaules et battements continus"], NAT_MAT,
         "4 x 25 m battements dos, bras le long du corps, puis 4 x 25 m dos complet souple.",
         ["Dos avec gobelet imaginaire sur le front pour stabiliser la tête", "Alternance 6 battements sur le côté / 3 mouvements complets", "6 x 50 m dos en visant une ligne au plafond ou un repère fixe"],
         ["Accentuer la rotation d’épaule", "Réduire les battements pour tester l’équilibre"],
         ["Trajectoire rectiligne sur 25 m", "Main entrant dans l’eau dans l’axe de l’épaule sans croisement"], NAT_SAFE,
         "Comparer le nombre de corrections de trajectoire entre la première et la dernière répétition."),
_session("natation", "Natation", 6, "Endurance continue", "Maintenir une nage économique sur une durée prolongée.",
         ["Choisir une allure soutenable", "Conserver une technique stable sous fatigue"], NAT_MAT,
         "400 m faciles, chaque 100 m légèrement plus rapide.",
         ["3 x 5 min de nage continue avec 1 min de récupération", "Pyramide 100-200-300-200-100 m à allure régulière", "Nage par binôme : le partenaire contrôle régularité et temps de passage"],
         ["Choisir crawl, dos ou alternance", "Réduire la récupération de 60 à 30 s"],
         ["Écart de moins de 5 % entre les temps de passage comparables", "Technique encore maîtrisée sur la dernière minute"], NAT_SAFE,
         "Reporter l’allure moyenne et décider si elle était trop rapide, adaptée ou trop lente."),
_session("natation", "Natation", 7, "Virages et reprises de nage", "Réduire les pertes de vitesse aux changements de longueur.",
         ["Approcher le mur sans rupture de rythme", "Se repousser en position hydrodynamique"], NAT_MAT,
         "8 passages de mur à vitesse progressive, sans faire de longueur complète.",
         ["Virage simple : toucher, grouper, orienter les pieds, pousser", "Culbute à sec puis dans l’eau avec repère à 2 m du mur", "8 x 25 m chronométrés uniquement sur les 5 m avant et après le mur"],
         ["Virage simple ou culbute selon maîtrise", "Ajouter 3 à 5 battements de reprise avant le premier bras"],
         ["Poussée dans l’axe sans dérive latérale", "Reprise de nage avant perte complète de vitesse"], NAT_SAFE,
         "Choisir le type de virage à conserver pour l’évaluation et préciser le repère d’approche utilisé."),
_session("natation", "Natation", 8, "Fréquence, amplitude et efficacité", "Adapter fréquence et amplitude pour nager plus efficacement.",
         ["Mesurer sa fréquence de nage", "Trouver un compromis vitesse / amplitude"], NAT_MAT,
         "6 x 50 m en augmentant progressivement la fréquence sans sprinter.",
         ["25 m en amplitude maximale puis 25 m en fréquence élevée", "4 x 50 m avec objectif de temps identique mais nombre de coups de bras différent", "Duel contre soi-même : améliorer le produit temps x coups de bras"],
         ["Utiliser un tempo sonore si disponible", "Limiter le nombre de coups de bras sur une longueur"],
         ["Identifier son réglage le plus économique", "Rester dans une variation de temps inférieure à 2 s sur les répétitions ciblées"], NAT_SAFE,
         "Chaque nageur retient une consigne personnelle : glisser davantage ou augmenter légèrement la fréquence."),
_session("natation", "Natation", 9, "Parcours combiné", "Enchaîner plusieurs contraintes techniques sans rupture.",
         ["Changer de tâche sans perdre son organisation", "Mobiliser respiration, virage et nage choisie"], NAT_MAT,
         "200 m comprenant 25 m crawl, 25 m dos, 25 m éducatif, 25 m libre, à répéter deux fois.",
         ["Circuit : coulée 5 m + 25 m crawl + virage + 25 m dos", "50 m avec respiration imposée puis 50 m libre optimisé", "Parcours chronométré où une pénalité technique vaut 5 s"],
         ["Augmenter ou réduire la distance totale", "Ajouter une contrainte de nombre de coups de bras"],
         ["Respecter toutes les consignes techniques du parcours", "Finir avec une allure encore contrôlée"], NAT_SAFE,
         "Faire le bilan des deux contraintes les plus coûteuses et définir la stratégie de l’évaluation."),
_session("natation", "Natation", 10, "Évaluation finale", "Mesurer les progrès techniques, énergétiques et méthodologiques.",
         ["Réaliser une performance maîtrisée", "Analyser sa progression à partir d’indicateurs simples"], NAT_MAT,
         "300 m souples avec 4 accélérations de 15 m et répétition du virage choisi.",
         ["Épreuve continue adaptée au niveau avec temps de passage", "Atelier technique noté : coulée, virage et coordination", "Auto-évaluation écrite courte comparant séance 1 et séance 10"],
         ["Distance d’évaluation adaptée au groupe", "Bonus technique pour régularité ou économie gestuelle"],
         ["Amélioration mesurable d’au moins un indicateur initial", "Capacité à justifier son allure et ses choix techniques"], NAT_SAFE,
         "Conserver une trace du résultat et formuler un objectif de poursuite de pratique."),
]

RUG_MAT = ["Ballons de rugby", "Plots", "Chasubles", "Boucliers de contact"]
RUG_SAFE = ["Interdire tout contact non annoncé ou hors zone de travail", "Faire retirer bijoux et objets durs avant les oppositions"]
RUG = [
(1,"Diagnostic et manipulation du ballon","Observer les acquis et sécuriser les manipulations",["Passer et recevoir à deux mains","Se déplacer balle en main sans la perdre"],"Course variée avec ballon : changements de main, passes courtes et ramassages.",["Relais manipulation avec passes avant demi-tour","Carré de passes en mouvement avec changement de sens","Jeu 4 contre 2 sans contact pour observer décisions"],["Réduire la taille du carré","Imposer passe après trois secondes maximum"],["Réussir 8 passes consécutives en mouvement","Conserver le ballon dans 3 attaques sur 4"],"Le groupe fixe les règles de contact autorisées pour la suite du cycle."),
(2,"Passe et réception en mouvement","Faire vivre le ballon sans casser la course",["Passer devant le partenaire","Recevoir en courant vers l’espace libre"],"Par deux, passes en trottinant sur 30 m, main droite puis gauche.",["Vague à 3 avec passe avant une ligne de plots","Passe après fixation d’un défenseur passif","3 contre 1 continu sur couloir large"],["Augmenter la vitesse de course","Réduire l’espace entre porteur et défenseur"],["Réception sans arrêt de course","Ballon transmis avant que le défenseur puisse toucher le porteur"],"Identifier le moment où la passe libère réellement le partenaire."),
(3,"Soutien du porteur","Se rendre disponible avant et après la passe",["Suivre le porteur dans l’axe utile","Recréer une solution après avoir passé"],"Jeu de poursuite en trio : porteur, soutien proche, soutien large.",["2 contre 1 avec obligation de soutien intérieur","3 contre 2 : le passeur doit redevenir disponible","Jeu à toucher où un essai compte double après deux soutiens successifs"],["Limiter le nombre de pas du porteur","Créer une zone interdite obligeant à contourner"],["Toujours au moins une solution de passe proche","Le passeur se replace avant le prochain contact"],"Chaque trio décrit la distance de soutien qui lui a permis de jouer le plus vite."),
(4,"Occuper et utiliser l’espace","Écarter le jeu et attaquer les intervalles",["Se répartir sur la largeur","Courir dans un intervalle plutôt que vers un défenseur"],"Échauffement en lignes de 4 avec conservation des largeurs.",["4 couloirs : conserver un joueur par couloir avant la passe","4 contre 3 avec bonus si l’essai est marqué en bord de zone","Jeu à toucher avec arrêt image sur l’occupation de l’espace"],["Élargir ou resserrer le terrain","Autoriser une passe sautée pour les avancés"],["Largeur occupée avant le lancement","Au moins une attaque crée un franchissement sans duel direct"],"Dessiner rapidement l’occupation idéale vue du dessus."),
(5,"Surnombre : 2 contre 1 et 3 contre 2","Fixer puis donner au bon moment",["Fixer un défenseur avant la passe","Lire l’orientation du défenseur"],"Révisions 2 contre 0 puis 2 contre 1 à vitesse progressive.",["2 contre 1 dans un couloir de 8 m","3 contre 2 avec départ décalé des défenseurs","Vagues continues où les défenseurs deviennent attaquants"],["Modifier le rapport de force à 3 contre 1 ou 3 contre 3","Limiter le porteur à une seule feinte"],["Le défenseur est réellement fixé avant la passe","L’attaque marque dans au moins 60 % des surnombres"],"Nommer le signal visuel qui déclenche la passe."),
(6,"Défendre ensemble","Monter, cadrer et communiquer collectivement",["Avancer en ligne","Cadrer intérieur/extérieur avec un partenaire"],"Montées défensives sans ballon, puis avec porteurs au pas.",["2 défenseurs contre 2 attaquants : fermer l’intervalle","4 contre 4 à toucher, défense récompensée si montée collective","Jeu de ligne : arrêt dès qu’un défenseur est 2 m derrière les autres"],["Changer la largeur du terrain","Autoriser ou non les croisées offensives"],["Défense avance avant le premier contact","Aucun intervalle de plus de 2 m entre défenseurs proches"],"Le groupe choisit deux mots-clés communs de communication défensive."),
(7,"Contact et plaquage sécurisé","Entrer dans le contact avec maîtrise et sécurité",["Adopter une posture basse et stable","Plaquer sous la ligne des épaules en accompagnant"],"Mobilité hanches/épaules, gainage puis contacts contrôlés sur bouclier.",["Placement de tête et ceinture sur bouclier immobile","Plaquage à genoux puis debout à vitesse réduite","1 contre 1 dans couloir court avec intensité progressive et consigne de maîtrise"],["Commencer sans course puis ajouter 3 m d’élan","Remplacer le plaquage par ceinturage pour débutants"],["Tête placée du bon côté et dos gainé","Le plaqué est accompagné au sol sans chute dangereuse"],["Toujours progresser du bouclier vers l’opposition réelle", "Arrêter immédiatement en cas de posture dangereuse ou appréhension forte"],"Chaque binôme valide trois points de sécurité avant de changer de rôle."),
(8,"Continuité après contact","Conserver ou libérer rapidement le ballon",["Présenter le ballon vers son camp","Arriver en soutien au-delà du contact"],"Rappels de chute contrôlée et présentation du ballon sans opposition.",["Porteur au sol : placer le ballon en moins de 2 s","2 soutiens franchissent la ligne de ballon avant de rejouer","4 contre 4 à contact aménagé avec ruck simulé"],["Passer du toucher au ceinturage","Limiter à un seul soutien pour accélérer les décisions"],["Ballon disponible côté équipe en moins de 3 s","Soutiens arrivent dans l’axe et restent sur leurs appuis"],"Comparer les attaques où le ballon sort vite et celles où le jeu s’arrête."),
(9,"Projet collectif","Organiser des principes communs d’attaque et de défense",["Définir deux principes offensifs","Définir deux principes défensifs"],"Jeu 5 contre 5 sans score, pause après chaque possession pour annoncer l’intention.",["Équipe conçoit un lancement à partir d’une touche simulée","Séquence de 5 minutes avec objectif collectif choisi","Temps mort coach : un étudiant observe largeur, soutien et montée défensive"],["Changer le point de départ des attaques","Donner un bonus à l’équipe qui applique son principe annoncé"],["Au moins un principe observable sur chaque possession","Les joueurs sont capables d’expliquer leur projet sans l’enseignant"],"Chaque équipe écrit son plan de jeu en quatre phrases maximum."),
(10,"Match évalué","Mobiliser les compétences dans une opposition aménagée",["Choisir efficacement entre porter, passer et soutenir","Respecter sécurité, règles et projet collectif"],"Vagues courtes 3 contre 2 puis rappels de plaquage ou toucher selon le niveau.",["Matchs de 6 à 8 minutes avec rotation des rôles","Observation par binômes sur passe, soutien, largeur et défense","Deuxième manche avec objectif d’amélioration choisi par équipe"],["Toucher ou plaquage selon le niveau du groupe","Terrain plus ou moins large pour favoriser certains apprentissages"],["Actions collectives réussies plus nombreuses en deuxième manche","Aucune faute de sécurité volontaire ou répétée"],"Auto-évaluation individuelle et retour collectif sur le projet de jeu."),
]
for item in RUG:
    if len(item) == 10:
        n,t,o,c,w,si,v,cr,safety,b = item
    else:
        n,t,o,c,w,si,v,cr,b = item
        safety = RUG_SAFE
    S.append(_session("rugby","Rugby",n,t,o,c,RUG_MAT,w,si,v,cr,safety,b))

SAU_MAT = ["Mannequins de sauvetage", "Frites ou bouées tube", "Planches", "Perches de sauvetage"]
SAU_SAFE = ["Travail sous surveillance directe avec zones et binômes clairement attribués", "Aucune apnée prolongée ni hyperventilation avant immersion"]
SAU = [
(1,"Sécurité et diagnostic aquatique","Identifier les risques et situer les capacités initiales",["Repérer les risques d’une zone aquatique","Évaluer sa capacité de nage avant intervention"],"200 m faciles puis entrée à l’eau contrôlée et déplacement tête hors de l’eau.",["Repérage collectif des zones à risque sur un schéma de bassin","100 m chronométré à allure maîtrisée","Approche d’une victime consciente simulée sans contact"],["Adapter distance au niveau","Ajouter une contrainte de prise d’information tête haute"],["Citer au moins trois risques avant action","Terminer le 100 m sans épuisement manifeste"],"Établir la règle : se protéger soi-même avant de secourir."),
(2,"Nage d’approche efficace","Rejoindre rapidement une zone d’intervention en gardant des réserves",["Nager vite tête hors de l’eau","Alterner prise d’information et propulsion"],"6 x 25 m : 15 m nage rapide + 10 m récupération active.",["Approche 25 m tête haute avec cible visuelle","Approche avec bouée tube en conservant une trajectoire directe","Relais 4 x 25 m où le temps n’est validé que si la cible est gardée en vue"],["Distance 15 à 50 m","Avec ou sans matériel de sauvetage"],["Trajectoire directe sans zigzag","Arriver capable de parler et d’enchaîner une action"],"Comparer temps pur et qualité d’arrivée pour choisir l’allure efficace."),
(3,"Immersion et récupération d’objet","Descendre, s’orienter et remonter en contrôle",["Effectuer une immersion efficace","Remonter un objet sans précipitation"],"Jeux d’immersion à faible profondeur, expiration contrôlée, récupération d’anneaux.",["Canard technique depuis surface","Récupération d’objet à profondeur progressive","Enchaîner nage 15 m + immersion + retour surface"],["Modifier profondeur selon aisance","Déplacer l’objet latéralement"],["Descente orientée sans lutte inutile","Retour surface calme avec expiration maîtrisée"],"Identifier le mouvement qui facilite le plus la descente."),
(4,"Prise du mannequin","Saisir et stabiliser un mannequin sans perte de temps",["Approcher le mannequin dans l’axe","Choisir une prise stable"],"Révision immersion + remontée d’objet léger, puis manipulation mannequin au bord.",["Prises de mannequin en surface au bord","Immersion, saisie et remontée verticale","Approche 10 m + prise + stabilisation avant remorquage"],["Mannequin vide ou lesté selon niveau","Départ surface ou après nage"],["Prise stable en moins de 5 s","Mannequin orienté voies aériennes hors de l’eau"],"Nommer la prise la plus efficace pour chacun et pourquoi."),
(5,"Remorquage","Transporter une victime/mannequin en conservant les voies aériennes dégagées",["Maintenir la tête de la victime hors de l’eau","Se propulser efficacement en remorquage"],"4 x 25 m jambes dos puis 4 x 15 m remorquage léger avec frite.",["Remorquage mannequin 15 m prise menton adaptée","Remorquage avec bouée tube autour d’une victime simulée","3 x 25 m en cherchant régularité plutôt que vitesse"],["Distance 10 à 50 m","Ajouter palmes si dispositif prévu"],["Voies aériennes hors eau sur tout le trajet","Trajectoire droite et vitesse sans rupture"],"Comparer deux prises et retenir celle qui préserve le mieux propulsion et contrôle."),
(6,"Sortie d’eau","Extraire une victime selon les moyens disponibles et en sécurité",["Choisir une technique d’extraction adaptée","Coordonner l’action à deux"],"Mobilité dos/jambes puis répétition à sec des prises d’extraction.",["Sortie au bord bas à deux intervenants","Utilisation d’une échelle ou zone de faible profondeur","Scénario : remorquage 10 m puis extraction sans rupture de communication"],["Victime coopérante puis passive simulée","Extraction seul uniquement sur dispositif adapté"],["Commandes verbales claires entre sauveteurs","Aucune traction dangereuse sur tête ou membres"],"Décrire quel dispositif d’extraction utiliser selon la configuration du lieu."),
(7,"Prise en charge à terre","Organiser l’alerte, le bilan et la conduite à tenir dans le cadre pédagogique",["Sécuriser et alerter rapidement","Réaliser un bilan simple et structuré"],"Jeu oral : identifier en 30 s danger, protection, alerte et informations utiles.",["Scénario victime consciente après extraction","Scénario victime ne répondant pas : enchaînement pédagogique selon protocole enseigné","Transmission d’un bilan synthétique à un partenaire jouant les secours"],["Ajouter témoins perturbateurs","Limiter à 60 s pour transmettre l’alerte"],["Les informations essentielles sont données dans l’ordre","Le sauveteur reste centré sur sécurité et surveillance de la victime"],["Suivre strictement les protocoles de secourisme enseignés et actualisés", "Utiliser uniquement du matériel pédagogique prévu pour la simulation"],"Faire reformuler la chaîne protéger–alerter–secourir dans l’ordre."),
(8,"Scénarios d’intervention","Choisir une réponse adaptée à plusieurs situations simulées",["Analyser avant d’agir","Choisir matériel et trajectoire adaptés"],"Révision rapide de trois entrées à l’eau et des prises de remorquage.",["Victime consciente paniquée : approche avec objet flottant","Victime passive à 20 m : nage d’approche + remorquage","Deux victimes simulées : prioriser, alerter et utiliser les moyens disponibles"],["Changer distance et position des victimes","Ajouter un sauveteur partenaire ou témoin"],["Choix d’intervention justifié avant entrée à l’eau","Aucun risque ajouté par le sauveteur"],"Débrief en trois questions : qu’ai-je vu, qu’ai-je choisi, qu’aurais-je changé ?"),
(9,"Parcours complet","Enchaîner approche, immersion, remorquage et sortie",["Maintenir l’efficacité sur une chaîne longue","Préserver la sécurité malgré la fatigue"],"300 m variés puis 2 répétitions techniques de chaque atelier à faible intensité.",["25 m approche + immersion + mannequin + 25 m remorquage","Même parcours avec extraction au bord","Parcours chronométré avec pénalités sécurité/technique"],["Distance 15 à 50 m selon niveau","Avec ou sans matériel de sauvetage"],["Aucune rupture de sécurité sur tout le parcours","Temps régulier entre deux essais sans dégradation technique"],"Choisir une stratégie d’allure pour l’évaluation finale."),
(10,"Évaluation finale","Réaliser un scénario complet avec efficacité et sécurité",["Conduire une intervention cohérente","Expliquer ses décisions après action"],"Échauffement autonome préparé par binômes : nage, immersion, remorquage.",["Scénario tiré au sort avec analyse initiale","Réalisation complète intervention + prise en charge","Entretien bref : justification du choix de technique et auto-évaluation"],["Deux niveaux de distance/profondeur","Matériel imposé ou à choisir selon objectif"],["Toutes les étapes essentielles sont réalisées dans un ordre cohérent","La sécurité prime sur le chronomètre et aucune faute majeure n’est observée"],"Consigner résultat, points forts et une priorité de perfectionnement."),
]
for item in SAU:
    if len(item) == 10:
        n,t,o,c,w,si,v,cr,safety,b = item
    else:
        n,t,o,c,w,si,v,cr,b = item
        safety = SAU_SAFE
    S.append(_session("sauvetage-ssa","Sauvetage / SSA",n,t,o,c,SAU_MAT,w,si,v,cr,safety,b))

CAP_MAT = ["Plots", "Chronomètres", "Repères de distance", "Cardiofréquencemètres si disponibles"]
CAP_SAFE = ["Échauffement progressif obligatoire avant les intensités élevées", "Adapter immédiatement l’effort en cas de douleur, malaise ou difficulté inhabituelle"]
CAP = [
(1,"Diagnostic d’allure","Identifier son niveau et ses allures de référence",["Courir régulièrement sur un effort test","Lire ses sensations et temps de passage"],"10 min footing + mobilité + 3 accélérations progressives.",["Test de 6 min ou distance adaptée au groupe","Relevé des temps de passage par minute","Retour au calme en marchant puis notation de la perception d’effort"],["Durée 5 à 8 min selon profil","Utiliser une boucle courte pour faciliter les repères"],["Allure sans départ sprint","Être capable d’indiquer une allure de travail réaliste"],"Calculer une première zone d’allure pour les prochaines séances."),
(2,"Régularité d’allure","Courir à une vitesse cible avec peu de variation",["Respecter un temps au tour","Ajuster sa vitesse sans arrêt"],"12 min footing avec 3 passages de 30 s à allure cible.",["6 x 2 min à allure cible avec relevé de chaque passage","Course en binôme meneur/suiveur puis inversion","Défi régularité : score basé sur l’écart au temps cible"],["Modifier cible de ±5 %","Augmenter durée des fractions à 3 min"],["Écart inférieur à 3 s sur tours identiques","Pas d’accélération brutale en fin de fraction"],"Identifier les sensations corporelles correspondant à l’allure juste."),
(3,"Technique de course","Améliorer posture, appuis et relâchement",["Poser le pied sous le centre de gravité","Maintenir buste stable et bras actifs"],"Footing 8 min puis gammes : montées de genoux, talons-fesses, pas bondissants.",["Lignes droites 60 m avec focales posture/appuis","Course silencieuse : réduire bruit d’impact sans ralentir","4 x 200 m en alternant consigne technique et course libre"],["Pente très légère pour travailler placement","Augmenter cadence sans accélérer"],["Buste reste haut sans crispation","Appuis deviennent plus rapides et moins freinants"],"Chaque coureur choisit une seule consigne technique à garder."),
(4,"VMA et intensités","Comprendre et expérimenter des intensités courtes",["Courir proche d’une vitesse haute contrôlée","Respecter récupération et répétitions"],"15 min complet avec 4 accélérations de 20 s.",["2 séries de 6 x 30 s vite / 30 s lent","Repères de distance individualisés à partir du diagnostic","Observation binôme : maintien de la distance sur les dernières répétitions"],["30/30 ou 45/45","Réduire distance cible de 5 % pour les débutants"],["Atteindre le repère sur au moins 10 répétitions sur 12","Dernière répétition techniquement comparable à la première"],"Relier perception d’effort et réussite des distances cibles."),
(5,"Fractionné court","Répéter des efforts rapides avec récupération maîtrisée",["Répéter une vitesse élevée sans effondrement","Utiliser la récupération active"],"10 min footing + gammes + 3 lignes droites.",["8 x 200 m avec récupération 1 min","2 x 4 x 200 m avec 3 min entre séries","Dernière série en binômes de niveau pour contrôler départ"],["Distance 150 à 300 m","Récupération 45 à 90 s"],["Écart inférieur à 5 % entre meilleur et pire temps","Récupération réalisée en marchant/trottinant sans s’allonger"],"Décider si la vitesse choisie permettait de finir aussi proprement qu’au début."),
(6,"Endurance fondamentale","Soutenir un effort continu à intensité modérée",["Courir longtemps en aisance respiratoire","Gérer hydratation et rythme"],"8 min de marche active/footing puis mobilisation douce.",["20 à 35 min de course continue selon niveau","Test de parole : pouvoir prononcer une phrase régulièrement","Boucle à contrats : valider chaque tour sans accélération finale"],["Alternance 4 min course / 1 min marche","Durée adaptée de 20 à 40 min"],["Allure stable sur l’ensemble de la durée","Capacité à parler brièvement sans essoufflement excessif"],"Reporter durée et sensations, puis estimer l’intensité sur 10."),
(7,"Travail au seuil","Maintenir une allure soutenue sans départ excessif",["Stabiliser une allure soutenue","Résister à la tentation d’accélérer trop tôt"],"15 min progressives avec 3 x 1 min soutenue.",["3 x 6 min soutenues récupération 2 min","2 x 10 min à allure légèrement inférieure selon niveau","Comparaison des temps de passage début/fin de bloc"],["Blocs de 4 à 10 min","Récupération 90 s à 3 min"],["Deuxième moitié du bloc aussi rapide que la première à ±3 %","Respiration soutenue mais encore contrôlée"],"Identifier l’allure maximale que l’on peut répéter sans dérive majeure."),
(8,"Gestion de course","Construire une stratégie d’allure selon distance et objectif",["Planifier un départ maîtrisé","Accélérer seulement si la réserve le permet"],"12 min faciles puis 3 accélérations à allure de fin de course.",["Course 12 min avec trois segments planifiés","Simulation 2 km : premier tiers contrôlé, deuxième stable, dernier optimisé","Comparaison plan annoncé / temps réellement réalisés"],["Distance 1,5 à 3 km","Départ groupé ou en vagues"],["Premier segment conforme au plan à ±5 s","Dernier segment n’est pas plus lent de plus de 5 % sauf choix justifié"],"Écrire la stratégie à reproduire lors de l’évaluation."),
(9,"Séance autonome","Concevoir et conduire une séance simple adaptée à son objectif",["Choisir contenu, intensité et récupération","Conduire un échauffement adapté"],"Chaque groupe présente son échauffement de 8 à 10 min avant validation.",["Choisir objectif endurance, régularité ou fractionné","Écrire le bloc principal avec temps/distances/récupérations","Conduire la séance par groupes de 3 avec un observateur"],["Objectif imposé par l’enseignant pour certains groupes","Durée totale limitée à 35 min"],["Séance cohérente avec l’objectif annoncé","Les intensités restent réalisables jusqu’au dernier bloc"],"Chaque groupe propose une amélioration de sa séance après l’avoir vécue."),
(10,"Évaluation finale","Mesurer la progression et justifier sa stratégie de course",["Réaliser une performance régulière","Analyser les écarts entre plan et résultat"],"15 min d’échauffement autonome incluant mobilité et accélérations.",["Épreuve de référence comparable au diagnostic","Relevé de temps intermédiaires","Analyse écrite courte : stratégie, ressenti, progression"],["Distance adaptée au protocole du groupe","Départ en vagues pour fluidifier la piste"],["Performance améliorée ou stratégie mieux maîtrisée","Analyse s’appuie sur au moins deux indicateurs mesurés"],"Fixer un objectif réaliste de poursuite après le cycle."),
]
for n,t,o,c,w,si,v,cr,b in CAP:
    S.append(_session("course-a-pied","Course à pied",n,t,o,c,CAP_MAT,w,si,v,cr,CAP_SAFE,b))

PEL_MAT = ["Pelotes adaptées au niveau", "Gants ou protections selon spécialité", "Plots", "Cibles murales"]
PEL_SAFE = ["Vérifier que personne ne traverse la zone de frappe", "Respecter une distance de sécurité derrière et latéralement au frappeur"]
PEL = [
(1,"Prise en main et sécurité","Découvrir matériel, espace, règles et frappe de base",["Tenir et frapper la pelote avec contrôle","Se repérer dans l’aire de jeu"],"Mobilité épaules/poignets puis échanges à la main sans mur.",["Lancer-frapper vers grande cible murale","Échanges après un rebond à distance courte","Parcours de découverte des lignes et zones du fronton"],["Pelote plus souple","Distance au mur 3 à 8 m"],["8 frappes sur 10 atteignent la zone large","Aucune frappe réalisée sans contrôle de l’espace"],"Nommer les trois règles de sécurité indispensables avant de jouer."),
(2,"Frappe et contrôle","Stabiliser le geste pour envoyer la balle dans une zone choisie",["Orienter la frappe vers une cible","Répéter un geste stable"],"20 frappes douces alternées main dominante/non dominante selon spécialité.",["Cibles horizontales au mur : 5 séries de 6","Frappe après rebond imposé devant une ligne","Défi précision par binômes avec points par zone"],["Augmenter distance au mur","Réduire la taille des cibles"],["Atteindre une cible choisie sur au moins 60 % des frappes","Conserver équilibre après la frappe"],"Identifier le réglage de placement qui améliore le plus la précision."),
(3,"Placement sous la trajectoire","Se déplacer tôt et frapper en équilibre",["Lire la trajectoire dès le rebond","Ajuster les petits pas avant frappe"],"Déplacements en étoile sans balle puis avec lancer du partenaire.",["Partenaire lance à droite/gauche, joueur se place puis frappe","Deux frappes consécutives avec replacement central","Échanges coopératifs où le point ne compte que si frappe en équilibre"],["Augmenter variation droite/gauche","Imposer départ depuis une zone arrière"],["Arriver placé avant le deuxième rebond","Finir la frappe sans croiser dangereusement les appuis"],"Observer un partenaire et repérer s’il part tôt ou tard vers la balle."),
(4,"Lire les trajectoires","Anticiper rebonds, hauteur et profondeur",["Prévoir zone de chute","Adapter recul/avance au type de frappe"],"Lancers variés contre mur, annoncer la zone de rebond avant de bouger.",["Lecture seule : annoncer court/long avant rebond","Échanges où le partenaire varie hauteur et profondeur","Jeu de prédiction : point bonus si zone annoncée avant déplacement"],["Ajouter effets simples","Masquer partiellement le geste du lanceur pour avancés"],["Annonce correcte sur 7 balles sur 10","Déplacement démarre avant le rebond au sol"],"Lister deux indices visuels utilisés pour anticiper."),
(5,"Précision des zones","Viser des zones pour déplacer l’adversaire",["Diriger court/long","Alterner largeur et profondeur"],"Échanges dans une zone centrale puis ouverture progressive vers les côtés.",["Cibles gauche/droite au fronton","Alternance imposée court puis long","Match à thème : marquer seulement après avoir changé de zone"],["Cibles plus petites","Autoriser choix libre après deux frappes imposées"],["Deux zones différentes touchées dans une même séquence","Adversaire obligé de se déplacer avant le point"],"Choisir la zone que chacun maîtrise le mieux et celle à travailler."),
(6,"Déplacement et replacement","Enchaîner frappe, replacement et nouvelle prise d’information",["Revenir vers une position utile après frappe","Garder le regard disponible sur la balle"],"Circuit déplacements avant/arrière/latéraux avec reprise d’appuis.",["Frappe puis passage par une zone de replacement","Échange coopératif 10 frappes avec retour central","2 contre 1 tournant où le joueur seul doit gérer replacement"],["Élargir la zone à couvrir","Limiter le temps de replacement avec signal sonore"],["Replacement engagé avant la frappe adverse","Pas de collision ni croisement dangereux entre partenaires"],"Faire dessiner la position de replacement la plus efficace selon la frappe."),
(7,"Construire le point","Alterner profondeur, largeur et rythme",["Préparer une ouverture avant d’attaquer","Enchaîner deux intentions différentes"],"Rallye coopératif avec alternance obligatoire d’une frappe longue et courte.",["Schéma 1 : long puis large","Schéma 2 : déplacer puis accélérer","Match à 7 points avec obligation d’annoncer l’intention avant service"],["Autoriser troisième frappe libre","Limiter à une zone d’attaque spécifique"],["Le point est préparé par au moins un déplacement de l’adversaire","L’intention annoncée est visible dans la trajectoire"],"Nommer le schéma de jeu le plus rentable pour soi."),
(8,"Opposition aménagée","Réinvestir les techniques dans des échanges à thème",["Choisir une réponse adaptée sous pression","Respecter règles et score"],"Échanges courts à intensité croissante, service alterné.",["Match avec bonus précision","Match où le serveur doit viser une zone annoncée","Rotation toutes les 5 minutes : joueur, arbitre, observateur"],["Terrain réduit","Interdire la zone la plus facile pour pousser à varier"],["Score tenu sans conflit de règle","Au moins trois choix tactiques variés observés"],"L’observateur donne une réussite et un choix à améliorer."),
(9,"Choix tactiques","Identifier un rapport de force et adapter son jeu",["Repérer faiblesse adverse","Changer de stratégie si elle ne fonctionne pas"],"Mini-matchs de 3 points pour observer rapidement les profils.",["Match 5 points avec temps mort tactique","Fiche observation : zones fortes/faibles adverses","Deuxième match avec consigne stratégique différente"],["Révéler ou non la fiche d’observation à l’adversaire","Bonus si stratégie annoncée produit le point"],["Stratégie cohérente avec une observation réelle","Capacité à changer de plan après deux échecs similaires"],"Écrire une phrase : contre ce profil, je cherche à…"),
(10,"Évaluation finale","Jouer un match aménagé avec critères techniques et tactiques",["Stabiliser les gestes sous opposition","Construire le point avec intention"],"Échanges coopératifs 5 min puis services et retours ciblés.",["Matchs poule courte avec arbitrage étudiant","Grille technique : placement, précision, replacement","Grille tactique : variation, construction, adaptation"],["Format 7 ou 11 points","Terrain adapté au niveau"],["Règles et sécurité respectées sur tout le match","Au moins deux points construits selon une intention identifiable"],"Auto-évaluation et choix d’un objectif de pratique future."),
]
for n,t,o,c,w,si,v,cr,b in PEL:
    S.append(_session("pelote-basque","Pelote Basque",n,t,o,c,PEL_MAT,w,si,v,cr,PEL_SAFE,b))

SURF_MAT = ["Planches adaptées", "Leashes en bon état", "Combinaisons", "Repères visuels de zone"]
SURF_SAFE = ["Vérifier météo, houle, vent, marée et zone autorisée avant mise à l’eau", "Maintenir une distance de sécurité et ne jamais lâcher volontairement la planche vers un autre pratiquant"]
SURF = [
(1,"Lire le milieu et se mettre en sécurité","Identifier zone, courant, priorité et conduite à tenir",["Observer le plan d’eau avant d’entrer","Connaître règles de priorité et sortie d’urgence"],"Échauffement à sec : épaules, rachis, hanches, puis simulation rame/take-off.",["Lecture collective : zones d’impact, chenal, baïnes/courants selon site","Jeu de décision à partir de scénarios de priorité","Entrées/sorties dans zone de mousse faible avec regroupement"],["Observation depuis deux points différents de la plage","Niveau débutant reste dans mousses; avancé identifie zone de take-off"],["Chaque étudiant montre la zone d’évolution autorisée","Les règles de priorité sont correctement expliquées"],"Avant de ranger, chacun indique le principal danger observé ce jour-là."),
(2,"Rame et position sur la planche","Se placer et produire une rame efficace",["Trouver le point d’équilibre longitudinal","Ramer avec amplitude sans zigzag"],"Activation épaules/gainage, puis 3 séries de 30 s de rame à sec.",["Glisse ventrale dans mousse pour régler la position","6 x 20 m rame vers repère avec retour facile","Défi trajectoire : atteindre une porte de plots sans corriger excessivement"],["Planche plus large ou plus courte selon niveau","Distance 10 à 40 m selon conditions"],["Nez de planche stable sans enfourner ni cabrer","Trajectoire reste dans un couloir de 3 m"],"Repérer la position du corps qui donne la meilleure glisse pour le moins d’effort."),
(3,"Passage de barre","Choisir sa trajectoire et franchir les mousses en sécurité",["Lire les séries avant de partir","Franchir une mousse sans perdre la planche"],"Rame en zone calme puis répétition de retournement/reprise de planche.",["Choisir le bon moment entre deux séries","Franchissement mousse faible avec poussée ou turtle roll selon planche","Aller-retour jusqu’à un repère extérieur proche en conservant groupe visible"],["Rester dans petite mousse pour débutants","Ajouter canard uniquement pour pratiquants et planches adaptés"],["Planche reste contrôlée à chaque mousse","Trajectoire évite la zone la plus chargée"],"Débrief sur le choix du moment de départ plutôt que sur la force de rame."),
(4,"Take-off","Se redresser rapidement en conservant équilibre et direction",["Enchaîner appuis mains-pieds sans passer par les genoux","Regarder la direction de déplacement"],"10 take-offs à sec avec repères de pieds dessinés sur le sable.",["Take-off dans mousse en position ventrale stable","Départ assisté par l’enseignant puis autonome","Série de 5 vagues : compter les redressements stabilisés plus de 3 s"],["Planche plus volumineuse","Départ sur mousse puis petite vague non cassée selon niveau"],["Pieds placés de part et d’autre de l’axe sans genoux au sol","Regard porté vers l’avant et stabilité au moins 3 s"],"Choisir une correction unique pour le prochain take-off : vitesse, pieds ou regard."),
(5,"Mise en situation et autonomie","Choisir une vague adaptée, partir et respecter les priorités",["Choisir une vague cohérente avec son niveau","Enchaîner rame, take-off et trajectoire en sécurité"],"Échauffement autonome contrôlé puis 10 min de rame et take-offs faciles.",["Séries de 15 min avec zone clairement délimitée","Objectif individuel : réussir 3 départs contrôlés plutôt qu’un nombre élevé d’essais","Observation croisée : priorité, choix de vague, take-off, trajectoire"],["Zone mousses ou outside selon niveau et conditions","Objectif technique personnalisé"],["Aucune faute de priorité ni mise en danger","Au moins trois vagues choisies de façon pertinente et engagées avec contrôle"],"Bilan final sur autonomie : ce que je sais lire, faire seul, et ce qui nécessite encore accompagnement."),
]
for n,t,o,c,w,si,v,cr,b in SURF:
    S.append(_session("surf","Surf",n,t,o,c,SURF_MAT,w,si,v,cr,SURF_SAFE,b))

OFFICIAL_SESSIONS = tuple(S)


def seed_official_resources(get_conn, use_postgres: bool) -> int:
    """Insère le fonds officiel une seule fois; retourne le nombre de créations."""
    created = 0
    for session in OFFICIAL_SESSIONS:
        content = {
            "numero": session["numero"],
            "objectif": session["objectif"],
            "competences": session["competences"],
            "materiel": session["materiel"],
            "echauffement": session["echauffement"],
            "situations": session["situations"],
            "variables": session["variables"],
            "criteres_reussite": session["criteres_reussite"],
            "securite": session["securite"],
            "retour_bilan": session["retour_bilan"],
        }
        if create_resource(
            get_conn,
            activity=session["activite"],
            resource_type="Séance",
            title=f'Séance {session["numero"]} — {session["titre"]}',
            description=session["objectif"],
            content=content,
            author="SUAPS UPPA",
            visible_students=False,
            official=True,
            seed_key=session["seed_key"],
        ):
            created += 1
    return created


# SUAPS — Présences, évaluations et compétences

Application MVP pour gérer :
- les étudiants et groupes ;\n- l’import Excel/CSV des listes d’étudiants ;\n- un modèle Excel prêt à remplir ;
- les séances de natation, sauvetage, surf, rugby et course à pied ;
- les présences / absences / dispenses ;\n- un mode « appel express mobile » ;
- un QR code temporaire propre à chaque séance ;
- l’auto-validation de présence par numéro étudiant ;
- la compatibilité NFC via la même URL d’émargement ;
- les évaluations et notes ;
- la validation des compétences ;
- une fiche individuelle avec présence, moyenne et compétences ;
- la validation finale par activité / semestre ;
- les exports CSV.

## Installation

1. Installer Python 3.11 ou plus récent.
2. Ouvrir un terminal dans le dossier de l'application.
3. Installer les dépendances :

```bash
pip install -r requirements.txt
```

4. Lancer l'application :

```bash
streamlit run app.py
```

L'application s'ouvre ensuite dans le navigateur.

## Données

Les données sont stockées localement dans le fichier :

`suaps_presence.db`

Ce fichier est créé automatiquement au premier lancement.

## Important pour un usage réel

Ce MVP ne comporte pas encore :
- authentification utilisateur ;
- gestion fine des droits ;
- hébergement sécurisé ;
- sauvegardes automatiques ;
- conformité RGPD complète ;
- import depuis Apogée / listes institutionnelles ;
- signature ou émargement étudiant.

Pour une mise en production avec des données nominatives d'étudiants, il faut prévoir une authentification, un hébergement institutionnel ou conforme aux exigences de l'établissement, une politique de conservation des données et une gestion des accès.


## Émargement QR / NFC

L'enseignant ouvre une séance puis choisit **Émargement QR / NFC**.
Il définit une durée (2 à 30 minutes), ouvre l'émargement et affiche le QR code.

L'étudiant scanne le QR code, saisit son numéro étudiant et valide sa présence.
Le lien expire à la fin de la période et l'enseignant peut le fermer manuellement.

Une étiquette NFC peut être programmée avec exactement la même URL.

### Utilisation en réseau local
Le téléphone enseignant/ordinateur et les téléphones étudiants doivent être sur le même réseau.
L'application propose l'adresse IP locale de la machine.

### Utilisation réelle
Pour un usage institutionnel, héberger l'application sur un serveur HTTPS sécurisé.
L'identification par simple numéro étudiant est adaptée à un prototype, mais une authentification universitaire (SSO) est préférable en production.


## Mode enseignant smartphone

Le mode **Appel express mobile** est conçu pour être utilisé sur téléphone :
- sélection de la séance ;
- bouton « Tous présents » ;
- recherche par nom ou prénom ;
- filtres Présents / Absents / Non renseignés ;
- gros boutons Présent / Absent / Justifié / Dispensé ;
- compteurs en direct ;
- modification immédiate d’un statut.


## Évaluation et performances

La version 7 ajoute :
- un cahier de notes avec saisie individuelle ou par groupe ;
- coefficients et barèmes personnalisables ;
- calcul automatique des moyennes sur 20 ;
- saisie de performances chiffrées (temps, distance, points, répétitions...) ;
- conversion facultative d'une performance en note sur 20 ;
- validation des compétences individuellement ou par groupe ;
- suivi du pourcentage de compétences acquises ;
- affichage des performances dans la fiche individuelle étudiant ;
- export CSV des performances.


## Version 8 — Barèmes personnalisables

La version 8 ajoute :
- des barèmes personnalisables par activité ;
- des barèmes différents selon le niveau ou le groupe ;
- un sens de performance configurable : « plus élevé = meilleur » ou « plus faible = meilleur » ;
- une conversion automatique performance → note sur 20 ;
- la possibilité de relier un barème à une ou plusieurs compétences ;
- des seuils de note pour attribuer automatiquement « En cours d’acquisition », « Acquis » ou « Maîtrisé » ;
- l’export des barèmes et l’affichage du barème utilisé dans l’historique des performances.

Les barèmes restent entièrement modifiables dans l’application afin de s’adapter aux choix pédagogiques du SUAPS.


## Version 9 — Inscriptions en ligne

La version 9 ajoute :
- la création d’offres d’inscription par activité ;
- un lien web et un QR code d’inscription ;
- une capacité maximale par créneau ;
- des dates d’ouverture et de fermeture ;
- le choix étudiant entre trois modalités : UET, UECF ou Non noté ;
- le suivi des inscriptions par modalité ;
- l’export CSV des inscrits ;
- l’affichage des inscriptions dans la fiche individuelle étudiant.


## Version 10 — Portail étudiant smartphone

La version 10 ajoute un portail étudiant optimisé smartphone :
- page d'accueil visuelle SUAPS / Université de Pau et des Pays de l'Adour ;
- design mobile avec cartes, indicateurs et gros boutons ;
- affichage des inscriptions ;
- taux de présence ;
- moyenne ;
- progression des compétences ;
- performances récentes ;
- présences récentes ;
- pages QR de présence et d'inscription visuellement harmonisées.

Le visuel est volontairement dynamique et motivant, sans intégrer de logo officiel. Un logo institutionnel pourra être ajouté ensuite à partir d'un fichier fourni par l'université.


## Version 11 — Identité visuelle UPPA

La version 11 intègre le logo UPPA fourni dans :
- le portail étudiant smartphone ;
- la page d'inscription en ligne ;
- la page de validation de présence QR/NFC ;
- l'interface principale enseignant.

Le fichier du logo est inclus dans le dossier `assets` de l'application.


## Version 12 — prête pour mise en ligne

La V12 ajoute :
- un superbe écran d'accueil SUAPS/UPPA ;
- le visuel promotionnel mobile ;
- les cartes des cinq activités ;
- une mise en page responsive ;
- la détection automatique de l'URL publique sur Render ;
- une variable `APP_BASE_URL` pour tout autre hébergeur ;
- un Dockerfile et une configuration Render ;
- une configuration Streamlit dédiée ;
- un guide `DEPLOIEMENT_EN_LIGNE.md`.

Cette version est prête à être déployée sur un hébergeur web.


## Version 13 — test en ligne + base persistante

- PostgreSQL externe via `DATABASE_URL`, avec SQLite en secours local.
- Codes d'accès distincts testeur / enseignant.
- Menus étudiants limités à l'accueil et au portail.
- Données persistantes sur une base PostgreSQL externe.
- Compatible Streamlit Community Cloud.
- URL publique configurable pour QR/NFC.

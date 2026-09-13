# Espace Ressources pédagogiques — Spécification de conception

Date : 2026-09-13

## 1. Objectif

Ajouter à l’application SUAPS UPPA un espace centralisé de ressources pédagogiques accessible aux enseignants, avec possibilité de partager certaines ressources aux étudiants. Le module doit contenir dès sa mise en service un fonds de séances prêtes à l’emploi et permettre aux enseignants d’ajouter leurs propres documents, séances et liens.

## 2. Périmètre fonctionnel

Le module ajoute un menu enseignant `📚 Ressources pédagogiques` avec cinq catégories principales :

- Progressions
- Séances
- Compétences / barèmes
- Documents
- Vidéos / liens

Toutes les ressources créées par un enseignant sont visibles immédiatement par tous les enseignants. Une ressource peut, séparément, être rendue visible aux étudiants.

Les ressources officielles SUAPS sont identifiées par un badge `Officiel SUAPS` et protégées contre les modifications ordinaires.

## 3. Fonds initial de contenus

Le module est livré avec 55 séances officielles SUAPS :

- Natation : 10 séances
- Rugby : 10 séances
- Sauvetage / SSA : 10 séances
- Course à pied : 10 séances
- Pelote basque : 10 séances
- Surf : 5 séances

Chaque séance comprend au minimum :

- numéro et titre de séance
- objectif principal
- compétences visées
- matériel
- échauffement / mise en route
- situations d’apprentissage
- variables de difficulté
- critères de réussite
- consignes de sécurité
- retour au calme / bilan

### Progressions initiales

**Natation** : diagnostic → respiration/équilibre → propulsion → crawl → dos → endurance → virages → efficacité → parcours combiné → évaluation.

**Rugby** : diagnostic/manipulation → passes → soutien → occupation de l’espace → 2c1/3c2 → défense → contact sécurisé → continuité → projet collectif → match évalué.

**Sauvetage / SSA** : sécurité → nage d’approche → immersion → mannequin → remorquage → sortie d’eau → prise en charge → scénarios → parcours complet → évaluation.

**Course à pied** : diagnostic → allure → technique → VMA → fractionné → endurance → seuil → gestion de course → séance autonome → évaluation.

**Pelote basque** : prise en main → frappe → placement → trajectoires → précision → déplacement → construction du point → opposition → tactique → évaluation.

**Surf** : sécurité/lecture du milieu → rame → passage de barre → take-off → mise en situation et autonomie.

## 4. Expérience utilisateur

### 4.1 Écran principal

L’écran affiche des cartes par activité et des filtres :

- activité
- type de ressource
- auteur
- ressources officielles / enseignants
- visibilité étudiants
- recherche texte

Chaque carte de ressource affiche : titre, activité, type, auteur, date, badge officiel éventuel et état de partage étudiant.

### 4.2 Consultation d’une séance

Une séance s’ouvre dans une vue mobile lisible pendant le cours. Les sections sont affichées sous forme de blocs clairs et repliables si nécessaire.

Actions disponibles :

- `Dupliquer`
- `Créer une séance à partir de cette ressource`
- `Télécharger le document` si présent
- `Ouvrir le lien` pour une vidéo ou une ressource externe
- `Partager aux étudiants` si autorisé

### 4.3 Création d’une ressource enseignant

Le formulaire comporte :

- activité
- type de ressource
- titre
- description
- auteur (nom/prénom saisi)
- contenu structuré si type `Séance`
- fichier PDF/document facultatif
- lien externe facultatif
- visibilité étudiants oui/non

Les vidéos sont stockées sous forme de liens, pas comme fichiers vidéo.

### 4.4 Modification et suppression

L’application n’ayant pas encore de comptes enseignants individuels, l’auteur déclaré ne constitue pas une identité forte. Pour respecter la règle « l’auteur modifie/supprime sa ressource » sans créer immédiatement un système de comptes, chaque ressource enseignant reçoit un `code de modification` choisi à la création et stocké uniquement sous forme hachée.

- modification/suppression : nom de l’auteur + code de modification
- administrateur SUAPS : possibilité de modifier/supprimer toute ressource via un code administrateur dédié
- ressources officielles : modifiables uniquement en mode administrateur

Cette solution est transitoire jusqu’à l’éventuelle mise en place de comptes enseignants individuels.

## 5. Données

Ajouter une table `ressources_pedagogiques` compatible PostgreSQL et SQLite.

Champs principaux :

- `id`
- `activite`
- `type_ressource`
- `titre`
- `description`
- `contenu_json` ou texte structuré pour les séances
- `auteur`
- `auteur_code_hash`
- `date_creation`
- `date_modification`
- `visible_etudiants`
- `officiel_suaps`
- `lien_externe`
- `nom_fichier`
- `mime_type`
- `taille_fichier`
- `fichier_data`

Le contenu détaillé des séances peut être stocké en JSON sérialisé dans un champ texte afin de conserver la compatibilité simple entre PostgreSQL et SQLite.

## 6. Stockage des fichiers

Le service Render est actuellement sur un plan sans disque persistant ; les fichiers ne doivent donc pas être écrits uniquement sur le système de fichiers local.

Pour la V1 :

- les PDF et documents sont stockés directement dans la base de données
- taille maximale recommandée : 5 Mo par fichier
- types acceptés au minimum : PDF, DOCX, PPTX, XLSX et images usuelles si besoin pédagogique
- les vidéos restent des liens externes

Une migration vers un stockage objet externe pourra être faite ultérieurement si le volume devient important.

## 7. Intégration avec les séances existantes

Le bouton `Créer une séance à partir de cette ressource` crée une nouvelle entrée dans la table `seances` existante.

L’enseignant choisit :

- date
- groupe
- activité

Le thème est prérempli avec le titre de la ressource et la séance créée conserve un lien logique vers la ressource source si un champ `ressource_id` est ajouté à `seances`.

La séance créée fonctionne ensuite normalement avec :

- présences
- QR/NFC
- évaluations
- suivi de groupe

## 8. Accès étudiants

En mode étudiant, seules les ressources avec `visible_etudiants = 1` sont visibles.

L’espace étudiant présente uniquement des ressources de consultation :

- titre
- activité
- description
- document téléchargeable
- lien externe

Aucune création, modification ou suppression n’est autorisée côté étudiant.

## 9. Sécurité et validation

- vérifier le type MIME et l’extension des fichiers
- limiter la taille des fichiers
- rejeter les liens non HTTP/HTTPS
- échapper les contenus affichés lorsque nécessaire
- ne jamais utiliser le nom de fichier fourni comme chemin serveur
- stocker les codes de modification sous forme hachée avec sel
- protéger les ressources officielles contre les écritures non administrateur
- ne pas exposer directement les données binaires hors action explicite de téléchargement

## 10. Erreurs et cas limites

Le module doit gérer proprement :

- ressource introuvable
- fichier trop volumineux
- type de fichier non autorisé
- lien invalide
- code de modification incorrect
- absence de PostgreSQL avec repli SQLite
- erreur de lecture/écriture du fichier en base
- tentative de suppression d’une ressource officielle sans droit admin

Les erreurs doivent être affichées avec des messages utilisateurs simples et sans informations techniques sensibles.

## 11. Structure du code

Éviter d’ajouter tout le module dans `app.py`, déjà volumineux. Prévoir au minimum un module séparé, par exemple :

- `pedagogie_resources.py` : logique UI et actions du module
- `pedagogie_seed.py` : contenu des 55 séances officielles et initialisation idempotente

Les fonctions d’accès aux données existantes (`qdf`, `exec_sql`, `get_conn`) peuvent être réutilisées ou déplacées progressivement vers un module commun si nécessaire, sans refactorisation générale hors périmètre.

## 12. Tests à prévoir

Tests fonctionnels minimaux :

1. création d’une ressource enseignant
2. visibilité immédiate pour un autre enseignant
3. modification avec bon code auteur
4. refus avec mauvais code auteur
5. suppression admin
6. protection d’une ressource officielle
7. partage / retrait côté étudiant
8. upload et téléchargement d’un PDF
9. rejet d’un fichier trop gros ou non autorisé
10. création d’une séance depuis une ressource
11. persistance après redéploiement via PostgreSQL
12. fonctionnement local SQLite
13. absence de doublons lors du réamorçage des 55 séances officielles

## 13. Déploiement

Le service Render est configuré avec auto-déploiement sur la branche principale. Une fois les changements poussés sur `main`, le déploiement doit se déclencher automatiquement ; aucun déclenchement manuel supplémentaire n’est nécessaire sauf si l’auto-déploiement est désactivé côté Render.

## 14. Hors périmètre V1

- comptes enseignants individuels complets
- SSO universitaire
- stockage vidéo interne
- versionning avancé des ressources
- commentaires collaboratifs
- notifications
- workflow de validation éditoriale

Ces éléments pourront être ajoutés plus tard sans remettre en cause la structure de données proposée.

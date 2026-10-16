# Migration SUAPS vers Google Cloud

Cette branche prépare une migration de l'application SUAPS depuis Render vers Google Cloud sans modifier la branche de production `main`.

## Architecture cible

- Application Streamlit : Cloud Run
- Base PostgreSQL : Cloud SQL for PostgreSQL 16
- Secrets : Secret Manager
- Code source : GitHub
- APK Android : conservée, avec changement d'URL uniquement après validation de la version Cloud Run

Région recommandée : `europe-west9` (Paris) pour Cloud Run et Cloud SQL.

## 1. Point d'entrée de l'application

La production Render actuelle lance :

```bash
streamlit run v14_complete.py --server.port $PORT --server.address 0.0.0.0
```

Le Dockerfile de cette branche a été aligné sur ce point d'entrée.

## 2. Sauvegarder la base Render avant toute migration

La base Render doit être accessible avant l'export.

Exemple d'export PostgreSQL au format custom :

```bash
pg_dump "$DATABASE_URL" \
  --format=custom \
  --no-owner \
  --no-acl \
  --file=suaps_uppa_db.dump
```

Ne jamais enregistrer `DATABASE_URL`, un mot de passe ou une clé dans GitHub.

## 3. Créer le projet Google Cloud

Définir les variables locales :

```bash
export PROJECT_ID="VOTRE_PROJECT_ID"
export REGION="europe-west9"
export SERVICE="suaps-uppa"
export SQL_INSTANCE="suaps-uppa-db"
```

Activer les API nécessaires :

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

## 4. Créer Cloud SQL PostgreSQL 16

Créer l'instance avec une configuration adaptée au niveau de service souhaité, dans la même région que Cloud Run.

Créer ensuite :

- la base `suaps_uppa_db`
- un utilisateur applicatif dédié
- un mot de passe fort

Le mot de passe doit être stocké dans Secret Manager.

## 5. Restaurer la base

Pour un dump créé avec `pg_dump --format=custom`, utiliser `pg_restore`.

Exemple :

```bash
pg_restore \
  --no-owner \
  --no-acl \
  --dbname="postgresql://UTILISATEUR:MOT_DE_PASSE@HOTE/suaps_uppa_db" \
  suaps_uppa_db.dump
```

Après restauration, vérifier au minimum les tables et les volumes d'enregistrements : étudiants/utilisateurs, inscriptions, offres/créneaux, séances, présences, évaluations, ressources pédagogiques et compétitions.

## 6. Déployer Cloud Run

Construire l'image depuis cette branche ou depuis le dépôt cloné :

```bash
gcloud builds submit --tag "$REGION-docker.pkg.dev/$PROJECT_ID/suaps/suaps-uppa"
```

Puis déployer :

```bash
gcloud run deploy "$SERVICE" \
  --image "$REGION-docker.pkg.dev/$PROJECT_ID/suaps/suaps-uppa" \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8501
```

Associer ensuite l'instance Cloud SQL au service Cloud Run et fournir les paramètres de connexion via Secret Manager / variables d'environnement.

L'application lit déjà :

- `DATABASE_URL`
- `APP_BASE_URL`

`APP_BASE_URL` doit correspondre à l'URL publique Cloud Run finale.

## 7. Tests avant bascule

Ne pas modifier l'APK tant que ces tests ne sont pas validés :

- ouverture de l'application
- authentification / accès enseignant
- affichage des étudiants
- offres et créneaux
- import Excel/CSV
- inscriptions
- QR code
- présences
- notes et observations
- exports
- ressources pédagogiques
- compétition
- persistance des données après redéploiement

## 8. Bascule APK

Une fois l'URL Cloud Run validée, modifier dans :

`app/src/main/java/fr/univpau/suaps/MainActivity.kt`

les constantes :

```kotlin
private const val APP_URL = "https://NOUVELLE_URL_CLOUD_RUN"
private const val APP_HOST = "NOUVEL_HOTE_CLOUD_RUN"
```

Puis reconstruire l'APK avec le workflow GitHub existant.

## 9. Retour arrière

Tant que Render reste actif :

- ne pas supprimer `render.yaml`
- ne pas supprimer le service Render
- ne pas supprimer l'ancienne base avant validation complète
- conserver un dump PostgreSQL hors de Render

La branche `main` reste la référence de production tant que la migration n'est pas validée.

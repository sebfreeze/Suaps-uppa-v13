# SUAPS UPPA V13 — test en ligne sécurisé

## Architecture recommandée pour 10 testeurs

- Application : Streamlit Community Cloud
- Base persistante : PostgreSQL gratuit (Supabase ou Neon)
- Connexion DB : `DATABASE_URL` avec SSL
- Accès test : `TEST_ACCESS_CODE`
- Accès enseignant : `TEACHER_ACCESS_CODE`
- APK : WebView Android pointant vers l'URL Streamlit

## 1. Créer la base PostgreSQL

Créez un projet Supabase/Neon gratuit et copiez la chaîne de connexion PostgreSQL.
Elle doit commencer par `postgresql://` et utiliser SSL.

## 2. Déployer sur Streamlit Community Cloud

Placez le dossier `suaps_presence_app` dans GitHub puis créez une application Streamlit avec `app.py`.

Dans **App settings > Secrets**, ajoutez :

```toml
DATABASE_URL = "postgresql://..."
APP_BASE_URL = "https://votre-app.streamlit.app"
TEST_ACCESS_CODE = "votre-code-test"
TEACHER_ACCESS_CODE = "votre-code-enseignant"
```

Au premier lancement, les tables sont créées automatiquement.

## 3. Sécurité pour le test

- Utilisez des comptes/données fictifs ou pseudonymisés.
- Partagez le code test uniquement aux 10 testeurs.
- Gardez le code enseignant séparé.
- Ne placez jamais `DATABASE_URL` dans GitHub.
- L'URL publique doit être HTTPS.

## 4. APK Android

Le projet Android fourni avec la V13 demande l'adresse de l'application au premier lancement.
Collez simplement l'URL `https://...streamlit.app`.
L'adresse est ensuite mémorisée sur le téléphone.

Un workflow GitHub Actions est inclus pour générer automatiquement un APK debug.

# SUAPS UPPA V12 — mise en ligne

Cette version est prête à être déployée comme application web Streamlit.

## Option simple : Render

1. Décompresser le dossier V12.
2. Placer le contenu dans un dépôt GitHub privé ou public.
3. Sur Render, créer un nouveau **Blueprint** ou **Web Service** depuis le dépôt.
4. Render détectera le `render.yaml` / `Dockerfile`.
5. Une fois l'URL publique attribuée, l'application détecte automatiquement le domaine Render.
6. Les QR codes de présence et d'inscription utilisent alors directement l'URL publique.

## Variable optionnelle APP_BASE_URL

Sur tout autre hébergeur, définir :

`APP_BASE_URL=https://votre-domaine.fr`

Ainsi, tous les QR codes et liens étudiants seront générés avec la bonne adresse.

## Données

Le prototype utilise SQLite (`suaps_presence.db`). Pour une démonstration en ligne, cela fonctionne sur une instance unique.
Pour une mise en production institutionnelle, prévoir une base persistante gérée, des sauvegardes, une authentification UPPA/SSO et la politique RGPD de l'établissement.

## Lancement local avec Docker

```bash
docker build -t suaps-uppa .
docker run -p 8501:8501 suaps-uppa
```

Puis ouvrir `http://localhost:8501`.

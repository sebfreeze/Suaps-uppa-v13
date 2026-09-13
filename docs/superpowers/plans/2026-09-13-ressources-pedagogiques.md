# Espace Ressources pédagogiques Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter à l’application SUAPS UPPA un espace de ressources pédagogiques persistant, partagé entre enseignants, consultable sélectivement par les étudiants, préchargé avec 55 séances officielles et relié aux séances de présence existantes.

**Architecture:** Le service Render exécute `app_design.py`, qui charge puis transforme `app.py` avant exécution. La logique métier du nouveau module doit donc rester hors de ces deux gros fichiers, dans `pedagogie_resources.py` pour la persistance, la sécurité et l’UI, et `pedagogie_seed.py` pour le fonds officiel. `app.py` ne reçoit que les appels d’initialisation, les entrées de navigation et les appels de rendu ; `app_design.py` continue de fournir la couche graphique sans dupliquer la logique pédagogique.

**Tech Stack:** Python 3.12, Streamlit >=1.36, SQLite local, PostgreSQL via psycopg >=3.2, bibliothèque standard (`hashlib`, `hmac`, `secrets`, `json`, `urllib.parse`, `mimetypes`), pytest pour les tests de développement.

**Spec:** `docs/superpowers/specs/2026-09-13-ressources-pedagogiques-design.md`

## Global Constraints

- Les ressources créées par un enseignant sont visibles immédiatement par tous les enseignants.
- La visibilité étudiante est indépendante et vaut `0` par défaut.
- Les ressources officielles SUAPS sont protégées des modifications ordinaires.
- Les vidéos sont des liens HTTP/HTTPS ; aucun fichier vidéo n’est stocké.
- Les fichiers acceptés sont limités à 5 Mo par ressource.
- Les données doivent fonctionner avec PostgreSQL en ligne et SQLite local.
- Les fichiers doivent être stockés en base, jamais seulement sur le disque Render.
- Les codes auteur sont stockés sous forme PBKDF2-HMAC salée, jamais en clair.
- Le code administrateur est lu uniquement depuis `PEDAGOGY_ADMIN_CODE`; s’il n’est pas configuré, les actions administrateur sont désactivées proprement.
- Le service Render déploie `app_design.py` via Docker et l’auto-déploiement est actif sur la branche principale.
- Ne pas déplacer ni réécrire les correctifs V14/V15 existants de `app_design.py` et `sitecustomize.py` sauf nécessité directement liée au module.

---

## Cartographie des fichiers

- **Créer `pedagogie_resources.py`** — schéma SQL, validations, hachage des codes, CRUD des ressources, téléchargement des blobs, filtres, droits auteur/admin et rendu Streamlit des écrans enseignant/étudiant.
- **Créer `pedagogie_seed.py`** — contenu structuré des 55 séances officielles et fonction d’amorçage idempotente.
- **Modifier `app.py`** — importer le module, initialiser le schéma, ajouter `ressource_id` à `seances`, amorcer les ressources officielles, ajouter les entrées de navigation et appeler le rendu.
- **Ne modifier `app_design.py` que si nécessaire** — son rôle reste d’appliquer le design puis d’exécuter `app.py`; le nouveau module doit hériter du design existant sans patch de chaîne additionnel.
- **Créer `tests/test_pedagogie_resources.py`** — tests SQLite des validations, du CRUD, de l’autorisation et de la liaison avec `seances`.
- **Créer `tests/test_pedagogie_seed.py`** — tests du catalogue des 55 séances et de l’amorçage idempotent.
- **Créer `requirements-dev.txt`** — dépendances de test sans alourdir l’image de production.
- **Modifier `README.md`** — documenter l’espace ressources, les droits et la variable `PEDAGOGY_ADMIN_CODE`.

---

### Task 1: Socle de persistance, sécurité et validations

**Files:**
- Create: `pedagogie_resources.py`
- Create: `tests/test_pedagogie_resources.py`
- Create: `requirements-dev.txt`

**Interfaces:**
- Consumes: une fabrique `get_conn: Callable[[], ConnectionLike]` compatible avec la `CompatConnection` de `app.py`; `use_postgres: bool`.
- Produces: `init_pedagogy_schema(get_conn, use_postgres) -> None`, `hash_edit_code(code: str) -> str`, `verify_edit_code(code: str, stored: str) -> bool`, `validate_external_url(url: str) -> str`, `validate_upload(filename: str, mime_type: str, data: bytes) -> tuple[str, str, int]`, `create_resource(...) -> None`, `update_resource(...) -> None`, `delete_resource(...) -> None`, `list_resources(...) -> list[dict]`, `get_resource(...) -> dict | None`, `get_resource_file(...) -> tuple[str, str, bytes] | None`, `can_edit_resource(resource: dict, author: str, author_code: str, admin_code: str, configured_admin_code: str) -> bool`.

- [ ] **Step 1: Ajouter pytest comme dépendance de développement**

Créer `requirements-dev.txt` :

```text
-r requirements.txt
pytest>=8.3,<9
```

- [ ] **Step 2: Écrire les tests en échec pour le hachage et les validations**

Dans `tests/test_pedagogie_resources.py`, créer une fabrique SQLite en mémoire et tester :

```python
from pedagogie_resources import (
    hash_edit_code,
    verify_edit_code,
    validate_external_url,
    validate_upload,
)


def test_edit_code_is_salted_and_verifiable():
    a = hash_edit_code("mon-code-123")
    b = hash_edit_code("mon-code-123")
    assert a != b
    assert verify_edit_code("mon-code-123", a)
    assert not verify_edit_code("mauvais", a)


def test_external_url_only_accepts_http_https():
    assert validate_external_url("https://youtu.be/abc") == "https://youtu.be/abc"
    with pytest.raises(ValueError):
        validate_external_url("javascript:alert(1)")


def test_upload_rejects_more_than_5mb():
    with pytest.raises(ValueError, match="5 Mo"):
        validate_upload("fiche.pdf", "application/pdf", b"x" * (5 * 1024 * 1024 + 1))
```

Inclure aussi les cas acceptés : `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.png`, `.jpg`, `.jpeg`; rejeter une extension non autorisée même si le MIME déclaré paraît acceptable.

- [ ] **Step 3: Lancer les tests de validation et vérifier qu’ils échouent**

Run: `python -m pytest tests/test_pedagogie_resources.py -v`

Expected: FAIL avec `ModuleNotFoundError: No module named 'pedagogie_resources'`.

- [ ] **Step 4: Implémenter le hachage et les validations minimales**

Dans `pedagogie_resources.py`, utiliser PBKDF2-HMAC SHA-256 avec sel aléatoire de 16 octets et 200 000 itérations :

```python
MAX_FILE_BYTES = 5 * 1024 * 1024
PBKDF2_ITERATIONS = 200_000
ALLOWED_FILES = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/octet-stream"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
}


def hash_edit_code(code: str) -> str:
    cleaned = code.strip()
    if len(cleaned) < 6:
        raise ValueError("Le code de modification doit contenir au moins 6 caractères.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", cleaned.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_edit_code(code: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", code.strip().encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError):
        return False
```

`validate_external_url()` doit retourner `""` pour une chaîne vide et lever `ValueError` si le schéma n’est pas `http`/`https` ou si `netloc` est vide. `validate_upload()` doit normaliser l’extension en minuscules, vérifier extension + MIME + taille, et retourner `(filename_safe_display, mime_type, size)` sans jamais construire de chemin local.

- [ ] **Step 5: Ajouter les tests en échec du schéma et du CRUD SQLite**

Le schéma attendu :

```sql
CREATE TABLE IF NOT EXISTS ressources_pedagogiques(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seed_key TEXT UNIQUE,
    activite TEXT NOT NULL,
    type_ressource TEXT NOT NULL,
    titre TEXT NOT NULL,
    description TEXT,
    contenu_json TEXT,
    auteur TEXT NOT NULL,
    auteur_code_hash TEXT,
    date_creation TEXT NOT NULL,
    date_modification TEXT NOT NULL,
    visible_etudiants INTEGER NOT NULL DEFAULT 0,
    officiel_suaps INTEGER NOT NULL DEFAULT 0,
    lien_externe TEXT,
    nom_fichier TEXT,
    mime_type TEXT,
    taille_fichier INTEGER,
    fichier_data BLOB
)
```

Pour PostgreSQL, `id` est `SERIAL PRIMARY KEY` et `fichier_data` est `BYTEA`; tous les autres champs gardent les mêmes noms et sens. Ajouter un index `idx_ressources_pedagogiques_filters` sur `(activite, type_ressource, officiel_suaps, visible_etudiants)`.

Les tests doivent prouver : création, liste sans charger `fichier_data`, récupération du blob à la demande, mise à jour, suppression, filtre étudiant, et conservation du binaire octet pour octet.

- [ ] **Step 6: Lancer les tests CRUD et vérifier qu’ils échouent**

Run: `python -m pytest tests/test_pedagogie_resources.py -v`

Expected: FAIL sur les fonctions de schéma/CRUD non définies.

- [ ] **Step 7: Implémenter le schéma et le CRUD minimal**

Règles d’implémentation :

```python
RESOURCE_TYPES = ("Progression", "Séance", "Compétences / barèmes", "Document", "Vidéo / lien")


def list_resources(get_conn, *, student_only=False, activity=None, resource_type=None, author=None, query=None):
    # SELECT explicite sans fichier_data
    # WHERE visible_etudiants=1 lorsque student_only=True
    # paramètres SQL uniquement, aucun assemblage avec des valeurs utilisateur
    ...
```

Les fonctions `create_resource` et `update_resource` doivent encoder `contenu` via `json.dumps(..., ensure_ascii=False)` et valider le lien/fichier avant l’écriture. Pour les ressources enseignant, `auteur_code_hash` est obligatoire; pour une ressource officielle, il reste `NULL`.

- [ ] **Step 8: Implémenter et tester les règles d’autorisation**

`can_edit_resource` doit appliquer exactement cet ordre :

```python
if configured_admin_code and admin_code and hmac.compare_digest(admin_code, configured_admin_code):
    return True
if bool(resource["officiel_suaps"]):
    return False
return (
    author.strip().casefold() == str(resource["auteur"]).strip().casefold()
    and verify_edit_code(author_code, resource["auteur_code_hash"] or "")
)
```

Ajouter les tests : auteur + bon code = autorisé; auteur + mauvais code = refusé; autre auteur = refusé; officiel = refusé hors admin; admin configuré + bon code = autorisé; admin non configuré = jamais autorisé par la voie admin.

- [ ] **Step 9: Exécuter le fichier de tests complet**

Run: `python -m pytest tests/test_pedagogie_resources.py -v`

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add pedagogie_resources.py tests/test_pedagogie_resources.py requirements-dev.txt
git commit -m "feat: add pedagogical resources data layer"
```

---

### Task 2: Fonds officiel de 55 séances pédagogiques

**Files:**
- Create: `pedagogie_seed.py`
- Create: `tests/test_pedagogie_seed.py`
- Modify: `pedagogie_resources.py`

**Interfaces:**
- Consumes: `create_resource(..., seed_key=..., official=True)` depuis Task 1.
- Produces: `OFFICIAL_SESSIONS: tuple[dict, ...]`, `seed_official_resources(get_conn, use_postgres) -> int`.

- [ ] **Step 1: Écrire le test de structure du catalogue**

Le test doit vérifier exactement 55 séances et la répartition suivante :

```python
expected = {
    "Natation": 10,
    "Rugby": 10,
    "Sauvetage / SSA": 10,
    "Course à pied": 10,
    "Pelote Basque": 10,
    "Surf": 5,
}
```

Chaque entrée doit contenir : `seed_key`, `activite`, `numero`, `titre`, `objectif`, `competences`, `materiel`, `echauffement`, `situations`, `variables`, `criteres_reussite`, `securite`, `retour_bilan`. Chaque liste (`competences`, `materiel`, `situations`, `variables`, `criteres_reussite`, `securite`) doit être non vide.

- [ ] **Step 2: Fixer les 55 intitulés et objectifs du fonds initial**

Utiliser exactement cette progression comme squelette éditorial :

| Activité | N° | Titre | Objectif principal |
|---|---:|---|---|
| Natation | 1 | Diagnostic et aisance aquatique | Situer le niveau initial et installer les règles de sécurité |
| Natation | 2 | Respiration et équilibre | Expirer dans l’eau et stabiliser un corps aligné |
| Natation | 3 | Propulsion et coulée | Produire une propulsion efficace et conserver la glisse |
| Natation | 4 | Crawl : coordination complète | Coordonner respiration, bras et battements |
| Natation | 5 | Dos crawlé | Se déplacer efficacement sur le dos avec repères stables |
| Natation | 6 | Endurance continue | Maintenir une nage économique sur une durée prolongée |
| Natation | 7 | Virages et reprises de nage | Réduire les pertes de vitesse aux changements de longueur |
| Natation | 8 | Fréquence, amplitude et efficacité | Adapter fréquence et amplitude pour nager plus efficacement |
| Natation | 9 | Parcours combiné | Enchaîner plusieurs contraintes techniques sans rupture |
| Natation | 10 | Évaluation finale | Mesurer les progrès techniques, énergétiques et méthodologiques |
| Rugby | 1 | Diagnostic et manipulation du ballon | Observer les acquis et sécuriser les manipulations |
| Rugby | 2 | Passe et réception en mouvement | Faire vivre le ballon sans casser la course |
| Rugby | 3 | Soutien du porteur | Se rendre disponible avant et après la passe |
| Rugby | 4 | Occuper et utiliser l’espace | Écarter le jeu et attaquer les intervalles |
| Rugby | 5 | Surnombre : 2 contre 1 et 3 contre 2 | Fixer puis donner au bon moment |
| Rugby | 6 | Défendre ensemble | Monter, cadrer et communiquer collectivement |
| Rugby | 7 | Contact et plaquage sécurisé | Entrer dans le contact avec maîtrise et sécurité |
| Rugby | 8 | Continuité après contact | Conserver ou libérer rapidement le ballon |
| Rugby | 9 | Projet collectif | Organiser des principes communs d’attaque et de défense |
| Rugby | 10 | Match évalué | Mobiliser les compétences dans une opposition aménagée |
| Sauvetage / SSA | 1 | Sécurité et diagnostic aquatique | Identifier les risques et situer les capacités initiales |
| Sauvetage / SSA | 2 | Nage d’approche efficace | Rejoindre rapidement une zone d’intervention en gardant des réserves |
| Sauvetage / SSA | 3 | Immersion et récupération d’objet | Descendre, s’orienter et remonter en contrôle |
| Sauvetage / SSA | 4 | Prise du mannequin | Saisir et stabiliser un mannequin sans perte de temps |
| Sauvetage / SSA | 5 | Remorquage | Transporter une victime/mannequin en conservant les voies aériennes dégagées |
| Sauvetage / SSA | 6 | Sortie d’eau | Extraire une victime selon les moyens disponibles et en sécurité |
| Sauvetage / SSA | 7 | Prise en charge à terre | Organiser l’alerte, le bilan et la conduite à tenir dans le cadre pédagogique |
| Sauvetage / SSA | 8 | Scénarios d’intervention | Choisir une réponse adaptée à plusieurs situations simulées |
| Sauvetage / SSA | 9 | Parcours complet | Enchaîner approche, immersion, remorquage et sortie |
| Sauvetage / SSA | 10 | Évaluation finale | Réaliser un scénario complet avec efficacité et sécurité |
| Course à pied | 1 | Diagnostic d’allure | Identifier son niveau et ses allures de référence |
| Course à pied | 2 | Régularité d’allure | Courir à une vitesse cible avec peu de variation |
| Course à pied | 3 | Technique de course | Améliorer posture, appuis et relâchement |
| Course à pied | 4 | VMA et intensités | Comprendre et expérimenter des intensités courtes |
| Course à pied | 5 | Fractionné court | Répéter des efforts rapides avec récupération maîtrisée |
| Course à pied | 6 | Endurance fondamentale | Soutenir un effort continu à intensité modérée |
| Course à pied | 7 | Travail au seuil | Maintenir une allure soutenue sans départ excessif |
| Course à pied | 8 | Gestion de course | Construire une stratégie d’allure selon distance et objectif |
| Course à pied | 9 | Séance autonome | Concevoir et conduire une séance simple adaptée à son objectif |
| Course à pied | 10 | Évaluation finale | Mesurer la progression et justifier sa stratégie de course |
| Pelote Basque | 1 | Prise en main et sécurité | Découvrir matériel, espace, règles et frappe de base |
| Pelote Basque | 2 | Frappe et contrôle | Stabiliser le geste pour envoyer la balle dans une zone choisie |
| Pelote Basque | 3 | Placement sous la trajectoire | Se déplacer tôt et frapper en équilibre |
| Pelote Basque | 4 | Lire les trajectoires | Anticiper rebonds, hauteur et profondeur |
| Pelote Basque | 5 | Précision des zones | Viser des zones pour déplacer l’adversaire |
| Pelote Basque | 6 | Déplacement et replacement | Enchaîner frappe, replacement et nouvelle prise d’information |
| Pelote Basque | 7 | Construire le point | Alterner profondeur, largeur et rythme |
| Pelote Basque | 8 | Opposition aménagée | Réinvestir les techniques dans des échanges à thème |
| Pelote Basque | 9 | Choix tactiques | Identifier un rapport de force et adapter son jeu |
| Pelote Basque | 10 | Évaluation finale | Jouer un match aménagé avec critères techniques et tactiques |
| Surf | 1 | Lire le milieu et se mettre en sécurité | Identifier zone, courant, priorité et conduite à tenir |
| Surf | 2 | Rame et position sur la planche | Se placer et produire une rame efficace |
| Surf | 3 | Passage de barre | Choisir sa trajectoire et franchir les mousses en sécurité |
| Surf | 4 | Take-off | Se redresser rapidement en conservant équilibre et direction |
| Surf | 5 | Mise en situation et autonomie | Choisir une vague adaptée, partir et respecter les priorités |

Pour chaque séance, rédiger du contenu réellement exploitable : un échauffement, 2 à 4 situations d’apprentissage, au moins 2 variables, 2 critères de réussite et 2 consignes de sécurité spécifiques à l’activité. Ne pas écrire de formulations génériques répétées entre toutes les séances.

- [ ] **Step 3: Lancer le test de catalogue et vérifier qu’il échoue**

Run: `python -m pytest tests/test_pedagogie_seed.py -v`

Expected: FAIL car `pedagogie_seed.py` n’existe pas encore.

- [ ] **Step 4: Implémenter `OFFICIAL_SESSIONS` et les clés stables**

Format d’une entrée :

```python
{
    "seed_key": "suaps:natation:01",
    "activite": "Natation",
    "numero": 1,
    "titre": "Diagnostic et aisance aquatique",
    "objectif": "Situer le niveau initial et installer les règles de sécurité.",
    "competences": ["Entrer dans l’eau en sécurité", "S’immerger et se déplacer sans appréhension"],
    "materiel": ["Planches", "Frites", "Plots de bord"],
    "echauffement": "...",
    "situations": ["...", "..."],
    "variables": ["...", "..."],
    "criteres_reussite": ["...", "..."],
    "securite": ["...", "..."],
    "retour_bilan": "...",
}
```

Les 55 `seed_key` suivent `suaps:<slug-activite>:<numero-2-chiffres>` et sont uniques.

- [ ] **Step 5: Écrire le test d’amorçage idempotent**

Le test doit : initialiser la table, appeler `seed_official_resources()` deux fois, vérifier que le premier appel crée 55 ressources, que le second en crée 0, puis vérifier `COUNT(*) = 55` et `officiel_suaps = 1` pour toutes.

- [ ] **Step 6: Implémenter `seed_official_resources`**

Chaque entrée devient une ressource `type_ressource="Séance"`, `auteur="SUAPS UPPA"`, `visible_etudiants=0`, `officiel_suaps=1`; `contenu_json` contient toutes les rubriques pédagogiques. L’insertion doit utiliser `seed_key` + `ON CONFLICT DO NOTHING` via la compatibilité SQL existante ou une vérification préalable portable.

- [ ] **Step 7: Exécuter les tests du fonds officiel**

Run: `python -m pytest tests/test_pedagogie_seed.py tests/test_pedagogie_resources.py -v`

Expected: PASS, 55 ressources après deux amorçages.

- [ ] **Step 8: Commit**

```bash
git add pedagogie_seed.py tests/test_pedagogie_seed.py pedagogie_resources.py
git commit -m "feat: seed 55 SUAPS pedagogical sessions"
```

---

### Task 3: Liaison entre ressource pédagogique et séance de présence

**Files:**
- Modify: `pedagogie_resources.py`
- Modify: `tests/test_pedagogie_resources.py`
- Modify: `app.py` around `CREATE TABLE IF NOT EXISTS seances(...)` and immediately after `init_db()`

**Interfaces:**
- Consumes: `get_conn`, `exec_sql`, table `seances` existante.
- Produces: `ensure_seance_resource_column(get_conn, use_postgres) -> None`, `create_seance_from_resource(exec_sql, resource, date_seance: str, groupe: str) -> None`.

- [ ] **Step 1: Écrire les tests de migration**

SQLite : créer une table `seances` ancienne sans `ressource_id`, appeler `ensure_seance_resource_column`, puis vérifier via `PRAGMA table_info(seances)` que la colonne existe. Rappeler la fonction une seconde fois et vérifier qu’aucune erreur ne survient.

- [ ] **Step 2: Exécuter le test et vérifier l’échec**

Run: `python -m pytest tests/test_pedagogie_resources.py -k seance_resource -v`

Expected: FAIL fonction non définie.

- [ ] **Step 3: Implémenter la migration portable**

Pour SQLite, lire `PRAGMA table_info(seances)`. Pour PostgreSQL, interroger :

```sql
SELECT 1
FROM information_schema.columns
WHERE table_schema='public'
  AND table_name='seances'
  AND column_name='ressource_id'
```

Si absente, exécuter `ALTER TABLE seances ADD COLUMN ressource_id INTEGER` puis commit. Ne pas ajouter de contrainte FK à chaud afin d’éviter de fragiliser les bases existantes; la cohérence est contrôlée applicativement.

- [ ] **Step 4: Écrire le test de création d’une séance depuis une ressource**

Le test doit vérifier qu’un appel avec une ressource `id=7`, `activite="Natation"`, `titre="Crawl : coordination complète"`, une date et un groupe insère : activité `Natation`, thème `Crawl : coordination complète`, groupe choisi, `ressource_id=7`, sans ouvrir le check-in.

- [ ] **Step 5: Implémenter `create_seance_from_resource`**

```python
def create_seance_from_resource(exec_sql, resource, date_seance: str, groupe: str) -> None:
    exec_sql(
        "INSERT INTO seances(activite,date_seance,groupe,theme,ressource_id) VALUES(?,?,?,?,?)",
        (
            str(resource["activite"]),
            date_seance,
            groupe.strip(),
            str(resource["titre"]),
            int(resource["id"]),
        ),
    )
```

- [ ] **Step 6: Brancher l’initialisation dans `app.py`**

Après `init_db()` :

```python
from pedagogie_resources import init_pedagogy_schema, ensure_seance_resource_column
from pedagogie_seed import seed_official_resources

init_pedagogy_schema(get_conn, USE_POSTGRES)
ensure_seance_resource_column(get_conn, USE_POSTGRES)
seed_official_resources(get_conn, USE_POSTGRES)
```

Conserver l’appel `init_db()` existant avant ces trois appels.

- [ ] **Step 7: Exécuter les tests**

Run: `python -m pytest tests/test_pedagogie_resources.py tests/test_pedagogie_seed.py -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add pedagogie_resources.py tests/test_pedagogie_resources.py app.py
git commit -m "feat: link pedagogical resources to sessions"
```

---

### Task 4: Interface enseignant — consulter, créer, dupliquer, modifier et supprimer

**Files:**
- Modify: `pedagogie_resources.py`
- Modify: `tests/test_pedagogie_resources.py`

**Interfaces:**
- Consumes: CRUD Task 1, catalogue Task 2, liaison Task 3, `activities`, `secret_value("PEDAGOGY_ADMIN_CODE")`, `exec_sql`.
- Produces: `render_teacher_resources(st, *, get_conn, use_postgres, exec_sql, activities, admin_code_value) -> None`.

- [ ] **Step 1: Ajouter les helpers de contenu testables avant l’UI**

Écrire les tests puis fonctions :

```python
def resource_card_summary(resource: dict) -> dict:
    return {
        "title": resource["titre"],
        "subtitle": f'{resource["activite"]} • {resource["type_ressource"]}',
        "author": resource["auteur"],
        "official": bool(resource["officiel_suaps"]),
        "student_visible": bool(resource["visible_etudiants"]),
    }


def duplicate_payload(resource: dict, new_author: str) -> dict:
    return {
        "activite": resource["activite"],
        "type_ressource": resource["type_ressource"],
        "titre": f'Copie — {resource["titre"]}',
        "description": resource.get("description") or "",
        "contenu": resource.get("contenu") or {},
        "auteur": new_author.strip(),
        "visible_etudiants": 0,
        "officiel_suaps": 0,
    }
```

Tester qu’une duplication d’une ressource officielle ne copie ni `officiel_suaps=1`, ni `seed_key`, ni le fichier binaire par défaut; l’enseignant choisit ensuite d’attacher un fichier si nécessaire.

- [ ] **Step 2: Construire la page enseignant en cinq zones**

La fonction `render_teacher_resources` doit afficher :

1. bandeau `📚 Ressources pédagogiques` + compteur total;
2. filtres activité/type/auteur/officiel/visibilité + recherche texte;
3. liste/cartes des résultats avec badge `Officiel SUAPS`;
4. zone `Ajouter une ressource` dans un expander/formulaire;
5. zone d’action sur la ressource sélectionnée : consulter, dupliquer, créer une séance, modifier/supprimer.

Le formulaire de création doit demander : activité, type, titre, description, nom/prénom auteur, code de modification (>=6), visibilité étudiant, lien facultatif, fichier facultatif. Pour `type_ressource="Séance"`, afficher les champs structurés : objectif, compétences, matériel, échauffement, situations, variables, critères, sécurité, retour/bilan.

- [ ] **Step 3: Implémenter le téléchargement à la demande**

Ne jamais charger tous les blobs pendant la liste. Lorsque la ressource sélectionnée possède `nom_fichier`, appeler `get_resource_file()` puis :

```python
st.download_button(
    "⬇️ Télécharger le document",
    data=file_bytes,
    file_name=file_name,
    mime=mime_type or "application/octet-stream",
    use_container_width=True,
)
```

- [ ] **Step 4: Implémenter la duplication**

Le bouton `Dupliquer` ouvre un petit formulaire demandant `Auteur` + nouveau `Code de modification`, crée une ressource enseignant avec `visible_etudiants=0`, puis `st.rerun()`.

- [ ] **Step 5: Implémenter “Créer une séance à partir de cette ressource”**

Afficher date + groupe, puis appeler `create_seance_from_resource`. Après succès, afficher `Séance créée : elle est maintenant disponible dans Présences / QR-NFC.`

- [ ] **Step 6: Implémenter modification/suppression avec contrôle d’autorisation**

Le formulaire d’accès à l’édition accepte soit :

- auteur déclaré + code auteur;
- ou code administrateur.

`PEDAGOGY_ADMIN_CODE` n’est jamais affiché. Si la variable est vide, ne pas afficher comme si un admin était configuré; indiquer seulement dans l’espace enseignant `Administration globale non configurée` dans une aide discrète.

Une ressource officielle ne peut être modifiée/supprimée que par l’admin. Une ressource enseignant peut être modifiée/supprimée par son auteur ou l’admin. La modification peut changer la visibilité étudiant.

- [ ] **Step 7: Ajouter les tests des transformations de contenu et permissions**

Run: `python -m pytest tests/test_pedagogie_resources.py -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add pedagogie_resources.py tests/test_pedagogie_resources.py
git commit -m "feat: add teacher pedagogical resources UI"
```

---

### Task 5: Interface étudiant et navigation de l’application live

**Files:**
- Modify: `pedagogie_resources.py`
- Modify: `app.py` around the role-specific `Navigation` radio and page dispatch chain
- Verify: `app_design.py` remains the Docker entrypoint and still ends with `exec(compile(source, ...))`

**Interfaces:**
- Consumes: `list_resources(..., student_only=True)`.
- Produces: `render_student_resources(st, *, get_conn) -> None` and navigation entries `Ressources pédagogiques` for both roles.

- [ ] **Step 1: Implémenter la vue étudiant en lecture seule**

`render_student_resources` doit :

- appeler `list_resources(student_only=True)`;
- proposer filtres activité/type + recherche;
- afficher titre, activité, description, auteur et document/lien;
- ne rendre aucun contrôle de création, édition, suppression, duplication ou changement de visibilité;
- afficher `Aucune ressource n’est actuellement partagée avec les étudiants.` quand la liste est vide.

- [ ] **Step 2: Ajouter la navigation enseignant dans `app.py`**

Ajouter `"Ressources pédagogiques"` dans la liste du `st.sidebar.radio("Navigation", [...])` du mode Enseignant, idéalement après `"Tableau de bord"` et avant les écrans de gestion opérationnelle.

Ajouter un dispatch :

```python
elif menu == "Ressources pédagogiques":
    render_teacher_resources(
        st,
        get_conn=get_conn,
        use_postgres=USE_POSTGRES,
        exec_sql=exec_sql,
        activities=ACTIVITES,
        admin_code_value=secret_value("PEDAGOGY_ADMIN_CODE", "").strip(),
    )
```

- [ ] **Step 3: Ajouter la navigation étudiant dans `app.py`**

Passer de `["Accueil", "Portail étudiant"]` à `["Accueil", "Portail étudiant", "Ressources pédagogiques"]` et, dans le dispatch étudiant, appeler `render_student_resources(st, get_conn=get_conn)`.

- [ ] **Step 4: Vérifier la compatibilité avec `app_design.py`**

Run local de syntaxe :

```bash
python -m py_compile app.py app_design.py pedagogie_resources.py pedagogie_seed.py
```

Expected: aucun message, code retour 0.

Puis lancer :

```bash
streamlit run app_design.py --server.headless=true --server.fileWatcherType=none
```

Vérifier manuellement :

- mode étudiant : l’entrée `Ressources pédagogiques` existe et reste en lecture seule;
- mode enseignant : l’entrée existe et les 55 séances officielles apparaissent;
- les styles V15 s’appliquent aux nouveaux formulaires/cartes;
- les autres menus existants restent accessibles.

- [ ] **Step 5: Commit**

```bash
git add app.py pedagogie_resources.py
git commit -m "feat: expose pedagogical resources in SUAPS navigation"
```

---

### Task 6: Documentation, configuration admin et régression

**Files:**
- Modify: `README.md`
- Modify: `tests/test_pedagogie_resources.py`
- Modify: `tests/test_pedagogie_seed.py`

**Interfaces:**
- Consumes: module complet Tasks 1–5.
- Produces: documentation d’exploitation et suite de régression complète.

- [ ] **Step 1: Documenter le module dans `README.md`**

Ajouter une section `Version suivante — Ressources pédagogiques` indiquant :

- 55 séances officielles préchargées;
- ressources partagées entre enseignants;
- documents <=5 Mo stockés en base;
- vidéos/liens externes;
- partage étudiant optionnel;
- création d’une séance de présence à partir d’une ressource;
- modification auteur par code;
- administration globale avec variable `PEDAGOGY_ADMIN_CODE`.

Inclure explicitement :

```text
PEDAGOGY_ADMIN_CODE=<secret fort, distinct du code enseignant>
```

Préciser de ne jamais versionner cette valeur dans GitHub.

- [ ] **Step 2: Ajouter le test de régression de volumétrie binaire**

Créer une ressource avec un PDF synthétique de quelques kilo-octets, récupérer le blob et vérifier égalité exacte; vérifier aussi que `list_resources()` ne contient jamais la clé `fichier_data`.

- [ ] **Step 3: Ajouter le test des filtres combinés**

Créer quatre ressources de plusieurs activités/types/auteurs et vérifier les combinaisons activité + type + auteur + texte + étudiant.

- [ ] **Step 4: Lancer toute la suite**

Run:

```bash
python -m pytest -v
```

Expected: PASS.

- [ ] **Step 5: Vérifier la syntaxe de tous les fichiers Python principaux**

Run:

```bash
python -m py_compile app.py app_design.py pedagogie_resources.py pedagogie_seed.py sports_co_module.py sitecustomize.py usercustomize.py
```

Expected: code retour 0.

- [ ] **Step 6: Commit**

```bash
git add README.md tests/test_pedagogie_resources.py tests/test_pedagogie_seed.py
git commit -m "docs: document pedagogical resources rollout"
```

---

### Task 7: Déploiement Render et vérification live

**Files:**
- No code file required if Tasks 1–6 are already committed on `main`.
- Operational configuration: Render environment variable `PEDAGOGY_ADMIN_CODE` when an administrator code is ready.

**Interfaces:**
- Consumes: commits sur `main`, auto-deploy Render, URL APK `https://suaps-uppa-v13.onrender.com`.
- Produces: module visible dans l’application web et donc dans la WebView Android sans reconstruction de l’APK.

- [ ] **Step 1: Vérifier que l’auto-déploiement se déclenche après le dernier commit**

Ne pas appeler de déploiement manuel si Render a déjà lancé un deploy pour le nouveau commit.

- [ ] **Step 2: Surveiller le deploy jusqu’au statut final**

Expected: build réussi, service `live`/`available`, health check `/_stcore/health` OK.

- [ ] **Step 3: Faire un smoke test enseignant live**

Vérifier :

1. accès enseignant existant inchangé;
2. menu `Ressources pédagogiques`;
3. 55 séances officielles présentes;
4. création d’une ressource test sans fichier;
5. création d’une ressource PDF <=5 Mo;
6. téléchargement du PDF;
7. duplication d’une séance officielle;
8. création d’une séance de présence depuis la copie;
9. modification/suppression de la ressource test avec son code auteur.

- [ ] **Step 4: Faire un smoke test étudiant live**

Créer ou modifier une ressource test avec `visible_etudiants=1`, passer en mode étudiant et vérifier qu’elle apparaît en lecture seule. La repasser à `0` et vérifier qu’elle disparaît de la vue étudiant.

- [ ] **Step 5: Vérifier la persistance**

Après un redéploiement ou redémarrage contrôlé, vérifier que la ressource PDF test et ses métadonnées sont toujours accessibles depuis PostgreSQL.

- [ ] **Step 6: Vérifier l’APK Android**

Ouvrir l’APK existant : la WebView doit afficher automatiquement le nouveau menu et les nouveaux écrans puisque `MainActivity.kt` pointe déjà vers `https://suaps-uppa-v13.onrender.com`.

- [ ] **Step 7: Nettoyer les données de smoke test**

Supprimer uniquement les ressources créées pour le test; ne jamais supprimer les 55 ressources `Officiel SUAPS`.

---

## Self-review du plan

- **Couverture de la spec :** catégories, 55 séances, filtres, auteur, partage étudiant, fichiers en base, vidéos par lien, droits auteur/admin, liaison `seances`, compatibilité PostgreSQL/SQLite, sécurité et déploiement sont couverts.
- **Point d’entrée live vérifié :** Docker lance `app_design.py`; celui-ci exécute `app.py`, donc le branchement fonctionnel se fait dans `app.py` et hérite du design V15.
- **Pas de dépendance production inutile :** pytest est isolé dans `requirements-dev.txt`.
- **Pas de stockage local persistant :** tous les fichiers utilisateurs sont des blobs en base.
- **Idempotence :** les séances officielles ont des `seed_key` uniques et l’amorçage est répétable.
- **Droits transitoires explicites :** auteur + code salé, admin par secret Render, sans prétendre disposer de comptes individuels.

FULL_SWIM_TABS = ["⏱️ Chronométrage", "👥 Équipes", "📊 Résultats", "🏅 Classements"]


def allowed_swim_tabs(role):
    if role == "Chronométreur étudiant":
        return ["⏱️ Chronométrage"]
    if role in {"Gestion compétition", "Enseignant"}:
        return list(FULL_SWIM_TABS)
    return []


def navigation_for_role(role):
    if role in {"Chronométreur étudiant", "Gestion compétition"}:
        return ["Accueil", "Compétition"]
    if role == "Étudiant":
        return ["Accueil", "Portail étudiant"]
    return []

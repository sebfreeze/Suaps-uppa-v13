import math
import re

def parse_level(value):
    """Return a sortable numeric level. Larger = stronger."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            if math.isnan(float(value)):
                return 0.0
        except Exception:
            pass
        return float(value)
    text = str(value).strip().lower().replace(",", ".")
    if not text:
        return 0.0
    aliases = {
        "debutant": 1.0, "débutant": 1.0,
        "intermediaire": 2.0, "intermédiaire": 2.0,
        "confirme": 3.0, "confirmé": 3.0,
        "expert": 4.0,
    }
    if text in aliases:
        return aliases[text]
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group(0)) if m else 0.0

def _as_positive_int(value):
    try:
        n = int(float(value))
        return n if n > 0 else None
    except Exception:
        return None

def _center_out_lines(max_lines):
    """Swimming seeding order: center first, then alternating around center."""
    max_lines = max(1, int(max_lines or 5))
    center = (max_lines + 1) / 2.0
    return sorted(range(1, max_lines + 1), key=lambda line: (abs(line - center), line))

def assign_series_lines(rows, max_lines=5):
    """Assign missing series/line using swimming-style seeding.

    Rules:
    - higher series number = stronger heat;
    - strongest teams fill the last series first;
    - the first series may therefore be incomplete;
    - inside each series, lane order is center-out (for 5 lanes: 3,2,4,1,5);
    - explicit series+line assignments are preserved.
    """
    max_lines = max(1, int(max_lines or 5))
    output = [dict(row) for row in rows]
    occupied = set()
    autos = []
    max_locked_series = 0

    for index, row in enumerate(output):
        series = _as_positive_int(row.get("series"))
        line = _as_positive_int(row.get("line"))
        if series and line and line <= max_lines:
            row["series"] = series
            row["line"] = line
            occupied.add((series, line))
            max_locked_series = max(max_locked_series, series)
        else:
            row["series"] = None
            row["line"] = None
            autos.append((parse_level(row.get("level")), index))

    total_rows = len(output)
    series_count = max(
        max_locked_series,
        int(math.ceil(total_rows / float(max_lines))) if total_rows else 1,
    )
    lane_order = _center_out_lines(max_lines)

    # Strongest first, and highest-numbered series first.
    autos.sort(key=lambda item: (item[0], item[1]), reverse=True)
    available_slots = []
    for series in range(series_count, 0, -1):
        for line in lane_order:
            if (series, line) not in occupied:
                available_slots.append((series, line))

    # If manual placements consume so much capacity that more series are needed,
    # append new stronger series above the current last series.
    next_series = series_count + 1
    while len(available_slots) < len(autos):
        for line in lane_order:
            available_slots.insert(0, (next_series, line))
        next_series += 1

    for (_, index), (series, line) in zip(autos, available_slots):
        output[index]["series"] = series
        output[index]["line"] = line

    return output


def normalize_swim_status(value, bonus=False):
    """Normalise les statuts d'engagement importés depuis Excel/CSV."""
    text = str(value or "").strip().lower()
    if not text or text in {"0", "non", "n", "-", "none", "nan"}:
        return None
    if bonus:
        return "Engagé" if text in {"1", "x", "oui", "o", "engage", "engagé", "titulaire", "t"} else None
    if text in {"r", "remplacant", "remplaçant", "remplacement"}:
        return "Remplaçant"
    if text in {"1", "x", "oui", "o", "t", "titulaire", "engage", "engagé"}:
        return "Titulaire"
    return None


def validate_swimmer_entries(entries):
    """Contrôle les plafonds d'effectif sans exiger un effectif complet."""
    errors = []
    limits = {
        "C1": 8,
        "C2-PAP": 2,
        "C2-DOS": 2,
        "C2-BR": 2,
        "C2-NL": 2,
        "C3": 8,
    }
    holders = {code: set() for code in limits}
    replacements = {code: set() for code in limits}
    bonus = set()

    for item in entries:
        swimmer = str(item.get("swimmer") or "").strip()
        code = str(item.get("code") or "").upper()
        status = item.get("status")
        if not swimmer or not status:
            continue
        if code in limits:
            if status == "Remplaçant":
                replacements[code].add(swimmer)
            elif status == "Titulaire":
                holders[code].add(swimmer)
        elif code == "BONUS" and status == "Engagé":
            bonus.add(swimmer)

    labels = {
        "C1": "C1",
        "C2-PAP": "C2 Papillon",
        "C2-DOS": "C2 Dos",
        "C2-BR": "C2 Brasse",
        "C2-NL": "C2 Crawl",
        "C3": "C3",
    }
    for code, maximum in limits.items():
        if len(holders[code]) > maximum:
            errors.append(f"{labels[code]} : maximum {maximum} titulaires")
        if len(replacements[code]) > 1:
            errors.append(f"{labels[code]} : maximum 1 remplaçant")
    if len(bonus) > 12:
        errors.append("BONUS : maximum 12 nageurs")
    return errors

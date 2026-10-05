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

def assign_series_lines(rows, max_lines=5):
    """Assign missing series/line by ascending level.

    Series 1 contains the weakest available teams; higher series numbers
    contain progressively stronger teams. Explicit series+line are preserved.
    """
    max_lines = max(1, int(max_lines or 5))
    output = [dict(row) for row in rows]
    occupied = set()
    autos = []

    for index, row in enumerate(output):
        series = _as_positive_int(row.get("series"))
        line = _as_positive_int(row.get("line"))
        if series and line and line <= max_lines:
            row["series"] = series
            row["line"] = line
            occupied.add((series, line))
        else:
            row["series"] = None
            row["line"] = None
            autos.append((parse_level(row.get("level")), index))

    autos.sort(key=lambda x: (x[0], x[1]))
    series = 1
    line = 1
    for _, index in autos:
        while (series, line) in occupied:
            line += 1
            if line > max_lines:
                series += 1
                line = 1
        output[index]["series"] = series
        output[index]["line"] = line
        occupied.add((series, line))
        line += 1
        if line > max_lines:
            series += 1
            line = 1

    return output

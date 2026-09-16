"""Optimisations de rerun Streamlit sans modifier les fonctions visibles."""

SENTINEL = "# --- suaps performance live ---"


def patch_app_source(source: str) -> str:
    if not isinstance(source, str) or SENTINEL in source:
        return source

    qr_marker = "def ensure_qr_registration_schema():"
    qr_cached = "@st.cache_resource(show_spinner=False)\ndef ensure_qr_registration_schema():"
    if qr_marker in source and qr_cached not in source:
        source = source.replace(
            qr_marker,
            SENTINEL + "\n" + qr_cached,
            1,
        )

    pedagogy_marker = "init_v14_pedagogy(db)"
    if pedagogy_marker in source and "def _suaps_init_pedagogy_once():" not in source:
        source = source.replace(
            pedagogy_marker,
            "@st.cache_resource(show_spinner=False)\n"
            "def _suaps_init_pedagogy_once():\n"
            "    return init_v14_pedagogy(db)\n"
            "_suaps_init_pedagogy_once()",
            1,
        )

    return source

"""Chronomètre navigateur : le temps du toucher est transmis à Streamlit."""
from pathlib import Path
import streamlit.components.v1 as components

_SWIM_TIMER = components.declare_component(
    "suaps_swim_timer_live",
    path=str(Path(__file__).resolve().parent / "swim_timer_frontend"),
)


def render_swim_timer(result_id, running, start_epoch, split_count, relay_count, final_seconds, key, saved_splits=None):
    return _SWIM_TIMER(
        result_id=int(result_id),
        running=bool(running),
        start_epoch=float(start_epoch or 0),
        split_count=int(split_count),
        relay_count=int(relay_count),
        final_seconds=float(final_seconds) if final_seconds is not None else None,
        saved_splits=list(saved_splits or []),
        key=key,
        default=None,
    )

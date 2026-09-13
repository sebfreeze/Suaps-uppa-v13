from pathlib import Path

from streamlit.testing.v1 import AppTest


ENTRYPOINT = Path(__file__).resolve().parents[1] / "v14_complete.py"


def test_live_entrypoint_starts_and_exposes_resources_button():
    app = AppTest.from_file(ENTRYPOINT)
    app.run(timeout=30)
    assert not app.exception
    labels = [button.label for button in app.button]
    assert "📚 Ressources pédagogiques" in labels

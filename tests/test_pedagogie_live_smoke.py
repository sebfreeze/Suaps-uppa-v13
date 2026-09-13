from streamlit.testing.v1 import AppTest


def test_live_entrypoint_starts_and_exposes_resources_button():
    app = AppTest.from_file("v14_complete.py")
    app.run(timeout=30)
    assert not app.exception
    labels = [button.label for button in app.button]
    assert "📚 Ressources pédagogiques" in labels

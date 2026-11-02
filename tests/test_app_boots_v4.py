"""The app has one interface: it opens V4 with no flag or setting."""
import os

from streamlit.testing.v1 import AppTest

# An absolute path: newer Streamlit resolves a relative one against this test file
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard", "app.py")


def test_app_opens_v4_without_any_flag():
    for k in [k for k in os.environ if k.startswith("STOCK_AGENT_")]:
        os.environ.pop(k)
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception
    html = " ".join(str(getattr(h, "body", "")) for h in at.get("html"))
    assert "v4-brand" in html and "v4-h1" in html

from pathlib import Path
from streamlit.testing.v1 import AppTest
ROOT = Path(__file__).resolve().parents[1]

def test_app_demo_and_export_flow():
    app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=30).run()
    assert not app.exception
    assert app.metric[0].value == 'ASMT-10'
    assert app.metric[1].value == '2'
    app.checkbox[0].check().run()
    assert not app.exception
    # Switch to the second sample and check metadata is not carried over.
    app.sidebar.selectbox[0].select('DRC-01 · RCM + blocked credit').run()
    assert not app.exception
    assert app.metric[0].value == 'DRC-01'
    assert app.metric[1].value == '2'
    app.sidebar.selectbox[0].select('DRC-01A · late filing + RCM').run()
    assert not app.exception
    assert app.metric[0].value == 'DRC-01A'
    app.radio[0].set_value('Paste notice text').run()
    assert not app.exception

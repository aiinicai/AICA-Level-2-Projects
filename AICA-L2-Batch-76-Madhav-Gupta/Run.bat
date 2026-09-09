python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pytest
pyinstaller AssetDepPro.spec
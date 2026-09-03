from app import create_app

def test_create_app(temp_config):
    app = create_app(temp_config)
    assert app is not None
    assert app.config['APP_CONFIG'] == temp_config
    assert app.secret_key is not None

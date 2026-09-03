def test_dashboard_returns_200(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Bank Statement Converter' in response.data

def test_settings_returns_200(client):
    response = client.get('/settings/')
    assert response.status_code == 200
    assert b'Configuration Settings' in response.data

def test_process_returns_200_and_shows_stage_notice(client):
    response = client.get('/process')
    assert response.status_code == 200
    assert b'Planned for later stage' in response.data

def test_profiles_returns_200(client):
    response = client.get('/profiles/')
    assert response.status_code == 200

def test_404_handler(client):
    response = client.get('/nonexistent_route')
    assert response.status_code == 404
    assert b'404 Not Found' in response.data

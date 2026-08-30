import io

def test_upload_missing_file(client):
    response = client.post('/upload', data={})
    assert response.status_code == 400
    assert b"No file part" in response.data

def test_upload_non_pdf(client):
    data = {'file': (io.BytesIO(b"fake data"), 'test.txt')}
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert b"Unsupported file extension" in response.data

def test_upload_valid_pdf(client, sample_pdf):
    with open(sample_pdf, 'rb') as f:
        data = {'file': (f, 'test.pdf')}
        response = client.post('/upload', data=data, content_type='multipart/form-data')
        
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert 'job_id' in json_data
    assert 'redirect' in json_data

def test_serve_pdf_invalid_job(client):
    response = client.get('/jobs/fake-id-123/pdf')
    assert response.status_code == 404

def test_preview_invalid_job(client):
    response = client.get('/jobs/fake-id-123/preview')
    assert response.status_code == 404

def test_serve_pdf_path_traversal(client):
    response = client.get('/jobs/../../config.ini/pdf')
    assert response.status_code == 404
    
def test_privacy_regression(app):
    config = app.config['APP_CONFIG']
    assert config.getboolean('privacy', 'allow_external_ai') is False
    assert config.getboolean('privacy', 'allow_cloud_ocr') is False
    assert config.get('application', 'host') == '127.0.0.1'

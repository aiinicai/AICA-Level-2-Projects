import pytest
from pathlib import Path

def test_unknown_bank_profile_workflow(client, app):
    # 1. Upload PDF
    pdf_path = Path('samples/synthetic_defect_test.pdf')
    with open(pdf_path, 'rb') as f:
        resp = client.post('/upload', data={'file': f})
    assert resp.status_code == 200
    job_id = resp.json['job_id']
    
    # 2. Extract
    resp = client.post(f'/jobs/{job_id}/extract')
    assert resp.status_code == 302
    
    # 3. Normalize (should fail to find rows because it's unknown/1 column)
    resp = client.post(f'/jobs/{job_id}/normalize')
    assert resp.status_code == 302
    
    resp = client.get(f'/jobs/{job_id}/normalization')
    html = resp.data.decode()
    # verify the "Create Profile" button is present
    assert 'Create Profile From Statement' in html
    assert '0' in html # Rows Normalized: 0 (hopefully)
    
    # 4. Create Profile
    resp = client.post('/profiles/api/create', json={
        "profile_name": "Synthetic Baroda",
        "bank_name": "Bank of Synthetic Baroda"
    })
    assert resp.status_code == 200
    profile_id = resp.json['profile']['profile_id']
    
    # 5. Map Columns via API (simulating visual builder)
    column_definitions = [
        {"canonical_name": "date", "x0": 10, "x1": 80},
        {"canonical_name": "narration", "x0": 160, "x1": 440},
        {"canonical_name": "withdrawal", "x0": 510, "x1": 600},
        {"canonical_name": "deposit", "x0": 620, "x1": 700},
        {"canonical_name": "balance", "x0": 730, "x1": 800}
    ]
    resp = client.put(f'/profiles/api/{profile_id}', json={
        "expected_header_signatures": ["Bank of Synthetic Baroda"],
        "column_definitions": column_definitions,
        "table_bbox": {"x0": 0, "top": 0, "x1": 1000, "bottom": 1000}
    })
    assert resp.status_code == 200
    
    # 6. Apply Profile & Normalize
    resp = client.post(f'/jobs/{job_id}/normalize?profile_id={profile_id}')
    assert resp.status_code == 302
    
    resp = client.get(f'/jobs/{job_id}/normalization')
    html = resp.data.decode()
    assert 'Rows Normalized:</strong> 3' in html
    
    # Done!


def test_create_profile_from_statement_no_name_error(client, app):
    """Regression: create_for_job must not raise NameError on redirect/url_for."""
    # Upload a PDF to get a real job_id
    pdf_path = Path('samples/synthetic_defect_test.pdf')
    with open(pdf_path, 'rb') as f:
        resp = client.post('/upload', data={'file': f})
    assert resp.status_code == 200
    job_id = resp.json['job_id']

    # GET should render the form (200), not crash with NameError
    resp = client.get(f'/profiles/create_for_job/{job_id}')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'Create Profile From Statement' in html
    assert 'profile_name' in html
    assert 'bank_name' in html

    # POST should redirect (302) to the profile editor, not crash
    resp = client.post(f'/profiles/create_for_job/{job_id}', data={
        'profile_name': 'UAT Regression Profile',
        'bank_name': 'UAT Test Bank'
    })
    assert resp.status_code == 302
    assert '/profiles/' in resp.headers['Location']
    assert 'edit' in resp.headers['Location']
    assert f'job_id={job_id}' in resp.headers['Location']

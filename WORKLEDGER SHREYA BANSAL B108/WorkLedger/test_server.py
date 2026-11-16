import importlib.util
import json
import io
from email.parser import BytesParser
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('workledger', Path(__file__).with_name('server.py'))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.PORT = 8510

    def request(self, path, body=None, headers=None):
        payload = json.dumps(body).encode() if body is not None else b''
        headers = {'Host': f'localhost:{app.PORT}', 'Content-Type': 'application/json', 'Content-Length': str(len(payload)), **(headers or {})}
        method = 'POST' if body is not None else 'GET'
        raw = (f'{method} {path} HTTP/1.0\r\n' + ''.join(f'{k}: {v}\r\n' for k,v in headers.items()) + '\r\n').encode() + payload
        class FakeSocket:
            def __init__(self):
                self.output = bytearray()
            def makefile(self, *args):
                return io.BytesIO(raw)
            def sendall(self, value):
                self.output.extend(value)
        sock = FakeSocket()
        app.Handler(sock, ('127.0.0.1', 12345), object())
        head, content = bytes(sock.output).split(b'\r\n\r\n', 1)
        status_line, fields = head.split(b'\r\n', 1)
        return int(status_line.split()[1]), content, BytesParser().parsebytes(fields)

    def test_static_app_and_model_are_served_but_configuration_is_not(self):
        self.assertEqual(self.request('/')[0], 200)
        self.assertEqual(self.request('/model.mjs')[0], 200)
        self.assertEqual(self.request('/connection.json')[0], 404)
        self.assertEqual(self.request('/setup.sql')[0], 404)

    def test_data_requires_a_session(self):
        self.assertEqual(self.request('/api/data')[0], 401)

    def test_foreign_origin_cannot_mutate(self):
        self.assertEqual(self.request('/api/login', {}, {'Origin': 'https://untrusted.example'})[0], 403)

    def test_rejects_secret_keys(self):
        with self.assertRaises(app.AppError):
            app.validate_connection('https://example.supabase.co', 'sb_secret_private')
        with self.assertRaises(app.AppError):
            app.validate_connection('http://evil.example', 'sb_publishable_' + 'x' * 30)

    def test_unauthenticated_action_rejected(self):
        self.assertEqual(self.request('/api/action', {'action': 'review'})[0], 401)

    def test_staff_cannot_change_shared_ai_key(self):
        session = {'token': 'fake', 'refresh': 'fake', 'created': time.time(), 'expires': time.time() + 3600}
        with patch.object(app, 'get_session', return_value=('test', session)), patch.object(app, 'rpc', return_value={'me': {'role': 'staff'}}):
            status, _, _ = self.request('/api/ai-settings', {'model': 'gemini-3.5-flash', 'key': 'fake'})
            self.assertEqual(status, 403)

    def test_login_uses_httponly_session_cookie(self):
        tokens = {'access_token': 'fake', 'refresh_token': 'fake', 'expires_in': 3600}
        with patch.object(app, 'supabase', return_value=tokens), patch.object(app, 'rpc', return_value={'me': {'role': 'staff'}}):
            status, _, headers = self.request('/api/login', {'email': 'test@example.com', 'password': 'test-only'})
            self.assertEqual(status, 200)
            self.assertIn('HttpOnly', headers['Set-Cookie'])
            self.assertIn('SameSite=Strict', headers['Set-Cookie'])


if __name__ == '__main__':
    unittest.main()

import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from app import create_app


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'test.db')
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-only', 'DATABASE': self.path})
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, path, data, client=None):
        client = client or self.client
        client.get('/login')
        with client.session_transaction() as session:
            data['csrf'] = session['csrf']
        return client.post(path, data=data)

    def register(self, username='student', document=b'One two\nthree\tfour five.'):
        data = dict(username=username, password='Example123!', firstname='Test',
                    lastname='Student', email='test@example.com', address='123 Sample Road')
        if document is not None:
            data['document'] = (io.BytesIO(document), 'Limerick (1).txt')
        return self.post('/', data)

    def test_registration_redirect_details_count_download_and_relogin(self):
        self.assertEqual(self.register().status_code, 302)
        page = self.client.get('/profile').get_data(as_text=True)
        for value in ('Test', 'Student', 'test@example.com', '123 Sample Road', '5 <span>words'):
            self.assertIn(value, page)
        self.assertEqual(self.client.get('/download').data, b'One two\nthree\tfour five.')
        self.post('/logout', {})
        self.assertEqual(self.client.get('/profile').status_code, 302)
        self.assertEqual(self.post('/login', dict(username='student', password='wrong')).status_code, 401)
        self.assertEqual(self.post('/login', dict(username='STUDENT', password='Example123!')).status_code, 302)
        self.assertEqual(self.client.get('/download').data, b'One two\nthree\tfour five.')

    def test_password_hashed_and_duplicate_rejected(self):
        self.register()
        with sqlite3.connect(self.path) as db:
            password_hash = db.execute('SELECT password_hash FROM users').fetchone()[0]
        self.assertNotEqual(password_hash, 'Example123!')
        self.assertEqual(self.register('STUDENT').status_code, 409)

    def test_no_upload_and_zero_word_upload(self):
        self.register(document=None)
        self.assertIn(b'No file was uploaded', self.client.get('/profile').data)
        self.assertEqual(self.client.get('/download').status_code, 404)
        self.register(username='empty', document=b'')
        self.assertIn(b'0 <span>words', self.client.get('/profile').data)
        self.assertEqual(self.client.get('/download').data, b'')

    def test_authentication_and_user_isolation(self):
        self.register(document=b'First user secret')
        outsider = self.app.test_client()
        self.assertEqual(outsider.get('/download').status_code, 302)
        self.register(username='second', document=b'Second document')
        self.assertEqual(self.client.get('/download?user_id=1').data, b'Second document')
        self.assertEqual(self.client.get('/profile/student').status_code, 404)

    def test_csrf_invalid_text_and_size_limit(self):
        self.assertEqual(self.client.post('/', data={}).status_code, 400)
        self.assertEqual(self.register(document=b'\xff\xfe').status_code, 400)
        self.assertEqual(self.register(document=b'x' * (2 * 1024 * 1024)).status_code, 413)

    def test_persistence_after_app_restart(self):
        self.register()
        restarted = create_app({'TESTING': True, 'SECRET_KEY': 'test-only', 'DATABASE': self.path}).test_client()
        self.assertEqual(self.post('/login', dict(username='student', password='Example123!'), restarted).status_code, 302)
        self.assertEqual(restarted.get('/download').data, b'One two\nthree\tfour five.')


if __name__ == '__main__':
    unittest.main(verbosity=2)

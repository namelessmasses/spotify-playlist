import unittest
from import_playlist import app

class ImportPlaylistTestCase(unittest.TestCase):
    def setUp(self):
        # Set up the test client
        self.app = app.test_client()
        self.app.testing = True

    def test_index(self):
        # Test the index route
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Hello World', response.data)

    def test_authorize(self):
        # Test the authorize route
        response = self.app.get('/authorize')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'/authorize', response.data)

    def test_upload_playlist(self):
        # Test the upload playlist functionality
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer YOUR_ACCESS_TOKEN'
        }
        data = {
            "playlist_id": "playlist_id",
            "playlist_tracks": [
                {
                    "track_title": "Artist - Title"
                }
            ]
        }
        response = self.app.post('/upload', headers=headers, json=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Upload successful', response.data)

if __name__ == '__main__':
    unittest.main()
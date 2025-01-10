import unittest
from unittest.mock import patch, MagicMock
from import_playlist import app
import uuid
import base64
import dotenv
dotenv.load_dotenv(dotenv_path=".env")
import os
from urllib.parse import urlparse, parse_qs

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

    @patch('import_playlist.requests.get')
    @patch('import_playlist.requests.post')
    def test_authorize(self, mock_post_api_token, mock_get_user_profile):
        '''
        Test the authorize route

        :param mock_get: MagicMock
        :param mock_post: MagicMock
        :return: None

        /authorize first redirects the client to the Spotify authorization page 
        with a redirect_uri back to /authorized.

        The client must invoke /authorized with an authorization code from spotify.
        The server will then exchange the authorization code for an access token 
        with Spotify, store it in the session and return it to the client.
        '''

        # Expect a redirect to the Spotify authorization page
        authorize_response = self.app.get('/authorize')
        self.assertEqual(authorize_response.status_code, 302)
        self.assertIn(b'accounts.spotify.com/authorize', authorize_response.data)

        mock_code = uuid.uuid4().hex
        mock_access_token = uuid.uuid4().hex
        mock_refresh_token = uuid.uuid4().hex

        # Mock the Spotify API call to exchange authorization code for access token
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': mock_access_token,
            'refresh_token': mock_refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600
        }
        mock_post_api_token.return_value = mock_response

        # Mock the Spotify API call to get the user profile
        mock_user_id  = uuid.uuid4().hex
        mock_display_name = f'fake_display_name{uuid.uuid4().hex}'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': mock_user_id,
            'display_name': mock_display_name,
        }
        mock_get_user_profile.return_value = mock_response

        # Invoke the /authorized route with a fake authorization code
        
        authorize_response_location = authorize_response.headers['Location']
        # authorize_response_location is a GET request.
        # Parse the URL query parameters
        parsed_url = urlparse(authorize_response_location)
        query_params = parse_qs(parsed_url.query)
        state = query_params.get('state', [None])[0]
        response = self.app.get(f'/authorized?code={mock_code}&state={state}')

        encoded_credentials = base64.b64encode(f"{os.getenv('APP_CLIENT_ID')}:{os.getenv('APP_CLIENT_SECRET')}".encode()).decode()
        mock_post_api_token.assert_called_once_with(
            'https://accounts.spotify.com/api/token',
            data={
                'grant_type': 'authorization_code',
                'code': mock_code,
                'redirect_uri': 'http://localhost/authorized'
            },
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {encoded_credentials}'
            }
        )

        mock_get_user_profile.assert_called_once_with(
            'https://api.spotify.com/v1/me',
            headers={
                'Authorization': f'Bearer {mock_access_token}',
            })

        self.assertEqual(response.status_code, 200)
        self.assertIn(f'Authorized as display_name={mock_display_name} id={mock_user_id}'.encode(), response.data)




if __name__ == '__main__':
    unittest.main()
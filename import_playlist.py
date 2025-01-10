#!/usr/bin/python3

import flask
from flask import Flask, request, redirect, url_for, render_template
import os
import base64
import requests
import dotenv
dotenv.load_dotenv(dotenv_path=".env")

import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG)

logger = logging.getLogger('IMPORT_PLAYLIST')
logger.propagate = True

app = Flask(__name__)
app.secret_key = os.getenv("APP_CLIENT_SECRET")

@app.route('/')
def index():
    logger.info("/")
    return '<a href="/authorize">Login with Spotify</a>'

@app.route('/authorize')
def authorize():
    logger.info("/authorize")

    flask.session["state"] = state = os.urandom(16).hex()
    logger.debug(f"{state=}")

    client_id = os.getenv("APP_CLIENT_ID")
    logger.debug(f"{client_id=}")

    redirect_uri = url_for("authorized", _external=True)
    logger.debug(f"{redirect_uri=}")

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "playlist-modify-public playlist-modify-private",
        "state": state
    }
    query_string = "&".join([f"{key}={value}" for key, value in params.items()])

    redirect_string = f"https://accounts.spotify.com/authorize?{query_string}"
    logger.debug(f"{redirect_string=}")

    return redirect(redirect_string)

@app.route('/authorized')
def authorized():
    logger.info("/authorized - origin: %s referrer: %s host: %s", request.origin, request.referrer, request.host)

    request_state = request.args.get("state")
    logger.debug(f"{request_state=}")

    session_state = flask.session["state"]
    logger.debug(f'{session_state=}')

    # Check if the state matches
    if request_state != session_state:
        logger.error("State mismatch")
        return "State mismatch", 400
    
    # Check if the user denied the request
    if request.args.get("error"):
        logger.error(f"Error: {request.args['error']}")
        return request.args["error"], 400
    
    # Exchange the code for a token
    code = request.args.get("code")
    logger.debug(f"{code=}")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": url_for("authorized", _external=True),
    }

    encoded_credentials = base64.b64encode(f"{os.getenv('APP_CLIENT_ID')}:{os.getenv('APP_CLIENT_SECRET')}".
                                            encode()).decode('utf-8')
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f"Basic {encoded_credentials}"
    }

    logger.debug(f"requesting token with {data=}")
    logger.debug(f"requesting token with {headers=}")

    response = requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers)
    token_response_data = response.json()
    logger.debug(f"{token_response_data=}")

    # if the response status code is not 200, return the error
    if response.status_code != 200:
        logger.error(f"Error: {token_response_data.get('error', 'Unknown error')}")
        return token_response_data.get("error", "Unknown error"), response.status_code
    
    # Save the access_token and refresh_token
    flask.session["access_token"] = token_response_data["access_token"]
    flask.session["refresh_token"] = token_response_data["refresh_token"]

    # Get the spotify user's id
    headers = {
        "Authorization": f"Bearer {token_response_data['access_token']}"
    }

    logger.debug(f"requesting user id with {headers=}")
    response = requests.get("https://api.spotify.com/v1/me", headers=headers)
    user_profile_response = response.json()
    logger.debug(f"user id response: {user_profile_response}")

    display_name = user_profile_response["display_name"]
    logger.debug(f"{display_name=}")
    
    user_id = user_profile_response["id"]
    flask.session["user_id"] = user_id
    logger.debug(f"{user_id=}")

    # return a document that allows a user to select a file from the client filesystem to upload as the playlist data to import
    return render_template('import.html', display_name=display_name, user_id=user_id, session_state=session_state)

def create_query(playlist_track):
    track_title = playlist_track["track_title"]
    query = f"q={requests.utils.quote(track_title)}&type=track&limit=1"
    logger.debug(f"{query=}")
    return query

def resolve_uris(access_token, playlist_tracks):
    logger.info(f"Resolving URIs: {playlist_tracks}")
    resolved_tracks = []
    for playlist_track in playlist_tracks:
        query = create_query(playlist_track)
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        logger.debug(f"requesting track with {query=}")
        response = requests.get(f"https://api.spotify.com/v1/search?{query}", headers=headers)
        logger.debug(f"search response: {response.json()}")

        playlist_track["status_code"] = response.status_code

        if response.status_code == 200:
            response_data = response.json()
            if len(response_data["tracks"]["items"]) > 0:
                playlist_track["uri"] = response_data["tracks"]["items"][0]["uri"]
                logger.debug(f"resolved track: {playlist_track}")
                resolved_tracks.append(playlist_track)
            else:
                logger.info(f"Track not found: {playlist_track}")
                playlist_track["uri"] = None
    
    logger.debug(f"{resolved_tracks=}")
    return resolved_tracks

@app.route('/import', methods=["POST"])
def import_playlist():
    '''
    Import a playlist to the user's account

    Request body:
    {
        "playlist_id": "playlist_id",
        "playlist_tracks": [
            {
                "track_title": "Artist - Title"
            },
            ...
        ]
    }
    '''

    logger.info("/import")

    # Check the stored state against the request state
    request_state = request.headers.get("state")
    logger.debug(f"{request_state=}")

    session_state = flask.session["state"]
    logger.debug(f"{session_state=}")

    if request_state != session_state:
        logger.error("State mismatch")
        # TODO: Trigger logout
        return "State mismatch", 400

    data = request.get_json()
    logger.debug(f"{data=}")

    playlist_name = data.get("playlist_name")
    logger.debug(f"{playlist_name=}")

    playlist_tracks = data.get("playlist_tracks")
    logger.debug(f"{playlist_tracks=}")

    resolved_tracks = resolve_uris(flask.session["access_token"], playlist_tracks)
    logger.debug(f"{resolved_tracks=}")

    if len(resolved_tracks) == 0:
        # Response 400 with json body 
        #   msg: "No tracks were resolved"
        #   tracks: []
        logger.error("No tracks were resolved")
        return {
            "msg": "No tracks were resolved",
            "tracks": []
        }, 400
    
    # Create a new playlist
    headers = {
        "Authorization": f"Bearer {flask.session['access_token']}",
        "Content-Type": "application/json"
    }

    logger.debug(f"creating playlist {playlist_name} with {headers=}")
    response = requests.post(f"https://api.spotify.com/v1/users/{flask.session['user_id']}/playlists",
                            headers=headers,
                            json={
                                "name": f"Imported {playlist_name}",
                                "public": False
                            })
    response_data = response.json()
    logger.debug(f"create playlist response: {response_data}")

    # If the response status code is not 201, return with status code, msg: "Error creating playlist", tracks: []
    if response.status_code != 201:
        logger.error(f"Error creating playlist {response.status_code=}")
        return {
            "msg": "Error creating playlist",
            "tracks": []
        }, response.status_code
    
    # Add tracks to the playlist
    playlist_id = response_data["id"]
    logger.debug(f"{playlist_id=}")
    logger.debug(f'adding tracks to playlist {playlist_id} with {headers=}')
    json = {
        "uris": [track['uri'] for track in resolved_tracks],
        "position": 0
    }
    logger.debug(f"{json=}")
    response = requests.post(f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                            headers=headers,
                            json=json)
    
    for track in resolved_tracks:
        track['status_code'] = response.status_code

    return {
        "msg": "Imported playlist",
        "tracks": playlist_tracks
    }, response.status_code

@app.route('/logout', methods=["POST"])
def logout():
    logger.info("/logout")

    flask.session.clear()
    return redirect(url_for("index"))

if __name__ == '__main__':
    app.run(debug=True)
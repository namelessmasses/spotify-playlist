#!/usr/bin/python3

import flask
from flask import Flask, request, redirect, url_for
import os
import base64
import requests

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

@app.route('/')
def index():
    return "Hello World"

@app.route('/authorize')
def authorize():
    flask.session["state"] = state = os.urandom(16).hex()

    params = {
        "client_id": os.getenv("CLIENT_ID"),
        "response_type": "code",
        "redirect_uri": url_for("authorized", _external=True),
        "scope": "playlist-modify-public playlist-modify-private",
        "state": state
    }
    query_string = "&".join([f"{key}={value}" for key, value in params.items()])

    return redirect(f"https://accounts.spotify.com/authorize?{query_string}")

@app.route('/authorized')
def authorized():
    state = request.args.get("state")

    # Check if the state matches
    if state != flask.session["state"]:
        return "State mismatch", 400
    
    # Check if the user denied the request
    if request.args.get("error"):
        return request.args["error"], 400
    
    # Exchange the code for a token
    code = request.args.get("code")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": url_for("authorized", _external=True),
    }

    encoded_credentials = base64.b64encode(f"{os.getenv('CLIENT_ID')}:{os.getenv('CLIENT_SECRET')}".
                                            encode()).decode('utf-8')
    headers = {
        'content-type': 'application/x-www-form-urlencoded',
        'Authorization': f"Basic {encoded_credentials}"
    }

    response = requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers)
    response_data = response.json()

    # if the response status code is not 200, return the error
    if response.status_code != 200:
        return response_data.get("error", "Unknown error"), response.status_code
    
    # Save the access_token and refresh_token
    flask.session["access_token"] = response_data["access_token"]
    flask.session["refresh_token"] = response_data["refresh_token"]

    # Get the spotify user's id
    headers = {
        "Authorization": f"Bearer {response_data['access_token']}"
    }
    response = requests.get("https://api.spotify.com/v1/me", headers=headers)
    response_data = response.json()

    flask.session["user_id"] = response_data["id"]

    # Return 200 "Authorized"
    return "Authorized"

def create_query(playlist_track):
    track_title = playlist_track["track_title"]
    query = f"q={requests.utils.quote(track_title)}&type=track&limit=1"
    return query

def resolve_uris(access_token, playlist_tracks):
    resolved_tracks = []
    for playlist_track in playlist_tracks:
        query = create_query(playlist_track)
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(f"https://api.spotify.com/v1/search?{query}", headers=headers)
        playlist_track["status_code"] = response.status_code

        if response.status_code == 200:
            response_data = response.json()
            if len(response_data["tracks"]["items"]) > 0:
                playlist_track["uri"] = response_data["tracks"]["items"][0]["uri"]
                resolved_tracks.append(playlist_track["uri"])
            else:
                playlist_track["uri"] = None
    
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
    data = request.get_json()
    playlist_id = data.get("playlist_id")
    playlist_tracks = data.get("playlist_tracks")
    resolved_tracks = resolve_uris(flask.session["access_token"], playlist_tracks)

    if len(resolved_tracks) == 0:
        # Response 400 with json body 
        #   msg: "No tracks were resolved"
        #   tracks: []
        return {
            "msg": "No tracks were resolved",
            "tracks": []
        }, 400
    
    # Create a new playlist
    headers = {
        "Authorization": f"Bearer {flask.session['access_token']}",
        "Content-Type": "application/json"
    }

    response = requests.post(f"https://api.spotify.com/v1/users/{flask.session['user_id']}/playlists",
                            headers=headers,
                            json={
                                "name": f"Imported {playlist_id}",
                                "public": False
                            })
    response_data = response.json()

    # If the response status code is not 201, return with status code, msg: "Error creating playlist", tracks: []
    if response.status_code != 201:
        return {
            "msg": "Error creating playlist",
            "tracks": []
        }, response.status_code
    
    # Add tracks to the playlist
    playlist_id = response_data["id"]
    response = requests.post(f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                            headers=headers,
                            json={
                                "uris": ' '.join([track.uri for track in resolved_tracks])
                            })
    
    for track in resolved_tracks:
        track['status_code'] = response.status_code

    return {
        "msg": "Imported playlist",
        "tracks": playlist_tracks
    }, response.status_code



if __name__ == '__main__':
    app.run(debug=True)
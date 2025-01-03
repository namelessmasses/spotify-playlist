# Detailed Design

# Description

- The system shall accept login credentials and submits them to the Spotify API.
- The system shall handle the response from the Spotify API.
- The system shall handle both successful and unsuccessful login attempts.
- The system shall allow the user to logout.
- The system shall allow the user to import playlists from a file.
- The system shall allow the user to import playlists from Apple Music.
- The system shall accept a playlist in M3U format.
- The system shall accept a playlist in XCF format.
- The system shall accept the playlist to create upon successful login.

# State Machine

## System Sequence Diagram

```mermaid
%%{init: {'sequence': {'messageAlign': 'left', 'noteAlign': 'left'}}}%%
sequenceDiagram
    Participant UserClient
    Participant WebApp
    Participant SpotifyAPI as api.spotify.com
    Participant SpotifyAccounts as accounts.spotify.com

    activate UserClient
        UserClient->>+WebApp: /authorize
        WebApp-->>-UserClient: redirect{url: accounts.spotify.com/authorize}
        
        UserClient->>+SpotifyAccounts: /authorize
        SpotifyAccounts-->>-UserClient: response
        break response.status != 200
            UserClient->>UserClient: display error
            Note right of UserClient: The authorization request failed<br>Check the specific HTTP status code.
        end

        UserClient->>+WebApp: /authorized
            WebApp->>+SpotifyAccounts: /api/token
            SpotifyAccounts-->>-WebApp: response
            break response.status != 200
                WebApp-->>UserClient: {<br/>#160;#160;#160;#160;status: response.status<br/>#160;#160;#160;#160;msg: "Failed to obtain token from auth code"<br/>#160;#160;#160;#160;tracks: []<br/>}
            end
            Note right of WebApp: store access_token and refresh_token
        WebApp-->>-UserClient: {<br/>#160;#160;#160;#160;status: 200<br/>#160;#160;#160;#160;msg: "Authorized"<br/>#160;#160;#160;#160;tracks: []<br/>}

        UserClient->>+WebApp: /import
            WebApp->>+WebApp: resolve_uris(playlist_tracks)
            loop playlist_track in playlist_tracks

                WebApp->>+WebApp: create_query(playlist_track)
                Note right of WebApp: Creates Spotify search query based on fields available in playlist_track
                WebApp-->>-WebApp: query object
                
                WebApp->>+SpotifyAPI: /v1/search
                SpotifyAPI-->>-WebApp: response

                Note right of WebApp: playlist_track.status = response.status

                opt tracks.total > 0
                    Note right of WebApp: playlist_track.uri = tracks.items[0].uri<br>resolved_tracks.append(playlist_track)
                end
            end
            WebApp-->>-WebApp: resolved_tracks

            opt resolved.length > 0
                WebApp->>+SpotifyAPI: /v1/users/{user_id}/playlists
                SpotifyAPI-->>-WebApp: response
                break response.status != 200
                    WebApp-->>UserClient: {<br/>#160;#160;#160;#160;status: response.status<br/>#160;#160;#160;#160;msg: "Failed to obtain token from auth code"<br/>#160;#160;#160;#160;tracks: playlist_tracks<br/>}
                end

                loop track in resolved_tracks
                    Note right of WebApp: Build list of resolved track URIs
                end

                WebApp->>+SpotifyAPI: /v1/playlists/{playlist_id}/tracks
                SpotifyAPI-->>-WebApp: response

                loop track in resolved_tracks
                    Note right of WebApp: track.status = response.status
                end
            end
        WebApp-->>-UserClient: {<br/>#160;#160;#160;#160;status: response.status<br/>#160;#160;#160;#160;msg: "Failed to obtain token from auth code"<br/>#160;#160;#160;#160;tracks: playlist_tracks<br/>}
    
    deactivate UserClient
```
## Service State Diagram

```mermaid
stateDiagram-v2
    
    [*] --> AuthorizationPending: PUT /authorize / REDIRECT{url=accounts.spotify.com/authorize}
    
    AuthorizationPending --> [*]: PUT /authorized(auth_status) [auth_status != 200] / {status=auth_status}
    AuthorizationPending --> AccessTokenPending: PUT /authorized(auth_status) [auth_status=200] / POST{url=accounts.spotify.com/api/token}

    AccessTokenPending --> [*]: response(status) [response.status!=200] / {status=response.status}
    AccessTokenPending --> Authorized: response(status) [response.status=200] / {status=200}

    Authorized --> LoggingOut: logout() / DELETE{url=accounts.spotify.com/api/token}
    Authorized --> ResolvingURI: import(visibility, name, tracks) / GET /search
    Authorized --> AccessTokenRefresh: token_timeout() / POST{url=accounts.spotify.com/api/token, access_token, refresh_token}

    ResolvingURIs --> CreatingPlaylist: response() [response.status = 200] / POST /users/{user_id}/playlists
    ResolvingURIs --> Authorized: response() [response.status != 200] / {status=response.status}
    ResolvingURIs --> LoggingOut: logout() / DELETE{url=accounts.spotify.com/api/token}

    CreatingPlaylist --> Authorized: response() [response.status != 200] / {status=response.status, tracks=tracks}
    CreatingPlaylist --> AddingTracks:  / POST{url=api.spotify.com/playlists/{playlist_id}/tracks}
    CreatingPlaylist --> AccessTokenRefresh: token_timeout() / POST{url=accounts.spotify.com/api/token, access_token, refresh_token}
    CreatingPlaylist --> LoggingOut: logout() / DELETE{url=accounts.spotify.com/api/token}

    AddingTracks --> [*]: response() / {status=response.status, tracks=tracks}
    AddingTracks --> AccessTokenRefresh: token_timeout() / POST{url=accounts.spotify.com/api/token, access_token, refresh_token}
    AddingTracks --> LoggingOut: logout() / DELETE{url=accounts.spotify.com/api/token}

    LoggingOut --> [*]: response() [response.status!=200] / {status=response.status}
    LoggingOut --> [*]: token_timeout() / {status=401}
    LoggingOut --> Authorized: response() [response.status!=200] / {status=response.status}

    LoggedOut --> [*]
```
### Start

| Trigger | Guard | Behavior | Destination State |
| --- | --- | --- | --- |
| `PUT /authorize` | - | Send to client a redirect to Spotify authorization page. | `AuthorizationPending` |

### AuthorizationPending

| Trigger | Guard | Behavior | Destination State |
| --- | --- | --- | --- |
| `PUT /authorized` | auth_status != 200 | Send to client an error message. | Terminal |
| `PUT /authorized` | auth_status == 200 | Request access token from Spotify API. | `AccessTokenPending` |

### AccessTokenPending

### Authorized

### ResolvingURIs

### CreatingPlaylist

### AddingTracks

### LoggingOut

## Token Expiration and Refresh

- The system shall handle token timeout from each of the following states.
    - Authorized
    - ResolvingURIs
    - CreatingPlaylist
    - AddingTracks
    - LoggingOut
        - If the token expires while logging out, the system will transition directly to `LoggedOut` regardless of the outcome of the `logout` operation.

- The system shall handle token timeout with a transition from the originating state to a `TokenExpired` state.
- The system shall transition back to the originating state after a successful token refresh.
- The system shall transition to `LoggedOut` after a failed token refresh.

```mermaid
stateDiagram-v2
    [*] --> TokenExpired: token_timeout() / POST{url=accounts.spotify.com/api/token, access_token, refresh_token}
    TokenExpired --> TokenRefreshPending: refresh

    TokenRefreshPending --> [*]: response(status) [response.status!=200] / {status=response.status}
    TokenRefreshPending --> [*]: response(status) [response.status==200] / {status=response.status}
    Note right of TokenRefreshPending: Separate transitions for success and failure as the outer fragment moves to one of the four calling states.
```

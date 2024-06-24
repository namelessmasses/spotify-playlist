$auth_root = "https://accounts.spotify.com/api"
$api_root = "https://api.spotify.com/v1/api"

$redirect_uri = "https://localhost:8080"

$client_id = "b2fe211780f240288b3137130150e31b"
$client_secret = "747cf69f24394999b8539aba1e6f95eb"

# Access the PSUserAgent class attribute Chrome
$PSUserAgent = [Microsoft.PowerShell.Commands.PSUserAgent]

# Form a POST request to the token endpoint
# Content-Type: application/x-www-form-urlencoded
# Body:
#  grant_type=client_credentials
#  client_id=<client_id>
#  client_secret=<client_secret>
$token_response = Invoke-RestMethod -UserAgent $PSUserAgent::Chrome -Uri "$auth_root/token" -Method Post -Body @{
    grant_type = "client_credentials"
    client_id = $client_id
    client_secret = $client_secret
}
$token_secure = ConvertTo-SecureString -String $token_response.access_token -AsPlainText -Force 
$csrf_state = $token_secure | ConvertFrom-SecureString | Out-String

$authorize_url = "https://accounts.spotify.com/authorize?" + [System.Web.HttpUtility]::UrlEncode(@{
    response_type = 'code'
    client_id = $client_id
    scope = $scope
    redirect_uri = $redirect_uri
    state = $csrf_state
})

# Open the URL in the default browser
Start-Process $authorize_url

# Spotify user login
# GET request to /login endpoint
# Query parameters:
#  client_id=<client_id>
#  response_type
$login_response = Invoke-RestMethod -Authentication OAuth -Token $token_secure -Uri "$auth_root/login" -Method Get -Body @{
    client_id = $client_id
}

# Spotify user authorize
# GET request to /authorize endpoint
# Query parameters:
#  client_id=<client_id>
#  response_type=code
#  redirect_uri=<redirect_uri> ; must be a registered redirect URI in the app settings
#  scope=playlist-modify-private
#  state=hash of the session cookie ; optional
#  show_dialog=false ; optional
$auth_response = Invoke-RestMethod -Authentication OAuth -Token $token_response.access_token -Uri "$auth_root/authorize" -Method Get -Headers $headers -Body @{
    client_id = $client_id
    response_type = "code"
    redirect_uri = "https://localhost:8080"
    scope = "playlist-modify-private"
    state = $csrf_state
    show_dialog = "false"
}
$auth_response

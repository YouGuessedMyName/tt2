import requests

BASE_URL = "http://localhost:8008"
FULL_URL = BASE_URL + "/_matrix/client/v3/"

session = {'user_id': '@one:my.matrix.host', 'access_token': 'syt_b25l_QdbFQsfBpaURBkMFNlTG_3elFko', 'home_server': 'my.matrix.host', 'device_id': 'KYUHHCVZVE'}

ROOM_ID = "!oPZjwZUChSmWuttWWZ:my.matrix.host"

def get_auth_header(user_session):
  return {"Authorization": f"Bearer {user_session["access_token"]}"}

response = requests.get(
    FULL_URL + "rooms/" + ROOM_ID + "/state",
    headers=get_auth_header(session)
)
print(response)
print(str(response.json()).replace(",", ",\n"))
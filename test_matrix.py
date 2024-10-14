import requests
import logging
import copy
import random
import string
from time import sleep

### ESTABLISH SESSIONS ###
BASE_URL = "http://localhost:8008"
FULL_URL = BASE_URL + "/_matrix/client/v3/"

logging.basicConfig(level=logging.INFO)

GET_TOKEN_BODY = {
  "type": "m.login.password",
  "identifier": {
    "type": "m.id.user",
    "user": "USER"
  },
  "password": "PASSWORD"
}

# Check if login with password is enabled
login_enabled_response = requests.get(FULL_URL + "login")
logging.info(login_enabled_response)
assert login_enabled_response.ok, "Server disabled password login, or the server is not running at all."

def generate_login_body(user, password) -> dict:
  body_copy = copy.deepcopy(GET_TOKEN_BODY)
  body_copy["identifier"]["user"] = user
  body_copy["password"] = password
  return body_copy

def login_user(user, password) -> dict:
  response = requests.post(
      FULL_URL + "login",
      json = generate_login_body(user, password)
  )
  logging.debug(response)
  assert response.ok, f"Login failed for user {user}"
  return response.json()
  
def random_room_name():
  return ''.join(random.choices(string.ascii_uppercase + string.digits, k=50))


CREATE_ROOM_JSON = {
    "name":"room11",
    "visibility":"public",
    "preset":"public_chat",
    "room_alias_name":"room11",
    "topic":"TOPIC",
    "initial_state":[]
  }

def create_room_json(visibility):
  res = copy.deepcopy(CREATE_ROOM_JSON)
  res["name"] = random_room_name()
  res["room_alias_name"] = res["name"]
  res["visibility"] = visibility
  return res

# Login to the three sessions.
one_session = login_user("one", "one")
sleep(0.2)
two_session = login_user("two", "two")
sleep(0.2)
three_session = login_user("three", "three")
print(one_session)

### START TESTS ###
def test1():
  """Creating a public room."""
  create_room_json1 = create_room_json("public")
  headers = {"Authorization": f"Bearer {one_session["access_token"]}"}
  response_create_room_1 = requests.post(
    FULL_URL + "createRoom",
    headers=headers,
    json= create_room_json1,
  )
  assert response_create_room_1.ok, "Failed to create room."


def test6():
  """Ban user from room."""
  create_room_json6 = create_room_json("public")
  headers = {"Authorization": f"Bearer {one_session["access_token"]}"}
  response_create_room_6 = requests.post(
    FULL_URL + "createRoom",
    headers=headers,
    json= create_room_json6,
  )
  assert response_create_room_6.ok, "Failed to create room."


test1()
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

def random_number_string():
  return str(random.randint)

TEXT_MESSAGE_JSON = {
    "msgtype": "m.text",
    "body": "Message from one that should succeed"
}

def text_message(text):
  res = copy.deepcopy(TEXT_MESSAGE_JSON)
  res["body"] = text
  return res


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
# two_session = login_user("two", "two")
# three_session = login_user("three", "three")

### START TESTS ###
def test1():
  # One: Create a public room.
  create_room_json1 = create_room_json("public")
  one_auth_headers = {"Authorization": f"Bearer {one_session["access_token"]}"}
  response_create_room_1 = requests.post(
    FULL_URL + "createRoom",
    headers=one_auth_headers,
    json= create_room_json1,
  )
  assert response_create_room_1.ok, "Failed to create room."
  logging.info("[Test 1] Created room succesfully.")
  room_id = response_create_room_1.json()["room_id"]

  # One: Create the same public room again (supposed to fail).
  response_create_room_2 = requests.post(
    FULL_URL + "createRoom",
    headers=one_auth_headers,
    json=create_room_json1,
  )
  assert not response_create_room_2.ok, "Re-created room with same succesfully? This should not happen."
  logging.info("[Test 1] Succesfully failed to create a room with the same name again.")

  # One: send a message in the room.
  response_message_one = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=one_auth_headers,
    json=text_message("Message from one that should succeed")
  )
  assert response_message_one.ok, "Failed to send message."
  logging.info("[Test 1] One succesfully sent message.")
  one_message_event_id = response_message_one.json()["event_id"]
  
  # Two: fail to send a message in the room.

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
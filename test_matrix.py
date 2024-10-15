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
  assert response.ok, f"Login failed for user {user}. Please run docker restart NAME_CONTAINER"
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

MESSAGES_WITH_FILTER = "/messages?filter=%7B%22types%22%3A%5B%22m.room.message%22%5D%7D"

def find_event(json, event_id):
  return list(filter(lambda msg: msg["event_id"] == event_id, json["chunk"]))[0]

CREATE_ROOM_JSON = {
    "name":"room11",
    "visibility":"public",
    "preset":"public_chat",
    "room_alias_name":"room11",
    "topic":"TOPIC",
    "initial_state":[]
  }

def create_room_json(preset):
  res = copy.deepcopy(CREATE_ROOM_JSON)
  res["name"] = random_room_name()
  res["room_alias_name"] = res["name"]
  res["preset"] = preset
  return res

def get_auth_header(user_session):
  return {"Authorization": f"Bearer {user_session["access_token"]}"}

# Login to the three sessions.
one_session = login_user("one", "one")
two_session = login_user("two", "two")
three_session = login_user("three", "three")

### START TESTS ###
def test1():
  MSG1 = "Message from one that should succeed"
  MSG2_FAIL = "Message from two that should fail"
  MSG2_SUCCES = "Message from two that should succeed"
  # One: Create a public room.
  create_room_json1 = create_room_json("public")
  response_create_room_1 = requests.post(
    FULL_URL + "createRoom",
    headers=get_auth_header(one_session),
    json= create_room_json1,
  )
  assert response_create_room_1.ok, "Failed to create room."
  logging.info("[Test 1] Created room succesfully.")
  room_id = response_create_room_1.json()["room_id"]

  # One: Create the same public room again (supposed to fail).
  response_create_room_2 = requests.post(
    FULL_URL + "createRoom",
    headers=get_auth_header(one_session),
    json=create_room_json1,
  )
  assert not response_create_room_2.ok, "Re-created room with same succesfully? This should not happen."
  logging.info("[Test 1] Succesfully failed to create a room with the same name again.")

  # One: send a message in the room.
  response_message_one = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(one_session),
    json=text_message(MSG1)
  )
  assert response_message_one.ok, "Failed to send message."
  logging.info("[Test 1] One succesfully sent message.")
  one_message_event_id = response_message_one.json()["event_id"]
  
  # Two: fail to send a message in the room (supposed to fail).
  response_message_two = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(two_session),
    json=text_message(MSG2_FAIL)
  )
  assert response_message_two.status_code == 403
  assert response_message_two.json()["errcode"] == "M_FORBIDDEN"
  assert response_message_two.json()["error"].find("not in room")
  logging.info("[Test 1] Two failed succesfully to send message.")

  # Two: join room.
  response_join_two = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_two.ok
  logging.info("[Test 1] Two joined the room succesfully.")

  # Two: Send a message in the room.
  response_message_two_retry = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(two_session),
    json=text_message(MSG2_SUCCES)
  )
  assert response_message_two_retry.ok
  logging.info("[Test 1] Two sent a message succesfully.")
  two_message_retry_event_id = response_message_two_retry.json()["event_id"]

  # One: read the messages in the room.
  response_one_reading = requests.get(
    FULL_URL + "rooms/" + room_id + MESSAGES_WITH_FILTER,
    headers=get_auth_header(one_session)
  )
  server_one_message = find_event(response_one_reading.json(), event_id=one_message_event_id)
  server_two_message = find_event(response_one_reading.json(), event_id=two_message_retry_event_id)
  assert server_one_message["content"]["body"] == MSG1
  assert server_two_message["content"]["body"] == MSG2_SUCCES
  assert len(response_one_reading.json()["chunk"]) == 2 # Exactly two messages in room
  logging.info("[Test 1] SUCCESS")

def test2():
  MSG2_SUCCESS = "Message from two that should succeed"
  MSG3_FAIL = "Message from three that should fail"
  # One: create room
  response_create_room_1 = requests.post(
    FULL_URL + "createRoom",
    headers =get_auth_header(one_session),
    json = create_room_json("trusted_private_chat"),
  )
  assert response_create_room_1.ok
  logging.info("[TEST 2] Sucesfully created room.")
  room_id = response_create_room_1.json()["room_id"]

  # One: invite two
  response_invite_2 = requests.post(
    FULL_URL + "rooms/" + room_id + "/invite",
    headers = get_auth_header(one_session),
    json={
      "reason": "Welcome",
      "user_id": two_session["user_id"]
    }
  )
  assert response_invite_2.ok
  logging.info("[TEST 2] Succesfully invited two.")

  # Two: join room
  response_join_2 = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_2.ok
  logging.info("[TEST 2] Two succesfully joined the room.")

  # Two: send message
  response_send_message_2 = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(two_session),
    json=text_message(MSG2_SUCCESS)
  )
  assert response_send_message_2.ok
  logging.info("[TEST 2] Two succesfully sent a message.")

  # Three: fail to join room
  response_join_3 = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(three_session),
  )
  assert response_join_3.status_code == 403
  logging.info("[TEST 2] Three succesfully failed to joined the room.")

  # Three: fail to send message
  response_send_message_3 = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(three_session),
    json=text_message(MSG3_FAIL)
  )
  assert response_send_message_3.status_code == 403
  logging.info("[TEST 2] Three succesfully failed to send a message.")

def test3():
  

def test6():
  """Ban user from room."""
  create_room_json6 = create_room_json("public_chat")
  headers = {"Authorization": f"Bearer {one_session["access_token"]}"}
  response_create_room_6 = requests.post(
    FULL_URL + "createRoom",
    headers=headers,
    json= create_room_json6,
  )
  assert response_create_room_6.ok, "Failed to create room."

test2()
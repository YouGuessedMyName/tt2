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

print(one_session)
print(two_session)
print(three_session)

### START TESTS ###
def test1():
  MSG1 = "Message from one that should succeed"
  MSG2_FAIL = "Message from two that should fail"
  MSG2_SUCCES = "Message from two that should succeed"
  # One: Create a public room.
  create_room_json1 = create_room_json("public_chat")
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
  logging.info("[Test 1] One succesfully send message.")
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
  MSG3_SUCCESS = "Message from 3 that should succeed"
  MSG3_FAIL = "Message from 3 that should fail"
  # One: create room
  response_create_room = requests.post(
    FULL_URL + "createRoom",
    headers=get_auth_header(one_session),
    json= create_room_json("public_chat"),
  )
  
  assert response_create_room.ok
  room_id = response_create_room.json()["room_id"]
  print(room_id)
  print(one_session)
  logging.info("[Test 3] One: created room")
  # Two: fail to kick three, two not in room
  response_kick_two = requests.post(
    FULL_URL + "rooms/" + room_id + "/kick",
    headers=get_auth_header(two_session),
    json={
      "user_id": three_session["user_id"],
      "reason": "You smell."
    }
  )
  assert response_kick_two.status_code == 403
  assert response_kick_two.json()["errcode"] == "M_FORBIDDEN"
  assert response_kick_two.json()["error"].find("not in room")
  logging.info("[Test 3] Two failed succesfully to kick three.")
  # Two: join power room
  response_join_two = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_two.ok
  logging.info("[Test 3] Two joined the room succesfully.")
  # Two: fail to kick three, three not in room
  response_kick_two = requests.post(
    FULL_URL + "rooms/" + room_id + "/kick",
    headers=get_auth_header(two_session),
    json={
      "user_id": three_session["user_id"],
      "reason": "You smell."
    }
  )
  assert response_kick_two.status_code == 403
  assert response_kick_two.json()["errcode"] == "M_FORBIDDEN"
  assert response_kick_two.json()["error"].find("not in room")
  logging.info("[Test 3] Two failed succesfully to kick three (again).")
  # Three: join power room
  response_join_two = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(three_session),
  )
  assert response_join_two.ok
  logging.info("[Test 3] Three joined the room succesfully.")
  # Three: send message
  response_send_message_3 = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(three_session),
    json=text_message(MSG3_SUCCESS)
  )
  assert response_send_message_3.ok
  logging.info("[TEST 3] Trhee succesfully sent a message.")
  three_message_event_id = response_send_message_3.json()["event_id"]
  # Two: fail to kick three because no permission
  response_kick_two = requests.post(
    FULL_URL + "rooms/" + room_id + "/kick",
    headers=get_auth_header(two_session),
    json={
      "user_id": three_session["user_id"],
      "reason": "You smell."
    }
  )
  assert response_kick_two.status_code == 403
  assert response_kick_two.json()["errcode"] == "M_FORBIDDEN"
  assert response_kick_two.json()["error"].find("not in room")
  logging.info("[Test 3] Two failed succesfully to kick three (again, again).")
  # One: set power level of two to 49
  response_set_power_level_49 = requests.put(
    FULL_URL + "rooms/" + room_id + "/state/m.room.power_levels/" + random_number_string(),
    headers=get_auth_header(one_session),
    json={
    "users":
        {
            one_session["user_id"]:100,
            two_session["user_id"]:49
        },
        "users_default":0,
        "events":
        {
            "m.room.name":50,
            "m.room.power_levels":100,
            "m.room.history_visibility":100,
            "m.room.canonical_alias":50,
            "m.room.avatar":50,"m.room.tombstone":100,
            "m.room.server_acl":100,"m.room.encryption":100,
            "m.space.child":50,
            "m.room.topic":50,
            "m.room.pinned_events":50,
            "m.reaction":0,
            "m.room.redaction":0,
            "org.matrix.msc3401.call":50,
            "org.matrix.msc3401.call.member":50,
            "im.vector.modular.widgets":50,
            "io.element.voice_broadcast_info":50
        },
    "events_default":0,
    "state_default":50,
    "ban":50,
    "kick":50,
    "redact":50,
    "invite":50,
    "historical":100,
    "m.call.invite":50
  }
  )
  assert response_set_power_level_49.ok
  logging.info("[Test 3] Succesfully set power level of two to 49.")
  # Two: fail to kick three again because no permission
  response_kick_two = requests.post(
    FULL_URL + "rooms/" + room_id + "/kick",
    headers=get_auth_header(two_session),
    json={
      "user_id": three_session["user_id"],
      "reason": "You smell."
    }
  )
  assert response_kick_two.status_code == 403
  assert response_kick_two.json()["errcode"] == "M_FORBIDDEN"
  assert response_kick_two.json()["error"].find("not in room")
  logging.info("[Test 3] Two failed succesfully to kick three (again, again, again).")
  # One: set power level of two to 50
  response_set_power_level_50 = requests.put(
    FULL_URL + "rooms/" + room_id + "/state/m.room.power_levels/" + random_number_string(),
    headers=get_auth_header(one_session),
    json={
    "users":
        {
            one_session["user_id"]:100,
            two_session["user_id"]:50
        },
        "users_default":0,
        "events":
        {
            "m.room.name":50,
            "m.room.power_levels":100,
            "m.room.history_visibility":100,
            "m.room.canonical_alias":50,
            "m.room.avatar":50,"m.room.tombstone":100,
            "m.room.server_acl":100,"m.room.encryption":100,
            "m.space.child":50,
            "m.room.topic":50,
            "m.room.pinned_events":50,
            "m.reaction":0,
            "m.room.redaction":0,
            "org.matrix.msc3401.call":50,
            "org.matrix.msc3401.call.member":50,
            "im.vector.modular.widgets":50,
            "io.element.voice_broadcast_info":50
        },
    "events_default":0,
    "state_default":50,
    "ban":50,
    "kick":50,
    "redact":50,
    "invite":50,
    "historical":100,
    "m.call.invite":50
  }
  )
  assert response_set_power_level_50.ok
  logging.info("[Test 3] Succesfully set power level of two to 50.")

  # Two: kick three
  response_kick_two = requests.put(
    FULL_URL + "rooms/" + room_id + "/kick",
    headers=get_auth_header(two_session),
    json={
      "user_id": three_session["user_id"],
      "reason": "You smell."
    }
  )
  assert response_kick_two.ok
  logging.info("[Test 3] Two succesfully kicked three.")
  # Three: fail to send message
  response_send_message_3 = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(three_session),
    json=text_message(MSG3_FAIL)
  )
  assert response_send_message_3.status_code == 403
  assert response_send_message_3.json()["errcode"] == "M_FORBIDDEN"
  assert response_send_message_3.json()["error"].find("not in room")
  logging.info("[Test 3] Three failed succesfully to send message after being kicked from the room.")
  # One: read messages
  response_one_reading = requests.get(
    FULL_URL + "rooms/" + room_id + MESSAGES_WITH_FILTER,
    headers=get_auth_header(one_session)
  )
  server_three_message = find_event(response_one_reading.json(), event_id=three_message_event_id)
  assert server_three_message["content"]["body"] == MSG3_SUCCESS
  assert len(response_one_reading.json()["chunk"]) == 1 # Exactly two messages in room
  logging.info("[Test 3] SUCCESS")

def test4():
  # One: create lobby
  create_lobby = requests.post(
    FULL_URL + "createRoom",
    headers=get_auth_header(one_session),
    json= create_room_json("public_chat"),
  )
  assert create_lobby.ok, "Failed to create lobby."
  logging.info("[Test 4] Succesfully created lobby")
  lobby_id = create_lobby.json()["room_id"]
  
  
  # One: create hotel
  create_hotel = requests.post(
    FULL_URL + "createRoom",
    headers=get_auth_header(one_session),
    json= create_room_json("private_chat"),
  )
  assert create_hotel.ok, "Failed to create hotel."
  logging.info("[Test 4] Succesfully created hotel")
  hotel_id = create_hotel.json()["room_id"]
  
  # One: set join rule for hotel
  set_join_rule = requests.put(
    FULL_URL + "rooms/" + hotel_id + "/state/m.room.join_rules/" + random_number_string(),
    headers=get_auth_header(one_session),
    json={
    "join_rule": "restricted",
    "allow": [
      {
        "room_id": lobby_id,
        "type": "m.room_membership"
      }
    ]}
  )
  assert set_join_rule.ok, "Failed to set join rule."
  logging.info("[Test 4] Succesfully set join rule.")
  
  # Two: fail to join hotel
  response_join_two = requests.post(
    FULL_URL + "join/" + hotel_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_two.status_code == 403
  logging.info("[Test 4] Two failed to join the hotel succesfully.")
  
  # Two: join lobby
  response_two_join_lobby = requests.post(
    FULL_URL + "join/" + lobby_id,
    headers=get_auth_header(two_session),
  )
  assert response_two_join_lobby.ok, "[Test 4] Two failed to join the lobby"
  logging.info("[Test 4] Two joined the lobby sucessfully.")
  
  # Two: join hotel
  response_join_two = requests.post(
    FULL_URL + "join/" + hotel_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_two.ok
  logging.info("[Test 4] Two joined the hotel succesfully.")
  logging.info("[Test 4] Succes.")

# Test 6: Ban user from room
def test6():
  MSG2_FAIL = "Message from two that should fail"
  MSG2_SUCCES = "Message from two that should succeed"

  # One : Create a public room.
  create_room_json6 = create_room_json("public_chat")
  response_create_room_6 = requests.post(
    FULL_URL + "createRoom",
    headers=get_auth_header(one_session),
    json= create_room_json6,
  )
  assert response_create_room_6.ok, "Failed to create room."
  logging.info("[Test 6] Created room succesfully.")
  room_id = response_create_room_6.json()["room_id"]

  # Two: Join the room.
  two_auth_headers = {"Authorization": f"Bearer {two_session["access_token"]}"}
  response_join_room_6 = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_room_6, "Failed to join room."
  logging.info("[Test 6] Joined room succesfully.")

  # Two: Send a message in the room.
  response_message_two_1 = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(two_session),
    json=text_message(MSG2_SUCCES)
  )
  assert response_message_two_1.ok, "Failed to send message."
  logging.info("[Test 6] Two succesfully send message.")
  two_message_1_event_id = response_message_two_1.json()["event_id"]

  # One: Ban 'Two' from the room.
  logging.info("[Test 11] One succesfully kicked Two")
  response_ban_two = requests.post(
    FULL_URL + "rooms/" + room_id + "/ban",
    headers=get_auth_header(one_session),
    json = {"user_id": two_session["user_id"],
            "reason": "Should be banned."}
  )
  print(FULL_URL + "rooms/" + room_id + "/ban")
  assert response_ban_two.ok, "Failed to ban user."
  logging.info("[Test 6] One succesfully banned Two")
  
  # response_test_members = requests.get(
  #   FULL_URL + "rooms/" + room_id + "/members",
  #   headers=get_auth_header(one_session)
  # )
  # print(response_test_members.json())
  
  # Two: fail to read messages without filter
  response_two_reading = requests.get(
    FULL_URL + "rooms/" + room_id + "/messages",
    headers=get_auth_header(two_session)
  )
  assert response_two_reading.ok
  # assert not str(response_two_reading.json()).find(MSG1_SUCCES), "Two could read a message that was sent after were kicked out of the room"
  # logging.info("[Test 11] Two succesfully failed to read messages.")

  # Two: Send a message in the room (should fail).
  response_message_two_2 = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(two_session),
    json=text_message(MSG2_FAIL)
  )
  print(response_message_two_2.json())
  assert response_message_two_2.status_code == 403, "Two could send a message, even though they were banned."
  logging.info("[Test 6] Two succesfully failed to send message.")
  
  
  
  # One: Send a message in the room.

  # Two: Read messages from the room (should fail).

  # Two: Join the room (should fail).

  # One: Invites 'Three'.

  # One: Invites 'Two' (should fail).

  # One: Read messages from the room.

# test 11: Left user information leak 1
def test11():
  MSG1_SUCCES = "Message from one that should succeed"
  # One: create room
  response_create_room_1 = requests.post(
    FULL_URL + "createRoom",
    headers =get_auth_header(one_session),
    json = create_room_json("private_chat"),
  )
  assert response_create_room_1.ok
  logging.info("[TEST 11] Sucesfully created room.")
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
  logging.info("[TEST 11] Succesfully invited two.")
  
  # Two: join the room
  response_join_two = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_two.ok
  logging.info("[Test 11] Two joined the room succesfully.")
  
  # One: kick 'Two' from the room.
  response_kick_two = requests.post(
    FULL_URL + "rooms/" + room_id + "/kick",
    headers=get_auth_header(one_session),
    json = {"user_id": two_session["user_id"],
            "reason": "You smell."}
  )
  assert response_kick_two.ok, "Failed to kick user."
  logging.info("[Test 11] One succesfully kicked Two")
  
  # One: Send a message
  response_message_one = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(one_session),
    json=text_message(MSG1_SUCCES)
  )
  assert response_message_one.ok, "One failed to send a message"
  logging.info("[Test 11] One succesfully sent a message")
  
  # Two: fail to read messages without filter
  response_two_reading = requests.get(
    FULL_URL + "rooms/" + room_id + "/messages",
    headers=get_auth_header(two_session)
  )
  assert response_two_reading.ok
  assert not str(response_two_reading.json()).find(MSG1_SUCCES), "Two could read a message that was sent after were kicked out of the room"
  logging.info("[Test 11] Two succesfully failed to read messages.")
  
  
  # Two: fail to read messages with filter
  response_two_reading = requests.get(
    FULL_URL + "rooms/" + room_id + MESSAGES_WITH_FILTER,
    headers=get_auth_header(two_session)
  )
  assert response_two_reading.ok
  assert not str(response_two_reading.json()).find(MSG1_SUCCES), "Two could read a message that was sent after were kicked out of the room"
  logging.info("[Test 11] Two succesfully failed to read messages with filter.")

# test 12: Left user information leak 2
def test12():
  MSG1_SUCCES = "Message from one that should succeed"
  # One: create room
  response_create_room_1 = requests.post(
    FULL_URL + "createRoom",
    headers =get_auth_header(one_session),
    json = create_room_json("private_chat"),
  )
  assert response_create_room_1.ok
  logging.info("[TEST 12] Sucesfully created room.")
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
  logging.info("[TEST 12] Succesfully invited two.")
  
  # Two: join the room
  response_join_two = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_two.ok
  logging.info("[Test 12] Two joined the room succesfully.")
  
  # Two: leave
  response_leave_2 = requests.post(
    FULL_URL + "rooms/" + room_id + "/leave",
    headers=get_auth_header(two_session),
  )
  assert response_leave_2.ok, "Failed to leave."
  logging.info("[Test 12] Two succesfully left the room")
  
  # One: Send a message
  response_message_one = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(one_session),
    json=text_message(MSG1_SUCCES)
  )
  assert response_message_one.ok, "One failed to send a message"
  logging.info("[Test 12] One succesfully sent a message")
  
  # Two: fail to read messages without filter
  response_two_reading = requests.get(
    FULL_URL + "rooms/" + room_id + "/messages",
    headers=get_auth_header(two_session)
  )
  assert response_two_reading.ok
  assert not str(response_two_reading.json()).find(MSG1_SUCCES), "Two could read a message that was sent after they left the room"
  logging.info("[Test 12] Two succesfully failed to read messages.")
  
  # Two: fail to read messages with filter
  response_two_reading = requests.get(
    FULL_URL + "rooms/" + room_id + MESSAGES_WITH_FILTER,
    headers=get_auth_header(two_session)
  )
  assert response_two_reading.ok
  assert not str(response_two_reading.json()).find(MSG1_SUCCES), "Two could read a message that was sent after they left the room"
  logging.info("[Test 12] Two succesfully failed to read messages with filter.")

test6()
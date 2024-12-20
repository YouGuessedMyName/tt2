import requests
import logging
import copy
import random
import string
import sys
import subprocess
from time import sleep

### CONSTANTS SET BY THE USER ###
SYNAPSE_DOCKER_NAME = "synapse"
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
  assert response_kick_two.ok, "Three failed to kick two, even though they had the required power level."
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
  assert response_join_two.ok, "Two could not join the hotel, even though they were in the lobby."
  logging.info("[Test 4] Two joined the hotel succesfully.")
  logging.info("[Test 4] Succes.")

# Test 6: Ban user from room
def test6():
  MSG2_FAIL = "Message from two that should fail"
  MSG2_SUCCES = "Message from two that should succeed"

  # One: Create a public room.
  create_room_json6 = create_room_json("public_chat")
  response_create_room_6 = requests.post(
    FULL_URL + "createRoom",
    headers=get_auth_header(one_session),
    json= create_room_json6,
  )
  assert response_create_room_6.ok, "Failed to create room."
  logging.info("[Test 6] One created room succesfully.")
  room_id = response_create_room_6.json()["room_id"]

  # Two: Join the room.
  response_join_room_6 = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_room_6.ok, "Failed to join room."
  logging.info("[Test 6] Two joined room succesfully.")

  # Two: Send a message in the room.
  response_message_two_1 = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(two_session),
    json=text_message(MSG2_SUCCES)
  )
  assert response_message_two_1.ok, "Failed to send message."
  logging.info("[Test 6] Two succesfully send message.")

  # One: Ban 'Two' from the room.
  response_ban_two = requests.post(
    FULL_URL + "rooms/" + room_id + "/ban",
    headers=get_auth_header(one_session),
    json = {"user_id": two_session["user_id"],
            "reason": "Should be banned."}
  )
  assert response_ban_two.ok, "Failed to ban user."
  logging.info("[Test 6] One succesfully banned Two")

  # Two: Send a message in the room (should fail).
  # This message was left out of the test due to an issue
  
  # One: Send a message in the room.
  response_message_one = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(one_session),
    json=text_message(MSG2_SUCCES)
  )
  assert response_message_one.ok, "Failed to send message."
  logging.info("[Test 6] One succesfully send message.")
  
  # Two: Read messages from the room (should fail).
  # This message was left out of the test due to an issue
  
  # Two: Join the room (should fail).
  response_join_room_6 = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_room_6.status_code == 403, "Joined room." 
  logging.info("[Test 6] Two succesfully failed to join room.")

  # One: Invites 'Three'.
  response_invite_3 = requests.post(
    FULL_URL + "rooms/" + room_id + "/invite",
    headers = get_auth_header(one_session),
    json={
      "reason": "Welcome",
      "user_id": three_session["user_id"]
    }
  )
  assert response_invite_3.ok, "Failed to invite Three"
  logging.info("[Test 6] One succesfully invited Three.")

  # One: Invites 'Two' (should fail).
  response_invite_2 = requests.post(
    FULL_URL + "rooms/" + room_id + "/invite",
    headers = get_auth_header(one_session),
    json={
      "reason": "Welcome",
      "user_id": two_session["user_id"]
    }
  )
  assert response_invite_2.status_code == 403, " Succeeded in inviting Two"
  logging.info("[Test 6] One succesfully failed to invited Two.")

  # One: Read messages from the room.
  # This part was left out of the test due to an issue


# test 7: Unban user from room
def test7():
  MSG2_SUCCES = "Message from two that should succeed"

  # One: Create a public room.
  create_room_json7 = create_room_json("public_chat")
  response_create_room_7 = requests.post(
    FULL_URL + "createRoom",
    headers=get_auth_header(one_session),
    json= create_room_json7,
  )
  assert response_create_room_7.ok, "Failed to create room."
  logging.info("[Test 7] One created room succesfully.")
  room_id = response_create_room_7.json()["room_id"]

  # Two: Join the room.
  response_join_room_7 = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_room_7.ok, "Failed to join room."
  logging.info("[Test 7] Two joined room succesfully.")

  # One: Ban 'Two' from the room.
  response_ban_two = requests.post(
    FULL_URL + "rooms/" + room_id + "/ban",
    headers=get_auth_header(one_session),
    json = {"user_id": two_session["user_id"],
            "reason": "Should be banned."}
  )
  assert response_ban_two.ok, "Failed to ban user."
  logging.info("[Test 7] One succesfully banned Two")

  # Two: Send a message in the room (should fail).
  # This message was left out of the test due to an issue

  # One: Unban 'Two' from the room.
  response_unban_two = requests.post(
    FULL_URL + "rooms/" + room_id + "/unban",
    headers=get_auth_header(one_session),
    json = {"user_id": two_session["user_id"]}
  )
  assert response_unban_two.ok, "Failed to unban user."
  logging.info("[Test 7] One succesfully unbanned Two")

  # Two: Send a message in the room (should fail).
  # This message was left out of the test due to an issue

  # Two: Join the room.
  response_join_room_7 = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_room_7.ok, "Failed to join room."
  logging.info("[Test 7] Two joined room succesfully.")

  # Two: Send a message in the room.
  response_message_two = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(two_session),
    json=text_message(MSG2_SUCCES)
  )
  assert response_message_two.ok, "Failed to send a messages"
  logging.info("[Test 7] Two succesfully send a message.")

  # One: Read messages from the room.
  # This part was left out of the test due to an issue

# Test 8: Leaving a room should prevent you from sending messages, and retrieving messages from after you left
def test8():
  # One: Create a new public room
  create_room_json8 = create_room_json("public_chat")
  response_create_room8 = requests.post(
    FULL_URL + "createRoom",
    headers=get_auth_header(one_session),
    json = create_room_json8
  )  
  assert response_create_room8.ok, "Failed to create room."
  logging.info("[Test 8] One created room successfully")
  room_id = response_create_room8.json()["room_id"]

  # Two: Join the room
  response_join_room8 = requests.post(
    FULL_URL + "join/" + room_id,
    headers = get_auth_header(two_session)
  )
  assert response_join_room8.ok, "Failed to join room."
  logging.info("[Test 8] Two joined room successfully")

  # Two: Send a message in the room
  MSG8_SUCCESS1 = "Message from two that should succeed"
  response_send_message_8_1 = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(two_session),
    json=text_message(MSG8_SUCCESS1)
  )
  assert response_send_message_8_1.ok, "Failed to send message"
  logging.info("[TEST 8] Two succesfully sent a message.")

  # Two: Leave the room
  response_leave_room = requests.post(
    FULL_URL + "rooms/" + room_id + "/leave",
    headers = get_auth_header(two_session)
  )
  assert response_leave_room.ok, "Failed to leave room."
  logging.info("[Test 8] Two left the room successfully.")

  # One: check members of the room
  response_get_members = requests.get(
    FULL_URL + "rooms/" + room_id + "/members",
    headers = get_auth_header(one_session)
  )
  assert response_get_members.ok, "Failed to get member list"
  logging.info("[Test 8] One retrieved member list successfully")
  
  # Check if member information is correct
  logging.info("[Test 8] Checking member list for correct statuses.")
  members_list = response_get_members.json().get("chunk", [])
  user_one_in_room = False
  user_two_left_room = False

  for member in members_list:
      user_id = member.get("user_id")
      membership_status = member.get("content", {}).get("membership")

      if user_id == "@one:my.matrix.host" and membership_status == "join":
          user_one_in_room = True
          logging.info("[Test 8] One is in the room as expected.")
      elif user_id == "@two:my.matrix.host" and membership_status == "leave":
          user_two_left_room = True
          logging.info("[Test 8] Two has left the room as expected.")
  assert user_one_in_room, "[Test 8] One is not in the room when they should be."
  assert user_two_left_room, "[Test 8] Two is still in the room when they should have left."

  # Two: Send a message in the room (should fail)
  MSG8_FAIL = "Message from two that should fail"
  response_send_message_8_2 = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message" + random_number_string(),
    headers = get_auth_header(two_session),
    json = text_message(MSG8_FAIL)
  )
  error_message = response_send_message_8_2.json().get("error", "No error message provided")
  if response_send_message_8_2.status_code == 403: 
    # Expected outcome: Two fails to send message
    logging.info("[Test 8] Two failed to send a messages successfully")
  elif response_send_message_8_2.status_code == 200: 
    # Unexpected outcome: Two was able to send a message
    logging.info("[Test 8] One was wrongly able to send a message")
  else:
    # Other outcome: Unexpected response status code
    logging.info(f"[Test 8] Unexpected response status code {error_message} {response_send_message_8_2.status_code}")

  response = requests.get(
    FULL_URL + f"rooms/{room_id}/messages?filter=%7B%22types%22%3A%5B%22m.room.message%22%5D%7D",
    headers=get_auth_header(one_session)
  )
  assert response.ok, "Failed to retrieve messages."

  # One: Check to see if the message from 2 is there
  response_messages = requests.get(
    FULL_URL + "rooms/" + room_id + MESSAGES_WITH_FILTER,
    headers = get_auth_header(one_session)
  )
  messages = response_messages.json().get("chunk", [])
  for message in messages:
    if message.get("content", {}).get("body") == MSG8_SUCCESS1:
      logging.info("[Test 8] First message from two correctly visible")
    if message.get("content", {}).get("body") == MSG8_FAIL:
      logging.info("[Test 8] Second message from two incorrectly visible")
    else:
      logging.info("[Test 8] Second message from two is not visible as expected")

  # One: Send a message in the room
  MSG8_SUCCESS2 = "Message from one that should succeed"
  response_send_message_8_3 = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(one_session),
    json=text_message(MSG8_SUCCESS2)
  )
  assert response_send_message_8_3.ok, "Failed to send message"
  logging.info("[TEST 8] One succesfully sent a message.")

  # Two: get all messages from the room, not supposed to get the message from One
  response_messages = requests.get(
    FULL_URL + "rooms/" + room_id + MESSAGES_WITH_FILTER,
    headers = get_auth_header(two_session)
  )
  messages = response_messages.json().get("chunk", [])
  for message in messages:
    if message.get("content", {}).get("body") == MSG8_SUCCESS1:
      logging.info("[Test 8] First message from two correctly visible")
    if message.get("content", {}).get("body") == MSG8_FAIL:
      logging.info("[Test 8] Second message from two incorrectly visible")
    else:
      logging.info("[Test 8] Second message from two is not visible as expected")
    if message.get("content", {}).get("body") == MSG8_SUCCESS2:
      logging.info("[Test 8] Message from one incorrectly visible")
    else:
      logging.info("[Test 8] Message from one is not visible as expected")
  
# Test 9: Leaving an invite-only room should prevent you from joining again  
def test9():
  # One: Create a new private room
  create_room_json9 = create_room_json("trusted_private_chat")
  response_create_room9 = requests.post(
    FULL_URL + "createRoom",
    headers=get_auth_header(one_session),
    json = create_room_json9
  )  
  assert response_create_room9.ok, "Failed to create room."
  logging.info("[Test 9] One created a private room successfully")
  room_id = response_create_room9.json()["room_id"]

  # One: invite two to the room
  response_invite_9 = requests.post(
    FULL_URL + "rooms/" + room_id + "/invite",
    headers = get_auth_header(one_session),
    json={
      "reason": "Two can join room now",
      "user_id": two_session["user_id"]
    }
  )  
  assert response_invite_9.ok, "Failed to invite two to room"
  logging.info("[Test 9] Succesfully invited two to room")

  # Two: Join the private room
  response_join_9 = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  assert response_join_9.ok, "Failed to join room"
  logging.info("[Test 9] Two succesfully joined the room.")

  # Two: send message in the room
  MSG2_SUCCESS = "Message from two that should succeed"
  response_send_message_2 = requests.put(
    FULL_URL + "rooms/" + room_id + "/send/m.room.message/" + random_number_string(),
    headers=get_auth_header(two_session),
    json=text_message(MSG2_SUCCESS)
  )
  assert response_send_message_2.ok, "Failed to send message"
  logging.info("[Test 9] Two succesfully sent a message.")

  # Two: Leave the room
  response_leave_room = requests.post(
    FULL_URL + "rooms/" + room_id + "/leave",
    headers = get_auth_header(two_session)
  )
  assert response_leave_room.ok, "Failed to leave room."
  logging.info("[Test 9] Two left the room successfully.")

  # One: check members of the room
  response_get_members = requests.get(
    FULL_URL + "rooms/" + room_id + "/members",
    headers = get_auth_header(one_session)
  )
  assert response_get_members.ok, "Failed to get member list"
  logging.info("[Test 9] One retrieved member list successfully")

  # Check if member information is correct
  logging.info("[Test 9] Checking member list for correct statuses.")
  members_list = response_get_members.json().get("chunk", [])
  user_one_in_room = False
  user_two_left_room = False

  for member in members_list:
      user_id = member.get("user_id")
      membership_status = member.get("content", {}).get("membership")

      if user_id == "@one:my.matrix.host" and membership_status == "join":
          user_one_in_room = True
          logging.info("[Test 9] One is in the room as expected.")
      elif user_id == "@two:my.matrix.host" and membership_status == "leave":
          user_two_left_room = True
          logging.info("[Test 9] Two has left the room as expected.")
  assert user_one_in_room, "One is not in the room when they should be."
  assert user_two_left_room, "Two is still in the room when they should have left."

  # Two: Try to join room again (should fail)
  response_rejoin_9 = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  if response_rejoin_9.status_code == 403:
    logging.info("[Test 9] Two failed to rejoin the room as expected")
  else:
    assert response_rejoin_9.ok, "Two was able to rejoin the room unexpectedly"
  
# Test 10: Leaving a room before joining should prevent you from joining at all.
def test10():
  # One: Create a new private room
  create_room_json10 = create_room_json("trusted_private_chat")
  response_create_room10 = requests.post(
    FULL_URL + "createRoom",
    headers=get_auth_header(one_session),
    json = create_room_json10
  )  
  assert response_create_room10.ok, "Failed to create room."
  logging.info("[Test 10] One created a private room successfully")
  room_id = response_create_room10.json()["room_id"]

  # One: invite two to the room
  response_invite_10 = requests.post(
    FULL_URL + "rooms/" + room_id + "/invite",
    headers = get_auth_header(one_session),
    json={
      "reason": "Two can join room now",
      "user_id": two_session["user_id"]
    }
  )  
  assert response_invite_10.ok, "Failed to invite two to room"
  logging.info("[Test 10] Succesfully invited two to room")

  # Two: Leave the room
  response_leave_room = requests.post(
    FULL_URL + "rooms/" + room_id + "/leave",
    headers = get_auth_header(two_session)
  )
  assert response_leave_room.ok, "Failed to leave room."
  logging.info("[Test 10] Two left the room successfully.")

  # One: check members of the room
  response_get_members = requests.get(
    FULL_URL + "rooms/" + room_id + "/members",
    headers = get_auth_header(one_session)
  )
  assert response_get_members.ok, "Failed to get member list"
  logging.info("[Test 10] One retrieved member list successfully")

  # Check if member information is correct
  logging.info("[Test 10] Checking member list for correct statuses.")
  members_list = response_get_members.json().get("chunk", [])
  user_one_in_room = False
  user_two_left_room = False

  for member in members_list:
      user_id = member.get("user_id")
      membership_status = member.get("content", {}).get("membership")

      if user_id == "@one:my.matrix.host" and membership_status == "join":
          user_one_in_room = True
          logging.info("[Test 10] One is in the room as expected.")
      elif user_id == "@two:my.matrix.host" and membership_status == "leave":
          user_two_left_room = True
          logging.info("[Test 10] Two has status leave as expacted.")
  assert user_one_in_room, "One is not in the room when they should be."
  assert user_two_left_room, "Two is still in the room when they should have left."

  # Two: Join the private room (should fail)
  response_join_10 = requests.post(
    FULL_URL + "join/" + room_id,
    headers=get_auth_header(two_session),
  )
  if response_join_10.status_code == 403:
    logging.info("[Test 10] Two failed to join the room as expected")
  else:
    assert response_join_10.ok, "Two was able to join the room unexpectedly"

  # One: check members of the room
  response_get_members = requests.get(
    FULL_URL + "rooms/" + room_id + "/members",
    headers = get_auth_header(one_session)
  )
  assert response_get_members.ok, "Failed to get member list"
  logging.info("[Test 10] One retrieved member list successfully")

  # Check if member information is correct
  logging.info("[Test 10] Checking member list for correct statuses.")
  members_list = response_get_members.json().get("chunk", [])
  user_one_in_room = False
  user_two_left_room = False

  for member in members_list:
      user_id = member.get("user_id")
      membership_status = member.get("content", {}).get("membership")

      if user_id == "@one:my.matrix.host" and membership_status == "join":
          user_one_in_room = True
          logging.info("[Test 10] One is in the room as expected.")
      elif user_id == "@two:my.matrix.host" and membership_status == "leave":
          user_two_left_room = True
          logging.info("[Test 10] Two has status leave as expacted.")
  assert user_one_in_room, "One is not in the room when they should be."
  assert user_two_left_room, "Two is still in the room when they should have left." 

# test 11: Kicked user information leak 1
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
  assert str(response_two_reading.json()).find(MSG1_SUCCES) == -1, "Two could read a message that was sent after were kicked out of the room"
  logging.info("[Test 11] Two succesfully failed to read messages.")
  
  
  # Two: fail to read messages with filter
  response_two_reading = requests.get(
    FULL_URL + "rooms/" + room_id + MESSAGES_WITH_FILTER,
    headers=get_auth_header(two_session)
  )
  assert response_two_reading.ok
  assert str(response_two_reading.json()).find(MSG1_SUCCES) == -1, "Two could read a message that was sent after were kicked out of the room"
  logging.info("[Test 11] Two succesfully failed to read messages with filter.")

# test 12: Left user information leak
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
  assert str(response_two_reading.json()).find(MSG1_SUCCES) == -1, "Two could read a message that was sent after they left the room"
  logging.info("[Test 12] Two succesfully failed to read messages.")
  
  # Two: fail to read messages with filter
  response_two_reading = requests.get(
    FULL_URL + "rooms/" + room_id + MESSAGES_WITH_FILTER,
    headers=get_auth_header(two_session)
  )
  assert response_two_reading.ok
  assert str(response_two_reading.json()).find(MSG1_SUCCES) == -1, "Two could read a message that was sent after they left the room"
  logging.info("[Test 12] Two succesfully failed to read messages with filter.")

# test 13: Banned user information leak
def test13():
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
  
  # One: ban two
  response_ban_two = requests.post(
    FULL_URL + "rooms/" + room_id + "/ban",
    headers=get_auth_header(one_session),
    json = {"user_id": two_session["user_id"],
            "reason": "You smell."}
  )
  assert response_ban_two.ok, "Failed to ban two."
  logging.info("[Test 12] One succesfully banned two")
  
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
  assert response_two_reading.status_code == 403
  logging.info("[Test 12] Two succesfully failed to read messages. (No permission)")
  
  # Two: fail to read messages with filter
  response_two_reading = requests.get(
    FULL_URL + "rooms/" + room_id + MESSAGES_WITH_FILTER,
    headers=get_auth_header(two_session)
  )
  assert response_two_reading.status_code == 403
  logging.info("[Test 12] Two succesfully failed to read messages (No permission).")

TESTS = {
  "1": test1,
  "2": test2,
  "3": test3,
  "4": test4,
  # "5": test5,
  "6": test6,
  "7": test7,
  "8": test8,
  "9": test9,
  "10": test10,
  "11": test11,
  "12": test12,
  "13": test13,
}
  
if (len(sys.argv) <= 1):
  print("Specifiy the test to run in the argument")
  exit()
else:
  if not sys.argv[1] in TESTS:
    print(f"test {sys.argv[1]} does not exist, skipping.")
    exit()
  print(f"\nRestarting synapse server for test {sys.argv[1]}")
  subprocess.run(["docker", "restart", "synapse"])
  sleep(3)
  # Login to the three sessions.
  one_session = login_user("one", "one")
  two_session = login_user("two", "two")
  three_session = login_user("three", "three")
  print(f"Running test {sys.argv[1]}")
  TESTS[sys.argv[1]]()
  print(f"Passed test {sys.argv[1]}")
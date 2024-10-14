import requests
import logging
import copy

### ESTABLISH SESSIONS ###
BASE_URL = "http://localhost:8008"
FULL_URL = BASE_URL + "/_matrix/client/v3/"

logging.basicConfig(level=logging.DEBUG)

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
assert login_enabled_response.ok, "Server disabled password login"

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

# Login to the three sessions.
one_session = login_user("one", "one")
two_session = login_user("two", "two")
three_session = login_user("three", "three")
print(one_session)

### START TESTS ###


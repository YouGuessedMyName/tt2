# Testing techniques Assignment 2
## Requirements & preparation
A docker container running synapse.

In the file `test_matrix.py`, set the following variables according to your specific setup:
* SYNAPSE_DOCKER_NAME: The name of the docker container
* BASE_URL: "http://localhost:8008"

Create three users on the Synapse server.
* User 'one' with password 'one'
* User 'two' with password 'two'
* User 'three' with password 'three'

You can do this manually, or using:
```sh
docker exec -it synapse register_new_matrix_user BASE_URL -c /data/homeserver.yaml --help
```

## Usage
Run all tests:
```sh
./run_all
```

Run a specific test:
```sh
python3 test_matrix.py 1
```
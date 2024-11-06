# Testing techniques Assignment 2
## Requirements & preparation
You need a docker container running synapse.

In the file `test_matrix.py`, set the following variables according to your specific setup:
* SYNAPSE_DOCKER_NAME: The name of the docker container
* BASE_URL: The URL where your synapse is live (e.g. "http://localhost:8008")

Create three users on the Synapse server.
* User 'one' with password 'one'
* User 'two' with password 'two'
* User 'three' with password 'three'

You can do this manually, or using:
```sh
docker exec -it synapse register_new_matrix_user BASE_URL -c /data/homeserver.yaml
```

## Usage
Run all tests:
```sh
./run_all.sh
```

Run a specific test:
```sh
python3 test_matrix.py n
```
(Where `n` is the number of the test that you want to run.)
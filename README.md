# To run (virtualenv)

    virtualenv3 .
    . bin/activate
    pip install -r requirements.txt
    python smoky3.py <hostname> <test config>

## Running in a docker container

    docker build -t t0mmyt/smoky .
    docker run --rm -t -v $(pwd)/uswitch.com.yml:/uswitch.com.yml t0mmyt/smoky nginx.uswitch.com /uswitch.com.yml

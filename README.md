# Smoky(3)

HTTP Test Harness for "Smoke testing" nginxlb using python3/asyncio.

# Running

## To run (virtualenv)

    virtualenv3 .
    . bin/activate
    pip install -r requirements.txt
    python smoky3.py <hostname> <test config>

## Running in a docker container

    docker build -t t0mmyt/smoky .
    docker run --rm -t -v $(pwd)/uswitch.com.yml:/uswitch.com.yml t0mmyt/smoky nginx.uswitch.com /uswitch.com.yml

# Config

Tests to run are stored in YAML. Top level key is the Host header, second level key is the name of the check (found in the HttpSmokeTest class).  Last level is an array test parameters, each parameter being an array of the arguments passed to the test.

### Example

    ---
    www.uswitch.com:
      check_200:
        - "/health-insurance/quote/secure/v2/getquotes.aspx"
        - "/home-insurance/quotes/"
      check_3xx:
        - ["/account/", "https://www.uswitch.com/account/signin"]
        - ["/gas-electricity", "https://www.uswitch.com/gas-electricity/"]

# Limitations

It will not successfully follow a 30x redirect to another domain due to the way it handles the host header.

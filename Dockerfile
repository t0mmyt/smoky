FROM ubuntu:16.04
MAINTAINER Core IT <tom.taylor@uswitch.com>

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -yqq update && apt-get -yqq upgrade

ENV INSTALL_LOCATION /opt/uswitch/smoky3

RUN apt-get -yqq install python3 python3-pip
RUN mkdir -p ${INSTALL_LOCATION}
WORKDIR ${INSTALL_LOCATION}
ADD requirements.txt smoky3.py ./
RUN pip3 install -r requirements.txt

ENTRYPOINT ["./smoky3.py"]

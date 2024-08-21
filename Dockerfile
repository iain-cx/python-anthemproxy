FROM python:3.10.14-alpine3.19

EXPOSE 14999/udp
EXPOSE 14999/tcp

COPY . /tmp/src
WORKDIR /tmp/src
RUN python setup.py build install
RUN rm -rf /tmp/src
COPY proxy /usr/bin/anthemproxy

WORKDIR /
ENTRYPOINT ["/usr/bin/anthemproxy"]

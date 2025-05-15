FROM debian:stable-slim

RUN apt update && \
    apt install -y tor openvpn && \
    apt clean

COPY torrc /etc/tor/torrc
COPY torvpn.ovpn /etc/openvpn/client.conf

CMD openvpn --config /etc/openvpn/client.conf --daemon && \
    sleep 5 && \
    tor

FROM debian:bookworm

# Установка зависимостей
RUN apt update && apt install -y tor snowflake-client

# Копируем конфиг
COPY torrc /etc/tor/torrc

# Запускаем tor
CMD ["tor", "-f", "/etc/tor/torrc"]

#!/usr/bin/with-contenv bashio
set -e

TIGO_SERVER=$(bashio::config 'tigo_server')
TIGO_PORT=$(bashio::config 'tigo_port')
MAX_READ=$(bashio::config 'max_read')

MQTT_HOST=$(bashio::services mqtt "host")
MQTT_PORT=$(bashio::services mqtt "port")
MQTT_USER=$(bashio::services mqtt "username")
MQTT_PASSWORD=$(bashio::services mqtt "password")

bashio::log.info "Remote Server: ${TIGO_SERVER}:${TIGO_PORT} - Max Read ${MAX_READ}"
bashio::log.info "MQTT Info: ${MQTT_HOST}:${MQTT_PORT}, ${MQTT_USER}/${MQTT_PASSWORD}"

python3 /app/server.py -s "${TIGO_SERVER}" -p "${TIGO_PORT}" -r "${MAX_READ}" --mqtt-host "${MQTT_HOST}" --mqtt-port "${MQTT_PORT}" --mqtt-user "${MQTT_USER}" --mqtt-password "${MQTT_PASSWORD}"
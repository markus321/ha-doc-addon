#!/usr/bin/with-contenv bashio
bashio::log.info "Starte HA-Doku ..."
cd /app
exec python3 -u server.py

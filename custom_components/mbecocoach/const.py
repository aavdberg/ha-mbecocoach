"""Constants for Mercedes Eco Coach."""

from datetime import timedelta

DOMAIN = "mbecocoach"
CONF_VIN = "vin"
CONF_TOKEN = "token"
BASE_URL = "https://ecocoach.query.api.dvb.corpinter.net"
UPDATE_INTERVAL = timedelta(minutes=15)

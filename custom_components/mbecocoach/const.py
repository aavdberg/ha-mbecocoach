"""Constants for Mercedes Eco Coach."""

from datetime import timedelta

DOMAIN = "mbecocoach"
CONF_VIN = "vin"
CONF_TOKEN = "token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_EXPIRES_AT = "expires_at"
BASE_URL = "https://ecocoach.query.api.dvb.corpinter.net"
UPDATE_INTERVAL = timedelta(minutes=15)

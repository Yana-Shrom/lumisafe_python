"""
Configuration centralisée du service Python LumiSafe.
Miroir de include/config.h côté C : mêmes topics, même broker.
"""

# ---------- MQTT ----------
MQTT_HOST = "localhost"
MQTT_PORT = 8883                     # port TLS, jamais 1883 en clair
MQTT_CLIENT_ID = "lumisafe-python-core"
MQTT_USERNAME = "python_client"
MQTT_PASSWORD = "CHANGE_ME_MOT_DE_PASSE_FORT"  # doit correspondre au compte créé côté Mosquitto

MQTT_CA_CERT = "/etc/mosquitto/certs/ca.crt"

# ---------- Topics ----------
LAMPPOST_ID = "lamppost1"
TOPIC_MOTION = f"lumisafe/{LAMPPOST_ID}/motion"
TOPIC_COMMANDS = f"lumisafe/{LAMPPOST_ID}/commands/#"

# Topic sur lequel ce service a le droit d'écrire (voir ACL Mosquitto)
TOPIC_LIGHT_COMMAND = f"lumisafe/{LAMPPOST_ID}/commands/light"

"""
Configuration centralisée du service Python LumiSafe.
Miroir de include/config.h côté C : mêmes topics, même broker.

Le mot de passe MQTT ne vit JAMAIS en clair ici : il est lu depuis la
variable d'environnement LUMISAFE_MQTT_PASSWORD (voir .env.example et
.gitignore — un fichier .env local n'est jamais commité).
"""

import os

# ---------- MQTT ----------
MQTT_HOST = "localhost"
MQTT_PORT = 8883                     # port TLS, jamais 1883 en clair
MQTT_CLIENT_ID = "lumisafe-python-core"
MQTT_USERNAME = "python_client"

# Valeur de secours volontairement invalide : si personne n'a défini la
# variable d'environnement, la connexion MQTT échouera bruyamment plutôt
# que d'utiliser silencieusement un mauvais mot de passe.
MQTT_PASSWORD = os.environ.get("LUMISAFE_MQTT_PASSWORD", "CHANGE_ME_MOT_DE_PASSE_FORT")

MQTT_CA_CERT = "/etc/mosquitto/certs/ca.crt"

# ---------- Topics ----------
LAMPPOST_ID = "lamppost1"
TOPIC_MOTION = f"lumisafe/{LAMPPOST_ID}/motion"
TOPIC_COMMANDS = f"lumisafe/{LAMPPOST_ID}/commands/#"

# Topic sur lequel ce service a le droit d'écrire (voir ACL Mosquitto)
TOPIC_LIGHT_COMMAND = f"lumisafe/{LAMPPOST_ID}/commands/light"

# ---------- Caméra ----------
# Dossier où sont stockées les photos prises lors d'une détection.
# Sur le Pi, préfère un chemin hors du repo (ex: /home/pi/lumisafe/captures).
CAMERA_OUTPUT_DIR = "/home/pi/lumisafe/captures"

CAMERA_RESOLUTION = (1920, 1080)

# Nombre de secondes minimum entre deux captures, pour éviter de spammer
# le disque si le PIR flickers (détection/effacement rapides).
CAMERA_COOLDOWN_SECONDS = 5

"""
Configuration centralisée du service Python LumiSafe.
Miroir de include/config.h côté C : mêmes topics, même broker.

Le mot de passe MQTT ne vit JAMAIS en clair ici : il est lu depuis la
variable d'environnement LUMISAFE_MQTT_PASSWORD (voir .env.example et
.gitignore — un fichier .env local n'est jamais commité).
"""

import os
from pathlib import Path

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

# ---------- Topics : capteurs vandalisme (micro + accéléromètre) ----------
# Contrat proposé à Cédric, à valider avant qu'il code le C (cf. CONTRACT_CAPTEURS.md) :
# le C publie la valeur brute en continu (payload = simple nombre en texte,
# ex: "72.4"), PAS un booléen déjà seuillé. Le seuillage vit ici, côté
# Python, pour pouvoir ajuster la sensibilité sans recompiler/redéployer
# sur le Pi.
TOPIC_SOUND = f"lumisafe/{LAMPPOST_ID}/sound"          # payload: niveau en dB, ex "72.4"
TOPIC_VIBRATION = f"lumisafe/{LAMPPOST_ID}/vibration"  # payload: accélération en g, ex "1.8"

# Topic de commande pour le buzzer/alerte (déjà couvert par l'ACL
# existante "python_client write lumisafe/lamppost1/commands/#", rien à
# changer côté Mosquitto)
TOPIC_ALERT_COMMAND = f"lumisafe/{LAMPPOST_ID}/commands/alert"

# Seuils de déclenchement — logique métier, à affiner avec Cédric une
# fois le micro et l'accéléromètre réellement branchés et calibrés.
SOUND_THRESHOLD_DB = 70.0
VIBRATION_THRESHOLD_G = 1.5

# ---------- Caméra ----------
# Dossier où sont stockées les photos prises lors d'une détection.
# Sur le Pi, préfère un chemin hors du repo (ex: /home/pi/lumisafe/captures).
CAMERA_OUTPUT_DIR = "/home/pi/lumisafe/captures"

CAMERA_RESOLUTION = (1920, 1080)

# Nombre de secondes minimum entre deux captures, pour éviter de spammer
# le disque si le PIR flickers (détection/effacement rapides).
CAMERA_COOLDOWN_SECONDS = 5

# ---------- Historique (SQLite) ----------
# Base partagée : le service MQTT (main.py) écrit, l'API REST (api/) lit.
# Défaut : un fichier dans le repo (ignoré par git, voir .gitignore) — ça
# marche sans configuration sur n'importe quelle machine de dev (Mac,
# Linux...), contrairement à un chemin Pi codé en dur. Sur le vrai Pi en
# prod, définis LUMISAFE_DB_PATH=/home/pi/lumisafe/history.db dans .env
# pour sortir la base du repo, comme CAMERA_OUTPUT_DIR.
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "lumisafe.db"
DB_PATH = os.environ.get("LUMISAFE_DB_PATH", str(_DEFAULT_DB_PATH))

# ---------- API REST (dashboard François/Guillaume) ----------
# Comme MQTT_PASSWORD : jamais en clair, lue depuis l'environnement.
# Le placeholder fait échouer l'auth bruyamment (500, voir api/auth.py)
# plutôt que d'exposer l'API sans clé par erreur.
API_KEY = os.environ.get("LUMISAFE_API_KEY", "CHANGE_ME_CLE_API")
API_HOST = os.environ.get("LUMISAFE_API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("LUMISAFE_API_PORT", "8000"))

# LumiSafe — Service Python (logique métier)

Ce service s'abonne au broker MQTT Mosquitto, reçoit les événements de
mouvement publiés par le module C (capteur PIR), applique la logique
métier, republie une commande d'allumage/extinction, et déclenche une
capture caméra lors d'une détection. Il ne connaît rien du GPIO ni du
C — uniquement des messages MQTT.

## 1. Prérequis

- Python 3.9+
- Le broker Mosquitto déjà configuré et sécurisé (voir le README du
  module C `lumisafe_pir`, section "Sécurisation du broker Mosquitto")
- Le compte `python_client` déjà créé côté Mosquitto (`mosquitto_passwd`)
- Une copie du certificat `ca.crt` accessible en lecture depuis ce service
- (Sur le Pi, pour la caméra) le module CSI branché + `python3-picamera2`
  installé via apt — voir section 8

## 2. Installation

```bash
cd lumisafe_python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> Le projet est volontairement figé sur `paho-mqtt==1.6.1` : la version
> 2.x a changé la signature des callbacks (`on_connect`, etc.). Si vous
> migrez vers paho-mqtt 2.x plus tard, il faudra adapter `mqtt_client.py`.

## 3. Configuration

Le mot de passe MQTT n'est plus jamais écrit en clair dans `config.py` :
il est lu depuis la variable d'environnement `LUMISAFE_MQTT_PASSWORD`.

```bash
cp .env.example .env
# édite .env avec le vrai mot de passe du compte python_client
export $(grep -v '^#' .env | xargs)
```

Puis édite `lumisafe/config.py` si besoin pour :

- `MQTT_CA_CERT` : le chemin vers `ca.crt` (copie-le depuis le Pi si ce
  service tourne ailleurs, sinon laisse le chemin par défaut)
- `LAMPPOST_ID` : doit correspondre à celui utilisé côté C
- `CAMERA_OUTPUT_DIR` / `CAMERA_RESOLUTION` / `CAMERA_COOLDOWN_SECONDS` :
  paramètres de capture (voir section 8)

`.env` est dans `.gitignore` — il ne partira jamais sur GitHub. Sans la
variable d'environnement définie, `MQTT_PASSWORD` retombe sur le
placeholder `CHANGE_ME_MOT_DE_PASSE_FORT`, qui fera échouer la connexion
MQTT bruyamment plutôt que d'utiliser silencieusement un mauvais secret.

## 4. Lancer

```bash
python3 main.py
```

Tu devrais voir :

```
LumiSafe - service Python démarré. Ctrl+C pour arrêter.
[mqtt] Connecté au broker (localhost:8883)
[mqtt] Abonné à lumisafe/lamppost1/motion
```

Et à chaque mouvement détecté par le module C :

```
[domaine] Mouvement détecté -> activation lampadaire + caméra
[camera] Photo capturée -> /home/pi/lumisafe/captures/20260710_151032_motion_detected.jpg
```

## 5. Structure du projet

```
lumisafe_python/
├── main.py                    # Point d'entrée, relie infra <-> domaine
├── requirements.txt
├── lumisafe/
│   ├── config.py               # Paramètres centralisés (miroir de config.h)
│   ├── mqtt_client.py         # Couche infra : tout paho-mqtt vit ici
│   ├── camera_controller.py   # Couche infra : tout picamera2 vit ici
│   └── motion_handler.py      # Couche domaine : logique métier pure
```

Cette séparation permet de tester `motion_handler.py` unitairement sans
avoir besoin d'un broker MQTT ni d'une caméra (aucune dépendance externe
dedans), et de faire évoluer la logique métier (vandalisme, historique,
reconnaissance faciale, facturation Stripe) sans toucher aux couches
réseau ou matériel.

## 6. Ce qu'il faut absolument obtenir de la personne qui gère le C/Mosquitto

- Le fichier `ca.crt`
- Les identifiants du compte `python_client`
- Confirmation que l'ACL Mosquitto autorise bien :
  - lecture sur `lumisafe/lamppost1/#`
  - écriture sur `lumisafe/lamppost1/commands/#`

## 7. Tester sans le matériel C (simulation)

Pour vérifier que ce service fonctionne avant que le capteur PIR soit
branché, on peut simuler un message directement :

```bash
mosquitto_pub -h localhost -p 8883 --cafile /etc/mosquitto/certs/ca.crt \
  -u sensor_client -P <mot_de_passe_sensor> \
  -t "lumisafe/lamppost1/motion" -m "detected"
```

Le service Python doit alors afficher la réaction métier immédiatement.

## 8. Caméra (picamera2)

`camera_controller.py` déclenche une capture photo à chaque transition
"mouvement détecté" (pas à chaque message — le C ne publie déjà que sur
changement d'état, donc pas de spam de photos si le mouvement reste actif).

- Sur le Raspberry Pi avec le module CSI branché :
  ```bash
  sudo apt install -y python3-picamera2
  ```
  Le service détecte `picamera2` automatiquement et utilise
  `Picamera2CameraController` (vraies photos, dossier `CAMERA_OUTPUT_DIR`).

- Sur toute autre machine (dev sans matériel, ex: ton Mac) : `picamera2`
  n'est pas installable, le service bascule automatiquement sur
  `NullCameraController` qui logge simplement ce qui se serait passé.
  Rien à configurer, aucun crash à l'import.

- `CAMERA_COOLDOWN_SECONDS` (5s par défaut) évite de spammer le disque si
  le PIR flickers (détection/effacement très rapides).

**TODO restant côté domaine** (`motion_handler.py`) : logique de
vandalisme (seuil décibel micro + accéléromètre), historique des
événements, et transmission au serveur/dashboard de Guillaume et
François.

## 9. Lancer le service automatiquement au démarrage

Crée `/etc/systemd/system/lumisafe-python.service` :

```ini
[Unit]
Description=LumiSafe Python business logic service
After=network.target mosquitto.service lumisafe-pir.service

[Service]
ExecStart=/home/pi/lumisafe_python/venv/bin/python3 /home/pi/lumisafe_python/main.py
Restart=on-failure
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now lumisafe-python
```

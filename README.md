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

Par défaut, l'historique SQLite (`DB_PATH`) est stocké dans un fichier
`lumisafe.db` à la racine du repo (ignoré par git) — ça marche sans rien
configurer sur ta machine de dev. Sur le Pi en prod, ajoute dans `.env` :

```bash
LUMISAFE_DB_PATH=/home/pi/lumisafe/history.db
```

pour sortir la base du repo, comme les captures caméra.

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
├── main.py                    # Point d'entrée du service MQTT, relie infra <-> domaine
├── requirements.txt
├── CONTRACT_CAPTEURS.md        # Contrat MQTT micro/accéléromètre, à valider avec Cédric
├── lumisafe/
│   ├── config.py               # Paramètres centralisés (miroir de config.h)
│   ├── mqtt_client.py          # Couche infra : tout paho-mqtt vit ici
│   ├── camera_controller.py    # Couche infra : tout picamera2 vit ici
│   ├── motion_handler.py       # Couche domaine : logique métier PIR/lumière
│   ├── vandalism_handler.py    # Couche domaine : logique métier son/choc
│   └── event_store.py          # Couche infra : historique SQLite (motion/vandalisme)
└── api/                         # API REST — process indépendant, voir section 10
    ├── main.py                  # App FastAPI + endpoints
    ├── auth.py                  # Vérification de la clé API
    └── schemas.py                # Structure des réponses JSON
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

Même chose pour le son et la vibration, avant que le micro/accéléromètre
soient branchés côté C — voir `CONTRACT_CAPTEURS.md` pour le détail et
les commandes `mosquitto_pub` de simulation.

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

Chaque décision motion/vandalisme est historisée dans SQLite
(`lumisafe/event_store.py`) et exposée à l'API REST — voir section 9.
La logique de vandalisme (seuil décibel + accéléromètre) est dans
`vandalism_handler.py` — voir `CONTRACT_CAPTEURS.md` pour ce qu'il reste
à valider avec Cédric côté C.

## 9. API REST pour le dashboard (François)

Le service MQTT (`main.py`) écrit chaque événement dans une base SQLite
locale. L'API REST (`api/`) est un **process séparé** qui lit cette base
et l'expose en HTTP — elle ne touche jamais à MQTT ni à la caméra.
Elle peut tourner sur le Pi à côté de `main.py`, ou ailleurs si elle a
accès au fichier `history.db`.

Pour tester l'API seule sans Mosquitto ni matériel (contrairement à
`main.py`, qui a besoin du broker pour démarrer) : lance juste `uvicorn`
ci-dessous, la base se crée toute seule au premier accès, même vide.

### Lancer l'API

```bash
# Génère une clé si ce n'est pas déjà fait :
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

export LUMISAFE_API_KEY="<la clé générée>"
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Doc interactive (Swagger) : `http://<ip-du-pi>:8000/docs`
Doc alternative (ReDoc) : `http://<ip-du-pi>:8000/redoc`

### Donner l'accès à François

Il n'a besoin que de deux choses : l'URL de base (`http://<ip-du-pi>:8000`)
et la clé API, à passer dans le header `X-API-Key` sur chaque requête.
Transmets la clé par un canal séparé du code (pas dans un message Slack
public, pas commitée) — c'est un secret au même titre que le mot de
passe MQTT.

```bash
curl -H "X-API-Key: <la clé>" http://<ip-du-pi>:8000/status
```

### Endpoints

| Méthode | Route | Auth | Description |
|---|---|---|---|
| GET | `/health` | non | Vérifie que l'API répond |
| GET | `/status` | oui | État courant : lumière allumée, alerte active, derniers horodatages |
| GET | `/events` | oui | Liste des événements récents (`?event_type=motion\|vandalism&limit=50`) |
| GET | `/events/latest` | oui | Dernier événement, tous types confondus |

Structure de réponse d'un événement (`EventOut`, voir `api/schemas.py`) :

```json
{
  "id": 42,
  "created_at": "2026-07-27T14:32:10.123456+00:00",
  "lamppost_id": "lamppost1",
  "event_type": "vandalism",
  "detail": "son 72.4dB",
  "light_on": null,
  "alert_active": true,
  "photo_path": "/home/pi/lumisafe/captures/20260727_143210_vandalism_sound.jpg"
}
```

`light_on` n'est renseigné que pour les events `motion`, `alert_active`
et `detail` que pour les events `vandalism` — l'autre vaut `null`.

### Ce qui reste à décider avant la mise en prod

- CORS est ouvert (`*`) pour le développement — à restreindre à l'origine
  réelle du dashboard de François dans `api/main.py` dès qu'elle est connue.
- Une seule clé API pour l'instant (un seul consommateur). Si un deuxième
  dashboard ou une appli mobile doit y accéder avec des permissions
  différentes, voir la note dans `api/auth.py` avant de dupliquer la logique.
- `photo_path` renvoie un chemin serveur, pas une URL téléchargeable —
  s'il faut que François affiche les photos dans son dashboard, il
  faudra soit exposer un endpoint `/photos/{filename}` qui sert le
  fichier, soit passer par un stockage objet (S3-like) avec URLs signées.

## 10. Lancer le service automatiquement au démarrage

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

Même chose pour l'API, dans un service séparé (elle peut redémarrer,
tomber, ou être mise à jour indépendamment du service MQTT) —
`/etc/systemd/system/lumisafe-api.service` :

```ini
[Unit]
Description=LumiSafe REST API (dashboard François/Guillaume)
After=network.target

[Service]
Environment=LUMISAFE_API_KEY=<la clé générée en section 9>
ExecStart=/home/pi/lumisafe_python/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
WorkingDirectory=/home/pi/lumisafe_python
Restart=on-failure
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now lumisafe-api
```

Préfère un fichier d'environnement (`EnvironmentFile=/home/pi/lumisafe_python/.env`
dans le `[Service]`) plutôt que la clé en clair dans l'unit file si
plusieurs personnes ont accès au Pi.

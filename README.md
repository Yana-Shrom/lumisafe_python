# LumiSafe — Service Python (logique métier)

Ce service s'abonne au broker MQTT Mosquitto, reçoit les événements de
mouvement publiés par le module C (capteur PIR), applique la logique
métier, et republie une commande d'allumage/extinction. Il ne connaît
rien du GPIO ni du C — uniquement des messages MQTT.

## 1. Prérequis

- Python 3.9+
- Le broker Mosquitto déjà configuré et sécurisé (voir le README du
  module C `lumisafe_pir`, section "Sécurisation du broker Mosquitto")
- Le compte `python_client` déjà créé côté Mosquitto (`mosquitto_passwd`)
- Une copie du certificat `ca.crt` accessible en lecture depuis ce service

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

Édite `lumisafe/config.py` :

- `MQTT_PASSWORD` : le mot de passe du compte `python_client` créé côté
  Mosquitto (doit être identique)
- `MQTT_CA_CERT` : le chemin vers `ca.crt` (copie-le depuis le Pi si ce
  service tourne ailleurs, sinon laisse le chemin par défaut)
- `LAMPPOST_ID` : doit correspondre à celui utilisé côté C

**Ne commite jamais `config.py` avec le vrai mot de passe dans Git** —
utilise plutôt une variable d'environnement ou un fichier `.env` ignoré
par `.gitignore` en production.

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
```

## 5. Structure du projet

```
lumisafe_python/
├── main.py                    # Point d'entrée, relie infra <-> domaine
├── requirements.txt
├── lumisafe/
│   ├── config.py              # Paramètres centralisés (miroir de config.h)
│   ├── mqtt_client.py         # Couche infra : tout paho-mqtt vit ici
│   └── motion_handler.py      # Couche domaine : logique métier pure
```

Cette séparation permet de tester `motion_handler.py` unitairement sans
avoir besoin d'un broker MQTT (aucune dépendance à paho dedans), et de
faire évoluer la logique métier (vandalisme, reconnaissance faciale,
facturation Stripe) sans toucher à la couche réseau.

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

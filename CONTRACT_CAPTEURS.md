# Contrat MQTT — capteurs vandalisme (micro + accéléromètre)

Statut : **proposition côté Python, en attente de validation par Cédric**
avant qu'il implémente la lecture matérielle côté C (comme pour le PIR,
voir `lumisafe_pir/README.md`).

## Principe

Le capteur (C) ne décide de rien : il lit la valeur brute et la publie.
Le seuillage (à partir de quand c'est "suspect") vit côté Python, pour
pouvoir ajuster la sensibilité sans recompiler/redéployer sur le Pi.

C'est différent du PIR, où le C fait déjà le passage binaire
detected/clear — ici on garde les valeurs analogiques brutes.

## Topics à publier côté C

| Topic | Payload | Fréquence suggérée |
|---|---|---|
| `lumisafe/lamppost1/sound` | nombre en texte, niveau en dB (ex: `"72.4"`) | ~2-5 Hz, pas plus (évite de saturer le broker) |
| `lumisafe/lamppost1/vibration` | nombre en texte, accélération en g (ex: `"1.8"`) | idem |

Pas de JSON, pas de préfixe — juste le nombre en texte brut, comme le
`"detected"`/`"clear"` du topic motion. Ça évite d'ajouter une dépendance
JSON côté C pour deux valeurs.

## Ce que le Python fait de ces valeurs

- `SOUND_THRESHOLD_DB = 70.0` et `VIBRATION_THRESHOLD_G = 1.5` dans
  `lumisafe/config.py` (valeurs de départ à affiner une fois le matériel
  branché et calibré avec Cédric)
- Franchissement du seuil (l'un ou l'autre) → alerte publiée sur
  `lumisafe/lamppost1/commands/alert` (`"on"`/`"off"`) + capture photo
- Cette route MQTT est déjà couverte par l'ACL Mosquitto existante
  (`python_client` a le droit d'écrire sur `commands/#`) — rien à changer
  côté broker

## Testable dès maintenant, sans matériel

```bash
mosquitto_pub -h localhost -p 8883 --cafile /etc/mosquitto/certs/ca.crt \
  -u sensor_client -P <mot_de_passe_sensor> \
  -t "lumisafe/lamppost1/sound" -m "75.0"

mosquitto_pub -h localhost -p 8883 --cafile /etc/mosquitto/certs/ca.crt \
  -u sensor_client -P <mot_de_passe_sensor> \
  -t "lumisafe/lamppost1/vibration" -m "2.1"
```

Le service Python doit réagir immédiatement (log `[domaine] Vandalisme
suspecté...`), sans que Cédric ait branché quoi que ce soit.

## À valider avec Cédric avant qu'il code

- [ ] Le format "nombre brut en texte" plutôt que JSON lui convient
- [ ] Les noms de topics (`sound`, `vibration`)
- [ ] La fréquence de publication (2-5 Hz proposé)
- [ ] Les capteurs réels du kit correspondent bien (micro + accéléromètre
      confirmés dans l'inventaire physique ?)

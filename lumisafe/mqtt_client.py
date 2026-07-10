"""
Couche infrastructure : tout ce qui touche à MQTT/paho vit ici.
Le reste du code (logique métier) ne connaît jamais paho-mqtt directement,
il reçoit juste des événements déjà "traduits".
"""

import ssl
import paho.mqtt.client as mqtt

from . import config


class MqttClient:
    def __init__(self, on_motion_callback):
        """
        on_motion_callback: fonction appelée avec un booléen
        (True = mouvement détecté, False = zone dégagée)
        """
        self._on_motion_callback = on_motion_callback
        self._client = mqtt.Client(client_id=config.MQTT_CLIENT_ID)

        self._client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
        self._client.tls_set(
            ca_certs=config.MQTT_CA_CERT,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )

        self._client.on_connect = self._handle_connect
        self._client.on_message = self._handle_message
        self._client.on_disconnect = self._handle_disconnect

    def connect(self):
        self._client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)

    def loop_forever(self):
        self._client.loop_forever()

    def publish_light_command(self, turn_on: bool):
        payload = "on" if turn_on else "off"
        self._client.publish(config.TOPIC_LIGHT_COMMAND, payload, qos=1)

    def disconnect(self):
        self._client.disconnect()

    # ---------- Callbacks internes paho ----------

    def _handle_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[mqtt] Connecté au broker ({config.MQTT_HOST}:{config.MQTT_PORT})")
            client.subscribe(config.TOPIC_MOTION)
            print(f"[mqtt] Abonné à {config.TOPIC_MOTION}")
        else:
            print(f"[mqtt] Échec de connexion, code={rc}")

    def _handle_disconnect(self, client, userdata, rc):
        print(f"[mqtt] Déconnecté (code={rc})")

    def _handle_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8")
        if msg.topic == config.TOPIC_MOTION:
            motion_detected = (payload == "detected")
            self._on_motion_callback(motion_detected)

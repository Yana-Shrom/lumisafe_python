"""
Point d'entrée du service Python LumiSafe.
Fait le lien entre la couche infra (MQTT) et la couche domaine (logique métier),
sans que les deux ne se connaissent directement.
"""

import signal
import sys

from lumisafe.mqtt_client import MqttClient
from lumisafe.motion_handler import MotionHandler

handler = MotionHandler()
mqtt_client = None  # initialisé dans main()


def on_motion_event(detected: bool):
    """Callback appelé par la couche MQTT à chaque message reçu."""
    should_light_be_on = handler.handle_motion(detected)
    mqtt_client.publish_light_command(should_light_be_on)


def handle_shutdown(sig, frame):
    print("\nArrêt en cours...")
    if mqtt_client:
        mqtt_client.disconnect()
    sys.exit(0)


def main():
    global mqtt_client

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    mqtt_client = MqttClient(on_motion_callback=on_motion_event)
    mqtt_client.connect()

    print("LumiSafe - service Python démarré. Ctrl+C pour arrêter.")
    mqtt_client.loop_forever()


if __name__ == "__main__":
    main()

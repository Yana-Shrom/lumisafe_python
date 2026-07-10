"""
Point d'entrée du service Python LumiSafe.
Fait le lien entre les couches infra (MQTT, caméra) et la couche domaine
(logique métier), sans que ces couches ne se connaissent entre elles.
"""

import signal
import sys

from lumisafe.mqtt_client import MqttClient
from lumisafe.motion_handler import MotionHandler
from lumisafe.camera_controller import build_camera_controller

handler = MotionHandler()
camera = build_camera_controller()
mqtt_client = None  # initialisé dans main()


def on_motion_event(detected: bool):
    """Callback appelé par la couche MQTT à chaque message reçu."""
    decision = handler.handle_motion(detected)
    mqtt_client.publish_light_command(decision.light_on)
    if decision.capture_photo:
        camera.capture_photo(reason="motion_detected")


def handle_shutdown(sig, frame):
    print("\nArrêt en cours...")
    if mqtt_client:
        mqtt_client.disconnect()
    camera.close()
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

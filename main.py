"""
Point d'entrée du service Python LumiSafe.
Fait le lien entre les couches infra (MQTT, caméra) et la couche domaine
(logique métier), sans que ces couches ne se connaissent entre elles.
"""

import signal
import sys

from lumisafe.mqtt_client import MqttClient
from lumisafe.motion_handler import MotionHandler
from lumisafe.vandalism_handler import VandalismHandler
from lumisafe.camera_controller import build_camera_controller
from lumisafe.event_store import EventStore

motion_handler = MotionHandler()
vandalism_handler = VandalismHandler()
camera = build_camera_controller()
event_store = EventStore()  # historise motion/vandalisme, lu par l'API REST (api/)
mqtt_client = None  # initialisé dans main()


def on_motion_event(detected: bool):
    """Callback appelé par la couche MQTT à chaque message PIR."""
    decision = motion_handler.handle_motion(detected)
    mqtt_client.publish_light_command(decision.light_on)
    photo_path = None
    if decision.capture_photo:
        photo_path = camera.capture_photo(reason="motion_detected")
    event_store.record_motion(light_on=decision.light_on, photo_path=photo_path)


def on_sound_event(level_db: float):
    """Callback appelé par la couche MQTT à chaque lecture du micro."""
    decision = vandalism_handler.handle_sound(level_db)
    _apply_vandalism_decision(decision, reason="vandalism_sound", detail=f"son {level_db:.1f}dB")


def on_vibration_event(level_g: float):
    """Callback appelé par la couche MQTT à chaque lecture de l'accéléromètre."""
    decision = vandalism_handler.handle_vibration(level_g)
    _apply_vandalism_decision(decision, reason="vandalism_vibration", detail=f"choc {level_g:.1f}g")


def _apply_vandalism_decision(decision, reason: str, detail: str):
    mqtt_client.publish_alert_command(decision.alert_active)
    photo_path = None
    if decision.capture_photo:
        photo_path = camera.capture_photo(reason=reason)
    event_store.record_vandalism(alert_active=decision.alert_active, detail=detail, photo_path=photo_path)


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

    mqtt_client = MqttClient(
        on_motion_callback=on_motion_event,
        on_sound_callback=on_sound_event,
        on_vibration_callback=on_vibration_event,
    )
    mqtt_client.connect()

    print("LumiSafe - service Python démarré. Ctrl+C pour arrêter.")
    mqtt_client.loop_forever()


if __name__ == "__main__":
    main()

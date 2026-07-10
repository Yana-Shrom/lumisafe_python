"""
Couche infrastructure : contrôle de la caméra CSI (picamera2).
Le domaine (motion_handler.py) ne sait pas COMMENT une photo est prise,
il décide juste QU'il en faut une (même esprit que mqtt_client.py).

Deux implémentations :
- Picamera2CameraController : la vraie, utilisée sur le Raspberry Pi avec
  le module caméra CSI branché.
- NullCameraController : factice, utilisée en dev sur un Mac/PC sans
  matériel — log ce qui se serait passé, ne plante jamais à l'import.

build_camera_controller() choisit automatiquement la bonne selon que
picamera2 est installable ou non (il ne l'est que sur un Pi avec
libcamera, cf. README).
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import config

try:
    from picamera2 import Picamera2
    _PICAMERA_AVAILABLE = True
except ImportError:
    _PICAMERA_AVAILABLE = False


class CameraController:
    """Interface attendue par main.py."""

    def capture_photo(self, reason: str) -> Optional[Path]:
        raise NotImplementedError

    def close(self) -> None:
        pass


class Picamera2CameraController(CameraController):
    """Implémentation réelle (Raspberry Pi + module caméra CSI)."""

    def __init__(self):
        if not _PICAMERA_AVAILABLE:
            raise RuntimeError(
                "picamera2 n'est pas installé sur cette machine — utilise "
                "build_camera_controller() pour retomber automatiquement "
                "sur NullCameraController en dev."
            )
        self._camera = Picamera2()
        still_config = self._camera.create_still_configuration(
            main={"size": config.CAMERA_RESOLUTION}
        )
        self._camera.configure(still_config)
        self._camera.start()
        time.sleep(2)  # temps de chauffe du capteur, évite les photos sous-exposées

        self._last_capture_monotonic = 0.0
        Path(config.CAMERA_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    def capture_photo(self, reason: str) -> Optional[Path]:
        now = time.monotonic()
        if now - self._last_capture_monotonic < config.CAMERA_COOLDOWN_SECONDS:
            print(f"[camera] Capture ignorée (cooldown), reason={reason}")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path(config.CAMERA_OUTPUT_DIR) / f"{timestamp}_{reason}.jpg"
        self._camera.capture_file(str(filename))
        self._last_capture_monotonic = now
        print(f"[camera] Photo capturée -> {filename}")
        return filename

    def close(self) -> None:
        self._camera.stop()


class NullCameraController(CameraController):
    """Implémentation factice — développer/tester sans Raspberry Pi ni caméra."""

    def capture_photo(self, reason: str) -> Optional[Path]:
        print(f"[camera] (simulation, picamera2 absent) photo qui aurait été prise, reason={reason}")
        return None


def build_camera_controller() -> CameraController:
    """Choisit l'implémentation selon la disponibilité du matériel."""
    if _PICAMERA_AVAILABLE:
        return Picamera2CameraController()
    print("[camera] picamera2 introuvable -> mode simulation (NullCameraController)")
    return NullCameraController()

"""
Couche domaine (logique métier), indépendante de MQTT ET du matériel.
Décide si le niveau sonore (micro) ou le choc (accéléromètre) dépasse un
seuil suspect de vandalisme. Les deux capteurs sont lus indépendamment
côté infra, combinés ici en une seule décision (OR : l'un ou l'autre
suffit à déclencher une alerte).

Ce module ne sait même pas que MQTT ou picamera2 existent — il ne fait
que décider, jamais agir (main.py fait le lien avec l'infra).
"""

from dataclasses import dataclass

from . import config


@dataclass(frozen=True)
class VandalismDecision:
    """Ce que le domaine décide, à charge pour main.py de l'exécuter."""

    alert_active: bool
    capture_photo: bool


class VandalismHandler:
    def __init__(self):
        self._sound_above_threshold = False
        self._vibration_above_threshold = False
        self._alert_is_active = False

    def handle_sound(self, level_db: float) -> VandalismDecision:
        self._sound_above_threshold = level_db >= config.SOUND_THRESHOLD_DB
        return self._evaluate(reason=f"son {level_db:.1f}dB")

    def handle_vibration(self, level_g: float) -> VandalismDecision:
        self._vibration_above_threshold = level_g >= config.VIBRATION_THRESHOLD_G
        return self._evaluate(reason=f"choc {level_g:.1f}g")

    def _evaluate(self, reason: str) -> VandalismDecision:
        should_alert = self._sound_above_threshold or self._vibration_above_threshold

        if should_alert and not self._alert_is_active:
            print(f"[domaine] Vandalisme suspecté ({reason}) -> alerte + capture")
            self._alert_is_active = True
            # TODO: historique/horodatage des alertes, remontée dashboard (François/Guillaume)
            return VandalismDecision(alert_active=True, capture_photo=True)

        if not should_alert and self._alert_is_active:
            print("[domaine] Retour sous les seuils -> fin d'alerte")
            self._alert_is_active = False
            return VandalismDecision(alert_active=False, capture_photo=False)

        return VandalismDecision(alert_active=self._alert_is_active, capture_photo=False)

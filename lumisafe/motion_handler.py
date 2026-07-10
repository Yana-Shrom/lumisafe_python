"""
Couche domaine (logique métier), indépendante de MQTT ET de la caméra.
C'est ici que vivra la vraie logique LumiSafe : activation caméra,
détection de vandalisme, plus tard reconnaissance faciale + Stripe, etc.
Ce module ne sait même pas que MQTT ou picamera2 existent — il ne fait
que décider, jamais agir (main.py fait le lien avec l'infra).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MotionDecision:
    """Ce que le domaine décide, à charge pour main.py de l'exécuter."""

    light_on: bool
    capture_photo: bool


class MotionHandler:
    def __init__(self):
        self._light_is_on = False

    def handle_motion(self, detected: bool) -> MotionDecision:
        """
        Reçoit l'état brut du capteur (True = mouvement, False = zone
        dégagée) et retourne la décision métier correspondante.
        """
        if detected and not self._light_is_on:
            print("[domaine] Mouvement détecté -> activation lampadaire + caméra")
            self._light_is_on = True
            # TODO: logique de vandalisme (seuil décibel + accéléromètre), historique, etc.
            return MotionDecision(light_on=True, capture_photo=True)

        if not detected and self._light_is_on:
            print("[domaine] Zone dégagée -> extinction lampadaire")
            self._light_is_on = False
            return MotionDecision(light_on=False, capture_photo=False)

        # Pas de changement d'état pertinent
        return MotionDecision(light_on=self._light_is_on, capture_photo=False)

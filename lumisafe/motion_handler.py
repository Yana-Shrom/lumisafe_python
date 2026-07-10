"""
Couche domaine (logique métier), indépendante de MQTT.
C'est ici que vivra la vraie logique LumiSafe : activation caméra,
détection de vandalisme, plus tard reconnaissance faciale + Stripe, etc.
Ce module ne sait même pas que MQTT existe.
"""


class MotionHandler:
    def __init__(self):
        self._light_is_on = False

    def handle_motion(self, detected: bool) -> bool:
        """
        Reçoit l'état brut du capteur, décide de l'action métier,
        retourne True si la lumière doit être allumée, False sinon.
        """
        if detected and not self._light_is_on:
            print("[domaine] Mouvement détecté -> activation lampadaire + caméra")
            self._light_is_on = True
            # TODO: déclencher l'activation caméra ici
            # TODO: logique de vandalisme, historique, etc.
            return True

        if not detected and self._light_is_on:
            print("[domaine] Zone dégagée -> extinction lampadaire")
            self._light_is_on = False
            return False

        # Pas de changement d'état pertinent
        return self._light_is_on

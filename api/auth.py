"""
Authentification de l'API REST par clé statique.

Choix volontaire plutôt qu'un vrai système de comptes (login/JWT/OAuth) :
il n'y a qu'un seul consommateur connu à ce stade (le dashboard de
François), pas plusieurs utilisateurs avec des permissions différentes.
Une clé API dans le header `X-API-Key` suffit et évite de construire une
couche d'auth surdimensionnée pour ce besoin.

Si un jour plusieurs dashboards/consommateurs distincts doivent accéder
à l'API avec des permissions différentes, migrer vers plusieurs clés
nommées (table `api_keys` dans event_store.py) plutôt que de tout
réécrire la dépendance `verify_api_key` reste le seul point à changer,
les endpoints ne bougent pas.
"""

import secrets

from fastapi import Header, HTTPException, status

from lumisafe import config


async def verify_api_key(
    x_api_key: str = Header(..., description="Clé API fournie par Thélia (voir README)")
) -> None:
    if config.API_KEY == "CHANGE_ME_CLE_API":
        # La clé placeholder ne doit jamais servir à protéger un vrai déploiement :
        # on préfère planter bruyamment (500) plutôt qu'exposer l'API sans clé.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LUMISAFE_API_KEY n'est pas configurée côté serveur.",
        )
    if not secrets.compare_digest(x_api_key, config.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API invalide.",
        )

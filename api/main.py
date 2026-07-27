"""
API REST LumiSafe historique des événements (motion, vandalisme) pour
le dashboard de François et Guillaume.

Process indépendant du service MQTT (main.py à la racine) : lit la même
base SQLite (lumisafe/event_store.py) mais n'écrit jamais et ne publie
aucune commande MQTT. Peut tourner sur une autre machine que le Pi tant
qu'il a accès au fichier history.db (à terme : base partagée réseau si
plusieurs lampadaires).

Lancer en local :
    uvicorn api.main:app --reload --port 8000

Doc interactive (Swagger) : http://localhost:8000/docs
Doc alternative (ReDoc)    : http://localhost:8000/redoc
"""

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from lumisafe.event_store import EventStore

from .auth import verify_api_key
from .schemas import ErrorResponse, EventListResponse, EventOut, StatusResponse

app = FastAPI(
    title="LumiSafe API",
    description=(
        "Historique des événements du lampadaire connecté LumiSafe "
        "(détection de mouvement, vandalisme, captures photo associées). "
        "Toutes les routes sauf `/health` demandent une clé API dans le "
        "header `X-API-Key`."
    ),
    version="1.0.0",
    contact={"name": "Thélia Beauzor"},
)

# CORS ouvert pour le développement. À restreindre à l'origine réelle du
# dashboard de François dès qu'elle est connue — ne jamais garder "*" en prod.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["X-API-Key"],
)

_store = EventStore()


@app.get("/health", tags=["Santé"], summary="Vérifie que l'API répond")
def health() -> dict:
    return {"status": "ok"}


@app.get(
    "/status",
    response_model=StatusResponse,
    responses={401: {"model": ErrorResponse}},
    dependencies=[Depends(verify_api_key)],
    tags=["Lampadaire"],
    summary="État courant du lampadaire (lumière allumée, alerte active)",
)
def get_status() -> StatusResponse:
    return StatusResponse(**_store.get_status())


@app.get(
    "/events",
    response_model=EventListResponse,
    responses={401: {"model": ErrorResponse}},
    dependencies=[Depends(verify_api_key)],
    tags=["Événements"],
    summary="Liste les événements récents, du plus récent au plus ancien",
)
def list_events(
    event_type: Optional[str] = Query(
        None,
        pattern="^(motion|vandalism)$",
        description="Filtre optionnel : 'motion' ou 'vandalism'",
    ),
    limit: int = Query(50, ge=1, le=500, description="Nombre max d'événements renvoyés (1-500)"),
) -> EventListResponse:
    events = _store.list_events(event_type=event_type, limit=limit)
    return EventListResponse(count=len(events), events=[EventOut(**e.__dict__) for e in events])


@app.get(
    "/events/latest",
    response_model=EventOut,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    dependencies=[Depends(verify_api_key)],
    tags=["Événements"],
    summary="Dernier événement enregistré, tous types confondus",
)
def latest_event() -> EventOut:
    events = _store.list_events(limit=1)
    if not events:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun événement enregistré.")
    return EventOut(**events[0].__dict__)

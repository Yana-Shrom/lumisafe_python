"""
Structure de réponse de l'API LumiSafe.

Convention : un objet métier direct pour les endpoints qui renvoient un
seul élément (StatusResponse, EventOut), une enveloppe {count, events}
pour les listes — ça laisse de la place pour ajouter pagination/metadata
plus tard sans casser le contrat existant.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class EventOut(BaseModel):
    id: int
    created_at: str = Field(..., description="Horodatage ISO 8601 UTC")
    lamppost_id: str
    event_type: str = Field(..., description="'motion' ou 'vandalism'")
    detail: Optional[str] = Field(None, description="Détail lisible, ex: 'son 72.4dB'")
    light_on: Optional[bool] = Field(None, description="Applicable seulement aux events 'motion'")
    alert_active: Optional[bool] = Field(None, description="Applicable seulement aux events 'vandalism'")
    photo_path: Optional[str] = Field(None, description="Chemin de la capture associée, si prise")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 42,
                "created_at": "2026-07-27T14:32:10.123456+00:00",
                "lamppost_id": "lamppost1",
                "event_type": "vandalism",
                "detail": "son 72.4dB",
                "light_on": None,
                "alert_active": True,
                "photo_path": "/home/pi/lumisafe/captures/20260727_143210_vandalism_sound.jpg",
            }
        }
    }


class EventListResponse(BaseModel):
    count: int
    events: List[EventOut]


class StatusResponse(BaseModel):
    lamppost_id: str
    light_on: bool
    alert_active: bool
    last_motion_at: Optional[str] = None
    last_vandalism_at: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str

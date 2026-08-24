from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Incident, User
from app.schemas.incident import IncidentIn, IncidentOut

router = APIRouter(tags=["incidents"])


@router.post("/incidents", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def create_incident(body: IncidentIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    incident = Incident(**body.model_dump(), user_id=user.id)
    db.add(incident); db.commit(); db.refresh(incident)
    return incident


@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(session_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Incident).order_by(Incident.id.desc())
    if session_id is not None:
        stmt = stmt.where(Incident.session_id == session_id)
    return list(db.scalars(stmt).all())

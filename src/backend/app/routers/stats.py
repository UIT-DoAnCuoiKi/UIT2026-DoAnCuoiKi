import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import User
from app.services import stats as stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return stats_service.summary(db, from_, to)


@router.get("/export")
def export_stats(
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
) -> Response:
    rows = stats_service.daily_rows(db, from_, to)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "entries", "exits", "revenue"])
    for r in rows:
        writer.writerow([r["date"], r["entries"], r["exits"], r["revenue"]])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stats.csv"},
    )

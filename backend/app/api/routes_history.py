"""GET /history -- last 50 chat analyses."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import AnalysisRecord
from app.models.schemas import HistoryItem, HistoryResponse

router = APIRouter()


@router.get("/history", response_model=HistoryResponse)
async def history(db: Session = Depends(get_db)) -> HistoryResponse:
    stmt = (
        select(AnalysisRecord)
        .where(AnalysisRecord.kind == "chat")
        .order_by(AnalysisRecord.id.desc())
        .limit(50)
    )
    rows = db.execute(stmt).scalars().all()

    items: list[HistoryItem] = []
    for row in rows:
        global_state = {}
        try:
            cognitive_state = json.loads(row.cognitive_state_json)
            global_state = cognitive_state.get("global_state", {})
        except (json.JSONDecodeError, AttributeError):
            global_state = {}

        items.append(
            HistoryItem(
                id=row.id,
                timestamp=row.timestamp,
                query=row.query,
                model=row.model,
                pathway=row.pathway,
                uncertainty=global_state.get("uncertainty", 0),
                confidence=global_state.get("confidence", 0),
                difficulty=global_state.get("difficulty", 0),
                verification_need=global_state.get("verification_need", 0),
                hallucination_risk=row.hallucination_risk,
            )
        )

    return HistoryResponse(items=items)

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
import psycopg
from psycopg.types.json import Jsonb

from backend.application.services.pmv1_services import PlatformService
from backend.infrastructure.config.dependencies import get_platform_service, require_legal_or_planner, require_planner
from backend.infrastructure.output.ml_mef.predictor import load_model, predict

router = APIRouter(prefix="/api/v1/ml", tags=["Predicción ML"])


class PredictionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_version_id: UUID
    function: str = Field(min_length=1, max_length=120)
    department: str = Field(min_length=1, max_length=60)
    execution_mode: str = Field(min_length=1, max_length=500)
    investment_type: str = Field(min_length=1, max_length=100)
    planned_days: int | None = Field(default=None, ge=1, le=3650)


@router.get("/model")
def model_metadata(_: Annotated[dict, Depends(require_legal_or_planner)]) -> dict:
    return load_model()["metadata"]


@router.post("/projects/{project_id}/predict")
def predict_project(project_id: UUID, payload: PredictionInput,
                    user: Annotated[dict, Depends(require_planner)],
                    platform: Annotated[PlatformService, Depends(get_platform_service)]) -> dict:
    project = platform.get_project(project_id)
    if str(project["project_version_id"]) != str(payload.project_version_id):
        raise HTTPException(409, "El expediente cambió de versión. Consúltelo de nuevo antes de predecir.")
    categories = {"FUNCION": payload.function, "DEPARTAMENTO": payload.department,
                  "DES_MODALIDAD": payload.execution_mode, "TIPO_INVERSION": payload.investment_type}
    try:
        result = predict(float(project["estimated_budget_pen"]), categories, payload.planned_days)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    result.update({"prediction_id": str(uuid4()), "project_id": str(project_id),
                   "project_version_id": str(payload.project_version_id), "project_code": project["code"],
                   "created_at": datetime.now(timezone.utc).isoformat()})
    with psycopg.connect(platform.db_url) as conn, conn.transaction():
        # Recheck the version and retain its exact identifier in the immutable snapshot.
        conn.execute("SELECT id FROM projects WHERE id=%s FOR UPDATE", (project_id,))
        latest = conn.execute("SELECT id FROM project_versions WHERE project_id=%s ORDER BY version_number DESC LIMIT 1", (project_id,)).fetchone()
        if latest is None or str(latest[0]) != str(payload.project_version_id):
            raise HTTPException(409, "El expediente cambió mientras se calculaba la predicción.")
        conn.execute("""INSERT INTO audit_events (actor_user_id, action, entity_type, entity_id, details)
                        VALUES (%s, 'ML_PREDICTION_CREATED', 'project', %s, %s)""",
                     (UUID(user["sub"]), project_id, Jsonb(result)))
    return result


@router.get("/projects/{project_id}/latest")
def latest_prediction(project_id: UUID,
                      _: Annotated[dict, Depends(require_legal_or_planner)],
                      platform: Annotated[PlatformService, Depends(get_platform_service)]) -> dict | None:
    project = platform.get_project(project_id)
    with psycopg.connect(platform.db_url) as conn:
        row = conn.execute("""SELECT details FROM audit_events WHERE entity_id=%s
            AND entity_type='project' AND action='ML_PREDICTION_CREATED'
            AND details->>'project_version_id'=%s ORDER BY occurred_at DESC LIMIT 1""",
            (project_id, str(project["project_version_id"]))).fetchone()
    return row[0] if row else None

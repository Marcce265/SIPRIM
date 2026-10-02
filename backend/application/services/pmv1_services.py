from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Protocol
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import jwt
import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend.application.dto.pmv1_dto import PMV1ProjectCreate
from backend.domain.exceptions.pmv1_exceptions import (
    ConfiguracionPMV1Error,
    CredencialesInvalidasError,
    ExpedientePMV1IncompletoError,
    RecursoPMV1NoEncontradoError,
)


def _dsn(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


class TaskDispatcher(Protocol):
    def dispatch_economic(self, payload: dict[str, Any]) -> None: ...


class AuthService:
    def __init__(
        self,
        db_url: str,
        jwt_secret: str,
        issuer: str,
        audience: str,
        expiration_minutes: int,
    ) -> None:
        self.db_url = _dsn(db_url)
        self.jwt_secret = jwt_secret
        self.issuer = issuer
        self.audience = audience
        self.expiration_minutes = expiration_minutes
        self.password_hasher = PasswordHasher()

    def login(self, email: str, password: str) -> dict[str, Any]:
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            row = conn.execute(
                """
                SELECT u.id, u.full_name, u.password_hash, u.is_active,
                       COALESCE(array_agg(r.code) FILTER (WHERE r.code IS NOT NULL), '{}') AS roles
                FROM users u
                LEFT JOIN user_roles ur ON ur.user_id = u.id
                LEFT JOIN roles r ON r.id = ur.role_id
                WHERE u.email = %s
                GROUP BY u.id
                """,
                (email.strip().lower(),),
            ).fetchone()
        if not row or not row["is_active"]:
            raise CredencialesInvalidasError("Credenciales invalidas")
        try:
            self.password_hasher.verify(row["password_hash"], password)
        except (VerifyMismatchError, InvalidHashError):
            raise CredencialesInvalidasError("Credenciales invalidas") from None

        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=self.expiration_minutes)
        claims = {
            "sub": str(row["id"]),
            "roles": list(row["roles"]),
            "iss": self.issuer,
            "aud": self.audience,
            "iat": now,
            "exp": expires,
        }
        token = jwt.encode(claims, self.jwt_secret, algorithm="HS256")
        return {
            "access_token": token,
            "expires_in": self.expiration_minutes * 60,
            "user_id": row["id"],
            "full_name": row["full_name"],
            "roles": list(row["roles"]),
        }

    def decode(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"],
                issuer=self.issuer,
                audience=self.audience,
            )
        except jwt.PyJWTError as exc:
            raise CredencialesInvalidasError("Token invalido o expirado") from exc


class PlatformService:
    def __init__(self, db_url: str, dispatcher: TaskDispatcher) -> None:
        self.db_url = _dsn(db_url)
        self.dispatcher = dispatcher

    @staticmethod
    def _missing(data: PMV1ProjectCreate) -> list[str]:
        values = {
            "title": data.title,
            "description": data.description,
            "estimated_budget_pen": data.estimated_budget_pen,
            "beneficiaries_count": data.beneficiaries_count,
        }
        missing = [name for name, value in values.items() if value is None]
        if data.estimated_budget_pen is not None and data.estimated_budget_pen <= 0:
            missing.append("estimated_budget_pen (> 0)")
        if data.beneficiaries_count is not None and data.beneficiaries_count <= 0:
            missing.append("beneficiaries_count (> 0)")
        return missing

    def create_project(self, data: PMV1ProjectCreate, actor_id: UUID) -> dict[str, Any]:
        missing = self._missing(data)
        if missing:
            raise ExpedientePMV1IncompletoError(missing)
        project_id, version_id = uuid4(), uuid4()
        code = data.code or f"PRY-{project_id.hex[:8].upper()}"
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            with conn.transaction():
                conn.execute(
                    "INSERT INTO projects (id, code, created_by_user_id, status) VALUES (%s,%s,%s,'ready')",
                    (project_id, code, actor_id),
                )
                conn.execute(
                    """
                    INSERT INTO project_versions
                    (id, project_id, version_number, title, description,
                     estimated_budget_pen, beneficiaries_count, created_by_user_id)
                    VALUES (%s,%s,1,%s,%s,%s,%s,%s)
                    """,
                    (
                        version_id,
                        project_id,
                        data.title,
                        data.description,
                        data.estimated_budget_pen,
                        data.beneficiaries_count,
                        actor_id,
                    ),
                )
                conn.execute(
                    """INSERT INTO audit_events
                    (actor_user_id, action, entity_type, entity_id, details)
                    VALUES (%s,'PROJECT_CREATED','project',%s,%s)""",
                    (actor_id, project_id, Jsonb({"project_version_id": str(version_id)})),
                )
        return self.get_project(project_id)

    def get_project(self, project_id: UUID) -> dict[str, Any]:
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            row = conn.execute(
                """
                SELECT p.id AS project_id, pv.id AS project_version_id, p.code,
                       pv.version_number, p.status, pv.title, pv.description,
                       pv.estimated_budget_pen, pv.beneficiaries_count
                FROM projects p JOIN project_versions pv ON pv.project_id = p.id
                WHERE p.id=%s ORDER BY pv.version_number DESC LIMIT 1
                """,
                (project_id,),
            ).fetchone()
        if not row:
            raise RecursoPMV1NoEncontradoError("Proyecto no encontrado")
        return dict(row)

    def validate_project(self, project_id: UUID) -> dict[str, Any]:
        project = self.get_project(project_id)
        missing = [
            field
            for field in ("title", "description", "estimated_budget_pen", "beneficiaries_count")
            if project.get(field) in (None, "")
        ]
        complete = not missing
        return {
            "complete": complete,
            "status": "ready" if complete else "incomplete",
            "missing_fields": missing,
            "message": "Expediente completo" if complete else "Complete los datos antes de evaluar",
        }

    def request_evaluation(
        self, project_version_id: UUID, actor_id: UUID, idempotency_key: str
    ) -> dict[str, Any]:
        if not idempotency_key.strip():
            raise ConfiguracionPMV1Error("Idempotency-Key es obligatorio")
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            with conn.transaction():
                previous = conn.execute(
                    """SELECT e.id AS evaluation_id, e.status, o.id AS event_id, o.payload,
                              o.published_at IS NULL AS publication_pending
                       FROM evaluations e JOIN outbox_events o ON o.aggregate_id=e.id
                       WHERE e.idempotency_key=%s""",
                    (idempotency_key,),
                ).fetchone()
                if previous:
                    previous = dict(previous)
                    previous["duplicated"] = True
                    return previous

                snapshot = conn.execute(
                    """
                    SELECT pv.id AS project_version_id, pv.project_id, pv.estimated_budget_pen,
                           pv.beneficiaries_count, cv.id AS criteria_version_id,
                           cv.version_number AS criteria_version_number,
                           cv.excellent_cost_pen, cv.unacceptable_cost_pen
                    FROM project_versions pv CROSS JOIN criteria_versions cv
                    WHERE pv.id=%s AND cv.status='active'
                    """,
                    (project_version_id,),
                ).fetchone()
                if not snapshot:
                    raise RecursoPMV1NoEncontradoError(
                        "Version de proyecto o criterios activos no encontrados"
                    )
                evaluation_id, event_id = uuid4(), uuid4()
                payload = {
                    "event_id": str(event_id),
                    "event_type": "EconomicEvaluationRequested",
                    "evaluation_id": str(evaluation_id),
                    "project_version_id": str(snapshot["project_version_id"]),
                    "criteria_version_id": str(snapshot["criteria_version_id"]),
                    "budget_pen": str(snapshot["estimated_budget_pen"]),
                    "beneficiaries_count": snapshot["beneficiaries_count"],
                    "excellent_cost_pen": str(snapshot["excellent_cost_pen"]),
                    "unacceptable_cost_pen": str(snapshot["unacceptable_cost_pen"]),
                    "criteria_version_number": snapshot["criteria_version_number"],
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                    "correlation_id": str(evaluation_id),
                    "schema_version": 1,
                }
                conn.execute(
                    """INSERT INTO evaluations
                    (id, project_version_id, criteria_version_id, requested_by_user_id,
                     status, idempotency_key) VALUES (%s,%s,%s,%s,'queued',%s)""",
                    (evaluation_id, project_version_id, snapshot["criteria_version_id"], actor_id, idempotency_key),
                )
                conn.execute(
                    "INSERT INTO outbox_events (id,event_type,aggregate_id,payload) VALUES (%s,'EconomicEvaluationRequested',%s,%s)",
                    (event_id, evaluation_id, Jsonb(payload)),
                )
                conn.execute("UPDATE projects SET status='evaluating', updated_at=now() WHERE id=%s", (snapshot["project_id"],))
                conn.execute(
                    """INSERT INTO audit_events
                    (actor_user_id,action,entity_type,entity_id,details)
                    VALUES (%s,'EVALUATION_QUEUED','evaluation',%s,%s)""",
                    (actor_id, evaluation_id, Jsonb({"event_id": str(event_id)})),
                )

        publication_pending = False
        try:
            self.dispatcher.dispatch_economic(payload)
            with psycopg.connect(self.db_url) as conn:
                conn.execute(
                    "UPDATE outbox_events SET published_at=now(), publish_attempts=publish_attempts+1 WHERE id=%s",
                    (event_id,),
                )
        except Exception:
            publication_pending = True
            with psycopg.connect(self.db_url) as conn:
                conn.execute(
                    "UPDATE outbox_events SET publish_attempts=publish_attempts+1 WHERE id=%s",
                    (event_id,),
                )
        return {
            "evaluation_id": evaluation_id,
            "event_id": event_id,
            "status": "queued",
            "duplicated": False,
            "publication_pending": publication_pending,
        }

    def get_evaluation(self, evaluation_id: UUID) -> dict[str, Any]:
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            row = conn.execute(
                """
                SELECT e.id AS evaluation_id,e.project_version_id,e.criteria_version_id,e.status,
                       r.economic_assessment_id,r.cost_per_beneficiary_pen,r.score_0_100,
                       r.explanation,r.algorithm_version
                FROM evaluations e LEFT JOIN economic_result_projections r ON r.evaluation_id=e.id
                WHERE e.id=%s
                """,
                (evaluation_id,),
            ).fetchone()
        if not row:
            raise RecursoPMV1NoEncontradoError("Evaluacion no encontrada")
        result = None
        if row["economic_assessment_id"]:
            result = {
                "economic_assessment_id": row["economic_assessment_id"],
                "cost_per_beneficiary_pen": row["cost_per_beneficiary_pen"],
                "score_0_100": row["score_0_100"],
                "explanation": row["explanation"],
                "algorithm_version": row["algorithm_version"],
            }
        return {
            "evaluation_id": row["evaluation_id"],
            "project_version_id": row["project_version_id"],
            "criteria_version_id": row["criteria_version_id"],
            "status": row["status"],
            "result": result,
        }

    def record_legal_abstention(self, project_id: UUID, actor_id: UUID) -> None:
        self.get_project(project_id)
        with psycopg.connect(self.db_url) as conn:
            conn.execute(
                """INSERT INTO audit_events
                (actor_user_id,action,entity_type,entity_id,details)
                VALUES (%s,'LEGAL_PRECHECK_REQUIRES_REVIEW','project',%s,%s)""",
                (actor_id, project_id, Jsonb({"reason": "no_versioned_legal_corpus"})),
            )


class EconomicProcessor:
    """Consumidor propietario exclusivo de economic_db e idempotente por event_id."""

    def __init__(self, db_url: str) -> None:
        self.db_url = _dsn(db_url)

    @staticmethod
    def calculate(
        budget: Decimal,
        beneficiaries: int,
        excellent: Decimal,
        unacceptable: Decimal,
    ) -> tuple[Decimal, Decimal]:
        if budget <= 0 or beneficiaries <= 0 or not 0 < excellent < unacceptable:
            raise ValueError("Datos economicos o umbrales invalidos")
        exact_cost = budget / Decimal(beneficiaries)
        if exact_cost <= excellent:
            score = Decimal(100)
        elif exact_cost >= unacceptable:
            score = Decimal(0)
        else:
            score = Decimal(100) * (unacceptable - exact_cost) / (unacceptable - excellent)
        return (
            exact_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        )

    def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_id = UUID(payload["event_id"])
        evaluation_id = UUID(payload["evaluation_id"])
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            with conn.transaction():
                existing = conn.execute(
                    """SELECT ea.* FROM processed_requests pr
                    JOIN economic_assessments ea ON ea.id=pr.assessment_id
                    WHERE pr.event_id=%s OR pr.evaluation_id=%s""",
                    (event_id, evaluation_id),
                ).fetchone()
                if existing:
                    return self._completion(event_id, existing)

                budget = Decimal(payload["budget_pen"])
                beneficiaries = int(payload["beneficiaries_count"])
                excellent = Decimal(payload["excellent_cost_pen"])
                unacceptable = Decimal(payload["unacceptable_cost_pen"])
                cost, score = self.calculate(budget, beneficiaries, excellent, unacceptable)
                assessment_id = uuid4()
                explanation = (
                    f"Costo por beneficiario = S/ {budget} / {beneficiaries} = S/ {cost}. "
                    f"Umbrales: excelente S/ {excellent}, inaceptable S/ {unacceptable}; score {score}/100. "
                    "No representa retorno socioeconomico ni viabilidad oficial."
                )
                row = {
                    "id": assessment_id,
                    "evaluation_id": evaluation_id,
                    "cost_per_beneficiary_pen": cost,
                    "score_0_100": score,
                    "explanation": explanation,
                    "algorithm_version": "economic-cost-per-beneficiary-v1",
                }
                conn.execute(
                    """INSERT INTO economic_assessments
                    (id,evaluation_id,project_version_id,criteria_version_id,budget_snapshot_pen,
                     beneficiaries_snapshot,excellent_cost_snapshot_pen,unacceptable_cost_snapshot_pen,
                     cost_per_beneficiary_pen,score_0_100,explanation,algorithm_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (assessment_id,evaluation_id,UUID(payload["project_version_id"]),UUID(payload["criteria_version_id"]),
                     budget,beneficiaries,excellent,unacceptable,cost,score,explanation,row["algorithm_version"]),
                )
                conn.execute(
                    """INSERT INTO assessment_metrics (id,assessment_id,metric_code,numeric_value,unit,formula)
                    VALUES (%s,%s,'COST_PER_BENEFICIARY',%s,'PEN/person','budget / beneficiaries'),
                           (%s,%s,'ECONOMIC_SCORE',%s,'points','linear normalization between thresholds')""",
                    (uuid4(),assessment_id,cost,uuid4(),assessment_id,score),
                )
                conn.execute(
                    "INSERT INTO processed_requests (event_id,evaluation_id,assessment_id) VALUES (%s,%s,%s)",
                    (event_id,evaluation_id,assessment_id),
                )
        return self._completion(event_id, row)

    @staticmethod
    def _completion(request_event_id: UUID, row: dict[str, Any]) -> dict[str, Any]:
        return {
            # Estable para que un reintento no genere un segundo evento lógico.
            "event_id": str(uuid5(NAMESPACE_URL, f"siprim:economic-completed:{row['evaluation_id']}")),
            "request_event_id": str(request_event_id),
            "event_type": "EconomicEvaluationCompleted",
            "evaluation_id": str(row["evaluation_id"]),
            "economic_assessment_id": str(row["id"]),
            "cost_per_beneficiary_pen": str(row["cost_per_beneficiary_pen"]),
            "score_0_100": str(row["score_0_100"]),
            "explanation": row["explanation"],
            "algorithm_version": row["algorithm_version"],
            "schema_version": 1,
        }


class CompletionProcessor:
    """Proyecta el evento en platform_db, con inbox para tolerar reintentos."""

    def __init__(self, db_url: str) -> None:
        self.db_url = _dsn(db_url)

    def process(self, payload: dict[str, Any]) -> None:
        event_id, evaluation_id = UUID(payload["event_id"]), UUID(payload["evaluation_id"])
        with psycopg.connect(self.db_url) as conn:
            with conn.transaction():
                inserted = conn.execute(
                    "INSERT INTO inbox_events (event_id) VALUES (%s) ON CONFLICT DO NOTHING RETURNING event_id",
                    (event_id,),
                ).fetchone()
                if not inserted:
                    return
                conn.execute(
                    """INSERT INTO economic_result_projections
                    (evaluation_id,economic_assessment_id,cost_per_beneficiary_pen,score_0_100,
                     explanation,algorithm_version) VALUES (%s,%s,%s,%s,%s,%s)""",
                    (evaluation_id,UUID(payload["economic_assessment_id"]),Decimal(payload["cost_per_beneficiary_pen"]),
                     Decimal(payload["score_0_100"]),payload["explanation"],payload["algorithm_version"]),
                )
                conn.execute("UPDATE evaluations SET status='completed',finished_at=now() WHERE id=%s", (evaluation_id,))
                conn.execute(
                    """UPDATE projects SET status='evaluated',updated_at=now()
                    WHERE id=(SELECT pv.project_id FROM project_versions pv JOIN evaluations e
                              ON e.project_version_id=pv.id WHERE e.id=%s)""",
                    (evaluation_id,),
                )
                conn.execute(
                    """INSERT INTO audit_events (action,entity_type,entity_id,details)
                    VALUES ('EVALUATION_COMPLETED','evaluation',%s,%s)""",
                    (evaluation_id,Jsonb({"event_id": str(event_id), "assessment_id": payload["economic_assessment_id"]})),
                )


class EvaluationStartedProcessor:
    def __init__(self, db_url: str) -> None:
        self.db_url = _dsn(db_url)

    def process(self, evaluation_id: str) -> None:
        with psycopg.connect(self.db_url) as conn:
            conn.execute(
                """UPDATE evaluations SET status='processing', started_at=COALESCE(started_at,now())
                WHERE id=%s AND status='queued'""",
                (UUID(evaluation_id),),
            )


class OutboxPublisher:
    """Recupera publicaciones que fallaron tras confirmar la transaccion local."""

    def __init__(self, db_url: str, dispatcher: TaskDispatcher) -> None:
        self.db_url = _dsn(db_url)
        self.dispatcher = dispatcher

    def publish_pending(self, limit: int = 50) -> int:
        published = 0
        with psycopg.connect(self.db_url, row_factory=dict_row) as conn:
            rows = conn.execute(
                """SELECT id,payload FROM outbox_events WHERE published_at IS NULL
                ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT %s""",
                (limit,),
            ).fetchall()
            for row in rows:
                try:
                    self.dispatcher.dispatch_economic(row["payload"])
                    conn.execute(
                        "UPDATE outbox_events SET published_at=now(),publish_attempts=publish_attempts+1 WHERE id=%s",
                        (row["id"],),
                    )
                    published += 1
                except Exception:
                    conn.execute(
                        "UPDATE outbox_events SET publish_attempts=publish_attempts+1 WHERE id=%s",
                        (row["id"],),
                    )
        return published
